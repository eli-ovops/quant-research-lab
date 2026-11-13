"""Independent F1 raw-data validator: no strategy import, no output quantity inputs.
Rebuild all entry sizes, sales, dust, funding/cash, hourly valuations and metrics.
"""
from pathlib import Path
from decimal import Decimal as D, ROUND_FLOOR, ROUND_CEILING, getcontext
from collections import defaultdict
import json,csv,datetime,hashlib,itertools
getcontext().prec=40
P=Path(__file__).resolve().parent;ROOT=P.parent;RAW=ROOT/'raw'
H=3600000;DAY=24*H;Z=D(0)
def stamp(s):return int(datetime.datetime.fromisoformat(s).replace(tzinfo=datetime.timezone.utc).timestamp()*1000)
def key(r):return (r['coin'],r.get('start',r.get('block')),int(r['fee_multiplier']),int(r['slippage_bps_per_leg_side']),r['execution_mode'])
def load(name):return json.loads((RAW/(name+'.txt')).read_text())['data']
def files(pattern,index):
    out={}
    for path in RAW.glob(pattern):
        if 'funding' in pattern and not path.stem.rsplit('_',1)[-1].isdigit():continue
        for row in json.loads(path.read_text())['data']:out[int(row[index])]=row
    return out
def emit(name,obj):
    (P/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2,default=str)+'\n')
def equal(actual,expected):
    assert abs(D(actual)-expected)<D('1e-28'),(actual,expected)
def sale(inventory,lot,minimum,maximum,px,fee,maxamount=None):
    number=(inventory/lot).to_integral_value(rounding=ROUND_FLOOR)*lot
    valid=number>0 and number>=minimum and number<=maximum and px.is_finite() and px>0
    if maxamount and number*px>D(maxamount):valid=False
    sold=number if valid else Z
    return sold,inventory-sold,sold*px*(1-fee) if valid else Z,sold*px*fee if valid else Z
def path_metrics(points,start):
    peak=D(2000);peak_time=start;under=None;dd=Z;recovery=0;first=None;last=D(2000);worst_hour=Z;daily={}
    for t,eq in points:
        worst_hour=min(worst_hour,eq-last);last=eq
        if eq>=peak:
            if under is not None:recovery=max(recovery,(t-under)/H)
            peak=eq;peak_time=t;under=None
        else:
            if under is None:under=peak_time
            dd=max(dd,peak-eq)
        if first is None and eq>=2000:first=(t-start)/DAY
        daily[t//DAY]=eq
    changes=[];previous=D(2000)
    for t,eq in sorted(daily.items()):changes.append(eq-previous);previous=eq
    return {'drawdown_usdt_hourly_proxy':dd,'drawdown_on_2000_proxy':dd/2000,'max_completed_recovery_hours':recovery,'unrecovered_hours_at_exit':(points[-1][0]-under)/H if under is not None else None,'net_cost_recovery_days_hourly_proxy':first,'worst_hour_proxy':worst_hour,'worst_daily_change_proxy':min(changes)}
def vwap(levels,amount,mult=D(1)):
    remain=amount;cost=Z
    for level in levels:
        take=min(remain,D(level[1])*mult);cost+=take*D(level[0]);remain-=take
        if not remain:break
    assert remain==0
    return cost/amount
def main():
    baseline=json.loads((P/'change_ledger.json').read_text())['original_files']
    for rec in baseline:assert hashlib.sha256((ROOT/rec['path']).read_bytes()).hexdigest()==rec['sha256'],rec['path']
    original={key(r):r for r in json.loads((ROOT/'scenarios_all.json').read_text())}
    corrected={key(r):r for r in json.loads((P/'scenarios_all.json').read_text())}
    expected=set(itertools.product(['BTC','ETH'],['2026-06-28','2026-07-28','2026-08-27'],[1,2],[5,20,50],['open','delay_1h','adverse_hour']))
    assert set(original)==set(corrected)==expected
    curves=defaultdict(dict)
    with (P/'equity_curves_all.csv').open() as f:
        for row in csv.DictReader(f):
            k=key(row);ts=stamp(row['time']);assert ts not in curves[k];curves[k][ts]=row
    details=[];checks=0;max_error=Z;changes=[]
    for c in ['BTC','ETH']:
        sp=load(c+'_spot_spec')[0];fp=load(c+'_swap_spec')[0]
        lot=D(sp['lotSz']);minimum=D(sp['minSz']);maximum=D(sp['maxMktSz']);amountmax=sp.get('maxMktAmt')
        unit=D(fp['ctVal'])*D(fp['ctMult']);clot=D(fp['lotSz'])
        ss=files(c+'_spot_1H_*.txt',0);ff=files(c+'_swap_1H_*.txt',0);mm=files(c+'_mark_1H_*.txt',0);fr=files(c+'_funding_*.txt','fundingTime')
        for k in sorted(x for x in corrected if x[0]==c):
            r=corrected[k];old=original[k];fee=D('.001')*k[2];futurefee=D('.0005')*k[2];sl=D(k[3])/10000
            delay=H if k[4]=='delay_1h' else 0;t0=stamp(r['start'])+delay;t1=stamp(r['end'])+delay
            s0,s1,f0,f1=map(D,[ss[t0][1],ss[t1][1],ff[t0][1],ff[t1][1]])
            if k[4]=='adverse_hour':s0,s1,f0,f1=map(D,[ss[t0][2],ss[t1][3],ff[t0][3],ff[t1][2]])
            # Derive size from raw specs and price; never start from emitted quantity.
            contracts=(D(800)*(1-fee)/(s0*(1+sl)*unit)/clot).to_integral_value(rounding=ROUND_FLOOR)*clot
            while True:
                q=contracts*unit;gross=(q/(1-fee)/lot).to_integral_value(rounding=ROUND_CEILING)*lot
                if gross*s0*(1+sl)<=800:break
                contracts-=clot
            net=gross*(1-fee)
            for field,number in [('contracts',contracts),('hedged_base',q),('gross_spot_base',gross),('net_spot_base',net)]:equal(r[field],number);equal(old[field],number)
            sold,remain,proceeds,sellfee=sale(net,lot,minimum,maximum,s1*(1-sl),fee,amountmax)
            for field,number in [('sold_spot_base',sold),('remaining_spot_base',remain),('remaining_spot_realizable_value',Z),('spot_sell_fee',sellfee)]:equal(r[field],number)
            assert sold%lot==0 and net==sold+remain and not r['all_inventory_flat']
            assert r['spot_order_filled']==(sold>0) and D(r['spot_exit_order']['cash_proceeds'])==proceeds
            buy=gross*s0*(1+sl);openfee=q*f0*(1-sl)*futurefee;closefee=q*f1*(1+sl)*futurefee
            fund=sum((q*D(mm[t][1])*D(row['realizedRate']) for t,row in fr.items() if t0<t<t1),Z)
            free=D(1200)-buy;terminal=free+proceeds+D(800)-openfee+q*(f0*(1-sl)-f1*(1+sl))+fund-closefee
            equal(r['cash_end'],terminal);equal(r['net_pnl_proxy'],terminal-2000);equal(r['funding_proxy'],fund)
            equal(r['spot_hold_same_cash_allocation_pnl_proxy'],proceeds-buy)
            equal(r['spot_hold_remaining_base'],remain);equal(r['spot_hold_remaining_realizable_value'],Z)
            delta=terminal-2000-D(old['net_pnl_proxy'])
            expected_delta=-remain*s1*(1-sl)*(1-fee)
            equal(delta,expected_delta)
            for bound in ['net_pnl_low_mark_boundary_only','net_pnl_high_mark_boundary_only']:equal(D(r[bound])-D(old[bound]),delta)
            points=[];oldpoints=[];cum=Z;max_eq_diff=Z
            assert len(curves[k])==721
            for t in range(t0,t1+H,H):
                if t0<t<t1 and t in fr:cum+=q*D(mm[t][1])*D(fr[t]['realizedRate'])
                hs,hr,hcash,hfee=sale(net,lot,minimum,maximum,D(ss[t][4])*(1-sl),fee,amountmax)
                collateral=D(800)-openfee+q*(f0*(1-sl)-D(ff[t][4])*(1+sl))+cum-q*D(ff[t][4])*(1+sl)*futurefee
                eq=free+hcash+collateral;oldeq=free+net*D(ss[t][4])*(1-sl)*(1-fee)+collateral
                if t==t1:eq=terminal;oldeq=D(2000)+D(old['net_pnl_proxy']);hs,hr,hcash,hfee=sold,remain,proceeds,sellfee
                row=curves[k][t]
                for field,num in [('equity_proxy',eq),('inventory_before_sale',net),('hypothetical_sold_base',hs),('retained_base',hr),('retained_realizable_value',Z),('spot_sale_cash',hcash),('spot_sale_fee',hfee),('cumulative_funding_proxy',cum)]:equal(row[field],num)
                assert net==hs+hr and hs%lot==0
                points.append((t,eq));oldpoints.append((t,oldeq));checks+=1
                max_error=max(max_error,abs(D(row['equity_proxy'])-eq));max_eq_diff=max(max_eq_diff,abs(eq-oldeq))
            metrics=path_metrics(points,t0);oldmetrics=path_metrics(oldpoints,t0)
            for field,value in metrics.items():
                if value is None:assert r[field] is None
                elif isinstance(value,D):equal(r[field],value)
                else:assert r[field]==value
            for field,value in oldmetrics.items():
                if value is None:assert old[field] is None
                elif isinstance(value,D):equal(old[field],value)
                else:assert old[field]==value
            sign=lambda x:(D(x)>0)-(D(x)<0)
            row={'coin':c,'start':k[1],'fee_multiplier':k[2],'slippage_bps_per_leg_side':k[3],'execution_mode':k[4],'original_net_pnl':old['net_pnl_proxy'],'F1_net_pnl':r['net_pnl_proxy'],'cash_pnl_delta':delta,'old_exit_base':net,'F1_sold_base':sold,'remaining_base':remain,'remaining_realizable_value':Z,'lotSz':lot,'minSz':minimum,'maxMktSz':maximum,'sign_changed':sign(old['net_pnl_proxy'])!=sign(r['net_pnl_proxy']),'original_drawdown':old['drawdown_usdt_hourly_proxy'],'F1_drawdown':r['drawdown_usdt_hourly_proxy'],'drawdown_delta':D(r['drawdown_usdt_hourly_proxy'])-D(old['drawdown_usdt_hourly_proxy']),'max_abs_hourly_equity_delta':max_eq_diff,'original_spot_hold_pnl':old['spot_hold_same_cash_allocation_pnl_proxy'],'F1_spot_hold_pnl':r['spot_hold_same_cash_allocation_pnl_proxy'],'cash_and_inventory_identity':'PASS'}
            details.append(row)
            if row['sign_changed']:changes.append(k)
    # Rebuild current snapshots from raw books; floor BEFORE checking exit depth.
    current=json.loads((P/'results_all.json').read_text())['current_snapshots'];snapchecks=[]
    oldcurrent={r['coin']:r for r in json.loads((ROOT/'results_all.json').read_text())['current_snapshots']}
    for r in current:
        c=r['coin'];sp=load(c+'_spot_spec')[0];fp=load(c+'_swap_spec')[0];sb=load(c+'_spot_book')[0];fb=load(c+'_swap_book')[0]
        fee=D('.001');unit=D(fp['ctVal'])*D(fp['ctMult']);clot=D(fp['lotSz']);lot=D(sp['lotSz']);ask=D(sb['asks'][0][0])
        n=(800*(1-fee)/ask/unit/clot).to_integral_value(rounding=ROUND_FLOOR)*clot
        while True:
            q=n*unit;gross=(q/(1-fee)/lot).to_integral_value(rounding=ROUND_CEILING)*lot
            if gross*ask<=800:break
            n-=clot
        net=gross*(1-fee);sold=(net/lot).to_integral_value(rounding=ROUND_FLOOR)*lot;remain=net-sold
        prices=[vwap(sb['asks'],gross),vwap(sb['bids'],sold),vwap(fb['bids'],q,unit),vwap(fb['asks'],q,unit)]
        buyprice,sellprice,shortprice,coverprice=prices
        cost=gross*buyprice-sold*sellprice*(1-fee)-q*(shortprice-coverprice)+q*(shortprice+coverprice)*D('.0005')
        equal(r['instant_roundtrip_cost_snapshot'],cost);equal(r['remaining_spot_base'],remain);equal(r['sold_spot_base'],sold)
        snapchecks.append({'coin':c,'old_cost':oldcurrent[c]['instant_roundtrip_cost_snapshot'],'corrected_cost':cost,'cost_delta':cost-D(oldcurrent[c]['instant_roundtrip_cost_snapshot']),'retained_base':remain,'retained_value':Z,'full_quote_depth_check':'PASS'})
    # Overlay costs use corrected equity; scenario parameters never change.
    count=0
    with (P/'overheads_all.csv').open() as f:
        for row in csv.DictReader(f):
            k=(row['coin'],row['start'],int(row['fee_multiplier']),int(row['slippage_bps']),row['mode'])
            expected=D(corrected[k]['net_pnl_proxy'])-D(row['operating_cost_30d'])-D(2000)*D(row['cash_opportunity_apr'])*30/365
            equal(row['net_after_costs_proxy'],expected);count+=1
    with (P/'scenario_differences.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(details[0]));w.writeheader();w.writerows(details)
    summary={'at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'original_artifact_hashes_unchanged':len(baseline),'raw_source_requests_new':0,'independent_entry_sizing_cash_inventory_cases':len(details),'independent_hourly_cash_inventory_valuations':checks,'independent_metric_sets':108,'max_hourly_cash_error':max_error,'scenarios_sign_changed':changes,'remaining_inventory_cases':sum(D(x['remaining_base'])>0 for x in details),'max_abs_net_pnl_delta':max(abs(x['cash_pnl_delta']) for x in details),'max_abs_hourly_equity_delta':max(x['max_abs_hourly_equity_delta'] for x in details),'max_abs_drawdown_delta':max(abs(x['drawdown_delta']) for x in details),'current_snapshot_checks':snapchecks,'cost_overlay_checks':count,'qualification':'Independent code within Owner B; C re-review and PMO acceptance pending. Conditional diagnostics only. Original seen results remain seen.'}
    emit('validation_f1.json',summary);print(json.dumps(summary,ensure_ascii=False,indent=2,default=str))
if __name__=='__main__':main()
