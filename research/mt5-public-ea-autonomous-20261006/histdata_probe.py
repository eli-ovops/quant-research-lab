from pathlib import Path
import urllib.request,urllib.parse,hashlib,json,re,html,datetime
B=Path(__file__).resolve().parent
def get(name,url):
 assert urllib.parse.urlparse(url).hostname in ['www.histdata.com','histdata.com']
 rec={'name':name,'url':url,'utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
 try:
  with urllib.request.urlopen(url,timeout=12) as r: data=r.read(2000000);rec['http_status']=r.status
  s=data.decode(errors='replace')
  # Download form ephemeral values are never retained or reported.
  sanitized=re.sub(r'(<input[^>]*name=["\'](?:tk|token)["\'][^>]*value=["\'])[^"\']*',r'\1REDACTED',s,flags=re.I)
  p=B/'raw'/name;p.write_text(sanitized);rec.update(bytes=len(data),original_sha256=hashlib.sha256(data).hexdigest(),saved_sha256=hashlib.sha256(sanitized.encode()).hexdigest(),form_token_redacted=True)
 except Exception as e:rec['error']=str(e);s=''
 with (B/'histdata_requests.jsonl').open('a') as f:f.write(json.dumps(rec)+'\n')
 print(json.dumps(rec));return s
if __name__=='__main__':
 s=get('histdata_download.html','https://www.histdata.com/download-free-forex-data/')
 links=[html.unescape(x) for x in re.findall(r'href=["\']([^"\']+)',s) if 'tick-data-quotes' in x]
 print('official_tick_hrefs',links[:4])
