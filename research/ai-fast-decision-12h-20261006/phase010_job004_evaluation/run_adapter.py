from pathlib import Path
from collections import Counter,defaultdict
import json,hashlib,datetime,statistics
import evaluator as ev
B=Path(__file__).resolve().parent
FAMILIES=['FLOW_IMPULSE','BOOK_STATE','BTC_TRANSMISSION']
def dump(name,x): (B/name).write_text(json.dumps(x,separators=(',',':')))
def stats(values):
 if not values:return {'n':0,'mean':None,'median':None,'minimum':None,'maximum':None,'positive_fraction':None}
 v=sorted(values);return {'n':len(v),'mean':statistics.mean(v),'median':statistics.median(v),'minimum':v[0],'maximum':v[-1],'p10':v[int((len(v)-1)*.1)],'p90':v[int((len(v)-1)*.9)],'positive_fraction':sum(x>0 for x in v)/len(v)}
def main():
 p=json.loads((B/'protocol.json').read_text());freeze=json.loads((B/'execution_freeze.json').read_text())
 for n,h in freeze['hashes'].items():assert hashlib.sha256((B/n).read_bytes()).hexdigest()==h
 old=json.loads((B/'original_suite_freeze.json').read_text());specs={x['instId']:x for x in json.loads((B/'instruments.json').read_text())}
 segments,source=ev.mature_source(p['source'],specs,old['clock_domain_id']);dump('source_guard_receipt.json',source)
 assert segments is not None and not source['invalid_rows'] and source['logical_sha256']==p['source_logical_sha256']
 assert source['identity']['run_id']==p['authorized_run']
 binding={**old,'capture_run_id':p['authorized_run']}
 assert all(ev.suite.forward_eligible(r,binding) for seg in segments for r in seg)
 captured=[];original_run=ev.suite.run_signals
 def run_with_receipt(rows,specs,domain):
  result=original_run(rows,specs,domain);captured.append({'segment_id':len(captured),'rows':len(rows),'run_id':rows[0]['run_id'],'connectionId':rows[0]['connectionId'],'counters':result[2]});return result
 ev.suite.run_signals=run_with_receipt
 events,out,matches=ev.evaluate(segments,specs,old,'JOB004_AFTER_SUITE_FREEZE_NEW_RECEIVED_EPISODE')
 dump('events.json',events);dump('event_deltas.json',out);dump('matched_controls.json',matches);dump('segment_counters.json',captured)
 primary=[];diagnostic=[];groups=defaultdict(list)
 for x in out:groups[(x['family'],x['asset'],x['action'],x['fee_each_side_bps'],x['delay_ms'],x['hold_seconds'])].append(x)
 for family in FAMILIES:
  for asset in specs:
   for action in ['FOLLOW','FADE']:
    for fee in [5,10]:
     for delay in [0,250,500,1000,3000]:
      for hold in [5,15,30]:
       rows=groups[(family,asset,action,fee,delay,hold)];obs=[x for x in rows if x['status']=='observed'];summary={'family':family,'asset':asset,'action':action,'fee_each_side_bps':fee,'delay_ms':delay,'hold_seconds':hold,'events':len(rows),'observed':len(obs),'censored':len(rows)-len(obs),'censor_reasons':dict(Counter(x.get('reason',x['status']) for x in rows if x['status']!='observed')),'price_fee_delta_USDT':stats([x['price_fee_delta_USDT'] for x in obs]),'break_even_fee_each_side_bps':stats([x['break_even_fee_each_side_bps'] for x in obs]),'funding_cash':'UNKNOWN'}
       (primary if hold==15 else diagnostic).append(summary)
 dump('primary_summary.json',primary);dump('diagnostic_summary.json',diagnostic)
 clusters=[]
 for e in sorted(events,key=lambda x:x['asof_ms']):
  if not clusters or e['asof_ms']-clusters[-1]['first_ms']>100:clusters.append({'first_ms':e['asof_ms'],'event_ids':[],'assets':[]})
  clusters[-1]['event_ids'].append(e['event_id']);clusters[-1]['assets'].append(e['asset'])
 dump('receive_time_clusters.json',{'definition':'100ms fromfirst cluster event, descriptive not independent N','clusters':clusters})
 dump('results.json',{'status':'CONDITIONAL_EVENT_EVALUATION','cohort':'JOB004_AFTER_SUITE_FREEZE_NEW_RECEIVED_EPISODE','event_counts':{f:sum(e['family']==f for e in events) for f in FAMILIES},'rows':len(out),'observed':sum(x['status']=='observed' for x in out),'censored':sum(x['status']!='observed' for x in out),'segments':len(segments),'matched':sum(m['control'] is not None for m in matches),'unmatched':sum(m['control'] is None for m in matches),'matched_controls_share':dict(Counter(str(m['control']['control_id']) for m in matches if m['control'])),'actual_AI_results':None,'model_calls':0,'not_account_PnL':True,'economic_financing_net':'UNKNOWN','global_goal':'ACTIVE','finished_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()})
 print({'events':len(events),'counts':Counter(e['family'] for e in events),'outcomes':len(out),'matches':len(matches)})
if __name__=='__main__':main()
