from pathlib import Path
import json,ssl,time,uuid,datetime as dt,os,hashlib,subprocess
import websocket
from shared_clock import sample,shared_ns,pair_delta,in_deadline
B=Path(__file__).resolve().parent
def main():
 p=json.loads((B/'protocol.json').read_text());freeze=json.loads((B/'execution_freeze.json').read_text())
 for n,h in freeze['hashes'].items():assert hashlib.sha256((B/n).read_bytes()).hexdigest()==h
 proof=json.loads((B/'clock_proof.json').read_text());assert proof['status']=='PASS_CURRENT_HOST_BOOT_OS_DOMAIN';run_id='ping-'+str(uuid.uuid4());boot=proof['boot_identity'];assert subprocess.check_output(['/usr/sbin/sysctl','-n','kern.boottime'],text=True).strip()==boot;start=sample(run_id,boot);globalwall=dt.datetime.fromisoformat(p['global_deadline_utc']).timestamp();wall_deadline=min(time.time()+20,globalwall);deadline=start['os_shared_ns']+int(max(0,wall_deadline-time.time())*1e9);attempted=0;ws=None;raw=[];samples=[];error=None;stop='completed';close=None;once=B/'ping_once.lock';fd=os.open(once,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600);os.write(fd,str(os.getpid()).encode());os.close(fd)
 (B/'diagnostic_identity.json').write_text(json.dumps({'pid':os.getpid(),'start':start,'deadline_shared_ns':deadline,'wall_deadline_utc':dt.datetime.fromtimestamp(wall_deadline,dt.timezone.utc).isoformat(),'url':p['WS']['url'],'TLS_verify':True,'auth':False,'subscribe':False,'reconnects':0},indent=2));print(json.dumps({'status':'STARTING_PING_ONLY','pid':os.getpid(),'deadline_shared_ns':deadline}),flush=True)
 try:
  before=sample(run_id,boot);remaining=min((deadline-shared_ns())/1e9,wall_deadline-time.time())
  if remaining<=0:raise TimeoutError('deadline_before_connect')
  attempted=1;raw.append({'event':'connect_attempt',**before})
  ws=websocket.create_connection(p['WS']['url'],timeout=min(10,remaining),sslopt={'cert_reqs':ssl.CERT_REQUIRED,'check_hostname':True},http_proxy_host='127.0.0.1',http_proxy_port=7890,proxy_type='http');connected=sample(run_id,boot);cold=pair_delta(before,connected)/1e6
  for i in range(5):
   remaining=min((deadline-shared_ns())/1e9,wall_deadline-time.time())
   if remaining<=0:stop='hard_deadline';break
   ws.settimeout(remaining);sent=sample(run_id,boot);ws.send('ping');raw.append({'event':'send','index':i,'literal':'ping',**sent})
   msg=ws.recv();received=sample(run_id,boot);raw.append({'event':'receive','index':i,'raw':msg,**received})
   if not in_deadline(received['os_shared_ns'],deadline):stop='hard_deadline';break
   if msg!='pong':stop='unknown_message_no_retry';break
   samples.append({'index':i,'RTT_OS_shared_ms':pair_delta(sent,received,20000000000)/1e6,'RTT_same_process_mono_ms':(received['process_monotonic_ns']-sent['process_monotonic_ns'])/1e6,'sent':sent,'received':received})
   if i<4:
    remaining=min((deadline-shared_ns())/1e9,wall_deadline-time.time())
    if remaining<=0:stop='hard_deadline';break
    time.sleep(min(.25,remaining))
 except Exception as e:
  stop='exception_no_retry';error={'type':type(e).__name__,'text':str(e)};cold=None if 'cold' not in locals() else cold
 finally:
  if ws:
   try:ws.close(timeout=3);close='normal_close_returned'
   except Exception as e:close={'type':type(e).__name__,'text':str(e)}
  finish=sample(run_id,boot);(B/'ping_raw.json').write_text(json.dumps(raw,indent=2));result={'at_utc':dt.datetime.now(dt.timezone.utc).isoformat(),'pid':os.getpid(),'connections_attempted':attempted,'subscriptions':0,'auth_messages':0,'reconnects':0,'TLS_verify':True,'start':start,'data_deadline_shared_ns':deadline,'finished':finish,'cold_connection_ms':cold if 'cold' in locals() else None,'samples':samples,'stop_reason':stop,'error':error,'close':close,'close_grace_seconds':3,'probe_not_AI_order_or_HFT':True,'reliable_percentiles':None};(B/'ping_summary.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
if __name__=='__main__':main()

