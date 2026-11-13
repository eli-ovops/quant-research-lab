from pathlib import Path
from collections import Counter,defaultdict
from decimal import Decimal
import json,gzip,hashlib,subprocess,statistics
from frozen_pressure_rules import PressureRules
import frozen_execution_v12 as core
B=Path(__file__).resolve().parent
def require_execution(protocol):
 if protocol.get('mode')!='AUTHORIZED_CLOSED_ANALYSIS':raise RuntimeError('PREPARE_ONLY_NO_CLOSED_ANALYSIS_AUTHORIZATION')
def stats(values):
 if not values:return {'n':0,'mean':None,'median':None,'min':None,'max':None,'p90':None,'p95':None}
 v=sorted(values);return {'n':len(v),'mean':statistics.mean(v),'median':statistics.median(v),'min':v[0],'max':v[-1],'p90':v[int((len(v)-1)*.9)],'p95':v[int((len(v)-1)*.95)]}
def check_timing(record,row):
 for k in ['local_ordinal','os_shared_ns','receive_wall_ns']:
  if not isinstance(row.get(k),int) or isinstance(row[k],bool):raise ValueError('RAW_CLOCK_OR_ORDINAL_TYPE')
 for k in ['local_ordinal','os_shared_ns','receive_wall_ns']:
  if not isinstance(record['source'].get(k),int) or isinstance(record['source'][k],bool):raise ValueError('TELEMETRY_CLOCK_OR_ORDINAL_TYPE')
 if not isinstance(record.get('ready_actual_OS_ns'),int) or isinstance(record['ready_actual_OS_ns'],bool) or not isinstance(record.get('state_valid'),bool) or not isinstance(record.get('ready_state_and_ages'),bool):raise ValueError('READY_FLAGS_OR_CLOCK_TYPE')
 if record['source']['local_ordinal']!=row['local_ordinal'] or any(record['source'][k]!=row[k] for k in ['run_id','connectionId','clock_domain_id','boot_identity','os_shared_ns','receive_wall_ns']):raise ValueError('TELEMETRY_SOURCE_BINDING')
 previous=row['os_shared_ns']
 for stage in ['ingest','snapshot','validate','canonical']:
  r=record.get(stage)
  if r is None:continue
  if not all(isinstance(r.get(k),int) and not isinstance(r[k],bool) for k in ['start_OS_ns','end_OS_ns','elapsed_ns']) or not previous<=r['start_OS_ns']<=r['end_OS_ns'] or r['elapsed_ns']!=r['end_OS_ns']-r['start_OS_ns']:raise ValueError('ACTUAL_TIMING_CHAIN')
  previous=r['end_OS_ns']
 if record['ready_actual_OS_ns']<previous or record['source_age_at_ready_ns']!=record['ready_actual_OS_ns']-row['os_shared_ns']:raise ValueError('READY_SOURCE_AGE')
 book=record.get('latest_book_shared_ns');age=record.get('latest_book_age_at_ready_ns')
 if book is not None and (not isinstance(book,int) or isinstance(book,bool) or book>row['os_shared_ns']):raise ValueError('LATEST_BOOK_FUTURE_OR_TYPE')
 if book is not None and age!=record['ready_actual_OS_ns']-book:raise ValueError('READY_BOOK_AGE')
 expected=(0<=record['source_age_at_ready_ns']<=250000000 and 0<=age<=250000000) if age is not None else None
 if record['ages_within250ms']!=expected or record['ready_state_and_ages']!=(record['state_valid'] and expected is True):raise ValueError('AGES_STATE_AXES')
 if record['provider_model_calls']!=0 or record['send_timestamp'] is not None or record['is_live'] is not False:raise ValueError('MODEL_SEND_NOT_DISABLED')
 return True
def check_invalid_timing(record,row):
 for k in ['local_ordinal','os_shared_ns']:
  if not isinstance(record['source'].get(k),int) or isinstance(record['source'][k],bool):raise ValueError('INVALID_TELEMETRY_CLOCK_OR_ORDINAL_TYPE')
 for k in ['local_ordinal','run_id','connectionId','clock_domain_id','os_shared_ns']:
  if record['source'].get(k)!=row[k]:raise ValueError('INVALID_TELEMETRY_SOURCE_BINDING')
 r=record['ingest']
 if any(not isinstance(r.get(k),int) or isinstance(r[k],bool) for k in ['start_OS_ns','end_OS_ns','elapsed_ns']) or not row['os_shared_ns']<=r['start_OS_ns']<=r['end_OS_ns'] or r['elapsed_ns']!=r['end_OS_ns']-r['start_OS_ns'] or r.get('error') is None:raise ValueError('INVALID_INGEST_TIMING_MISSING')
 return True
def outcome_summary(rows):
 valid=[r for r in rows if r['status']=='observed'];values=[r['price_fee_delta_USDT'] for r in valid]
 return {'total':len(rows),'valid':len(valid),'unknown_censored':len(rows)-len(valid),'censor_reasons':dict(Counter(r.get('reason') for r in rows if r['status']!='observed')),'mean':statistics.mean(values) if values else None,'median':statistics.median(values) if values else None,'min':min(values) if values else None,'max':max(values) if values else None,'p10':sorted(values)[int((len(values)-1)*.1)] if values else None,'p90':sorted(values)[int((len(values)-1)*.9)] if values else None,'positive_fraction':sum(v>0 for v in values)/len(values) if values else None}
def pressure_summaries(actual,shadows,assets):
 aa=[];ss=[]
 for rule in ['CONTINUATION_FOLLOW_V1','PRESSURE_DECAY_FADE_V1']:
  for asset in assets:
   for fee in [5,10]:
    for delay in [0,250,500,1000,3000]:
     for hold in [15,5,30]:
      key={'rule':rule,'asset':asset,'fee_each_side_bps':fee,'delay_ms':delay,'hold_seconds':hold,'primary':hold==15 and delay==0};select=lambda rows:[r for r in rows if r['family']==rule and r['asset']==asset and r['fee_each_side_bps']==fee and r['delay_ms']==delay and r['hold_seconds']==hold];aa.append({**key,**outcome_summary(select(actual))})
      for action in ['FOLLOW','FADE']:ss.append({**key,'shadow_action':action,**outcome_summary([r for r in select(shadows) if r['action']==action]),'not_actual_registered_branch':True})
 return aa,ss
def load_closed(protocol):
 source=Path(protocol['source']);final=json.loads((source/'collector_final.json').read_text());identity=json.loads((source/'collector_identity.json').read_text());ps=subprocess.run(['ps','-p',str(identity['pid']),'-o','pid=,command='],capture_output=True,text=True)
 if final['status']!='STOPPED' or ps.returncode!=1 or ps.stdout.strip() or ps.stderr.strip() or identity['run_id']!=protocol['expected_run'] or identity['clock_domain_id']!=protocol['expected_domain']:raise ValueError('SOURCE_NOT_CLOSED_OR_IDENTITY_UNKNOWN')
 rows=[];rawsha=hashlib.sha256();logical=0;last=-1;data=Counter();frames=Counter();anchors={};bucketfirst={}
 with gzip.open(source/'raw/ws_messages.jsonl.gz','rb') as raw:
  for line in raw:
   rawsha.update(line);logical+=len(line);r=json.loads(line);rows.append(r)
   if any(not isinstance(r.get(k),int) or isinstance(r[k],bool) for k in ['local_ordinal','os_shared_ns','receive_wall_ns']) or r['local_ordinal']!=len(rows) or r['os_shared_ns']<last or r['run_id']!=identity['run_id'] or r['clock_domain_id']!=identity['clock_domain_id'] or r['boot_identity']!=identity['boot_identity'] or r['connectionId']!=final['connectionId']:raise ValueError('RAW_ORDER_RUN_CLOCK')
   last=r['os_shared_ns'];o=json.loads(r['raw']) if r['raw']!='pong' else {}
   if not isinstance(o,dict) or not isinstance(o.get('arg',{}),dict) or o.get('arg',{}).get('channel')!=r['channel'] or o.get('arg',{}).get('instId')!=r['instId']:raise ValueError('RAW_ARG_OR_SHAPE')
   if r['channel']:frames[r['channel']+'|'+r['instId']]+=1
   if o.get('data'):
    data[r['channel']+'|'+r['instId']]+=1;anchors.setdefault(r['instId'],r['os_shared_ns']);slot=(r['os_shared_ns']-anchors[r['instId']])//1000000000;bucketfirst.setdefault((r['instId'],slot),r['local_ordinal'])
 if len(rows)!=final['messages'] or logical!=final['logical_JSONL_bytes'] or dict(frames)!=final['channel_counts'] or len(data)!=18:raise ValueError('SOURCE_COUNTS_OR_CHANNELS')
 if rawsha.hexdigest()!=protocol['source_raw_sha256']:raise ValueError('SOURCE_FROZEN_RAW_HASH')
 timing=source/'local_processing_timing.jsonl';assert hashlib.sha256(timing.read_bytes()).hexdigest()==protocol['source_telemetry_sha256'];records=[json.loads(x) for x in timing.read_text().splitlines()];sample=Counter();slots=set()
 invalidsaved=0
 for record in records:
  if record.get('status')=='INVALID_INGEST_STOP_REQUIRED':check_invalid_timing(record,rows[record['source']['local_ordinal']-1]);invalidsaved+=1;continue
  check_timing(record,rows[record['source']['local_ordinal']-1]);key=(record['asset'],record['slot'])
  if not isinstance(record['slot'],int) or isinstance(record['slot'],bool) or record['slot']<0:raise ValueError('SLOT_TYPE')
  if key in slots:raise ValueError('DUPLICATE_BUCKET_SAMPLE')
  if bucketfirst.get(key)!=record['source']['local_ordinal']:raise ValueError('NOT_FIRST_MESSAGE_IN_ANCHORED_BUCKET')
  slots.add(key);sample[record['asset']+'|'+record['status']]+=1
 if len(records)!=final['local_processing_samples_rows'] or timing.stat().st_size!=final['local_processing_samples_bytes'] or logical+timing.stat().st_size!=final['combined_raw_telemetry_logical_bytes']:raise ValueError('TELEMETRY_LEDGER_COUNT')
 if final['probe_counts'].get('received_rows')!=len(rows):raise ValueError('ALL_MESSAGE_INGEST_DENOMINATOR')
 if len(records)+final['local_processing_samples_dropped_due_cap']!=final['probe_counts'].get('sampled_rows',0)+final['probe_counts'].get('INVALID_INGEST',0):raise ValueError('SAMPLED_INVALID_DROPPED_DENOMINATOR')
 receipt={'CRC_EOF':True,'raw_rows':len(rows),'raw_logical_bytes':logical,'raw_sha256':rawsha.hexdigest(),'actual_data_channels':dict(data),'telemetry_rows':len(records),'telemetry_dropped_due_cap':final['local_processing_samples_dropped_due_cap'],'saved_invalid_ingest_records':invalidsaved,'final_probe_counts':final['probe_counts'],'all_status_counts':dict(sample),'final_error':final.get('error'),'invalid_finalerror_or_cap_condition':bool(invalidsaved and (final.get('error') is not None or final['local_processing_samples_dropped_due_cap']>0)),'real_duration_seconds':(rows[-1]['os_shared_ns']-rows[0]['os_shared_ns'])/1e9 if rows else None,'model_API_calls':0,'clock_measure_scope':'recv-return localonly notNIC/network/model/transaction'}
 return rows,records,receipt
def main():
 p=json.loads((B/'protocol.json').read_text());require_execution(p);f=json.loads((B/'execution_freeze.json').read_text())
 for n,h in f['hashes'].items():assert hashlib.sha256((B/n).read_bytes()).hexdigest()==h
 rows,records,receipt=load_closed(p);registry=json.loads((B/'instruments.json').read_text());rules=PressureRules(registry,p['rule_domain'],forward_cut_ns=p['rule_cut_OS_shared_ns']);events=[];warm=eligible=0;states={a:{'books':[],'times':[]} for a in p['assets']}
 for row in rows:
  if row['os_shared_ns']<p['rule_cut_OS_shared_ns']:warm+=1
  else:eligible+=1
  result=rules.ingest(row)
  if result and result['qualified_rule']:events.append({'event_id':len(events)+1,'family':result['qualified_rule'],'direction':result['shock_direction'],'asof_ms':result['source_asof_shared_ns']/1e6,**result})
  if row['instId'] in states and row['channel']=='books5':
   for d in json.loads(row['raw']).get('data',[]):
    valid=core.valid_book(d)
    if valid:
     book={'time':row['os_shared_ns']/1e6,'ordinal':row['local_ordinal'],'conn':row['connectionId'],'asks':valid[0],'bids':valid[1]};states[row['instId']]['books'].append(book);states[row['instId']]['times'].append(book['time'])
 shadows=core.outcomes(events,states,{x['instId']:x for x in registry});emap={e['event_id']:e for e in events}
 for r in shadows:r['family']=emap[r['event_id']]['family'];r['registered_action']=emap[r['event_id']]['action']
 actual=[r for r in shadows if r['action']==emap[r['event_id']]['action']];actualsummary,shadowsummary=pressure_summaries(actual,shadows,p['assets'])
 def dump(n,x):(B/n).write_text(json.dumps(x,separators=(',',':')))
 dump('source_timing_receipt.json',receipt);dump('pressure_events.json',events);dump('pressure_shadow_outcomes.json',shadows);dump('pressure_actual_branch_outcomes.json',actual);dump('pressure_reject_counters.json',dict(rules.counters))
 dump('pressure_actual_full_summary.json',actualsummary);dump('pressure_shadow_full_summary.json',shadowsummary)
 pairgroups=defaultdict(dict)
 for r in shadows:pairgroups[(r['event_id'],r['fee_each_side_bps'],r['delay_ms'],r['hold_seconds'])][r['action']]=r
 pair_receipts=[]
 for key,pair in pairgroups.items():
  follow,fade=pair['FOLLOW'],pair['FADE'];status='UNKNOWN_CENSORED';same=None
  if follow['status']=='observed' and fade['status']=='observed':same=Decimal(follow['contracts'])==Decimal(fade['contracts']);status='BOTH_OBSERVED_SAMEQTY' if same else 'BOTH_OBSERVED_QTY_MISMATCH_NOT_STRICTPAIR'
  pair_receipts.append({'event_id':key[0],'fee_each_side_bps':key[1],'delay_ms':key[2],'hold_seconds':key[3],'family':follow['family'],'asset':follow['asset'],'registered_action':follow['registered_action'],'status':status,'same_contract_quantity':same,'FOLLOW_status':follow['status'],'FADE_status':fade['status'],'FOLLOW_contracts':follow.get('contracts'),'FADE_contracts':fade.get('contracts'),'not_perfectbest_or_model_result':True})
 dump('pressure_shadow_pair_receipts.json',pair_receipts)
 group=defaultdict(list)
 for r in records:group[(r.get('asset','UNKNOWN'),r['status'])].append(r)
 timing_summary=[]
 for (a,status),rr in group.items():
  timing_summary.append({'asset':a,'status':status,'samples':len(rr),'state_valid':sum(r.get('state_valid',False) for r in rr),'ages_within250':sum(r.get('ages_within250ms') is True for r in rr),'ready':sum(r.get('ready_state_and_ages',False) for r in rr),'source_age_ms':stats([r['source_age_at_ready_ns']/1e6 for r in rr if 'source_age_at_ready_ns' in r]),'book_age_ms':stats([r['latest_book_age_at_ready_ns']/1e6 for r in rr if r.get('latest_book_age_at_ready_ns') is not None]),'ingest_ms':stats([r['ingest']['elapsed_ns']/1e6 for r in rr if r.get('ingest')]),'snapshot_ms':stats([r['snapshot']['elapsed_ns']/1e6 for r in rr if r.get('snapshot')]),'validate_ms':stats([r['validate']['elapsed_ns']/1e6 for r in rr if r.get('validate')]),'canonical_ms':stats([r['canonical']['elapsed_ns']/1e6 for r in rr if r.get('canonical')])})
 dump('actual_local_timing_summary.json',timing_summary);dump('results.json',{'status':'CLOSED_PUBLIC_LOCAL_TIMING_AND_POSTCUT_PRESSURE_CONDITIONAL_EVALUATION','layerA':receipt,'layerB':{'precut_warmup_rows':warm,'postcut_rows':eligible,'events_by_rule_asset':{family:{a:sum(e['family']==family and e['asset']==a for e in events) for a in p['assets']} for family in ['CONTINUATION_FOLLOW_V1','PRESSURE_DECAY_FADE_V1']},'events':len(events),'actual_branch_rows':len(actual),'shadow_rows':len(shadows),'noevent_means_null':not events},'actual_AI':None,'provider_adapter':'NOT_IMPLEMENTED','not_actual_execution_or_combined_PnL':True,'globalgoal':'ACTIVE'})
if __name__=='__main__':main()
