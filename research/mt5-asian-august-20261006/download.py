from pathlib import Path
import html.parser,html,urllib.request,urllib.parse,re,json,hashlib,datetime
B=Path(__file__).resolve().parent;R=B/'raw';R.mkdir(exist_ok=True)
old=Path('/Volumes/EXTERNAL/量化/research/mt5-public-ea-autonomous-20261006/raw/histdata_eurusd2026.html').read_text()
links=[html.unescape(x) for x in re.findall(r'href=["\']([^"\']+)',old) if x.endswith('/2026/8')]
assert len(set(links))==1;url=urllib.parse.urljoin('https://www.histdata.com',links[0])
opener=urllib.request.build_opener(urllib.request.ProxyHandler({'http':'http://127.0.0.1:7890','https':'http://127.0.0.1:7890'}))
def request(name,req,limit):
 rec={'name':name,'url':req.full_url if hasattr(req,'full_url') else req,'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'route':'request-local inherited existing system proxy, TLSverifyON'}
 try:
  with opener.open(req,timeout=20) as r:rec.update(http_status=r.status,content_type=r.headers.get('Content-Type'));data=r.read(limit+1)
  assert len(data)<=limit
  rec.update(bytes=len(data),original_sha256=hashlib.sha256(data).hexdigest())
 except Exception as e:rec['error']=str(e);data=None
 with (B/'requests.jsonl').open('a') as f:f.write(json.dumps(rec)+'\n')
 print(json.dumps(rec),flush=True);return data
data=request('officialAugustMonth',url,1000000)
if data is None:raise SystemExit('STOP original page unavailable, no token/url guesses')
s=data.decode();sanitized=re.sub(r'(<input[^>]*name=["\'](?:tk|token)["\'][^>]*value=["\'])[^"\']*',r'\1REDACTED',s,flags=re.I);(R/'AugustMonth_redacted.html').write_text(sanitized)
class P(html.parser.HTMLParser):
 def __init__(self):super().__init__();self.forms=[];self.current=None
 def handle_starttag(self,t,a):
  d=dict(a)
  if t=='form':self.current={'action':d.get('action'),'method':d.get('method'),'fields':{}};self.forms.append(self.current)
  if t=='input' and self.current is not None and d.get('name'):self.current['fields'][d['name']]=d.get('value','')
 def handle_endtag(self,t):
  if t=='form':self.current=None
p=P();p.feed(s);forms=[f for f in p.forms if urllib.parse.urlparse(f['action']).path=='/get.php' and f['fields'].get('datemonth')=='202608' and f['fields'].get('fxpair')=='EURUSD'];assert len(forms)==1
f=forms[0];action=urllib.parse.urljoin(url,f['action']);assert urllib.parse.urlparse(action).hostname=='www.histdata.com' and f['method'].lower()=='post'
req=urllib.request.Request(action,data=urllib.parse.urlencode(f['fields']).encode(),headers={'Referer':url});zipdata=request('originalPublicFormPOST',req,30000000)
if zipdata is None:raise SystemExit('STOP no archive')
(R/'EURUSD_202608_provider_response.bin').write_bytes(zipdata)
if not zipdata.startswith(b'PK'):raise SystemExit('STOP nonZIP response; no retries/guesses')
print('originalZIP retained; tokenvalues never logged')
