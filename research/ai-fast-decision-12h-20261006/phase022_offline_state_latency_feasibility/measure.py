from pathlib import Path
import json,gzip,hashlib,time,datetime,subprocess
import state_v3 as schema
B=Path(__file__).resolve().parent
def clock():return time.clock_gettime_ns(time.CLOCK_MONOTONIC)
def timed(fn):
 start=clock()
 try:value=fn();error=None
 except Exception as exc:value=None;error={'type':type(exc).__name__,'message':str(exc)}
 end=clock();return value,{'start_actual_OS_ns':start,'end_actual_OS_ns':end,'elapsed_ns':end-start,'elapsed_ms':(end-start)/1e6,'status':'PASS' if error is None else 'FAIL','error':error}
def main():
 p=json.loads((B/'protocol.json').read_text());fr=json.loads((B/'execution_freeze.json').read_text())
 for n,h in fr['hashes'].items():assert hashlib.sha256((B/n).read_bytes()).hexdigest()==h
 boot=subprocess.check_output(['/usr/sbin/sysctl','-n','kern.boottime'],text=True).strip();domain='OS_CLOCK_MONOTONIC|boot='+boot
 _,hash_receipt=timed(lambda:hashlib.sha256(Path(p['source']).read_bytes()).hexdigest());assert hashlib.sha256(Path(p['source']).read_bytes()).hexdigest()==p['source_gzip_sha256'];registry=json.loads((B/'instruments.json').read_text());rows=[];prefixes={};loads=[];start=clock()
 with gzip.open(p['source'],'rb') as raw:
  for line in raw:
   rows.append(json.loads(line))
   if len(rows) in p['prefix_points']:
    end=clock();prefixes[len(rows)]=rows.copy();loads.append({'checkpoint_rows':len(rows),'start_actual_OS_ns':start,'end_actual_OS_ns':end,'elapsed_cumulative_ms':(end-start)/1e6,'scope':'gzipread/decompress/JSONparse+checkpointlistcopy separatefrombuilder'})
   if len(rows)==max(p['prefix_points']):break
 assert sorted(prefixes)==p['prefix_points'];records=[]
 for n in p['prefix_points']:
  prefix=prefixes[n]
  for repetition in range(1,p['repetitions_each']+1):
   s,factory=timed(lambda:schema.from_causal_prefix(prefix,registry,feature_ns=None,is_live=False));record={'prefix_rows':n,'repetition':repetition,'source_asof_ordinal':prefix[-1]['local_ordinal'],'source_asset':prefix[-1]['instId'],'factory':factory,'validate':None,'serialize_state':None,'envelope':None,'serialize_envelope':None,'historical_never_sent':True}
   if s is not None:
    assert s['is_live'] is False;_,record['validate']=timed(lambda:schema.validate(s));_,record['serialize_state']=timed(lambda:schema.canonical(s));e,record['envelope']=timed(lambda:schema.build_request(s))
    if e is not None:_,record['serialize_envelope']=timed(lambda:schema.canonical(e));assert e['sendable_payload'] is None
   record['local_factory_within_250ms']=factory['elapsed_ns']<=250000000;record['successful_factory_and_validation']=factory['status']=='PASS' and record['validate'] is not None and record['validate']['status']=='PASS';records.append(record)
 (B/'timing_records.json').write_text(json.dumps(records,indent=2));(B/'loading_records.json').write_text(json.dumps({'compressedfile_integrity_read':hash_receipt,'checkpoints':loads,'clock_domain_id':domain,'boot_identity':boot},indent=2));(B/'results.json').write_text(json.dumps({'status':'REAL_LOCAL_OFFLINE_TIMINGS_ONLY','fixedpoints':p['prefix_points'],'all_repetitions_retained':len(records),'successful_factories':sum(x['factory']['status']=='PASS' for x in records),'failed_factories':sum(x['factory']['status']=='FAIL' for x in records),'local_factory_over250ms':sum(not x['local_factory_within_250ms'] for x in records),'actual_provider_latency':None,'model_calls':0,'actual_live_send':None,'clock_domain_id':domain,'globalgoal':'ACTIVE'},indent=2));print([(x['prefix_rows'],x['repetition'],round(x['factory']['elapsed_ms'],3),x['factory']['status']) for x in records])
if __name__=='__main__':main()
