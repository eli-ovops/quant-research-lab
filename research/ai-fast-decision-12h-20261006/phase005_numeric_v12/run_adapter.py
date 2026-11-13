from pathlib import Path
from collections import defaultdict
import json,hashlib,datetime as dt,math
import frozen_core as core
B=Path(__file__).resolve().parent
def utc_ns(text):
 d=dt.datetime.fromisoformat(text.replace('Z','+00:00'));delta=d-dt.datetime(1970,1,1,tzinfo=dt.timezone.utc);return ((delta.days*86400+delta.seconds)*1000000+delta.microseconds)*1000
def cohort(ordinal,wall_ns,cutoff):
 if ordinal<=20000:return 'dev_prefix'
 return 'prefreeze_remainder' if wall_ns<cutoff else 'postfreeze_new'
def dedup_records(row,seen):
 if row['channel']!='trades':return row,0,0
 o=json.loads(row['raw']);keep=[];duplicates=conflicts=0
 for d in o.get('data',[]):
  key=(row['instId'],d.get('tradeId'),d.get('source'))
  if d.get('tradeId') is None:keep.append(d);continue
  signature=(d.get('px'),d.get('sz'),d.get('side'),d.get('ts'),d.get('count'))
  if key in seen:
   if seen[key]==signature:duplicates+=1
   else:conflicts+=1
  else:seen[key]=signature;keep.append(d)
 if duplicates or conflicts:
  o['data']=keep;row={**row,'raw':json.dumps(o,separators=(',',':'))}
 return row,duplicates,conflicts
def quantiles(values):
 if not values:return {'n':0,'mean':None,'median':None,'p05':None,'p95':None,'min':None,'max':None,'positive_fraction':None}
 a=sorted(values);n=len(a);return {'n':n,'mean':sum(a)/n,'median':(a[(n-1)//2]+a[n//2])/2,'p05':a[int((n-1)*.05)],'p95':a[int((n-1)*.95)],'min':a[0],'max':a[-1],'positive_fraction':sum(x>0 for x in a)/n,'empirical_not_reliable_population_tail':True}
def main():
 p=json.loads((B/'protocol.json').read_text());f=json.loads((B/'execution_freeze.json').read_text());inp=json.loads((B/'input_freeze.json').read_text())
 for n,h in f['hashes'].items():assert hashlib.sha256((B/n).read_bytes()).hexdigest()==h
 assert inp['collector_STOPPED'] and inp['session_completed'] and inp['PID_exited'];source=Path(p['source_live_until_stop']);blob=source.read_bytes();assert hashlib.sha256(blob).hexdigest()==inp['sha256'];specs={s['instId']:s for s in json.loads((B/'instruments.json').read_text())};rows=[];byord={};seen={};dups=conflicts=0;channel=defaultdict(list);drifts=[];jumps=[];prev=None;volume=defaultdict(float);countdiag=defaultdict(int);tradeIdMissing=0
 for raw in blob.splitlines():
  original=json.loads(raw);byord[original['local_ordinal']]=original;r,d,c=dedup_records(original,seen);dups+=d;conflicts+=c;rows.append(r);key=str(r['channel'])+'|'+str(r['instId']);channel[key].append(r['monotonic_ns']/1e6)
  if prev:
   drift=(r['receive_wall_ns']-prev['receive_wall_ns']-(r['monotonic_ns']-prev['monotonic_ns']))/1e6;drifts.append(drift)
   if abs(drift)>50:jumps.append({'ordinal':r['local_ordinal'],'wall_minus_processmono_delta_ms':drift})
  prev=r;o=json.loads(r['raw'])
  if r['channel']=='trades':
   a=r['instId'];unit=float(specs[a]['ctVal'])*float(specs[a]['ctMult'])
   for d in o.get('data',[]):
    volume[a]+=float(d['sz'])*unit;countdiag[a]+=int(d.get('count',1));tradeIdMissing+=d.get('tradeId') is None
 quality={'rows':len(rows),'source_bytes':len(blob),'source_sha256':inp['sha256'],'duplicate_identical_trade_groups_removed':dups,'conflicting_trade_identity':conflicts,'tradeId_missing':tradeIdMissing,'trade_identity':'instId/tradeId/source exactrepeat dropfirstretain; conflictingkey dataINVALID; seqIdnotdedup','volume_underlying_qty_sz_ctVal_ctMult':dict(volume),'aggregation_count_not_volume_multiplier':dict(countdiag),'wall_processmono_drift_adjacent_ms':quantiles(drifts),'wall_jump_gt50ms':jumps,'channel_receive_gaps_ms':{k:quantiles([b-a for a,b in zip(v,v[1:])]) for k,v in channel.items()},'oldprocess_monotonic_NOT_OS_shared':True,'fullmarketcompleteness':'UNKNOWN','funding_noactualcash':True}
 (B/'capture_quality.json').write_text(json.dumps(quality,indent=2));events,states,counters=core.triggers(rows,specs);cut=utc_ns(p['cohort_asof_cutoff_UTC'])
 for e in events:e.update(cohort=cohort(e['asof_ordinal'],byord[e['asof_ordinal']]['receive_wall_ns'],cut),asof_receive_wall_ns=byord[e['asof_ordinal']]['receive_wall_ns'],data_validity='INVALID_WALL_JUMP_OR_DUPCONFLICT' if jumps or conflicts else 'CONDITIONAL_CAPTURE')
 result=core.outcomes(events,states,specs);emap={e['event_id']:e for e in events};funding=json.loads((B/'funding_times.json').read_text())
 for r in result:
  e=emap[r['event_id']];r['cohort']=e['cohort'];r['data_validity']=e['data_validity'];r['financing_economic_net']='UNKNOWN rateflags only no realmark/accountcash'
  if r['status']=='observed':
   en=byord[r['entry_ordinal']]['receive_wall_ns']/1e6;ex=byord[r['exit_ordinal']]['receive_wall_ns']/1e6;times=funding['assets'].get(r['asset'],{}).get('history',[]);between=[x for x in times if en<=x['fundingTime_ms']<=ex];possible=[x for x in times if en-600<=x['fundingTime_ms']<=ex+600];r['funding_settlement_receive_window']=between;r['funding_near_boundary600ms_diagnostic']=possible;r['entry_receive_wall_ms']=en;r['exit_receive_wall_ms']=ex
   r['funding_time_evidence']=funding['assets'].get(r['asset'],{}).get('status','UNKNOWN')
  else:r['funding_time_evidence']='UNKNOWN incompleteentryexit'
 summaries=[]
 for asset in specs:
  for co in ['dev_prefix','prefreeze_remainder','postfreeze_new']:
   for action in ['FOLLOW','FADE']:
    for delay in [0,250,500,1000,3000]:
     for hold in [15,5,30]:
      for fee in [5,10]:
       subset=[r for r in result if (r['asset'],r['cohort'],r['action'],r['delay_ms'],r['hold_seconds'],r['fee_each_side_bps'])==(asset,co,action,delay,hold,fee)];vals=[r['price_fee_delta_USDT'] for r in subset if r['status']=='observed'];summaries.append({'asset':asset,'cohort':co,'action':action,'delay_ms':delay,'hold_seconds':hold,'fee_each_side_bps':fee,'observed':len(vals),'censored':len(subset)-len(vals),'event_delta_statistics':quantiles(vals),'not_account_PnL':True})
 clusters=[]
 for e in sorted(events,key=lambda e:e['asof_receive_wall_ns']):
  if not clusters or e['asof_receive_wall_ns']-clusters[-1]['first_wall_ns']>100000000:clusters.append({'first_wall_ns':e['asof_receive_wall_ns'],'event_ids':[],'assets':[]})
  clusters[-1]['event_ids'].append(e['event_id']);clusters[-1]['assets'].append(e['asset'])
 (B/'events.json').write_text(json.dumps(events,indent=2));(B/'event_price_fee_deltas.json').write_text(json.dumps(result,indent=2));(B/'summary.json').write_text(json.dumps(summaries,indent=2));(B/'event_clusters.json').write_text(json.dumps(clusters,indent=2));(B/'results.json').write_text(json.dumps({'status':'CONDITIONAL_FULL_CAPTURE_EVENT_STUDY','events':len(events),'cohort_counts':{co:sum(e['cohort']==co for e in events) for co in ['dev_prefix','prefreeze_remainder','postfreeze_new']},'counters':counters,'clusters100ms':len(clusters),'not_account_PnL':True,'actual_AI_results':None,'quality':'capture_quality.json','financing':'UNKNOWN flagsnotcash','source_sha256':inp['sha256']},indent=2));print({'events':len(events),'outcomes':len(result),'dups':dups,'conflicts':conflicts,'walljumps':len(jumps)})
if __name__=='__main__':main()

