import sys,json,gzip,time,hashlib,statistics as st
from pathlib import Path
R=Path(__file__).resolve().parent;O=R.parent/'aggressive-500-20261006'
import engine,audit
sys.path.append(str(O));import data,evaluate
P=json.loads((R/'protocol.json').read_text());deadline=time.time()+1800
assert not (R/'results.json').exists()
data.enable_seal();results=[];checks=0
for c in P['configs']:
 rows=[];effective=[];excess=0;entry_checks=0
 with gzip.open(R/(c['id']+'.jsonl.gz'),'wt') as out:
  for coin in P['assets']:
   raw,spec,fund=data.load(coin,'CONDITIONAL_SWAP');ep=engine.prepare_rows(raw);ap=audit.prepare_rows(raw);sig=engine.prepare_signals(ep,c['rule'])
   assert audit.compare_signals(sig,audit.prepare_signals(raw,[c['rule']])[c['rule']['id']])['ok']
   for fold in range(3):
    for start in evaluate.schedule(fold,168):
     assert time.time()<deadline
     end=start+168*3600000;x=engine.simulate(ep,spec,fund,c,start,end,sig);assert audit.verify(ap,spec,fund,c,start,end,sig,x)['ok'];checks+=1
     entries={}
     for e in x['events']:
      if e['type']=='ENTRY':
       cash=e['cash_after']+e['fee'];n=abs(e['base_delta'])*e['price'];unit=2*e['atr_fraction']+.004+2*float(spec['tickSz'])/e['reference_price']
       assert n*unit<=cash*c['risk_fraction']+1e-7
       assert n*(1/c['leverage']+.001)<=.95*cash+1e-7
       effective.append(n/cash);entries[e['trade_id']]=cash;entry_checks+=1
      if e['type'] in ('EXIT','MAINTENANCE_PROXY_BREACH'):
       excess+=int(-e['trade_net_pnl']>entries[e['trade_id']]*c['risk_fraction']+1e-7)
     row=dict(coin=coin,start=start,fold=fold,**x);rows.append(row);out.write(json.dumps(row)+'\n')
 a=evaluate.aggregate(rows);a.update(id=c['id'],risk_fraction=c['risk_fraction'],leverage_cap=c['leverage'],loss50=sum(r['metrics']['return']<=-.5 for r in rows),effective_leverage_median=st.median(effective),effective_leverage_max=max(effective),trades_exceeding_planned_risk=excess,entry_checks=entry_checks,by_fold=[st.mean(r['metrics']['return'] for r in rows if r['fold']==f) for f in range(3)])
 results.append(a);print(json.dumps(a),flush=True)
assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==h for p,h in P['source_sha256'].items());data.enable_seal()
(R/'results.json').write_text(json.dumps(dict(status='COMPLETED',independent_replays=checks,source_seal_pass=True,new_blind_test=False,results=results),indent=2))
