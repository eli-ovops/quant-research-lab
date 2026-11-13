from pathlib import Path
import json,datetime,time,urllib.request,urllib.parse,hashlib,sys
P=Path(__file__).resolve().parent;R=P/'raw';H=3600000
S=json.loads((P/'sources.json').read_text());A=json.loads((P/'attempts.json').read_text()) if (P/'attempts.json').exists() else []
def stamp(s):return int(datetime.datetime.fromisoformat(s).replace(tzinfo=datetime.timezone.utc).timestamp()*1000)
def save():
 (P/'attempts.json').write_text(json.dumps(A,indent=2)+'\n');(P/'sources.json').write_text(json.dumps(S,indent=2)+'\n')
def fetch(name,c,lo,hi,limit):
 f=R/(name+'.json');url='https://www.okx.com/api/v5/market/history-candles?'+urllib.parse.urlencode({'instId':c+'-USDT','bar':'1H','after':hi,'before':lo-1,'limit':limit})
 if f.exists():return json.loads(f.read_text())['data']
 assert len(A)<600,'request cap';assert not any(x['url']==url for x in A),'no identical failed repeats'
 rec={'name':name,'url':url,'request_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'authenticated':False};A.append(rec);save();start=time.time()
 try:
  req=urllib.request.Request(url,headers={'User-Agent':'ResearchPublicData/1.0','Connection':'close'})
  with urllib.request.urlopen(req,timeout=25) as resp:b=resp.read();headers=dict(resp.headers);status=resp.status
  f.write_bytes(b);obj=json.loads(b);rec.update(status=status,received_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),elapsed_seconds=time.time()-start,rows=len(obj.get('data',[])))
  S.append(dict(rec,path=str(f),sha256=hashlib.sha256(b).hexdigest(),bytes=len(b),headers=headers,new_request=True));save()
  assert obj['code']=='0',obj;rows=obj['data'];assert rows,'empty window';t=[int(r[0]) for r in rows];assert min(t)>=lo and max(t)<hi,(min(t),max(t),lo,hi);assert all(r[-1]=='1' for r in rows);time.sleep(.5);return rows
 except Exception as e:
  rec.update(error=str(e),elapsed_seconds=time.time()-start);save();print('BLOCKED',name,repr(e),flush=True);raise
if __name__=='__main__':
 start=stamp('2019-12-28T16:00:00');end=stamp('2026-07-01T00:00:00')
 for c in ['BTC','ETH']:
  rows=fetch(c+'_pilot',c,start,start+12*H,12);assert sorted(int(r[0]) for r in rows)==list(range(start,start+12*H,H));print(c,'PILOT PASS',flush=True)
  lo=start;i=0
  while lo<end:
   hi=min(end,lo+300*H);cur=hi
   while cur>lo:
    rows=fetch(c+'_hour_'+str(i).zfill(3),c,lo,cur,300);cur=min(int(r[0]) for r in rows);i+=1
    print(c,'page',i,'rows',len(rows),'oldest',datetime.datetime.fromtimestamp(cur/1000,datetime.timezone.utc).isoformat(),'requests',len(A),flush=True)
   lo=hi
 print('COMPLETE requests',len(A),flush=True)
