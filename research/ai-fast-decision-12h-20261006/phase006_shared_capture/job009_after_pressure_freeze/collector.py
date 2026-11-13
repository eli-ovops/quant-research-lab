from pathlib import Path
import os,time,json,hashlib,datetime as dt,ssl,signal,subprocess,gzip
import websocket
from bounded_gzip import BoundedGzipWriter
from shared_clock import shared_ns
B=Path(__file__).resolve().parent;TASK_ROOT=B.parent.parent;UTC=dt.timezone.utc
def write_json(path,obj):path.write_text(json.dumps(obj,indent=2))
def task_bytes():return sum(p.stat().st_size for p in TASK_ROOT.rglob('*') if p.is_file())
def absent_pid(pid):
 result=subprocess.run(['ps','-p',str(pid),'-o','pid=,command='],capture_output=True,text=True)
 if result.returncode==1 and not result.stdout.strip() and not result.stderr.strip():return True
 if result.returncode==0 and result.stdout.strip() and not result.stderr.strip():return False
 raise RuntimeError('PID_QUERY_UNKNOWN')
def main():
 proto=json.loads((B/'protocol.json').read_text());freeze=json.loads((B/'execution_freeze.json').read_text())
 for n,h in freeze['hashes'].items():assert hashlib.sha256((B/n).read_bytes()).hexdigest()==h
 old=json.loads((TASK_ROOT/'phase001_readiness/collector_final.json').read_text());assert old['status']=='STOPPED'
 previous=json.loads((B.parent/'job002_corrected_cap/collector_final.json').read_text());assert previous['status']=='STOPPED'
 third=json.loads((B.parent/'job003_after_suite_freeze/collector_final.json').read_text());assert third['status']=='STOPPED'
 assert absent_pid(35525)
 assert absent_pid(32079)
 fourth=json.loads((B.parent/'job004_after_diagnostic/collector_final.json').read_text());assert fourth['status']=='STOPPED'
 assert absent_pid(36575)
 assert absent_pid(36315)
 assert absent_pid(32689)
 assert absent_pid(26221)
 fifth=json.loads((B.parent/'job005_after_job004_terminal/collector_final.json').read_text());assert fifth['status']=='STOPPED'
 assert absent_pid(42092)
 sixth=json.loads((B.parent/'job006_fixed_universe_expansion/collector_final.json').read_text());assert sixth['status']=='STOPPED'
 assert absent_pid(48225)
 seventh=json.loads((B.parent/'job007_after_cost_shock_freeze/collector_final.json').read_text());assert seventh['status']=='STOPPED'
 assert absent_pid(51279)
 eighth=json.loads((B.parent/'job008_after_fixed_meme_readiness/collector_final.json').read_text());assert eighth['status']=='STOPPED'
 assert absent_pid(54627)
 probe25=json.loads((TASK_ROOT/'phase025_public_input_latency_probe/collector_final.json').read_text());assert probe25['status']=='STOPPED' and probe25['error'] is None
 assert absent_pid(58613)
 accept20=json.loads((TASK_ROOT/'PMO_PHASE020_CLOSED_EVALUATION_ACCEPTANCE.json').read_text());assert accept20['accepted'] is True and accept20['scope']=='closed_job008_fixed_rule_evaluation'
 accept27=json.loads((TASK_ROOT/'PMO_PHASE027_ACCEPTANCE.json').read_text());assert accept27.get('accepted') is True or str(accept27.get('status','')).startswith('ACCEPTED')
 proof=json.loads((B/'clock_proof.json').read_text());boot=subprocess.check_output(['/usr/sbin/sysctl','-n','kern.boottime'],text=True).strip();assert boot==proof['boot_identity'],'BOOT_DOMAIN_CHANGED'
 clockid=proof['checks'][0]['parent_before']['clock_domain_id']
 fd=os.open(B/'collector_once.lock',os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600);os.write(fd,str(os.getpid()).encode());os.close(fd)
 startwall=time.time();startOS=shared_ns();globalwall=dt.datetime.fromisoformat('2026-10-07T03:16:33+00:00').timestamp();stopwall=min(startwall+2700,globalwall);stopOS=startOS+int((stopwall-startwall)*1e9);job='phase006-'+str(os.getpid())+'-'+str(int(startwall));maximum=min(230000000,240000000-sum(p.stat().st_size for p in B.parent.rglob('*') if p.is_file())-5000000,2147483648-task_bytes()-10000000);logicalmax=240000000
 identity={'pid':os.getpid(),'job_id':job,'run_id':job,'start_utc':dt.datetime.fromtimestamp(startwall,UTC).isoformat(),'stop_at_utc':dt.datetime.fromtimestamp(stopwall,UTC).isoformat(),'stop_OS_shared_ns':stopOS,'clock_domain_id':clockid,'boot_identity':boot,'maximum_gzip_file_bytes':maximum,'maximum_logical_JSONL_bytes':logicalmax,'global_task_bytes_max':2147483648,'global_task_bytes_atstart':task_bytes(),'format':'gzip JSONL directlynewstream notoldfilecompression','source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'auth':False,'TLS_verify':True,'automatic_reconnects':0,'url':'wss://ws.okx.com:8443/ws/v5/public','close_grace_seconds':3}
 write_json(B/'collector_identity.json',identity);print(json.dumps({'status':'STARTING',**identity}),flush=True)
 n=0;logical=0;compressed=0;conn=None;counts={};acks=[];error=None;reason='deadline';ws=None;rawfile=None;gz=None;initial=None;laststatus=0;lastrecv=shared_ns();lastping=0;terminate=[False];skewmax=0;skewmin=None
 def sig(*_):terminate[0]=True
 signal.signal(signal.SIGTERM,sig);signal.signal(signal.SIGINT,sig)
 def status(state):
  s={**identity,'status':state,'at_utc':dt.datetime.now(UTC).isoformat(),'messages':n,'logical_JSONL_bytes':logical,'gzip_file_bytes':compressed,'connectionId':conn,'channel_counts':counts,'subscription_acks':acks,'sampling_OS_bracket_ns_min':skewmin,'sampling_OS_bracket_ns_max':skewmax,'stop_reason_planned_untilfinal':reason,'error':error};write_json(B/'collector_status.json',s);return s
 try:
  if identity['global_task_bytes_atstart']>=2147483648-10000000:raise RuntimeError('GLOBAL_STORAGE_HEADROOM_INSUFFICIENT')
  remaining=min((stopOS-shared_ns())/1e9,stopwall-time.time());assert remaining>0
  ws=websocket.create_connection(identity['url'],timeout=min(10,remaining),sslopt={'cert_reqs':ssl.CERT_REQUIRED,'check_hostname':True},http_proxy_host='127.0.0.1',http_proxy_port=7890,proxy_type='http');ws.settimeout(3);ws.send(json.dumps({'op':'subscribe','args':[{'channel':c,'instId':a} for a in proto['assets'] for c in proto['channels']]}))
  (B/'raw').mkdir();gz=BoundedGzipWriter(B/'raw/ws_messages.jsonl.gz',maximum);initial=(B/'first100_messages.jsonl').open('x');status('CONNECTED_SUBSCRIBE_SENT')
  while time.time()<stopwall and shared_ns()<stopOS and not terminate[0]:
   remaining=min((stopOS-shared_ns())/1e9,stopwall-time.time())
   if remaining<=0:break
   ws.settimeout(min(3,remaining))
   try:raw=ws.recv()
   except websocket.WebSocketTimeoutException:
    now=shared_ns()
    if now-lastrecv>20000000000 and now-lastping>20000000000:ws.send('ping');lastping=now
    if now-lastrecv>60000000000:reason='no_message_60s';break
    continue
   osbefore=shared_ns();wallns=time.time_ns();processns=time.monotonic_ns();osafter=shared_ns();skew=osafter-osbefore;skewmax=max(skewmax,skew);skewmin=skew if skewmin is None else min(skewmin,skew);lastrecv=osafter
   if not raw:reason='remote_close';break
   if isinstance(raw,bytes):raw=raw.decode('utf-8')
   try:o=json.loads(raw)
   except json.JSONDecodeError:o={}
   arg=o.get('arg',{});channel=arg.get('channel');asset=arg.get('instId')
   if o.get('connId'):conn=o['connId']
   if o.get('event')=='subscribe':acks.append(arg)
   row={'local_ordinal':n+1,'receive_wall_ms':wallns/1e6,'receive_wall_ns':wallns,'monotonic_ns':processns,'process_monotonic_ns':processns,'os_shared_ns':osbefore,'os_shared_after_sampling_ns':osafter,'clock_domain_id':clockid,'boot_identity':boot,'run_id':job,'sampling_OS_bracket_ns':skew,'channel':channel,'instId':asset,'exchange_ts':[d.get('ts') for d in o.get('data',[]) if isinstance(d,dict)],'connectionId':conn,'connection_local_id':job,'raw':raw}
   line=json.dumps(row,separators=(',',':'))+'\n';enc=line.encode()
   if time.time()>=stopwall or shared_ns()>=stopOS:reason='deadline';break
   if logical+len(enc)>logicalmax or compressed>=maximum:reason='bytecap';break
   if not gz.append(enc):reason='compressed_bytecap';break
   logical+=len(enc);n+=1;compressed=gz.tell()
   if n<=100:initial.write(line);initial.flush()
   if channel:counts[channel+'|'+asset]=counts.get(channel+'|'+asset,0)+1
   if o.get('event')=='error':reason='server_error_no_retry';error={'code':o.get('code'),'msg':o.get('msg')};break
   if osafter-laststatus>=5000000000:
    gz.flush();compressed=gz.tell()
    if compressed>=maximum or task_bytes()>=2147483648-10000000:reason='compressed_or_global_bytecap';break
    status('RUNNING');laststatus=osafter
  if terminate[0]:reason='signal_stop'
 except Exception as e:reason='exception_no_retry';error={'type':type(e).__name__,'text':str(e)}
 finally:
  if initial:initial.close()
  if gz:
   try:gz.close();compressed=(B/'raw/ws_messages.jsonl.gz').stat().st_size
   except Exception as e:error=error or {'close_gzip_error':str(e)}
  if ws:
   try:ws.close(timeout=3)
   except Exception as e:error=error or {'close_WS_error':str(e)}
  final=status('STOPPED');final['finished_utc']=dt.datetime.now(UTC).isoformat();write_json(B/'collector_final.json',final);print(json.dumps(final),flush=True)
if __name__=='__main__':main()

