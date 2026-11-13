import urllib.request,pathlib,json,datetime,hashlib,sys
B=pathlib.Path(__file__).resolve().parent;R=B/'rawsource';R.mkdir(exist_ok=True)
def fetch(name,url,limit=5000000):
 receipt={'name':name,'url':url,'utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
 try:
  with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'public-research/1.0'}),timeout=15) as resp:data=resp.read(limit+1);receipt['status']=resp.status
  assert len(data)<=limit;f=R/name;f.write_bytes(data);receipt.update(bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),path=str(f))
 except Exception as e:receipt['error']=repr(e);data=None
 with (B/'requests.jsonl').open('a') as f:f.write(json.dumps(receipt)+'\n')
 print(json.dumps(receipt));return data
if __name__=='__main__':
 for name,url in [('candidate1.html','https://www.mql5.com/en/code/76153'),('candidate2.html','https://www.mql5.com/en/articles/17239'),('candidate3.html','https://www.mql5.com/en/signals/2329290'),('dukascopy-doc.html','https://www.dukascopy.com/wiki/en/development/data-export/')]:fetch(name,url)
