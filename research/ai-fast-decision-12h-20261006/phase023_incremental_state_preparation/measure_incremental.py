from pathlib import Path
from collections import Counter
import json,gzip,time,hashlib,statistics,sys,subprocess
import state_v3 as old
from incremental_state import IncrementalState
B=Path(__file__).resolve().parent
def clock():return time.clock_gettime_ns(time.CLOCK_MONOTONIC)
def timed(fn):
 start=clock()
 try:value=fn();error=None
 except Exception as e:value=None;error={'type':type(e).__name__,'message':str(e)}
 end=clock();return value,{'start_OS_ns':start,'end_OS_ns':end,'elapsed_ms':(end-start)/1e6,'error':error}
def save_ingest_failure(directory,row,receipt,records):
 directory=Path(directory);(directory/'failure_receipt.json').write_text(json.dumps({'status':'FAILED_INGEST_STOPPED_NO_UNKNOWN_STATE','row_ordinal':row.get('local_ordinal'),'timing':receipt,'prior_completed_samples':len(records),'actual_AI':None},indent=2));(directory/'timing_partial_early_failure.json').write_text(json.dumps(records,indent=2))
def sizes(obj,seen=None):
 if seen is None:seen=set()
 if id(obj) in seen:return 0
 seen.add(id(obj));n=sys.getsizeof(obj)
 if isinstance(obj,dict):return n+sum(sizes(k,seen)+sizes(v,seen) for k,v in obj.items())
 if isinstance(obj,(list,tuple,set)) or type(obj).__name__=='deque':return n+sum(sizes(v,seen) for v in obj)
 if hasattr(obj,'__dict__'):return n+sizes(obj.__dict__,seen)
 return n
def main():
 p=json.loads((B/'protocol.json').read_text());f=json.loads((B/'execution_freeze.json').read_text())
 for n,h in f['hashes'].items():assert hashlib.sha256((B/n).read_bytes()).hexdigest()==h
 hash_,sourcecheck=timed(lambda:hashlib.sha256(Path(p['source']).read_bytes()).hexdigest());assert hash_==p['source_gzip_sha256'];(B/'source_integrity_receipt.json').write_text(json.dumps({'actual_gzip_sha256':hash_,'expected_sha256':p['source_gzip_sha256'],'match':True,'integrityread_plus_hash_timing':sourcecheck},indent=2))
 registry=json.loads((B/'instruments.json').read_text());boot=subprocess.check_output(['/usr/sbin/sysctl','-n','kern.boottime'],text=True).strip();cache=IncrementalState(registry);rows=[];row_ms=[];records=[];retention=[];load_ms=[];gzip_read_ms=[]
 with gzip.open(p['source'],'rb') as raw:
  while True:
   line,readreceipt=timed(raw.readline);gzip_read_ms.append(readreceipt['elapsed_ms'])
   if not line:break
   row,lr=timed(lambda:json.loads(line));load_ms.append(lr['elapsed_ms']);rows.append(row);_,ir=timed(lambda:cache.ingest(row));row_ms.append(ir['elapsed_ms'])
   if ir['error']:save_ingest_failure(B,row,ir,records);raise RuntimeError(str(ir['error']))
   if len(rows) in p['fixedprefix_points']:
    reference,rr=timed(lambda:old.from_causal_prefix(rows,registry,feature_ns=None,is_live=False));ret=cache.retention();ret['approx_recursive_python_bytes']=sizes(cache);ret['not_rss_or_hard_limit']=True;retention.append(ret)
    for repetition in [1,2,3]:
     snap,sr=timed(lambda:cache.snapshot(feature_ns=None,is_live=False));record={'rows':len(rows),'repetition':repetition,'hot_snapshot':sr,'old_reference_once':rr,'old_reference_success':reference is not None,'validate':None,'serialize':None,'canonical_equal':None,'entire_state_sha256':None,'prefix_hash_equal':cache.prefix_sha256()==old.digest(rows),'is_live':False}
     if snap is not None:
      _,record['validate']=timed(lambda:old.validate(snap));enc,record['serialize']=timed(lambda:old.canonical(snap));record['canonical_equal']=reference is not None and enc==old.canonical(reference);record['entire_state_sha256']=hashlib.sha256(enc).hexdigest();record['reference_state_sha256']=old.digest(reference) if reference is not None else None
     records.append(record)
   if len(rows)==max(p['fixedprefix_points']):break
 observed=sorted(row_ms);(B/'timing_records.json').write_text(json.dumps(records,indent=2));(B/'retention_records.json').write_text(json.dumps(retention,indent=2));(B/'ingest_timing.json').write_text(json.dumps({'rows':len(rows),'total_ingest_ms':sum(row_ms),'perrow_mean_ms':statistics.mean(row_ms),'perrow_median_ms':statistics.median(row_ms),'perrow_p95_ms':observed[int((len(observed)-1)*.95)],'perrow_max_ms':max(row_ms),'JSON_parse_separate_total_ms':sum(load_ms),'gzip_read_decompress_separate_total_ms':sum(gzip_read_ms),'gzip_io_decompression_not_in_ingest_timer':True,'clock_domain_id':'OS_CLOCK_MONOTONIC|boot='+boot},indent=2));(B/'results.json').write_text(json.dumps({'status':'OFFLINE_INCREMENTAL_STATE_EQUIVALENCE_AND_HOT_TIMING','fixed9samples':len(records),'canonical_equal_count':sum(x['canonical_equal'] is True for x in records),'prefixhash_equal_count':sum(x['prefix_hash_equal'] for x in records),'successful_snapshots':sum(x['hot_snapshot']['error'] is None for x in records),'successful_validations':sum(x['validate'] is not None and x['validate']['error'] is None for x in records),'failed_validations':sum(x['validate'] is not None and x['validate']['error'] is not None for x in records),'hot_snapshot_over250ms':sum(x['hot_snapshot']['elapsed_ms']>250 for x in records),'actual_API_latency':None,'no_live_send':True,'original_builder_rule_unchanged':True,'model_new3_registry':'NOT_VALIDATED','globalgoal':'ACTIVE'},indent=2));print([(x['rows'],x['repetition'],round(x['hot_snapshot']['elapsed_ms'],4),x['canonical_equal']) for x in records])
if __name__=='__main__':main()
