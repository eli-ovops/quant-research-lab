import sys,json,gzip,hashlib,time
from pathlib import Path
from datetime import datetime,timezone
R=Path(__file__).resolve().parent;O=R.parent/'aggressive-500-20261006';S=R.parent/'risk-sizing-20261006'
import signals,signal_audit,entry_structure
import engine_intrabar as engine,audit_intrabar as audit
sys.path.append(str(O));import data,evaluate
C=json.loads((R/'campaign.json').read_text());P=json.loads((O/'protocol.json').read_text())
D=R/'batch7';D.mkdir(exist_ok=False)
variants=[('baseline',12)]+[(m,n) for m in ['filter','breakout'] for n in [6,12,24]]
assets=P['screen_assets']+P['holdout_assets'];c=dict(P['configs'][0]);c.update(leverage=10,horizon_hours=168,cost='stress',risk_fraction=.1)
configs=[dict(c,id=f'{kind}_n{n}_hold{h}',mode='breakout',n=n,entry_kind=kind,hold_bars=h*4,intrabar_stop='adverse_bar',risk_fraction=.2) for kind in ['direct','confirm','retest'] for n in [6,12,24] for h in [24,48]]
(D/'protocol.json').write_text(json.dumps({'configs':configs,'assets':assets,'known_data_only':True,'ratio':.75,'volume_ratio':1,'source_hashes':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in [R/'entry_structure.py',R/'signals.py',R/'signal_audit.py',R/'engine_intrabar.py',R/'audit_intrabar.py']}},indent=2))
C['configs_used']+=len(configs);C['current_stage']=2;C['next']='batch7 entry structure running';assert C['configs_used']<=120;(R/'campaign.json').write_text(json.dumps(C,ensure_ascii=False,indent=2))
data.enable_seal();allrows={v['id']:[] for v in configs};checks=0
files={v['id']:gzip.open(D/(v['id']+'.jsonl.gz'),'wt') for v in configs}
try:
 for coin in assets:
  assert datetime.now(timezone.utc)<datetime.fromisoformat(C['deadline_utc'])
  raw,spec,fund=data.load(coin,'CONDITIONAL_SWAP');ep=engine.prepare_rows(raw);ap=audit.prepare_rows(raw);base=engine.prepare_signals(ep,c['rule']);bars=engine._hourly(raw)
  assert audit.compare_signals(base,audit.prepare_signals(raw,[c['rule']])[c['rule']['id']])['ok']
  for v in configs:
   sig=signals.build(bars,base,v['mode'],v['n']);ind=signal_audit.build(bars,base,v['mode'],v['n']);assert sig==ind,(coin,v['id'],'signal mismatch')
   sig2=entry_structure.build(bars,sig,v['entry_kind'],v['n']);assert sig2==entry_structure.audit(bars,sig,v['entry_kind'],v['n']);sig=sig2
   for f in range(3):
    for start in evaluate.schedule(f,168):
     end=start+168*3600000;x=engine.simulate(ep,spec,fund,v,start,end,sig);assert audit.verify(ap,spec,fund,v,start,end,sig,x)['ok'];checks+=1
     row=dict(coin=coin,start=start,fold=f,**x);allrows[v['id']].append(row);files[v['id']].write(json.dumps(row)+'\n')
  print(json.dumps({'coin':coin,'audits':checks}),flush=True)
finally:
 for f in files.values():f.close()
summary={k:evaluate.aggregate(v) for k,v in allrows.items()}
(D/'results.json').write_text(json.dumps({'independent_audits':checks,'results':summary},indent=2));print(json.dumps(summary),flush=True)
C['next']='inspect entry structure; no retrospective rule rewrite';(R/'campaign.json').write_text(json.dumps(C,ensure_ascii=False,indent=2))
