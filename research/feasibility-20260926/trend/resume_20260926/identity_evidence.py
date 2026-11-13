from pathlib import Path
import urllib.request,json,hashlib,datetime,gzip,csv,io
P=Path(__file__).resolve().parent;S=json.loads((P/'sources.json').read_text());entries=[]
urls=[('identity_unified','https://www.okx.com/en-gb/help/announcement-on-migration-to-unified-account'),('identity_tardis','https://docs.tardis.dev/historical-data-details/okex.md'),('identity_tardis_metadata','https://api.tardis.dev/v1/exchanges/okex'),('identity_ETH_20200101','https://datasets.tardis.dev/v1/okex/trades/2020/01/01/ETH-USDT.csv.gz'),('identity_BTC_20200101','https://datasets.tardis.dev/v1/okex/trades/2020/01/01/BTC-USDT.csv.gz')]
for name,url in urls:
 f=P/'raw'/(name+'.bin');rec={'name':name,'url':url,'request_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
 if not f.exists():
  try:
   with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'ResearchPublicData/1.0'}),timeout=25) as r:b=r.read(12*1024*1024+1);rec['http_status']=r.status
   assert len(b)<=12*1024*1024,'response exceeds bounded size';f.write_bytes(b)
  except Exception as e:rec['error']=str(e);entries.append(rec);continue
 else:b=f.read_bytes()
 rec.update(path=str(f),received_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),sha256=hashlib.sha256(b).hexdigest(),bytes=len(b),authenticated=False);S.append(rec);entries.append(rec);(P/'sources.json').write_text(json.dumps(S,ensure_ascii=False,indent=2)+'\n')
 if name.startswith('identity_') and '20200101' in name:
  rows=list(csv.DictReader(io.StringIO(gzip.decompress(b).decode())));print(name,'rows',len(rows),'first',rows[0],flush=True)
(P/'identity_requests.json').write_text(json.dumps(entries,ensure_ascii=False,indent=2)+'\n');print('identity_requests',len(entries),flush=True)
