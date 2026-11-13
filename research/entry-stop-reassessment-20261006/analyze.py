import json,gzip,statistics as s,hashlib,collections
from pathlib import Path
R=Path(__file__).resolve().parent;B=R.parent/'strategy-campaign-20261006'
seals={}
def load(batch,name):
 p=B/batch/(name+'.jsonl.gz');seals[str(p)]=hashlib.sha256(p.read_bytes()).hexdigest();return [json.loads(z) for z in gzip.open(p,'rt')]
def trades(rr):
 out={}
 for r in rr:
  entries={}
  for e in r['events']:
   if e['type']=='ENTRY':entries[e['trade_id']]=e
   if e['type'] in ['EXIT','MAINTENANCE_PROXY_BREACH']:
    a=entries[e['trade_id']];cash=a['cash_after']+a['fee'];key=(r['coin'],r['start'],a['timestamp'],a['direction'])
    assert key not in out
    out[key]={'pnl_pct':100*e['trade_net_pnl']/cash,'hours':(e['timestamp']-a['timestamp'])/3600000,'reason':e.get('reason',e['type'])}
 return out
def describe(rr):
 ts=list(trades(rr).values());pos=[t['pnl_pct'] for t in ts if t['pnl_pct']>0];neg=[t['pnl_pct'] for t in ts if t['pnl_pct']<0]
 return {'accounts':len(rr),'active_accounts':sum(r['metrics']['entry_count']>0 for r in rr),'trades':len(ts),'mean_account_pct':100*s.mean(r['metrics']['return'] for r in rr),'win_trade_fraction':len(pos)/len(ts),'mean_win_pct':s.mean(pos) if pos else None,'mean_loss_pct':s.mean(neg) if neg else None,'mean_trade_pct':s.mean(t['pnl_pct'] for t in ts),'median_hold_hours':s.median(t['hours'] for t in ts),'exit_counts':dict(collections.Counter(t['reason'] for t in ts))}
entry={}
for n in [6,12,24]:
 entry[n]={k:describe(load('batch7',f'{k}_n{n}_hold24')) for k in ['direct','confirm','retest']}
stop={}
for n in [6,24]:
 modes={'close':load('batch1',f'filter_{n}'),'trigger':load('batch4',f'filter_{n}_trigger'),'adverse_bar':load('batch4',f'filter_{n}_adverse_bar')};tt={k:trades(v) for k,v in modes.items()};common=set.intersection(*(set(v) for v in tt.values()));comparisons={}
 for mode in ['trigger','adverse_bar']:
  changes=[(tt[mode][k]['pnl_pct']-tt['close'][k]['pnl_pct']) for k in common]
  comparisons[mode]={'common_entries':len(common),'mean_trade_return_difference_pp':s.mean(changes),'better':sum(z>1e-9 for z in changes),'worse':sum(z<-1e-9 for z in changes),'close_profitable_changed_to_loss':sum(tt['close'][k]['pnl_pct']>0 and tt[mode][k]['pnl_pct']<0 for k in common),'different_exit':sum(tt['close'][k]['reason']!=tt[mode][k]['reason'] for k in common)}
 stop[n]={'all':{k:describe(v) for k,v in modes.items()},'common_entry_diagnostics':comparisons,'warning':'common-entry subset is selected post hoc; later equity and position sizes differ; not a whole-strategy causal estimate'}
assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==h for p,h in seals.items())
(R/'attribution.json').write_text(json.dumps({'entry':entry,'stop':stop,'sources':seals},indent=2));print(json.dumps({'entry':entry,'stop':stop},indent=2))
