from pathlib import Path
from collections import Counter,defaultdict
import json,hashlib,statistics
import evaluator as ev
from controls import own_momentum,grid_candidates
B=Path(__file__).resolve().parent
def dump(n,x):(B/n).write_text(json.dumps(x,separators=(',',':')))
def stats(rows):
 obs=[x['price_fee_delta_USDT'] for x in rows if x['status'] in ['observed','WAIT_TRUE_ZERO']];v=sorted(obs)
 return {'total':len(rows),'observed_or_truewait':len(v),'truewait':sum(x['status']=='WAIT_TRUE_ZERO' for x in rows),'unknown_or_censored':len(rows)-len(v),'statuses':dict(Counter(x['status'] if x['status']!='censored' else x.get('reason') for x in rows)),'mean':statistics.mean(v) if v else None,'median':statistics.median(v) if v else None,'min':min(v) if v else None,'max':max(v) if v else None,'p10':v[int((len(v)-1)*.1)] if v else None,'p90':v[int((len(v)-1)*.9)] if v else None,'positive_fraction':sum(x>0 for x in v)/len(v) if v else None}
def main():
 p=json.loads((B/'protocol.json').read_text());fr=json.loads((B/'execution_freeze.json').read_text())
 for n,h in fr['hashes'].items():assert hashlib.sha256((B/n).read_bytes()).hexdigest()==h
 old=json.loads((B/'original_suite_freeze.json').read_text());specs={x['instId']:x for x in json.loads((B/'instruments.json').read_text())};segments,receipt=ev.mature_source(p['source'],specs,old['clock_domain_id']);assert segments is not None and not receipt['invalid_rows'] and receipt['logical_sha256']==p['raw_logical_sha256'];binding={**old,'capture_run_id':p['run_id']};assert all(ev.suite.forward_eligible(r,binding) for seg in segments for r in seg)
 all_events=[];all_signal=[];all_a=[];all_b=[];all_be=[];rejects=[];counters=[];clusters=[];a_features=[];nextid=1
 for segid,rows in enumerate(segments):
  events,states,cc=ev.suite.run_signals(rows,specs,old['clock_domain_id']);counters.append({'segment_id':segid,'run_id':rows[0]['run_id'],'connectionId':rows[0]['connectionId'],'counters':cc})
  for e in events:e.update(event_id=nextid,segment_id=segid);nextid+=1
  signal=ev.execution.outcomes(events,states,specs);emap={e['event_id']:e for e in events}
  for x in signal:x.update(family=emap[x['event_id']]['family'],segment_id=segid,financing='UNKNOWN')
  for e in events:
   feature=own_momentum(e,states[e['asset']]);a_features.append({'event_id':e['event_id'],'asset':e['asset'],'family':e['family'],'asof_ordinal':e['asof_ordinal'],**feature})
   for fee in [5,10]:
    base={'event_id':e['event_id'],'asset':e['asset'],'family':e['family'],'fee_each_side_bps':fee,'delay_ms':0,'hold_seconds':15,'baseline':'A_OWN_1S_MOMENTUM','segment_id':segid,'not_account_PnL':True}
    if feature['direction'] is None:all_a.append({**base,'status':feature['status'],'price_fee_delta_USDT':None})
    elif feature['direction']==0:all_a.append({**base,'status':'WAIT_TRUE_ZERO','price_fee_delta_USDT':0,'fee_USDT':0,'no_trade':True})
    else:
     action='FOLLOW' if feature['direction']==e['direction'] else 'FADE';x=next(x for x in signal if x['event_id']==e['event_id'] and x['action']==action and x['fee_each_side_bps']==fee and x['hold_seconds']==15 and x['delay_ms']==0);all_a.append({**x,**base,'own_direction':feature['direction'],'matched_signal_action':action})
  be,br=grid_candidates(states,p['run_id'],rows[0]['os_shared_ns']/1e6,rows[-1]['os_shared_ns']/1e6)
  for e in be:e['segment_id']=segid
  bo=[x for x in ev.execution.outcomes(be,states,specs) if x['action']=='FOLLOW' and x['delay_ms']==0 and x['hold_seconds']==15]
  for x in bo:x.update(baseline='B_FIXED_TIMEGRID_SEEDED_DIRECTION',segment_id=segid,not_matched_causal_control=True)
  all_events+=events;all_signal+=signal;all_be+=be;all_b+=bo;rejects+=br
 dump('events.json',all_events);dump('event_deltas.json',all_signal);dump('baseline_A_features.json',a_features);dump('baseline_A_outcomes.json',all_a);dump('baseline_B_events.json',all_be);dump('baseline_B_outcomes.json',all_b);dump('baseline_B_grid_rejections.json',rejects);dump('segment_counters.json',counters);dump('source_guard_receipt.json',receipt)
 summary=[];full=[]
 for family in ev.suite.FAMILIES:
  for asset in specs:
   for fee in [5,10]:
    aa=[x for x in all_a if x['family']==family and x['asset']==asset and x['fee_each_side_bps']==fee]
    for action in ['FOLLOW','FADE']:
     ss=[x for x in all_signal if x['family']==family and x['asset']==asset and x['fee_each_side_bps']==fee and x['action']==action and x['delay_ms']==0 and x['hold_seconds']==15];summary.append({'family':family,'asset':asset,'action':action,'fee_each_side_bps':fee,'signal_primary':stats(ss),'baseline_A_same_signal_timestamps':stats(aa)})
    for action in ['FOLLOW','FADE']:
     for delay in [0,250,500,1000,3000]:
      for hold in [15,5,30]:full.append({'family':family,'asset':asset,'action':action,'fee_each_side_bps':fee,'delay_ms':delay,'hold_seconds':hold,'stats':stats([x for x in all_signal if x['family']==family and x['asset']==asset and x['fee_each_side_bps']==fee and x['action']==action and x['delay_ms']==delay and x['hold_seconds']==hold])})
 bb=[{'asset':asset,'fee_each_side_bps':fee,'stats':stats([x for x in all_b if x['asset']==asset and x['fee_each_side_bps']==fee])} for asset in specs for fee in [5,10]]
 dump('primary_vs_A_summary.json',summary);dump('all_signal_summary.json',full);dump('B_timegrid_summary.json',bb)
 for e in sorted(all_events,key=lambda x:x['asof_ms']):
  if not clusters or e['asof_ms']-clusters[-1]['first_ms']>100:clusters.append({'first_ms':e['asof_ms'],'event_ids':[],'assets':[]})
  clusters[-1]['event_ids'].append(e['event_id']);clusters[-1]['assets'].append(e['asset'])
 dump('time_clusters.json',{'definition':'100ms from first; correlated/overlap not independentN','clusters':clusters});dump('results.json',{'status':'SECOND_NEW_EPISODE_FIXED_RULES_AND_DEVELOPMENT_CONTROLS','event_counts':{f:sum(e['family']==f for e in all_events) for f in ev.suite.FAMILIES},'signal_condition_rows':len(all_signal),'signal_observed':sum(x['status']=='observed' for x in all_signal),'signal_censored':sum(x['status']!='observed' for x in all_signal),'A_conditions':len(all_a),'B_grid_events':len(all_be),'B_grid_rejected':len(rejects),'B_conditions':len(all_b),'segments':len(segments),'actual_AI':None,'model_calls':0,'not_account_PnL':True,'baselines_not_matched_causal_trials':True,'global_goal':'ACTIVE'});print({'events':len(all_events),'B_grid':len(all_be),'B_rejected':len(rejects)})
if __name__=='__main__':main()
