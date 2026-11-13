from pathlib import Path
import json,datetime,time,urllib.request,urllib.parse,hashlib
P=Path(__file__).resolve().parent;R=P/'raw';R.mkdir(exist_ok=True);DAY=86400000
S=json.loads((P/'sources.json').read_text());A=json.loads((P/'request_attempts.json').read_text()) if (P/'request_attempts.json').exists() else []
def stamp(s):return int(datetime.datetime.fromisoformat(s).replace(tzinfo=datetime.timezone.utc).timestamp()*1000)
def fetch(name,url):
 f=R/(name+'.txt')
 if f.exists():return json.loads(f.read_text())
 assert len(A)<60
 assert not any(x['url']==url for x in A),'no exact failed repeats'
 rec={'url':url,'name':name,'request_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()};A.append(rec);(P/'request_attempts.json').write_text(json.dumps(A,indent=2)+'\n');start=time.time()
 try:
  req=urllib.request.Request(url,headers={'User-Agent':'ResearchPublicData/1.0','Connection':'close'})
  with urllib.request.urlopen(req,timeout=25) as resp:b=resp.read();headers=dict(resp.headers);status=resp.status
  obj=json.loads(b);assert obj['code']=='0',obj
 except Exception as e:
  rec.update(error=str(e),elapsed=time.time()-start);(P/'request_attempts.json').write_text(json.dumps(A,indent=2)+'\n');raise
 f.write_bytes(b);rec.update(status=status,received_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),elapsed=time.time()-start,rows=len(obj['data']));S.append(dict(rec,path=str(f),sha256=hashlib.sha256(b).hexdigest(),bytes=len(b),headers=headers,authenticated=False));(P/'sources.json').write_text(json.dumps(S,ensure_ascii=False,indent=2)+'\n');(P/'request_attempts.json').write_text(json.dumps(A,indent=2)+'\n');return obj
if __name__=='__main__':
 lo=stamp('2019-11-22');end=stamp('2025-02-26');i=0
 while lo<end:
  hi=min(end,lo+300*DAY);cursor=hi
  while cursor>lo:
   url='https://www.okx.com/api/v5/market/history-candles?'+urllib.parse.urlencode({'instId':'ETH-USDT','bar':'1Dutc','after':cursor,'before':lo-1,'limit':300})
   rows=fetch('ETH_daily_resume_'+str(i).zfill(2),url)['data'];assert rows,'empty bounded window';t=[int(r[0]) for r in rows];assert min(t)>=lo and max(t)<cursor,(min(t),max(t),lo,cursor);cursor=min(t);i+=1;print('page',i,'rows',len(t),'oldest',datetime.datetime.fromtimestamp(cursor/1000,datetime.timezone.utc).date(),flush=True)
  lo=hi
 print('COMPLETE',i,flush=True)
