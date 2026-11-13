import json,gzip,hashlib,statistics as st,collections,random
from pathlib import Path
R=Path(__file__).resolve().parent; B=R.parent; O=B.parent/'aggressive-500-20261006'
def summary(rr):
 return dict(n=len(rr),target=sum(r['metrics']['target_hit'] for r in rr),zero=sum(r['metrics']['final_equity']==0 for r in rr),mean=st.mean(r['metrics']['return'] for r in rr),median=st.median(r['metrics']['return'] for r in rr),worst=min(r['metrics']['return'] for r in rr))
out={};seals={}
for lev,p in [(10,B/'ledger10_h168.jsonl.gz'),(20,O/'ledgers/holdout_trend_1_L20_H168_stress.jsonl.gz')]:
 seals[str(p)]=hashlib.sha256(p.read_bytes()).hexdigest(); rows=[json.loads(s) for s in gzip.open(p,'rt')];assert len(rows)==60
 groups=collections.defaultdict(list);trades=[]
 for r in rows:
  m=r['metrics'];g='no_trade' if not m['entry_count'] else 'target' if m['target_hit'] else 'loss' if m['return']<0 else 'positive_below_target';groups[g].append(r)
  entries={e['trade_id']:e for e in r['events'] if e['type']=='ENTRY'}
  for e in r['events']:
   if e['type']=='EXIT':
    a=entries[e['trade_id']];trades.append(dict(group=g,direction=a['direction'],hold_hours=(e['timestamp']-a['timestamp'])/3600000,atr=a['atr_fraction'],reason=e['reason'],net=e['trade_net_pnl']))
 clusters=collections.defaultdict(list)
 for r in rows:clusters[r['start']].append(r['metrics']['return'])
 means=[st.mean(v) for v in clusters.values()];rng=random.Random(612);boots=sorted(st.mean(rng.choices(means,k=len(means))) for _ in range(10000))
 out[lev]={'all':summary(rows),'by_fold':{f:summary([r for r in rows if r['fold']==f]) for f in range(3)},'by_coin':{c:summary([r for r in rows if r['coin']==c]) for c in sorted({r['coin'] for r in rows})},'date_clusters':len(means),'descriptive_cluster90':[boots[500],boots[9499]],'groups':{g:{**summary(rr),'one_entry':sum(r['metrics']['entry_count']==1 for r in rr),'mean_fees':st.mean(r['metrics']['fees'] for r in rr)} for g,rr in groups.items()},'trades_by_account_outcome':{g:{'n':len(tt),'median_hold_hours':st.median(t['hold_hours'] for t in tt),'median_entry_atr':st.median(t['atr'] for t in tt),'long':sum(t['direction']==1 for t in tt),'reasons':dict(collections.Counter(t['reason'] for t in tt))} for g in groups if (tt:=[t for t in trades if t['group']==g])}}
 assert sum(v['n'] for v in out[lev]['groups'].values())==60
assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==h for p,h in seals.items())
(R/'results.json').write_text(json.dumps({'owner':'root','scope':'post-hoc diagnostics only; no strategy changes; 30 minute maximum','source_hashes':seals,'results':out},indent=2)+'\n')
print(json.dumps(out,ensure_ascii=False,indent=2))
