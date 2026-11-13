import urllib.request, json, pathlib, hashlib, datetime
BASE=pathlib.Path(__file__).resolve().parent
REQS={
 'option_summary':'https://www.okx.com/api/v5/public/opt-summary?uly=BTC-USD',
 'option_tiers':'https://www.okx.com/api/v5/public/position-tiers?instType=OPTION&tdMode=isolated&uly=BTC-USD',
 'prediction_event':'https://gamma-api.polymarket.com/events?slug=when-will-bitcoin-etf-be-approved',
 'index_april':'https://downloads.coindesk.com/cd3/CDI/IA/CD20-Final-Apr-2026-Reconstitution-Results.pdf',
 'factsheet':'https://dataspanapi.wisdomtree.com/pdr/documents/FACTSHEET/WIXL/EU/EN-GB/GB00BN474G19/'
}
receipts=[]
for name,url in REQS.items():
 receipt={'name':name,'url':url,'time_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
 try:
  with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'public-research/1.0'}),timeout=15) as r:
   data=r.read(2000000);receipt.update(status=r.status,bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),content_type=r.headers.get('content-type'))
  suffix='.pdf' if data.startswith(b'%PDF') else '.json'
  path=BASE/'raw'/(name+suffix);path.write_bytes(data);receipt['file']=str(path)
 except Exception as e:receipt['error']=repr(e)
 receipts.append(receipt);print(json.dumps(receipt))
(BASE/'raw'/'fetch_receipts.json').write_text(json.dumps(receipts,indent=2))
