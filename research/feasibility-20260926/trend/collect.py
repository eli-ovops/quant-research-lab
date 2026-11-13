from pathlib import Path
import urllib.request,urllib.parse,json,time,hashlib,datetime,sys,subprocess
P=Path(__file__).resolve().parent;R=P/'raw';R.mkdir(exist_ok=True)
S=json.loads((P/'sources.json').read_text()) if (P/'sources.json').exists() else []
def fetch(name,url):
 f=R/(name+'.txt')
 if f.exists():return f.read_bytes()
 assert len(S)<90
 t=time.time();req=urllib.request.Request(url,headers={'User-Agent':'ResearchPublicData/1.0'})
 response=subprocess.run(['curl','--http1.1','--fail','--silent','--show-error','--max-time','30','-A','ResearchPublicData/1.0',url],capture_output=True,check=True)
 b=response.stdout;headers={'transport':'curl HTTP/1.1; certificate verification enabled'};status='2xx (curl --fail)'
 f.write_bytes(b);S.append({'name':name,'url':url,'request_utc':datetime.datetime.fromtimestamp(t,datetime.timezone.utc).isoformat(),'received_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'elapsed_seconds':time.time()-t,'status':status,'headers':headers,'path':str(f),'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b),'authenticated':False});(P/'sources.json').write_text(json.dumps(S,ensure_ascii=False,indent=2)+'\n');return b
def api(name,path,**kw):
 x=json.loads(fetch(name,'https://app.okx.com/api/v5/'+path+'?'+urllib.parse.urlencode(kw)));assert x['code']=='0',x;return x['data']
def stamp(s):return int(datetime.datetime.fromisoformat(s).replace(tzinfo=datetime.timezone.utc).timestamp()*1000)
if __name__=='__main__':
 api('time','public/time')
 for c in ['BTC','ETH']:
  api(c+'_spec','public/instruments',instType='SPOT',instId=c+'-USDT')
  cursor=stamp('2026-07-01');lo=stamp('2019-11-22')
  for page in range(55):
   rows=api(c+'_daily_'+str(page).zfill(2),'market/history-candles',instId=c+'-USDT',bar='1Dutc',after=cursor,limit=50)
   if not rows:raise RuntimeError('history empty before required start '+c)
   oldest=min(int(r[0]) for r in rows);assert oldest<cursor
   if oldest<=lo:break
   cursor=oldest
  else:raise RuntimeError('bounded history incomplete')
  print(c,'pages',page+1,flush=True)
 fetch('docs_api','https://www.okx.com/docs-v5/en/')
 fetch('docs_fees','https://www.okx.com/en-sg/help/trading-fee-rules-faq')
 print('sources',len(S),flush=True)
