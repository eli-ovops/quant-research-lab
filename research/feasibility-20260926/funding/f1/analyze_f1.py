"""F1 post-result correction; original sealed B-v1 remains untouched.
Offline conditional OHLC carry diagnostics, NOT executable strategy backtest.
No predicted or realized rate affects entry/exit/size. Only predetermined dates.
"""
from pathlib import Path
from decimal import Decimal as D, ROUND_FLOOR, ROUND_CEILING, getcontext
from collections import Counter
import json, csv, hashlib, datetime, sys, platform
getcontext().prec=40
P=Path(__file__).resolve().parent; ROOT=P.parent; RAW=ROOT/'raw'
HOUR=3600000; DAY=24*HOUR; ZERO=D(0); TOTAL=D(2000)
def stamp(x):return int(datetime.datetime.fromisoformat(x).replace(tzinfo=datetime.timezone.utc).timestamp()*1000)
def iso(t):return datetime.datetime.fromtimestamp(t/1000,datetime.timezone.utc).isoformat()
BLOCKS=[('2026-06-28','2026-07-28','development'),('2026-07-28','2026-08-27','validation'),('2026-08-27','2026-09-26','sealed')]
def encode(x):
    if isinstance(x,D):return str(x)
    raise TypeError(type(x).__name__)
def save(name,x): (P/name).write_text(json.dumps(x,default=encode,ensure_ascii=False,indent=2)+'\n')
def read(name):
    obj=json.loads((RAW/(name+'.txt')).read_text());assert obj['code']=='0',name
    return obj['data']
def csvsave(name,rows):
    if not rows:return
    with (P/name).open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
def round_down(v,step):return (v/step).to_integral_value(rounding=ROUND_FLOOR)*step
def round_up(v,step):return (v/step).to_integral_value(rounding=ROUND_CEILING)*step
def positive_price(value):
    try:
        price=D(value)
        return price if price.is_finite() and price>0 else None
    except (TypeError,ValueError,ArithmeticError):return None
def spot_exit(inventory,spec,fee,price=None,levels=None):
    """Atomic modeled taker sale, not actual fills. A reject retains ALL inventory.
    Decimal quantities; no automatic splitting/retry/dust monetization.
    Level size is spot base quantity. Partial available depth rejects modeled fill.
    """
    lot=D(spec['lotSz']);candidate=round_down(inventory,lot)
    result={'candidate_sell_base':candidate,'sold_base':ZERO,'remaining_base':inventory,
            'execution_price':None,'gross_proceeds':ZERO,'sell_fee':ZERO,'cash_proceeds':ZERO,
            'remaining_realizable_value':ZERO,'sell_filled':False,'fully_flat':inventory==0,
            'reason':'NOT_ATTEMPTED','depth_unfilled_base':ZERO}
    if candidate<=0:result['reason']='NO_VALID_LOT';return result
    if candidate<D(spec['minSz']):result['reason']='BELOW_MIN_SZ';return result
    if candidate>D(spec['maxMktSz']):result['reason']='ABOVE_MAX_SZ';return result
    if levels is not None:
        price,unfilled=book_vwap(levels,candidate)
        result['depth_unfilled_base']=unfilled
        if unfilled>0:result['reason']='INSUFFICIENT_OR_INVALID_DEPTH';return result
    price=positive_price(price)
    if price is None:result['reason']='NO_VALID_QUOTE';return result
    if spec.get('maxMktAmt') and candidate*price>D(spec['maxMktAmt']):
        result['reason']='ABOVE_MAX_AMOUNT';return result
    proceeds=candidate*price;charge=proceeds*fee;remaining=inventory-candidate
    assert remaining>=0 and remaining<lot
    result.update(sold_base=candidate,remaining_base=remaining,execution_price=price,
                  gross_proceeds=proceeds,sell_fee=charge,cash_proceeds=proceeds-charge,
                  sell_filled=True,fully_flat=remaining==0,
                  reason='FILLED_WITH_RETAINED_DUST' if remaining else 'FILLED')
    return result
def identity(c):
    s=read(c+'_spot_spec')[0];f=read(c+'_swap_spec')[0]
    assert s['instType']=='SPOT' and s['baseCcy']==c and s['quoteCcy']=='USDT' and s['state']=='live'
    assert f['instType']=='SWAP' and f['ctType']=='linear' and f['ctValCcy']==c and f['settleCcy']=='USDT' and f['state']=='live' and f['ruleType']=='normal'
    assert f['instId']==c+'-USDT-SWAP' and not f['expTime']
    return s,f
def candle_series(c,kind):
    result={};duplicates=0;raw_descending=True
    paths=sorted(RAW.glob(c+'_'+kind+'_1H_*.txt'))
    for path in paths:
        obj=json.loads(path.read_text());assert obj['code']=='0'
        times=[int(r[0]) for r in obj['data']]
        raw_descending &= all(a>b for a,b in zip(times,times[1:]))
        for r in obj['data']:
            t=int(r[0]);v={'o':D(r[1]),'h':D(r[2]),'l':D(r[3]),'c':D(r[4]),'confirm':r[-1]}
            assert t%HOUR==0 and 0<v['l']<=min(v['o'],v['c'])<=max(v['o'],v['c'])<=v['h']
            if t in result:assert result[t]==v;duplicates+=1
            result[t]=v
    return result,{'files':len(paths),'rows':len(result),'duplicates':duplicates,'descending_pages':raw_descending,'first':iso(min(result)),'last':iso(max(result))}
def rates(c):
    result={};duplicates=0;descending=True
    paths=[p for p in RAW.glob(c+'_funding_*.txt') if p.stem.split('_')[-1].isdigit()]
    for path in paths:
        obj=json.loads(path.read_text());assert obj['code']=='0'
        times=[int(r['fundingTime']) for r in obj['data']]
        descending &= all(a>b for a,b in zip(times,times[1:]))
        for row in obj['data']:
            assert row['instId']==c+'-USDT-SWAP' and row['instType']=='SWAP' and row['realizedRate']!=''
            t=int(row['fundingTime'])
            if t in result:assert row==result[t];duplicates+=1
            result[t]=row
    return result,{'rows':len(result),'duplicates':duplicates,'descending_pages':descending,'first':iso(min(result)),'last':iso(max(result)),'older_probe_rows':len(read(c+'_funding_older_probe'))}
def prepare(c):
    spot_spec,swap_spec=identity(c)
    series={};audit={}
    for kind in ['spot','swap','mark']:series[kind],audit[kind]=candle_series(c,kind)
    series['funding'],audit['funding']=rates(c)
    series.update(spot_spec=spot_spec,swap_spec=swap_spec,mmr=D(read(c+'_tiers')[0]['mmr']))
    return series,audit
def size(spot_price,spec,future,fee):
    unit=D(future['ctVal'])*D(future['ctMult']);lot=D(future['lotSz']);step=D(spec['lotSz'])
    contracts=round_down(D(800)*(1-fee)/spot_price/unit,lot)
    while contracts>0:
        q=contracts*unit;gross=round_up(q/(1-fee),step)
        if gross*spot_price<=800:break
        contracts-=lot
    assert contracts>=D(future['minSz']) and gross>=D(spec['minSz'])
    assert contracts<=D(future['maxMktSz']) and gross<=D(spec['maxMktSz'])
    # Current instrument template, historical changes remain unknown.
    net=gross*(1-fee);assert net>=q and net-q<step
    return contracts,q,gross,net
def fund_event(q,row,mark):
    rate=D(row['realizedRate']);nominal=q*mark['o']
    low,high=sorted([q*mark['l']*rate,q*mark['h']*rate])
    return nominal*rate,low,high
def replay(c,data,start,end,label,fee_mult=1,bps=5,mode='open'):
    t0=stamp(start)+(HOUR if mode=='delay_1h' else 0);t1=stamp(end)+(HOUR if mode=='delay_1h' else 0)
    needed=range(t0,t1+HOUR,HOUR)
    for kind in ['spot','swap','mark']:
        assert all(t in data[kind] and data[kind][t]['confirm']=='1' for t in needed),(c,kind,start,'missing/unconfirmed')
    funding=data['funding'];ftimes=sorted(t for t in funding if t0<=t<=t1)
    # Observed timestamp intervals, not an assumed 3 payments/day.
    assert ftimes and min(funding)<=t0 and max(funding)>=t1-HOUR*8
    gaps=[(b-a)/HOUR for a,b in zip(ftimes,ftimes[1:])]
    assert all(g in [1,2,4,6,8] for g in gaps),(c,start,'unexplained funding gap')
    a=D('.001')*fee_mult;b=D('.0005')*fee_mult;s=D(bps)/10000
    so=data['spot'][t0]['o'];se=data['spot'][t1]['o'];fo=data['swap'][t0]['o'];fe=data['swap'][t1]['o']
    if mode=='adverse_hour':
        so=data['spot'][t0]['h'];fo=data['swap'][t0]['l'];se=data['spot'][t1]['l'];fe=data['swap'][t1]['h']
    sbuy=so*(1+s);fsell=fo*(1-s);ssell=se*(1-s);fbuy=fe*(1+s)
    contracts,q,gross,net=size(sbuy,data['spot_spec'],data['swap_spec'],a)
    buycost=gross*sbuy;openfee=q*fsell*b;exitfee=q*fbuy*b
    exit_order=spot_exit(net,data['spot_spec'],a,price=ssell)
    sold=exit_order['sold_base'];remaining=exit_order['remaining_base']
    spot_entryfee=(gross-net)*sbuy;spot_exitfee=exit_order['sell_fee']
    entry_slip=net*(sbuy-so)+q*(fo-fsell);exit_slip=sold*(se-ssell)+q*(fbuy-fe)
    # Net inventory is marked in reference PnL; retained units have zero realizable value.
    inventory_writeoff=remaining*se
    fees=spot_entryfee+spot_exitfee+openfee+exitfee;slips=entry_slip+exit_slip
    price=net*(se-so)+q*(fo-fe)
    funding_sum=ZERO;flo=ZERO;fhi=ZERO;boundlo=ZERO;boundhi=ZERO;events=[]
    negative=0;neg_run=0;max_neg_run=0;max_neg_hours=0;run_start=None
    cum=ZERO;first_funding_recovery=None;reversal_before_recovery=False;prev_rate=None
    cost_target=fees+slips+inventory_writeoff
    for t in ftimes:
        r=funding[t];point,low,high=fund_event(q,r,data['mark'][t]);edge=t in [t0,t1]
        if edge:
            boundlo+=min(ZERO,low);boundhi+=max(ZERO,high)
        else:
            funding_sum+=point;flo+=low;fhi+=high;cum+=point
            rate=D(r['realizedRate'])
            if rate<0:
                negative+=1;neg_run+=1
                if run_start is None:run_start=t
                max_neg_run=max(max_neg_run,neg_run);max_neg_hours=max(max_neg_hours,(t-run_start)/HOUR)
                if prev_rate is not None and prev_rate>=0 and first_funding_recovery is None:reversal_before_recovery=True
            else:neg_run=0;run_start=None
            if first_funding_recovery is None and cum>=cost_target:first_funding_recovery=(t-t0)/DAY
            prev_rate=rate
        events.append({'coin':c,'block':start,'split':label,'time':iso(t),'ts':t,'boundary_unknown':edge,'contracts':contracts,'base_quantity':q,'realized_rate':r['realizedRate'],'historical_prediction_not_signal':r.get('fundingRate',''),'formulaType':r.get('formulaType',''),'method':r.get('method',''),'mark_open_proxy':data['mark'][t]['o'],'variable_notional':q*data['mark'][t]['o'],'funding_proxy':point,'funding_ohlc_low':low,'funding_ohlc_high':high})
    low_total=flo+boundlo;high_total=fhi+boundhi
    netpnl=price+funding_sum-fees-slips-inventory_writeoff
    # Independent CASH flow sum, not a restatement of the spread decomposition.
    free=TOTAL-D(800)-buycost
    collateral_end=D(800)-openfee+q*(fsell-fbuy)+funding_sum-exitfee
    cash_end=free+exit_order['cash_proceeds']+collateral_end
    identity_error=cash_end-TOTAL-netpnl
    assert abs(identity_error)<D('1e-30'),identity_error
    assert free>=400 and D(800)-openfee>=q*fsell*D(read(c+'_tiers')[0]['imr'])
    mmr=data['mmr'];running=ZERO;running_low=ZERO;minimum_buffer=None;liquidation_flag=False
    peak=TOTAL;dd=ZERO;peak_time=t0;worst_recovery_hours=0;underwater_since=None;last_equity=TOTAL;worst_hour=ZERO;daily={};curve=[];first_net_recovery=None
    ev={r['ts']:r for r in events}
    # At entry/exit settlement boundaries, worst case includes negative payment but cannot count positive receipt.
    for t in needed:
        e=ev.get(t)
        added=ZERO;low_added=ZERO
        if e:
            added=ZERO if e['boundary_unknown'] else e['funding_proxy']
            low_added=min(ZERO,e['funding_ohlc_low']) if e['boundary_unknown'] else e['funding_ohlc_low']
        mark=data['mark'][t];sp=data['spot'][t];sw=data['swap'][t]
        # Conservative hourly high before positive funding credit; negative credit before high.
        worst_cash=D(800)-openfee+running_low+min(ZERO,low_added)
        buffer=worst_cash+q*(fsell-mark['h'])-q*mark['h']*(mmr+b)
        minimum_buffer=buffer if minimum_buffer is None else min(minimum_buffer,buffer)
        liquidation_flag |= buffer<=0
        running+=added;running_low+=low_added
        # Exit-valued curve uses hourly closes, not guaranteed fills; includes all fees.
        hypothetical_exit=spot_exit(net,data['spot_spec'],a,price=sp['c']*(1-s))
        eq=free+hypothetical_exit['cash_proceeds']+D(800)-openfee+q*(fsell-sw['c']*(1+s))+running-q*sw['c']*(1+s)*b
        if t==t1:
            eq=cash_end;hypothetical_exit=exit_order
        worst_hour=min(worst_hour,eq-last_equity);last_equity=eq
        if eq>=peak:
            if underwater_since is not None:worst_recovery_hours=max(worst_recovery_hours,(t-underwater_since)/HOUR)
            peak=eq;peak_time=t;underwater_since=None
        else:
            if underwater_since is None:underwater_since=peak_time
            dd=max(dd,peak-eq)
        if first_net_recovery is None and eq>=TOTAL:first_net_recovery=(t-t0)/DAY
        daily[t//DAY]=eq
        curve.append({'coin':c,'block':start,'split':label,'fee_multiplier':fee_mult,'slippage_bps_per_leg_side':bps,'execution_mode':mode,'time':iso(t),'equity_proxy':eq,'cumulative_funding_proxy':running,'isolated_margin_buffer_stress':buffer,'inventory_before_sale':net,'hypothetical_sold_base':hypothetical_exit['sold_base'],'retained_base':hypothetical_exit['remaining_base'],'retained_realizable_value':ZERO,'spot_sale_cash':hypothetical_exit['cash_proceeds'],'spot_sale_fee':hypothetical_exit['sell_fee'],'spot_exit_status':hypothetical_exit['reason'],'actual_inventory_action':'No intermediate order; terminal row is hypothetical model exit only'})
    daily_changes=[];previous=TOTAL
    for day,equity in sorted(daily.items()):daily_changes.append(equity-previous);previous=equity
    unresolved_recovery=(t1-underwater_since)/HOUR if underwater_since is not None else None
    positives=sorted([e['funding_proxy'] for e in events if not e['boundary_unknown'] and e['funding_proxy']>0],reverse=True)
    positive_total=sum(positives,ZERO)
    stresses={}
    for up in [D('.25'),D('.5'),D('1')]:
        m=fo*(1+up);stresses[str(up)]=D(800)-openfee+q*(fsell-m)-q*m*(mmr+b)
    held_spot=exit_order['cash_proceeds']-buycost
    result={'coin':c,'split':label,'start':start,'end':end,'fee_multiplier':fee_mult,'slippage_bps_per_leg_side':bps,'execution_mode':mode,'evidence_kind':'conditional_OHLC_diagnostic_not_execution','capital':TOTAL,'contracts':contracts,'hedged_base':q,'gross_spot_base':gross,'net_spot_base':net,'residual_base':net-q,'spot_cash_used':buycost,'initial_margin':D(800),'free_cash':free,'spot_reference_pnl':net*(se-so),'swap_reference_pnl':q*(fo-fe),'price_pnl':price,'funding_proxy':funding_sum,'funding_low_with_boundary':low_total,'funding_high_with_boundary':high_total,'spot_buy_fee_usdt_equivalent':spot_entryfee,'spot_sell_fee':spot_exitfee,'swap_open_fee':openfee,'swap_close_fee':exitfee,'fees':fees,'slippage':slips,'net_pnl_proxy':netpnl,'net_pnl_low_mark_boundary_only':price+low_total-fees-slips-inventory_writeoff,'net_pnl_high_mark_boundary_only':price+high_total-fees-slips-inventory_writeoff,'return_on_2000_proxy':netpnl/TOTAL,'cash_end':cash_end,'identity_error':identity_error,'funding_events_interior':len([e for e in events if not e['boundary_unknown']]),'boundary_events_unknown':len([e for e in events if e['boundary_unknown']]),'negative_events':negative,'max_negative_run_events':max_neg_run,'max_negative_run_span_hours':max_neg_hours,'funding_cost_recovery_days_ex_post_target':first_funding_recovery,'fee_reversal_before_funding_recovery':reversal_before_recovery,'net_cost_recovery_days_hourly_proxy':first_net_recovery,'funding_covers_total_cost_at_exit':funding_sum>=cost_target,'top5_share_positive_funding':sum(positives[:5],ZERO)/positive_total if positive_total else None,'drawdown_usdt_hourly_proxy':dd,'drawdown_on_2000_proxy':dd/TOTAL,'max_completed_recovery_hours':worst_recovery_hours,'unrecovered_hours_at_exit':unresolved_recovery,'worst_hour_proxy':worst_hour,'worst_daily_change_proxy':min(daily_changes),'isolated_margin_min_buffer_current_mmr_stress':minimum_buffer,'liquidation_unresolved':liquidation_flag,'instant_price_rise_margin_buffers':stresses,'cash_benchmark_nominal_pnl':ZERO,'spot_hold_same_cash_allocation_pnl_proxy':held_spot,'spot_hold_risk_comparability':'Different directional exposure; not risk-adjusted benchmark','actual_trades':0}
    result.update(version='B-v1-F1', correction_after_original_results=True, spot_exit_order=exit_order, sold_spot_base=sold, remaining_spot_base=remaining, remaining_spot_realizable_value=ZERO, inventory_zero_value_charge=inventory_writeoff, spot_order_filled=exit_order['sell_filled'], all_inventory_flat=exit_order['fully_flat'], remaining_directional_exposure_base=remaining, swap_position_remaining=ZERO, spot_hold_remaining_base=remaining, spot_hold_remaining_realizable_value=ZERO, cost_recovery_includes_zero_valued_inventory_charge=True)
    return result,events,curve
def book_vwap(levels,quantity,unit= D(1)):
    rem=quantity;value=ZERO
    if quantity<=0 or unit<=0:return None,quantity
    for row in levels:
        try:
            px=positive_price(row[0]);avail=D(row[1])*unit
            if px is None or not avail.is_finite() or avail<0:return None,quantity
        except (IndexError,TypeError,ValueError,ArithmeticError):return None,quantity
        take=min(rem,avail);value+=take*px;rem-=take
        if rem==0:break
    return (value/quantity if rem==0 else None),rem
def current_snapshot(c):
    sp,fp=identity(c);sb=read(c+'_spot_book')[0];fb=read(c+'_swap_book')[0]
    now=read(c+'_funding_current')[0];sources=json.loads((ROOT/'sources.json').read_text())
    sr=next(x for x in sources if x['name']==c+'_spot_book');fr=next(x for x in sources if x['name']==c+'_swap_book')
    unit=D(fp['ctVal'])*D(fp['ctMult']);n,q,gross,net=size(D(sb['asks'][0][0]),sp,fp,D('.001'))
    spot_buy,_=book_vwap(sb['asks'],gross);fut_sell,_=book_vwap(fb['bids'],q,unit)
    exit_order=spot_exit(net,sp,D('.001'),levels=sb['bids']);spot_sell=exit_order['execution_price']
    fut_buy,_=book_vwap(fb['asks'],q,unit)
    assert all(x is not None for x in [spot_buy,fut_sell,fut_buy])
    immediate= -gross*spot_buy +exit_order['cash_proceeds']+q*(fut_sell-fut_buy)-q*(fut_sell+fut_buy)*D('.0005')
    return {'coin':c,'contracts':n,'hedged_base':q,'spot_ask_vwap':spot_buy,'swap_bid_vwap':fut_sell,'spot_bid_vwap':spot_sell,'swap_ask_vwap':fut_buy,'instant_roundtrip_cost_snapshot':-immediate if exit_order['sell_filled'] else None,'cash_change_with_retained_inventory_valued_zero':immediate,'roundtrip_status':'TRADABLE_SIZE_SOLD_DUST_RETAINED' if exit_order['sell_filled'] else 'SPOT_EXIT_REJECTED_POSITION_RETAINED','funding_current_prediction':now['fundingRate'],'nextFundingRate':now.get('nextFundingRate'),'last_settled_rate':now['settFundingRate'],'next_assessment_timestamp':now['fundingTime'],'prediction_time':now['ts'],'book_pair_skew_ms':abs(int(sb['ts'])-int(fb['ts'])),'spot_receipt_minus_book_ms':sr['received_ms']-int(sb['ts']),'swap_receipt_minus_book_ms':fr['received_ms']-int(fb['ts']),'spot_rtt_ms':sr['elapsed_ms'],'swap_rtt_ms':fr['elapsed_ms'],'spot_exit_order':exit_order,'sold_spot_base':exit_order['sold_base'],'remaining_spot_base':exit_order['remaining_base'],'remaining_spot_realizable_value':ZERO,'all_inventory_flat':exit_order['fully_flat'],'capacity_at_snapshot':exit_order['sell_filled'],'executable_opportunity':False,'reason':'Sequential snapshot, unverified account/timing/future carry; no historical cost inference.'}
def main():
    phase=sys.argv[1] if len(sys.argv)>1 else 'preseal';assert phase in ['preseal','all']
    if phase=='all':
        seal=json.loads((ROOT/'seal.json').read_text());assert seal['analysis_sha256']==hashlib.sha256((ROOT/'analyze.py').read_bytes()).hexdigest()
    p_hash=hashlib.sha256((ROOT/'protocol.json').read_bytes()).hexdigest();assert p_hash==(ROOT/'protocol.sha256').read_text().split()[0]
    src=json.loads((ROOT/'sources.json').read_text());hashchecks=0
    for x in src:
        if 'path' in x:assert hashlib.sha256(Path(x['path']).read_bytes()).hexdigest()==x['sha256'];hashchecks+=1
    audits={};out=[];events=[];curves=[];stress=[];failures=[];ratesummary=[]
    for c in ['BTC','ETH']:
        data,audits[c]=prepare(c)
        for start,end,label in BLOCKS:
            if phase=='preseal' and label=='sealed':continue
            for fm in [1,2]:
                for bp in [5,20,50]:
                    for mode in ['open','delay_1h','adverse_hour']:
                        try:r,e,curve=replay(c,data,start,end,label,fm,bp,mode)
                        except (AssertionError,KeyError) as err:
                            failures.append({'coin':c,'start':start,'fee':fm,'bps':bp,'mode':mode,'error':str(err)});continue
                        out.append(r)
                        curves.extend(curve)
                        if fm==1 and bp==5 and mode=='open':events.extend(e)
                        for overhead in [0,5,20]:
                            for apr in [D(0),D('.02'),D('.05')]:
                                cost=TOTAL*apr*D(30)/365
                                stress.append({'coin':c,'start':start,'split':label,'fee_multiplier':fm,'slippage_bps':bp,'mode':mode,'operating_cost_30d':overhead,'cash_opportunity_apr':apr,'opportunity_cost_30d':cost,'net_after_costs_proxy':r['net_pnl_proxy']-overhead-cost})
        cutoff=stamp('2026-08-27') if phase=='preseal' else stamp('2026-09-26')
        rr=[(t,x) for t,x in sorted(data['funding'].items()) if stamp('2026-06-28')<=t<cutoff]
        gaps=Counter(str((b[0]-a[0])/HOUR) for a,b in zip(rr,rr[1:]))
        ratesummary.append({'coin':c,'first':iso(rr[0][0]),'last':iso(rr[-1][0]),'observations_not_independent_trades':len(rr),'negative':sum(D(x['realizedRate'])<0 for t,x in rr),'zero':sum(D(x['realizedRate'])==0 for t,x in rr),'sum_realized_rates_not_return':sum((D(x['realizedRate']) for t,x in rr),ZERO),'interval_hours':dict(gaps),'formulaType':dict(Counter(x['formulaType'] for t,x in rr)),'method':dict(Counter(x['method'] for t,x in rr)),'prediction_equals_realized_count':sum(x.get('fundingRate')==x['realizedRate'] for t,x in rr),'point_in_time_prediction_archive':False})
    primary=[r for r in out if r['fee_multiplier']==1 and r['slippage_bps_per_leg_side']==5 and r['execution_mode']=='open']
    result={'version':'B-v1-F1','post_result_correction':True,'original_seal_unchanged':True,'fresh_holdout':False,'phase':phase,'python':platform.python_version(),'protocol_sha256':p_hash,'analysis_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'raw_hash_checks':hashchecks,'data_audit':audits,'rate_summary':ratesummary,'primary':primary,'scenarios':len(out),'failed_scenarios':failures,'verdict':'INSUFFICIENT_EVIDENCE','heldout_executable_trades':0,'actual_orders':0,'statistical_interval':'NOT_ESTIMABLE_RELIABLY: at most 3 nonoverlapping highly correlated calendar blocks, only 1 sealed block; no block bootstrap claim','current_snapshots':[current_snapshot(c) for c in ['BTC','ETH']]}
    save('results_'+phase+'.json',result)
    save('scenarios_'+phase+'.json',out)
    csvsave('funding_events_'+phase+'.csv',events);csvsave('equity_curves_'+phase+'.csv',curves);csvsave('overheads_'+phase+'.csv',stress)
    print(json.dumps({'phase':phase,'scenarios':len(out),'failed':len(failures),'hash_checks':hashchecks,'rate_summary':ratesummary,'primary':[ {k:r[k] for k in ['coin','start','split','net_pnl_proxy','funding_proxy','price_pnl','fees','slippage','net_pnl_low_mark_boundary_only','net_pnl_high_mark_boundary_only','isolated_margin_min_buffer_current_mmr_stress','funding_cost_recovery_days_ex_post_target','drawdown_usdt_hourly_proxy']} for r in primary]},default=encode,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
