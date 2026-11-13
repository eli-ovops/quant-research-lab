"""Frozen bounded evaluation. Selection saved before confirmation evaluation."""
import json,gzip,time,datetime
from pathlib import Path
import data,engine,replay
P=Path(__file__).resolve().parent

def compact(m):return {k:v for k,v in m.items() if k!='daily_returns'}
def eligible(rows,mintrades):
 return len(rows)==3 and {r['condition'] for r in rows}=={'base','stress','delayed_stress'} and all(r['audit']['status']=='PASS' and r['metrics']['total_return']>0 and r['metrics']['max_drawdown']<=.5 and r['metrics']['closed_trades']>=mintrades for r in rows)
def select(rows,candidates):
 winners=[]
 for family in ('trend','reversion','rotation'):
  good=[]
  for c in candidates:
   rs=[r for r in rows if r['candidate']==c['id'] and r['period']=='validation']
   if c['family']==family and eligible(rs,30):
    stress=next(r for r in rs if r['condition']=='stress')
    good.append((-stress['metrics']['total_return'],stress['metrics']['max_drawdown'],c['id']))
  if good:winners.append(sorted(good)[0][2])
 return winners

def main():
 proto=json.loads((P/'protocol.json').read_text());deadline=data.ms(proto['deadline_utc'])
 (P/'results_v2').mkdir(exist_ok=True)
 freeze_names=['protocol.json','execution_semantics.json','data_quality_policy.json','engine.py','replay.py','data.py','evaluate.py','confirmation_seal.json','development_input_gate.json']
 freeze={name:data.sha(P/name) for name in freeze_names}
 for dep in [data.LEGACY/'source_gate.py',data.OLD/'cross-asset-01/manifest.json']:
  freeze[str(dep)]=data.sha(dep)
 if (P/'evaluation_freeze_v2.json').exists():
  assert json.loads((P/'evaluation_freeze_v2.json').read_text())['hashes']==freeze,'changed frozen inputs'
 else:data.dump(P/'evaluation_freeze_v2.json',{'time_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'hashes':freeze})
 d,sp,proof=data.load()
 assert proof==json.loads((P/'development_input_gate.json').read_text()),'input proof changed'
 data.dump(P/'evaluated_input_gate.json',proof)
 rows=[]
 def evaluate(c,condname,period):
  if time.time()*1000>=deadline:raise TimeoutError('authorized six hour cap reached')
  key=f'{period}__{c["id"]}__{condname}';path=P/'results_v2'/f'{key}.json.gz';record=P/'results_v2'/f'{key}.summary.json'
  if record.exists():
   r=json.loads(record.read_text());assert r['artifact_sha256']==data.sha(path)
   assert r['candidate']==c['id'] and r['family']==c['family'] and r['condition']==condname and r['period']==period
   assert r['freeze_sha256']==data.sha(P/'evaluation_freeze_v2.json')
   with gzip.open(path,'rt') as f:cached=json.load(f)
   assert r['metrics']==compact(cached['metrics'])
   start,end=map(data.ms,proto[period]);inp={coin:[v for v in vs if start-22*24*3600000<=int(v[0])<end] for coin,vs in d.items()}
   assert r['audit']==replay.verify(inp,sp,c,proto['conditions'][condname],start,end,cached,initial=proto['initial_equity'])
   if time.time()*1000>=deadline:raise TimeoutError('authorized six hour cap reached during cached audit')
   rows.append(r);return r
  start,end=map(data.ms,proto[period]);condition=proto['conditions'][condname]
  # Include only required prehistory and evaluation period, preserving missing hours.
  inp={coin:[v for v in vs if start-22*24*3600000<=int(v[0])<end] for coin,vs in d.items()}
  result=engine.run(inp,sp,c,condition,start,end,proto['initial_equity'])
  audit=replay.verify(inp,sp,c,condition,start,end,result,initial=proto['initial_equity'])
  if time.time()*1000>=deadline:raise TimeoutError('authorized six hour cap reached during evaluation')
  with gzip.open(path,'wt',encoding='utf-8') as f:json.dump(result,f,separators=(',',':'))
  r={'candidate':c['id'],'family':c['family'],'condition':condname,'period':period,'metrics':compact(result['metrics']),'audit':audit,'artifact_sha256':data.sha(path),'freeze_sha256':data.sha(P/'evaluation_freeze_v2.json')}
  data.dump(record,r);rows.append(r)
  print(key,'return',round(r['metrics']['total_return']*100,3),'dd',round(r['metrics']['max_drawdown']*100,3),'trades',r['metrics']['closed_trades'],'audit',audit['status'],flush=True)
  return r
 for period in ('development','validation'):
  for c in proto['candidates']:
   for cond in proto['conditions']:evaluate(c,cond,period)
  for family in ('cash','hold'):
   for cond in proto['conditions']:evaluate({'id':'control_'+family,'family':family},cond,period)
 winners=select(rows,proto['candidates'])
 selection={'selected_ids':winners,'time_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'rule':proto['selection'],'freeze_sha256':data.sha(P/'evaluation_freeze_v2.json'),'validation_summary_hashes':{f.name:data.sha(f) for f in (P/'results_v2').glob('validation*.summary.json')},'confirmation_evaluated_before_selection':False}
 if (P/'selection.json').exists():
  previous=json.loads((P/'selection.json').read_text());selection['time_utc']=previous['time_utc'];assert previous==selection,'selection evidence changed'
 else:data.dump(P/'selection.json',selection)
 promoted=[]
 if winners:
  sealed=json.loads((P/'confirmation_seal.json').read_text())
  for f in sealed['files']:assert data.sha(Path(f['path']))==f['sha256'],'confirmation seal changed'
  d,sp,proof=data.load(confirmation=True)
  data.dump(P/'confirmation_input_gate.json',proof)
  for family in ('cash','hold'):
   for cond in proto['conditions']:evaluate({'id':'control_'+family,'family':family},cond,'confirmation')
  for c in proto['candidates']:
   if c['id'] in winners:
    cr=[evaluate(c,cond,'confirmation') for cond in proto['conditions']]
    control=next(r for r in rows if r['period']=='confirmation' and r['candidate']=='control_hold' and r['condition']=='stress')
    stress=next(r for r in cr if r['condition']=='stress')
    if eligible(cr,15) and control['audit']['status']=='PASS' and stress['metrics']['total_return']>control['metrics']['total_return']:promoted.append(c['id'])
 if time.time()*1000>=deadline:raise TimeoutError('authorized six hour cap reached before completion')
 out={'status':'COMPLETE_CONDITIONAL_RESEARCH','selected':winners,'conditional_pass':promoted,'validated_profitable_strategy':False,'rows':rows,'completed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'limitations':['Historical specs UNKNOWN','Partly seen later period; not fully blind','Current survivors selected; survivorship bias','OHLC fixed-slippage execution proxy; no fill/queue/capacity validation','Independent replay scope as recorded, not independent market/execution proof','SPOT only; futures funding/liquidation UNKNOWN','No confidence claim from parameter winner; prospective preregistered evaluation still required']}
 data.dump(P/'summary.json',out)
 print('COMPLETE selection=',winners,'conditional_pass=',promoted,flush=True)
if __name__=='__main__':main()
