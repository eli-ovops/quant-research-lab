from pathlib import Path
from collections import Counter,defaultdict
import json,statistics,hashlib,datetime
import run_adapter as old_context
import evaluator
from frozen_cost_shock import run
B=Path(__file__).resolve().parent
def main():
 from prepare_guard import require_authorized
 require_authorized()
 p=json.loads((B/'protocol.json').read_text());f=json.loads((B/'execution_freeze.json').read_text())
 for n,h in f['hashes'].items():assert hashlib.sha256((B/n).read_bytes()).hexdigest()==h
 old_context.main();specs={x['instId']:x for x in json.loads((B/'instruments.json').read_text())};segments,source=evaluator.mature_source(p['source'],specs,p['cost_rule_domain']);assert segments is not None and not source['invalid_rows'] and source['logical_sha256']==p['raw_logical_sha256'];events=[];out=[];counts=[];nextid=1;schema=datetime.datetime.fromisoformat(p['schema016_freeze_UTC']);schemawall=int(schema.timestamp())*1000000000+schema.microsecond*1000
 for segid,rows in enumerate(segments):
  assert all(x['os_shared_ns']>=p['cost_rule_OS_shared_ns'] and x['run_id']==p['run_id'] for x in rows)
  es,states,cc=run(rows,specs,p['cost_rule_domain']);counts.append({'segment_id':segid,**cc})
  for e in es:e.update(event_id=nextid,segment_id=segid,rule_cohort='AFTER_COST_RULE_FREEZE',schema_cohort='POST_SCHEMA016_WALL_FREEZE' if e['source_receive_wall_ns']>=schemawall else 'PRE_SCHEMA016_FREEZE_NO_MODEL_RUN');nextid+=1
  rr=evaluator.execution.outcomes(es,states,specs);emap={e['event_id']:e for e in es}
  for x in rr:x.update(family='COST_CAPABLE_SHOCK_V1',rule_cohort=emap[x['event_id']]['rule_cohort'],schema_cohort=emap[x['event_id']]['schema_cohort'],funding_economic_net='UNKNOWN')
  events+=es;out+=rr
 def dump(n,x):(B/n).write_text(json.dumps(x,separators=(',',':')))
 dump('costshock_events.json',events);dump('costshock_price_fee_deltas.json',out);dump('costshock_WAIT_counters_receipts.json',counts);summary=[]
 for asset in specs:
  for action in ['FOLLOW','FADE']:
   for fee in [5,10]:
    for delay in [0,250,500,1000,3000]:
     for hold in [15,5,30]:
      xs=[x for x in out if x['asset']==asset and x['action']==action and x['fee_each_side_bps']==fee and x['delay_ms']==delay and x['hold_seconds']==hold];v=sorted(x['price_fee_delta_USDT'] for x in xs if x['status']=='observed');summary.append({'asset':asset,'action':action,'fee_each_side_bps':fee,'delay_ms':delay,'hold_seconds':hold,'events':len(xs),'observed':len(v),'censored':len(xs)-len(v),'mean':statistics.mean(v) if v else None,'median':statistics.median(v) if v else None,'min':min(v) if v else None,'max':max(v) if v else None,'positive_fraction':sum(x>0 for x in v)/len(v) if v else None})
 dump('costshock_all_summary.json',summary);r=json.loads((B/'results.json').read_text());r.update(status='CLOSED_JOB007_EIGHT_FIXED_RULES_CONTEXT_AND_CONTROLS',costshock_events_by_asset={a:sum(e['asset']==a for e in events) for a in specs},costshock_events=len(events),costshock_condition_rows=len(out),costshock_observed=sum(x['status']=='observed' for x in out),costshock_censored=sum(x['status']!='observed' for x in out),costshock_schema_cohorts=dict(Counter(e['schema_cohort'] for e in events)),rule_cut_earlier_than_capture=True,schema_cut_later_than_capture_start=True,actual_AI=None,not_account_PnL=True,global_goal='ACTIVE');dump('results.json',r);print({'costshock':len(events),'old_context_counts':r['event_counts'],'newrows':len(out)})
if __name__=='__main__':main()
