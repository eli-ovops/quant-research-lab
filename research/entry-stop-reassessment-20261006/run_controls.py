import sys,json,gzip,hashlib,statistics,datetime
from pathlib import Path
R=Path(__file__).resolve().parent;B=R.parent/'strategy-campaign-20261006';O=R.parent/'aggressive-500-20261006'
sys.path.insert(0,str(B));import engine_intrabar as engine,audit_intrabar as audit,signals,entry_structure
sys.path.append(str(O));import data,evaluate
P=json.loads((O/'protocol.json').read_text());deadline=datetime.datetime.fromisoformat(json.loads((B/'campaign.json').read_text())['deadline_utc']);assets=P['screen_assets']+P['holdout_assets']
c=json.loads((B/'batch7/protocol.json').read_text())['configs'][0]
configs=[dict(c,id=f'control_{kind}_n{n}_s{seed}',entry_kind=kind,n=n,seed=seed) for kind in ['confirm','retest'] for n in [6,12,24] for seed in range(4)]
D=R/'controls';D.mkdir(exist_ok=False)
seal={str(B/n):hashlib.sha256((B/n).read_bytes()).hexdigest() for n in ['engine_intrabar.py','audit_intrabar.py','signals.py','entry_structure.py']}
(D/'protocol.json').write_text(json.dumps({'configs':configs,'assets':assets,'deadline':deadline.isoformat(),'scope':'retrospective same direction and fold signal-count controls, not matched holding exposure','source_hashes':seal,'new_config_count':24,'campaign_configs_after':101},indent=2))
data.enable_seal();rr={c['id']:[] for c in configs};files={c['id']:gzip.open(D/(c['id']+'.jsonl.gz'),'wt') for c in configs};count=0
try:
 for coin in assets:
  assert datetime.datetime.now(datetime.timezone.utc)<deadline
  raw,spec,fund=data.load(coin,'CONDITIONAL_SWAP');ep=engine.prepare_rows(raw);ap=audit.prepare_rows(raw);bars=engine._hourly(raw);base=engine.prepare_signals(ep,c['rule'])
  maps={}
  for n in [6,12,24]:
   rawsig=signals.build(bars,base,'breakout',n)
   for kind in ['direct','confirm','retest']:maps[n,kind]=entry_structure.build(bars,rawsig,kind,n)
  for v in configs:
   direct=maps[v['n'],'direct'];target=maps[v['n'],v['entry_kind']];sig={t:dict(z,direction=0) for t,z in direct.items()}
   for a,b in P['folds']:
    lo,hi=data.ms(a),data.ms(b)
    for side in [-1,1]:
     pool=[t for t,z in direct.items() if lo<=t<hi and z['direction']==side]
     wanted=sum(lo<=t<hi and z['direction']==side for t,z in target.items())
     # Confirmation can rarely exceed direct due cooldown; count cap disclosed.
     chosen=sorted(pool,key=lambda t:hashlib.sha256(f'{coin}:{side}:{t}:{v["seed"]}'.encode()).digest())[:wanted]
     for t in chosen:sig[t]=dict(direct[t])
   for fold in range(3):
    for start in evaluate.schedule(fold,168):
     end=start+168*3600000;x=engine.simulate(ep,spec,fund,v,start,end,sig);assert audit.verify(ap,spec,fund,v,start,end,sig,x)['ok'];count+=1
     row=dict(coin=coin,start=start,fold=fold,**x);rr[v['id']].append(row);files[v['id']].write(json.dumps(row)+'\n')
  print(json.dumps({'coin':coin,'audits':count}),flush=True)
finally:
 for f in files.values():f.close()
assert all(hashlib.sha256(Path(k).read_bytes()).hexdigest()==h for k,h in seal.items())
(D/'results.json').write_text(json.dumps({'audits':count,'results':{k:evaluate.aggregate(v) for k,v in rr.items()}},indent=2))
