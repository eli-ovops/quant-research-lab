from pathlib import Path
from decimal import Decimal as D
import json,datetime,hashlib,sys
P=Path(__file__).resolve().parent
def sha(f):return hashlib.sha256(f.read_bytes()).hexdigest()
def save(f,x):f.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
plan=json.loads((P/'gap_plan_v1.json').read_text());assert sha(P/'gap_plan_v1.json')==json.loads((P/'gap_plan_v1_freeze.json').read_text())['sha256'];mode,ident=sys.argv[1:3];page=next(x for x in plan['pages'] if x['id']==ident);log=P/'attempts.json';a=json.loads(log.read_text()) if log.exists() else [];record=next((x for x in a if x['id']==ident),None);raw=P/'raw'/page['file'];norm=P/'raw'/(ident+'_normalized.json')
if mode=='start':
 if record:
  assert record.get('success') and sha(raw)==record['raw_sha256'] and sha(norm)==record['normalized_sha256'],'refuse failed/incomplete/hash-changed repeat';print(json.dumps({'skip':True}));sys.exit()
 assert len(a)+6<600
 record={'id':ident,'args':page['args'],'request_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'expected_rows':page['expected_rows'],'explicit_cumulative_call_number':len(a)+7};a.append(record);save(log,a);print(json.dumps({'skip':False,'args':page['args']}))
elif mode=='finish':
 assert record and not record.get('success')
 record['received_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat();record['raw_sha256']=sha(raw)
 try:
  env=json.loads(raw.read_text());obj=env.get('structuredContent') or json.loads(env['content'][0]['text']);assert obj.get('ok'),str(obj)[:500];assert obj['data']['endpoint']=='GET /api/v5/market/history-candles';rr=obj['data']['data'];timestamps=[int(r[0]) for r in rr]
  assert len(rr)==page['expected_rows'] and sorted(timestamps)==list(range(page['start'],page['end'],3600000)),('truncated_or_wrong_grid',len(rr),page['expected_rows'])
  for r in rr:
   assert len(r)==9 and r[-1]=='1';v=list(map(D,r[1:8]));assert all(x.is_finite() for x in v) and 0<v[2]<=min(v[0],v[3])<=max(v[0],v[3])<=v[1] and min(v[4:])>=0
  assert not norm.exists();save(norm,{'code':'0','data':rr});record.update(success=True,rows=len(rr),normalized_sha256=sha(norm),source_endpoint=obj['data']['endpoint'],server_request_utc=obj['data'].get('requestTime'));save(log,a);print(json.dumps({'id':ident,'success':True,'rows':len(rr),'completed_pages':sum(bool(x.get('success')) for x in a)}))
 except Exception as e:
  record.update(success=False,error=str(e));save(log,a);raise
