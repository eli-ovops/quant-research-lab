import json,hashlib
from collections import Counter
import state_v3 as schema
from incremental_state import IncrementalState
from shared_clock import shared_ns
def require_network_authorization(protocol,taskroot=None):
 if protocol.get('execution_mode')!='AUTHORIZED_PUBLIC_LOCAL_PROBE' or protocol.get('network_activation_authorized') is not True or not protocol.get('root_authorization_evidence'):raise RuntimeError('PREPARE_ONLY_NO_NETWORK_AUTHORIZATION')
 from pathlib import Path
 if taskroot is None:raise RuntimeError('MISSING_ROOT_AUTH_CONTEXT')
 root=Path(taskroot).resolve();path=Path(protocol['root_authorization_evidence']).resolve()
 if path!=root/'PMO_PHASE024_PUBLIC_PROBE_AUTHORIZATION.json' or not path.is_file():raise RuntimeError('ACTUAL_ROOT_AUTH_RECEIPT_MISSING')
 receipt=json.loads(path.read_text())
 if receipt.get('approved') is not True or receipt.get('scope')!='phase024_public_local_processing_probe' or receipt.get('WS_once')!=1 or receipt.get('model_API_calls')!=0:raise RuntimeError('ROOT_AUTH_RECEIPT_WRONG_SCOPE')
 if receipt.get('actual_job_directory')!=protocol.get('phase') or receipt.get('max_seconds')!=1800 or receipt.get('fixed_assets')!=9 or receipt.get('no_auto_reconnect') is not True:raise RuntimeError('ROOT_AUTH_CURRENT_JOB_OR_BOUNDS_MISMATCH')
 return receipt
def require_completed_020(taskroot,authorization=None):
 from pathlib import Path
 root=Path(taskroot).resolve();results=json.loads((root/'phase020_job008_fixed_rule_evaluation/results.json').read_text())
 if not str(results.get('status','')).startswith('CLOSED_JOB008_'):raise RuntimeError('020_CLOSED_EVALUATION_NOT_COMPLETE')
 if authorization is None or not authorization.get('evaluation020_acceptance'):raise RuntimeError('020_ACTUAL_EVALUATION_ACCEPTANCE_MISSING')
 path=Path(authorization['evaluation020_acceptance']).resolve()
 if path.parent!=root or not path.name.startswith('PMO_') or not path.is_file():raise RuntimeError('020_ACTUAL_EVALUATION_ACCEPTANCE_MISSING')
 receipt=json.loads(path.read_text())
 if receipt.get('accepted') is not True or receipt.get('scope')!='closed_job008_fixed_rule_evaluation' or receipt.get('source_run_id')!=results.get('current_source_run_id'):raise RuntimeError('020_WRONG_ACCEPTANCE_SCOPE_OR_RUN')
 return True
def validate_registration(protocol,registry):
 assets=protocol.get('assets');channels=protocol.get('channels')
 if not isinstance(assets,list) or len(assets)!=9 or len(set(assets))!=9 or assets!=protocol.get('fixed_assets') or channels!=['books5','trades']:raise RuntimeError('NINE_ASSET_18_CHANNEL_PREFLIGHT_MISMATCH')
 if len(registry)!=9 or {x['instId'] for x in registry}!=set(assets):raise RuntimeError('REGISTRY_ASSET_PREFLIGHT_MISMATCH')
def absent_pid(pid):
 import subprocess
 result=subprocess.run(['ps','-p',str(pid),'-o','pid=,command='],text=True,capture_output=True)
 if result.returncode==1 and not result.stdout.strip() and not result.stderr.strip():return True
 if result.returncode==0 and result.stdout.strip() and not result.stderr.strip():return False
 raise RuntimeError('PID_QUERY_UNKNOWN')
def physical_write_allowed(phase_current,task_current,gzip_projected_closed,gzip_current_physical,extra_file_bytes):
 growth=max(0,gzip_projected_closed-gzip_current_physical)+extra_file_bytes
 return phase_current+growth<=240000000-1000000 and task_current+growth<=2147483648-1000000
def timed(clock,fn):
 begin=clock()
 try:value=fn();error=None
 except Exception as e:value=None;error={'type':type(e).__name__,'message':str(e)}
 end=clock();return value,{'start_OS_ns':begin,'end_OS_ns':end,'elapsed_ns':end-begin,'error':error}
class LocalProbe:
 def __init__(self,registry,identity,clock=shared_ns,label='PUBLIC_LIVE_LOCAL_PROCESSING_NO_MODEL_SEND'):
  self.cache=IncrementalState(registry,identity);self.identity=identity;self.clock=clock;self.label=label;self.anchor={};self.last_slot={};self.counts=Counter()
 def on_received(self,row):
  _,ingest=timed(self.clock,lambda:self.cache.ingest(row));self.counts['received_rows']+=1
  if ingest['error']:self.counts['INVALID_INGEST']+=1;return {'kind':self.label,'status':'INVALID_INGEST_STOP_REQUIRED','source':{k:row.get(k) for k in ['run_id','connectionId','clock_domain_id','local_ordinal','os_shared_ns']},'ingest':ingest,'transport':'DISABLED'}
  asset=row['instId']
  if asset not in self.cache.specs or row['channel'] not in ['books5','trades'] or not json.loads(row['raw']).get('data'):return None
  receive=row['os_shared_ns'];self.anchor.setdefault(asset,receive);slot=(receive-self.anchor[asset])//1000000000
  if slot==self.last_slot.get(asset):return None
  previous=self.last_slot.get(asset,-1);self.last_slot[asset]=slot;self.counts['sampled_rows']+=1;self.counts['sampling_grid_skipped']+=max(0,slot-previous-1)
  state,snapshot=timed(self.clock,lambda:self.cache.snapshot(feature_ns=None,is_live=False));validation=serialization=None;payload_hash=None;state_valid=False;qualified=None;reason=None
  if state is not None:
   state['feature_completed_shared_ns']=snapshot['end_OS_ns'];state['evidence_label']=self.label;_,validation=timed(self.clock,lambda:schema.validate(state));state_valid=validation['error'] is None
   if state_valid:
    encoded,serialization=timed(self.clock,lambda:schema.canonical(state));payload_hash=hashlib.sha256(encoded).hexdigest() if encoded is not None else None;state_valid=serialization['error'] is None;qualified=state['eligibility'];reason=state['rejectreason']
  ready=self.clock();latest=self.cache.features.states[asset].get('latest');book_ns=latest.get('source_os_shared_ns') if latest else None;source_age=ready-receive;book_age=ready-book_ns if isinstance(book_ns,int) else None;ages=(0<=source_age<=250000000 and 0<=book_age<=250000000) if book_age is not None else None;ttl=state_valid and ages is True
  if state_valid:status='QUALIFIED_LOCAL_STATE' if qualified else 'UNQUALIFIED_LOCAL_STATE'
  else:
   error=snapshot['error'] or (validation or {}).get('error') or (serialization or {}).get('error');reason=str(error)
   st=self.cache.features.states[asset]
   if st['flow_unknown'] or self.cache.flow.states.get(asset,{}).get('unknown'):status='SOURCE_CONFLICT_UNKNOWN'
   elif st['firsttrade'] is None or receive/1e6-st['firsttrade']<1000 or not st['times']:status='COLD'
   elif 'COST_DEPTH' in reason:status='DEPTH_UNKNOWN'
   elif 'MISSING_CAUSAL_REFERENCE' in reason:status='STALE_OR_MISSING_REFERENCE'
   else:status='ERROR'
  self.counts[status]+=1
  self.counts['AGES_WITHIN250' if ages is True else 'AGES_EXPIRED' if ages is False else 'AGE_UNKNOWN']+=1
  if not ttl:self.counts['NOT_READY_STATE_AND_AGES']+=1
  if source_age>250000000:self.counts['SLOW_READY']+=1
  return {'kind':self.label,'asset':asset,'slot':slot,'source':{k:row[k] for k in ['run_id','connectionId','clock_domain_id','boot_identity','local_ordinal','os_shared_ns','receive_wall_ns']},'ingest':ingest,'snapshot':snapshot,'validate':validation,'canonical':serialization,'ready_actual_OS_ns':ready,'source_age_at_ready_ns':source_age,'latest_book_shared_ns':book_ns,'latest_book_age_at_ready_ns':book_age,'state_valid':state_valid,'qualified':qualified,'ages_within250ms':ages,'ready_state_and_ages':ttl,'status':status,'reject_or_error':reason,'state_sha256':payload_hash,'is_live':False,'transport':'DISABLED','provider_model_calls':0,'send_timestamp':None}
