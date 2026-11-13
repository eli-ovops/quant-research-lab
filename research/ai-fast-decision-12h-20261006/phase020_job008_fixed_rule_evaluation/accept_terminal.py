from pathlib import Path
import json,gzip,hashlib,subprocess,datetime
B=Path(__file__).resolve().parent
def main():
 p=json.loads((B/'protocol.json').read_text());j=Path(p['source']);final=json.loads((j/'collector_final.json').read_text());identity=json.loads((j/'collector_identity.json').read_text());assert final['status']=='STOPPED' and final['pid']==identity['pid'] and final['run_id']==p['run_id'];ps=subprocess.run(['ps','-p',str(identity['pid']),'-o','pid=,command='],text=True,capture_output=True);assert ps.returncode==1 and not ps.stdout.strip() and not ps.stderr.strip()
 n=logical=0;last=-1;channels={};datachannels={};hash_=hashlib.sha256();first100=hashlib.sha256();lastwall=None
 with gzip.open(j/'raw/ws_messages.jsonl.gz','rb') as raw:
  for line in raw:
   hash_.update(line);logical+=len(line);n+=1;r=json.loads(line);assert r['local_ordinal']==n and r['os_shared_ns']>=last and r['run_id']==identity['run_id'] and r['clock_domain_id']==identity['clock_domain_id'] and r['boot_identity']==identity['boot_identity'];last=r['os_shared_ns'];lastwall=r['receive_wall_ns']
   if n<=100:first100.update(line)
   if r['channel']:
    key=r['channel']+'|'+r['instId'];channels[key]=channels.get(key,0)+1
    if json.loads(r['raw']).get('data'):datachannels[key]=datachannels.get(key,0)+1
 assert n==final['messages'] and logical==final['logical_JSONL_bytes'];assert len(channels)==2*len(p['assets']) and channels==final['channel_counts'];assert first100.hexdigest()==hashlib.sha256((j/'first100_messages.jsonl').read_bytes()).hexdigest();gziphash=hashlib.sha256((j/'raw/ws_messages.jsonl.gz').read_bytes()).hexdigest();receipt={'checked_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'STOPPED_TERMINAL_CAPTURE_ACCEPTED_CONDITIONALLY','pid':identity['pid'],'PID_absent':True,'exec_session':57237,'finished_utc':final['finished_utc'],'error':final['error'],'stop_reason':final['stop_reason_planned_untilfinal'],'rows':n,'logical_bytes':logical,'logical_sha256':hash_.hexdigest(),'gzip_bytes':(j/'raw/ws_messages.jsonl.gz').stat().st_size,'gzip_sha256':gziphash,'channels':channels,'ACK_count':len(final['subscription_acks']),'CRC_EOF':True,'ordinal_run_domain_shared_order':True,'last_shared_ns':last,'last_receive_wall_ns':lastwall,'first100_matches':True,'full_market_completeness':'UNKNOWN','strategy_pass':None}
 assert len(datachannels)==2*len(p['assets']) and all(v>0 for v in datachannels.values());receipt['actual_data_channel_counts']=datachannels;receipt['channel_count_semantics']='final includes subscriptionACK frames; data counts separate';receipt['v1_audit_fix']='compared data-onlycounts to collector allchannel frames; assertion evidence retained, no source orstrategy change'
 (j/'terminal_receipt.json').write_text(json.dumps(receipt,indent=2));(B/'capture_terminal_receipt.json').write_text(json.dumps(receipt,indent=2));current=j.parent/'CURRENT_CAPTURE.json';(j.parent/'CURRENT_CAPTURE_before_job008_terminal.json').write_bytes(current.read_bytes());current.write_text(json.dumps({**receipt,'current_directory':str(j),'global_goal':'ACTIVE'},indent=2));print(receipt)
if __name__=='__main__':main()
