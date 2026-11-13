from pathlib import Path
import subprocess,json,hashlib,datetime
B=Path(__file__).resolve().parent;R=B/'raw';R.mkdir(exist_ok=True)
def fetch(name,url,maxbytes=5000000):
 assert url.startswith(('https://www.mql5.com/','https://c.mql5.com/','https://datafeed.dukascopy.com/'))
 attempts=(B/'requests.jsonl').read_text().count('\n') if (B/'requests.jsonl').exists() else 0
 assert attempts<150
 assert sum(p.stat().st_size for p in B.rglob('*') if p.is_file())<100000000
 f=R/name;receipt={'name':name,'url':url,'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'route':'request-local inherited existing system proxy;TLSverificationON'}
 p=subprocess.run(['curl','--proxy','http://127.0.0.1:7890','--location','--silent','--show-error','--connect-timeout','10','--max-time','25','--max-filesize',str(maxbytes),'-A','public-research/1.0','--output',str(f),'--write-out','%{http_code}',url],capture_output=True)
 receipt.update(returncode=p.returncode,http_status=p.stdout.decode(),stderr=p.stderr.decode(),bytes=f.stat().st_size if f.exists() else 0,sha256=hashlib.sha256(f.read_bytes()).hexdigest() if f.exists() else None)
 with (B/'requests.jsonl').open('a') as log:log.write(json.dumps(receipt)+'\n')
 print(json.dumps(receipt),flush=True)
 if receipt['http_status'] in ['401','403']:raise PermissionError('HTTPdeny STOP no retry')
 return receipt
if __name__=='__main__':fetch('candidate1.html','https://www.mql5.com/en/code/76153')
