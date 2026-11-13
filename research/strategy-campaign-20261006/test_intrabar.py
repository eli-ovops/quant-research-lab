import sys,json
from pathlib import Path
R=Path(__file__).resolve().parent
import engine_intrabar as engine,audit_intrabar as audit
sys.path.append(str(R.parent/'aggressive-500-20261006'));from test_engine import fixture,funding,SWAP,START,H,Q
records=[]
for direction in [-1,1]:
 for mode in ['trigger','adverse_bar']:
  cfg=dict(product='CONDITIONAL_SWAP',leverage=10,horizon_hours=24,cost='stress',rule={'family':'trend'},risk_fraction=.1,intrabar_stop=mode)
  rows=fixture();i=START//Q;rows[i][2:5]=['103','97','100'];sig={START:dict(direction=direction,atr_fraction=.01)};end=START+24*H
  out=engine.simulate(rows,SWAP,funding(end),cfg,START,end,sig)
  assert audit.verify(rows,SWAP,funding(end),cfg,START,end,sig,out)['ok']
  exits=[e for e in out['events'] if e['type']=='EXIT'];assert len(exits)==1 and exits[0]['reason']=='INTRABAR_STOP_'+mode
  assert out['metrics']['final_equity']<500
  records.append(dict(direction=direction,mode=mode,equity=out['metrics']['final_equity']))
 for mode in ['trigger','adverse_bar']:
  cfg.update(leverage=20,risk_fraction=None,intrabar_stop=mode)
  rows=fixture();rows[i][2:5]=['120','80','100']
  out=engine.simulate(rows,SWAP,funding(end),cfg,START,end,sig)
  assert audit.verify(rows,SWAP,funding(end),cfg,START,end,sig,out)['ok']
  assert out['metrics']['final_equity']==0 # maintenance-first ambiguity remains pessimistic
assert records[1]['equity']<=records[0]['equity'] and records[3]['equity']<=records[2]['equity']
(R/'intrabar_tests.json').write_text(json.dumps({'status':'PASS','cases':8,'records':records,'scope':'crossing on recovered candle and maintenance-first ambiguity; fills are scenarios not validated execution'},indent=2))
print('PASS 8 intrabar-stop scenarios')
