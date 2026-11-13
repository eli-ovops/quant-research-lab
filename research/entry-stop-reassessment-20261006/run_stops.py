import sys,json,gzip,hashlib,datetime
from pathlib import Path
R=Path(__file__).resolve().parent;B=R.parent/'strategy-campaign-20261006';O=R.parent/'aggressive-500-20261006'
import engine_stop as engine,audit_stop as audit
sys.path.insert(0,str(B));import signals,signal_audit
sys.path.append(str(O));import data,evaluate
P=json.loads((O/'protocol.json').read_text());assets=P['screen_assets']+P['holdout_assets'];c=json.loads((B/'batch4/protocol.json').read_text())['configs'][0]
D=R/'stops';D.mkdir(exist_ok=False)
configs=[dict(c,id=f'filter{n}_stop{sl}_{mode}',mode='filter',n=n,stop_atr=sl,intrabar_stop=mode) for n in [6,24] for sl in [1,3] for mode in ['trigger','adverse_bar']]
seal={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in [R/'engine_stop.py',R/'audit_stop.py',B/'signals.py']}
(D/'protocol.json').write_text(json.dumps({'configs':configs,'assets':assets,'source_hashes':seal,'cumulative_configs':109,'known_data_only':True},indent=2))
data.enable_seal();rr={c['id']:[] for c in configs};files={c['id']:gzip.open(D/(c['id']+'.jsonl.gz'),'wt') for c in configs};count=0
try:
 for coin in assets:
  assert datetime.datetime.now(datetime.timezone.utc)<datetime.datetime.fromisoformat('2026-10-06T15:20:03+00:00')
  raw,spec,fund=data.load(coin,'CONDITIONAL_SWAP');ep=engine.prepare_rows(raw);ap=audit.prepare_rows(raw);bars=engine._hourly(raw);base=engine.prepare_signals(ep,c['rule'])
  maps={n:signals.build(bars,base,'filter',n) for n in [6,24]}
  for n,m in maps.items():assert m==signal_audit.build(bars,base,'filter',n)
  for v in configs:
   for fold in range(3):
    for start in evaluate.schedule(fold,168):
     end=start+168*3600000;x=engine.simulate(ep,spec,fund,v,start,end,maps[v['n']]);assert audit.verify(ap,spec,fund,v,start,end,maps[v['n']],x)['ok'];count+=1
     row=dict(coin=coin,start=start,fold=fold,**x);rr[v['id']].append(row);files[v['id']].write(json.dumps(row)+'\n')
  print(json.dumps({'coin':coin,'audits':count}),flush=True)
finally:
 for f in files.values():f.close()
assert all(hashlib.sha256(Path(k).read_bytes()).hexdigest()==v for k,v in seal.items())
(D/'results.json').write_text(json.dumps({'audits':count,'results':{k:evaluate.aggregate(v) for k,v in rr.items()}},indent=2))
