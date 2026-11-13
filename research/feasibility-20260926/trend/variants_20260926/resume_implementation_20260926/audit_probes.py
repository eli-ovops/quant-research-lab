from pathlib import Path
from decimal import Decimal as D
import json,hashlib,datetime
P=Path(__file__).resolve().parent;OLD=P.parent;H=3600000
attempts=json.loads((P/'probe_attempts.json').read_text());checks=[];normalized=[]
for n,a in enumerate(attempts,1):
 f=P/'raw'/('probe'+str(n)+'_result.json')
 if not f.exists():continue
 envelope=json.loads(f.read_text());obj=envelope.get('structuredContent') or json.loads(envelope['content'][0]['text']);args=a['args'];coin=args['instId'].split('-')[0];assert args['bar']=='1H' and args['instId'] in ['BTC-USDT','ETH-USDT']
 sp=json.loads((OLD.parent/'raw'/(coin+'_spec.txt')).read_text())['data'][0];assert sp['instType']=='SPOT' and sp['instId']==args['instId'] and sp['baseCcy']==coin and sp['quoteCcy']=='USDT'
 if not obj.get('ok'):
  checks.append({'probe':n,'success':False,'raw_sha256':hashlib.sha256(f.read_bytes()).hexdigest(),'error':obj});continue
 assert obj['data']['endpoint']=='GET /api/v5/market/history-candles';rr=obj['data']['data'];lo=int(args['before'])+1;hi=int(args['after']);ts=[int(r[0]) for r in rr]
 assert len(rr)==12 and sorted(ts)==list(range(lo,hi,H));assert all(t%H==0 for t in ts)
 for r in rr:
  assert len(r)==9 and r[-1]=='1';v=list(map(D,r[1:8]));assert all(x.is_finite() for x in v) and 0<v[2]<=min(v[0],v[3])<=max(v[0],v[3])<=v[1] and min(v[4:])>0
 cached={}
 for ref in json.loads((OLD/'reuse_hourly_sources.json').read_text()):
  if ref['coin']==coin:
   for r in json.loads(Path(ref['path']).read_text())['data']:cached[r[0]]=r
 overlap=[r for r in rr if r[0] in cached];assert all(r==cached[r[0]] for r in overlap)
 if n==1:assert len(overlap)==12
 out=P/'raw'/('probe'+str(n)+'_normalized.json');out.write_text(json.dumps({'code':'0','data':rr},indent=2)+'\n')
 normalized.append({'coin':coin,'path':str(out),'sha256':hashlib.sha256(out.read_bytes()).hexdigest(),'source_raw':str(f),'source_sha256':hashlib.sha256(f.read_bytes()).hexdigest(),'role':'Lossless nine-field rows extracted from tool response; normalization adds code0 envelope from ok=true'})
 checks.append({'probe':n,'success':True,'instId_request':args['instId'],'bar_request':'1H','response_identity_echo':False,'identity_basis':'Explicit instrument request, current SPOT spec, historical-candles endpoint;2026 overlap matched raw; response itself does not echo instrument/bar','rows':len(rr),'completed':True,'range_match':True,'first_UTC':datetime.datetime.fromtimestamp(min(ts)/1000,datetime.timezone.utc).isoformat(),'last_UTC':datetime.datetime.fromtimestamp(max(ts)/1000,datetime.timezone.utc).isoformat(),'overlap_rows':len(overlap),'overlap_all9fields_equal':True if overlap else None,'source_sha256':hashlib.sha256(f.read_bytes()).hexdigest(),'normalization_sha256':hashlib.sha256(out.read_bytes()).hexdigest()})
(P/'normalized_sources.json').write_text(json.dumps(normalized,indent=2)+'\n');(P/'probe_checks.json').write_text(json.dumps(checks,indent=2)+'\n');print(json.dumps(checks,indent=2))
