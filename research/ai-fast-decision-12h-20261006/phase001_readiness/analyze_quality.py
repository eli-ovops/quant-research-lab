from pathlib import Path
import json,hashlib,datetime as dt,argparse
def analyze(path,limit):
 blob=path.open('rb').read(limit);lines=blob.splitlines();stats={};prior={};lastord=0;lastmono=0;ordered=True;monotonic=True;rows=0
 for line in lines:
  try:r=json.loads(line)
  except json.JSONDecodeError:continue
  rows+=1;ordered &=r['local_ordinal']==lastord+1;monotonic &=r['monotonic_ns']>=lastmono;lastord=r['local_ordinal'];lastmono=r['monotonic_ns'];o=json.loads(r['raw']);key=str(r['channel'])+'|'+str(r['instId']);s=stats.setdefault(key,{'messages':0,'data_records':0,'ages':[],'receive_gaps':[],'seq_present':0,'prevseq_present':0,'invalid_book':0,'trade_count_gt1':0});s['messages']+=1
  if key in prior:s['receive_gaps'].append((r['monotonic_ns']-prior[key])/1e6)
  prior[key]=r['monotonic_ns']
  for d in o.get('data',[]):
   s['data_records']+=1
   if d.get('ts'):s['ages'].append(r['receive_wall_ms']-int(d['ts']))
   s['seq_present']+='seqId' in d;s['prevseq_present']+='prevSeqId' in d
   if r['channel']=='books5':
    try:s['invalid_book']+=not (d['bids'] and d['asks'] and float(d['bids'][0][0])<float(d['asks'][0][0]))
    except Exception:s['invalid_book']+=1
   if r['channel']=='trades':s['trade_count_gt1']+=int(d.get('count',1))>1
 for s in stats.values():
  for key in ['ages','receive_gaps']:
   a=sorted(s.pop(key));s[key+'_ms']={'n':len(a),'min':min(a) if a else None,'p50':a[len(a)//2] if a else None,'p95':a[min(len(a)-1,int(len(a)*.95))] if a else None,'max':max(a) if a else None}
 return {'prefix_bytes_read':len(blob),'prefix_sha256':hashlib.sha256(blob).hexdigest(),'rows':rows,'ordinal_contiguous':ordered,'monotonic_nondecreasing':monotonic,'channels':stats,'age_includes_clock_offset_and_network_not_AI_latency':True,'exchange_clock_sync':'UNKNOWN','full_market_completeness':'UNKNOWN'}
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--bytes',type=int,required=True);p.add_argument('--output',required=True);a=p.parse_args();B=Path(__file__).resolve().parent;q=analyze(B/'raw/ws_messages.jsonl',a.bytes);q['analyzed_utc']=dt.datetime.now(dt.timezone.utc).isoformat();(B/a.output).write_text(json.dumps(q,indent=2))

