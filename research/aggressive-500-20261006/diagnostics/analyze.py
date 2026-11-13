import gzip,json,statistics,hashlib,collections
from pathlib import Path
from datetime import datetime,timezone
R=Path(__file__).resolve().parent;P=R.parent
f=P/'ledgers/holdout_trend_1_L20_H168_stress.jsonl.gz';rows=[json.loads(v) for v in gzip.open(f,'rt')];assert len(rows)==60
out={'source_sha256':hashlib.sha256(f.read_bytes()).hexdigest(),'mode':'POST_HOC_DESCRIPTIVE_ONLY_NO_RETUNING','groups':{},'zero_details':[],'screen_leverage_comparison':[]}
for label,rr in [('target',[r for r in rows if r['metrics']['target_hit']]),('zero',[r for r in rows if r['metrics']['final_equity']==0]),('other',[r for r in rows if not r['metrics']['target_hit'] and r['metrics']['final_equity']>0])]:
 durations=[];moves=[];atrs=[];dirs=[]
 for r in rr:
  es=[e for e in r['events'] if e['type']=='ENTRY']
  if not es:continue
  e=es[-1];z=r['events'][-1];dirs.append(e['direction']);atrs.append(e['atr_fraction'])
  durations.append((z['timestamp']-e['timestamp'])/3600000)
  px=z.get('price',z.get('adverse_price'));moves.append(e['direction']*(px/e['price']-1))
  if label=='zero':
   q=abs(e['base_delta']);balance=-z['cash_delta'];entry=e['price'];side=e['direction']
   boundary=(q*entry-balance)/(q*.978) if side==1 else (balance+q*entry)/(q*1.022)
   distance=abs(boundary/entry-1)
   out['zero_details'].append({'coin':r['coin'],'fold':r['fold'],'window_start':r['start'],'entry_utc':datetime.fromtimestamp(e['timestamp']/1000,timezone.utc).isoformat(),'side':side,'trade_id':e['trade_id'],'hours':durations[-1],'atr':e['atr_fraction'],'single_trade_stop_distance':2*e['atr_fraction'],'computed_proxy_boundary_distance':distance,'adverse_price_move':moves[-1],'stop_beyond_proxy_boundary':2*e['atr_fraction']>=distance,'phase':z['phase']})
 out['groups'][label]={'accounts':len(rr),'long_last_entry':dirs.count(1),'short_last_entry':dirs.count(-1),'no_entry':sum(not r['metrics']['entry_count'] for r in rr),'entry_counts':dict(collections.Counter(r['metrics']['entry_count'] for r in rr)),'mean_return':statistics.mean(r['metrics']['return'] for r in rr),'mean_fees':statistics.mean(r['metrics']['fees'] for r in rr),'mean_funding':statistics.mean(r['metrics']['funding'] for r in rr),'median_last_trade_hours':statistics.median(durations),'median_last_trade_direction_adjusted_move':statistics.median(moves),'median_entry_atr':statistics.median(atrs),'fold_counts':dict(collections.Counter(r['fold'] for r in rr))}
for lev in (10,20):
 v=json.loads((P/f'screen_trend_1_L{lev}_H168_stress.json').read_text());out['screen_leverage_comparison'].append({'leverage':lev,**v['strategy']})
assert sum(g['accounts'] for g in out['groups'].values())==60
assert len(out['zero_details'])==9
(R/'attribution.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
