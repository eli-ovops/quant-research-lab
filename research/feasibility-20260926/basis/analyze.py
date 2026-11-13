"""Offline only. No historical trading PnL is inferred from normalized price differences."""
from pathlib import Path
from decimal import Decimal as D, ROUND_CEILING
import json,csv,hashlib,datetime,platform
P=Path(__file__).resolve().parent

def read(name):
    x=json.loads((P/'raw'/f'{name}.txt').read_text());assert x['code']=='0',x
    return x['data']
def eligible(i):
    return i.get('instFamily') in ('BTC-USDT','ETH-USDT') and i.get('ctType')=='linear' and i.get('settleCcy')=='USDT' and i.get('state')=='live' and i.get('ruleType')=='normal'
def cash_ledger(q,s0,f0,s1,f1,spot_fee,fut_fee,delivery_fee=None):
    gross=q/(1-spot_fee);cost=gross*s0;buy_fee_base=gross-q
    open_fee=q*f0*fut_fee;exit_fee=q*f1*(fut_fee if delivery_fee is None else delivery_fee)
    sell_net=q*s1*(1-spot_fee);future=q*(f0-f1)
    end=D(2000)-cost-open_fee+sell_net+future-exit_fee
    spread=q*((f0-s0)-(f1-s1))-buy_fee_base*s0-q*s1*spot_fee-open_fee-exit_fee
    assert abs((end-D(2000))-spread)<D('1e-20')
    return end-D(2000)
def main():
    src=json.loads((P/'sources.json').read_text());checks=[]
    for r in src:
        if 'path' in r:assert hashlib.sha256(Path(r['path']).read_bytes()).hexdigest()==r['sha256']
    universe=read('all_futures');chosen=[i for i in universe if eligible(i)]
    assert not chosen
    for c in ['BTC','ETH']:assert read(c+'_futures')==read(c+'_family')==[]
    fields=['instId','instFamily','ctType','ctVal','ctMult','ctValCcy','settleCcy','ruleType','state','listTime','expTime','minSz','lotSz','tickSz']
    btceth=[i for i in universe if i['instId'].startswith(('BTC-','ETH-'))]
    with (P/'universe.csv').open('w') as f:
        w=csv.DictWriter(f,fields+['in_scope']);w.writeheader();w.writerows([{**{k:i.get(k,'') for k in fields},'in_scope':eligible(i)} for i in btceth])
    rows=[];audits=[]
    for c in ['BTC','ETH']:
        delivery=read(c+'_delivery')[0];i=delivery['details'][0]['insId'];terminal=D(delivery['details'][0]['px'])
        events=sorted((int(d['ts']),D(x['settlePx'])) for d in read(c+'_settlement') for x in d['details'] if x['instId']==i)
        path=events+[(int(delivery['ts']),terminal)]
        assert len(set(t for t,p in path))==len(path)
        diffs=[]
        for (ta,pa),(tb,pb) in zip(path,path[1:]):
            diff=pa-pb;diffs.append(diff);rows.append({'instId':i,'start_utc':datetime.datetime.fromtimestamp(ta/1000,datetime.timezone.utc).isoformat(),'end_utc':datetime.datetime.fromtimestamp(tb/1000,datetime.timezone.utc).isoformat(),'start_price':str(pa),'end_price':str(pb),'normalized_short_USDT_per_base_unit':str(diff),'evidence_kind':'observed_prices_not_trades'})
        direct=path[0][1]-terminal;assert sum(diffs,D(0))==direct
        audits.append({'asset':c,'events':len(path),'sum_deltas':str(sum(diffs,D(0))),'direct_difference':str(direct),'independent_identity':True,'quantity':'normalized one base unit; not contract count or invested capital','historical_trade_pnl':'UNKNOWN'})
    with (P/'settlement_audit.csv').open('w') as f:
        w=csv.DictWriter(f,rows[0].keys());w.writeheader();w.writerows(rows)
    # Synthetic accounting verification only; no performance sample or selection.
    for mode in [None,D('.0001')]:
        for s1,f1 in [(D(60000),D(60000)),(D(66000),D(66100)),(D(30000),D(29900))]:
            cash_ledger(D('.01'),D(60000),D(60300),s1,f1,D('.001'),D('.0005'),mode)
    # Explicit double-count counterexample, partial-size and fee-direction boundary.
    assert sum([D(100)-D(110),D(110)-D(90)])==D(100)-D(90)
    assert sum([D(100)-D(110),D(100)-D(90)])!=D(100)-D(90)
    net=D('.01');lot=D('.00000001');gross=(net/(1-D('.001'))/lot).to_integral_value(rounding=ROUND_CEILING)*lot
    residual=gross*(1-D('.001'))-net
    assert D(0)<=residual<lot
    # Eligibility must reject USD/inverse/X-Perp, not just matching BTC/ETH text.
    fixture={'instFamily':'BTC-USDT','ctType':'linear','settleCcy':'USDT','state':'live','ruleType':'normal'}
    assert eligible(fixture)
    for k,v in [('settleCcy','USD'),('ctType','inverse'),('ruleType','xperp'),('state','expired')]:assert not eligible({**fixture,k:v})
    timerec=next(r for r in src if r['name']=='time');server=int(read('time')[0]['ts']);clock_skew=server-(timerec['request_ms']+timerec['received_ms'])/2
    out={'python':platform.python_version(),'source_hash_checks':len([r for r in src if 'path'in r]),'universe_count':len(universe),'btc_eth_count':len(btceth),'eligible_count':0,'clock_server_midpoint_delta_ms':clock_skew,'clock_rtt_ms':timerec['elapsed_ms'],'settlement_audits':audits,'synthetic_cash_identity_cases':6,'fee_rounding_residual_base':str(residual),'eligibility_boundary_tests':5,'decision':'INFEASIBLE_CURRENT_SPECIFIED_OKX_USDT_EXPIRY_VERSION','historical_profitability':'INSUFFICIENT_EVIDENCE','independent_trade_events':0,'real_orders':0,'heldout_completed_trades':0,'pnl_USDT':None,'return_on_2000':None,'note':'No eligible product. No bids/asks or future execution assumed. Price telescope audit is not trading return.'}
    (P/'results.json').write_text(json.dumps(out,indent=2,ensure_ascii=False));print(json.dumps(out,indent=2,ensure_ascii=False))
if __name__=='__main__':main()
