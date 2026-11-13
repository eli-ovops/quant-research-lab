from pathlib import Path
from collections import Counter
import json,hashlib,statistics
import evaluator
from cost_shock import run
B=Path(__file__).resolve().parent
def main():
 p=json.loads((B/'protocol.json').read_text());f=json.loads((B/'execution_freeze.json').read_text())
 for n,h in f['hashes'].items():assert hashlib.sha256((B/n).read_bytes()).hexdigest()==h
 specs={x['instId']:x for x in json.loads((B/'instruments.json').read_text())};segments,source=evaluator.mature_source(p['development_source'],specs,f['clock_domain_id']);assert segments is not None and not source['invalid_rows'] and source['logical_sha256']==p['development_raw_sha256'];events=[];out=[];counters=[];nextid=1
 for segid,rows in enumerate(segments):
  es,states,counts=run(rows,specs,f['clock_domain_id'])
  for e in es:e.update(event_id=nextid,segment_id=segid,cohort='CLOSED_JOB006_ALREADY_USED_DEVELOPMENT');nextid+=1
  rr=evaluator.execution.outcomes(es,states,specs)
  for x in rr:x.update(family='COST_CAPABLE_SHOCK_V1',segment_id=segid,cohort='CLOSED_JOB006_ALREADY_USED_DEVELOPMENT',funding_economic_net='UNKNOWN')
  counters.append({'segment_id':segid,**counts});events+=es;out+=rr
 def dump(n,x):(B/n).write_text(json.dumps(x,separators=(',',':')))
 dump('development_events.json',events);dump('development_price_fee_deltas.json',out);dump('development_counters_wait_receipts.json',counters);dump('source_guard_receipt.json',source);summary=[]
 for asset in specs:
  for action in ['FOLLOW','FADE']:
   for fee in [5,10]:
    for delay in [0,250,500,1000,3000]:
     for hold in [15,5,30]:
      xs=[x for x in out if x['asset']==asset and x['action']==action and x['fee_each_side_bps']==fee and x['delay_ms']==delay and x['hold_seconds']==hold];v=sorted(x['price_fee_delta_USDT'] for x in xs if x['status']=='observed');summary.append({'asset':asset,'action':action,'fee_each_side_bps':fee,'delay_ms':delay,'hold_seconds':hold,'events':len(xs),'observed':len(v),'censored':len(xs)-len(v),'mean':statistics.mean(v) if v else None,'median':statistics.median(v) if v else None,'min':min(v) if v else None,'max':max(v) if v else None,'positive_fraction':sum(x>0 for x in v)/len(v) if v else None})
 dump('development_summary.json',summary);dump('results.json',{'status':'NEW_GATE_FROZEN_DEVELOPMENT_AVAILABILITY_ONLY','events_by_asset':{a:sum(e['asset']==a for e in events) for a in specs},'events':len(events),'condition_rows':len(out),'observed':sum(x['status']=='observed' for x in out),'censored':sum(x['status']!='observed' for x in out),'future_job007_result':None,'actual_AI':None,'newfamily_provider_schema':'NOT_IMPLEMENTED noaliasoldfamily','not_account_PnL':True,'global_goal':'ACTIVE'});print({'events':len(events),'assets':Counter(e['asset'] for e in events),'condition_rows':len(out)})
if __name__=='__main__':main()
