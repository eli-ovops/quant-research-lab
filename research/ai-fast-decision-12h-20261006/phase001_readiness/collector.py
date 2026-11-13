from pathlib import Path
import os,time,json,hashlib,datetime as dt,ssl,signal
import websocket
B=Path(__file__).resolve().parent;UTC=dt.timezone.utc
URL='wss://ws.okx.com:8443/ws/v5/public'
ASSETS=['BTC-USDT-SWAP','ETH-USDT-SWAP','SOL-USDT-SWAP']
def stop_at(start,global_deadline):return min(start+2700,global_deadline)
def allowed(wall,mono,stopwall,stopmono,total,nextbytes,maximum):return wall<stopwall and mono<stopmono and total+nextbytes<=maximum
def acquire(path):
 fd=os.open(path,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600);os.write(fd,str(os.getpid()).encode());os.close(fd)
def metadata(raw):
 try:
  o=json.loads(raw);return o,o.get('arg',{}).get('channel'),o.get('arg',{}).get('instId'),[d.get('ts') for d in o.get('data',[]) if isinstance(d,dict)]
 except (json.JSONDecodeError,AttributeError):return {},None,None,[]
def main():
 acquire(B/'collector_once.lock')
 start=time.time();monostart=time.monotonic();globalend=dt.datetime.fromisoformat('2026-10-07T03:16:33+00:00').timestamp();end=stop_at(start,globalend);monoend=monostart+max(0,end-start)
 maximum=240000000;pid=os.getpid();identity={'pid':pid,'job_id':'phase001-'+str(pid)+'-'+str(int(start)),'start_utc':dt.datetime.fromtimestamp(start,UTC).isoformat(),'stop_at_utc':dt.datetime.fromtimestamp(end,UTC).isoformat(),'max_raw_bytes':maximum,'url':URL,'TLS_verify':True,'auth':False,'proxy':'existing system HTTP 127.0.0.1:7890 request-level only','source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'initial_connections_authorized':2,'automatic_reconnects':0}
 (B/'collector_identity.json').write_text(json.dumps(identity,indent=2));print(json.dumps({'status':'STARTING',**identity}),flush=True)
 ws=None;total=0;n=0;connid=None;counts={};acks=[];reason='deadline';error=None;laststatus=0;lastrecv=time.monotonic();lastping=0;terminate=[False]
 def sig(*args):terminate[0]=True
 signal.signal(signal.SIGTERM,sig);signal.signal(signal.SIGINT,sig)
 def status(state):
  obj={**identity,'status':state,'at_utc':dt.datetime.now(UTC).isoformat(),'messages':n,'raw_bytes':total,'connectionId':connid,'channel_counts':counts,'subscription_acks':acks,'stop_reason':reason,'error':error}
  (B/'collector_status.json').write_text(json.dumps(obj,indent=2));return obj
 try:
  ws=websocket.create_connection(URL,timeout=10,sslopt={'cert_reqs':ssl.CERT_REQUIRED,'check_hostname':True},http_proxy_host='127.0.0.1',http_proxy_port=7890,proxy_type='http')
  ws.settimeout(3);args=[{'channel':c,'instId':a} for a in ASSETS for c in ['books5','trades']];ws.send(json.dumps({'op':'subscribe','args':args}));status('CONNECTED_SUBSCRIBE_SENT')
  with (B/'raw/ws_messages.jsonl').open('x') as output:
   while allowed(time.time(),time.monotonic(),end,monoend,total,0,maximum) and not terminate[0]:
    try:raw=ws.recv()
    except websocket.WebSocketTimeoutException:
     now=time.monotonic()
     if now-lastrecv>20 and now-lastping>20:ws.send('ping');lastping=now
     if now-lastrecv>60:reason='no_message_60s';break
     continue
    wallns=time.time_ns();monons=time.monotonic_ns();lastrecv=time.monotonic()
    if not raw:reason='remote_close';break
    if isinstance(raw,bytes):raw=raw.decode('utf-8')
    obj,channel,asset,exchanges=metadata(raw)
    if obj.get('connId'):connid=obj['connId']
    if obj.get('event')=='subscribe':acks.append(obj['arg'])
    row={'local_ordinal':n+1,'receive_wall_ms':wallns/1000000,'receive_wall_ns':wallns,'monotonic_ns':monons,'channel':channel,'instId':asset,'exchange_ts':exchanges,'connectionId':connid,'connection_local_id':identity['job_id'],'raw':raw}
    line=json.dumps(row,separators=(',',':'))+'\n';encoded=line.encode()
    if not allowed(time.time(),time.monotonic(),end,monoend,total,len(encoded),maximum):reason='deadline_or_bytecap';break
    output.write(line);output.flush();total+=len(encoded);n+=1
    if channel:counts[channel+'|'+asset]=counts.get(channel+'|'+asset,0)+1
    if obj.get('event')=='error':reason='server_error_no_retry';error={'code':obj.get('code'),'msg':obj.get('msg')};break
    if time.monotonic()-laststatus>=5:status('RUNNING');laststatus=time.monotonic()
   if terminate[0]:reason='signal_stop'
 except Exception as exc:
  reason='exception_no_retry';error={'type':type(exc).__name__,'text':str(exc)}
 finally:
  if ws:
   try:ws.close(timeout=3)
   except Exception:pass
  final=status('STOPPED');final['finished_utc']=dt.datetime.now(UTC).isoformat();(B/'collector_final.json').write_text(json.dumps(final,indent=2));print(json.dumps(final),flush=True)
if __name__=='__main__':main()
