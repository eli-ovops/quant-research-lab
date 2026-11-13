"""Independent read-only recomputation from raw sources, never calls replay()."""
from pathlib import Path
from decimal import Decimal as D, getcontext
import json, csv, hashlib, datetime
getcontext().prec=40
P=Path(__file__).resolve().parent
def stamp(s):return int(datetime.datetime.fromisoformat(s).replace(tzinfo=datetime.timezone.utc).timestamp()*1000)
def rows(pattern,field):
    items={}
    for path in (P/'raw').glob(pattern):
        if 'funding' in pattern and not path.stem.split('_')[-1].isdigit():continue
        for r in json.loads(path.read_text())['data']:items[int(r[field])]=r
    return items
def main():
    out=json.loads((P/'results_all.json').read_text());scenarios=json.loads((P/'scenarios_all.json').read_text())
    details=[];rate_runs=[];expected_bars={}
    for c in ['BTC','ETH']:
        spot=rows(c+'_spot_1H_*.txt',0);swap=rows(c+'_swap_1H_*.txt',0);mark=rows(c+'_mark_1H_*.txt',0);fund=rows(c+'_funding_*.txt','fundingTime')
        tstart=stamp('2026-06-28');tend=stamp('2026-09-26')
        for kind,bars in [('spot',spot),('swap',swap),('mark',mark)]:
            missing=[t for t in range(tstart,tend+7200000,3600000) if t not in bars]
            assert not missing,(c,kind,missing)
            expected_bars[c+'_'+kind]=len(range(tstart,tend+7200000,3600000))
        times=[t for t in sorted(fund) if tstart<=t<=tend]
        assert len(times)==271 and all(b-a==28800000 for a,b in zip(times,times[1:]))
        run=[]
        for t in times:
            if D(fund[t]['realizedRate'])<0:run.append(t)
            elif run:
                rate_runs.append({'coin':c,'start':datetime.datetime.fromtimestamp(run[0]/1000,datetime.timezone.utc).isoformat(),'last_negative_settlement':datetime.datetime.fromtimestamp(run[-1]/1000,datetime.timezone.utc).isoformat(),'negative_events':len(run),'first_to_last_hours':(run[-1]-run[0])/3600000,'to_next_nonnegative_hours':(t-run[0])/3600000});run=[]
        if run:rate_runs.append({'coin':c,'negative_events':len(run),'right_censored':True})
        for r in [x for x in scenarios if x['coin']==c]:
            delay=3600000 if r['execution_mode']=='delay_1h' else 0
            t0=stamp(r['start'])+delay;t1=stamp(r['end'])+delay
            # Independently sum q * each historical mark opening * ACTUAL fee rate.
            q=D(r['hedged_base']);gross=D(r['gross_spot_base']);fee=D('.001')*r['fee_multiplier'];ff=D('.0005')*r['fee_multiplier'];sl=D(r['slippage_bps_per_leg_side'])/10000
            s0,s1,f0,f1=[D(x) for x in [spot[t0][1],spot[t1][1],swap[t0][1],swap[t1][1]]]
            if r['execution_mode']=='adverse_hour':s0,s1,f0,f1=[D(x) for x in [spot[t0][2],spot[t1][3],swap[t0][3],swap[t1][2]]]
            base=gross*(1-fee)
            cash=D(1200)-gross*s0*(1+sl)
            collateral=D(800)-q*f0*(1-sl)*ff
            funding=D(0)
            for t in sorted(fund):
                if t0<t<t1:funding+=q*D(mark[t][1])*D(fund[t]['realizedRate'])
            collateral+=funding+q*(f0*(1-sl)-f1*(1+sl))-q*f1*(1+sl)*ff
            cash+=base*s1*(1-sl)*(1-fee)+collateral
            error=cash-D(2000)-D(r['net_pnl_proxy'])
            assert abs(error)<D('1e-28')
            assert abs(funding-D(r['funding_proxy']))<D('1e-28')
            details.append({'coin':c,'start':r['start'],'fee_multiplier':r['fee_multiplier'],'bps':r['slippage_bps_per_leg_side'],'mode':r['execution_mode'],'raw_cash_recomputed_pnl':str(cash-2000),'difference':str(error)})
    # Primary CSV funding events are independently reconciled to raw rates and mark prices.
    count=0
    with (P/'funding_events_all.csv').open() as f:
        for r in csv.DictReader(f):
            expected=D(r['base_quantity'])*D(r['mark_open_proxy'])*D(r['realized_rate'])
            assert expected==D(r['funding_proxy']);count+=1
    src=json.loads((P/'sources.json').read_text())
    checks=sum('path' in x for x in src)
    for x in src:
        if 'path' in x:assert hashlib.sha256(Path(x['path']).read_bytes()).hexdigest()==x['sha256']
    result={'validated_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source_hashes':checks,'independently_recomputed_scenarios':len(details),'event_formula_rows':count,'complete_hourly_rows_needed_per_series':expected_bars,'boundary_events_excluded_from_point_estimate_included_in_bounds':True,'negative_runs':rate_runs,'max_abs_cash_error':str(max(abs(D(x['difference'])) for x in details)),'details':details,'qualification':'Owner B independent implementation check only; reviewer C still required. Cash is modeled, not actual account cash.'}
    (P/'validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ['details','negative_runs']},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
