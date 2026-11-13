from histdata_probe import get,B
import html.parser,urllib.request,urllib.parse,json,hashlib,datetime,zipfile,csv,io
MONTH='https://www.histdata.com/download-free-forex-historical-data/?/ascii/tick-data-quotes/eurusd/2026/9'
class Forms(html.parser.HTMLParser):
 def __init__(self):super().__init__();self.forms=[];self.current=None
 def handle_starttag(self,tag,attrs):
  a=dict(attrs)
  if tag=='form':self.current={'action':a.get('action'),'method':a.get('method','get'),'fields':{}};self.forms.append(self.current)
  if tag=='input' and self.current is not None and a.get('name'):self.current['fields'][a['name']]=a.get('value','')
 def handle_endtag(self,tag):
  if tag=='form':self.current=None
s=get('histdata_september_download_redacted.html',MONTH);p=Forms();p.feed(s)
forms=[f for f in p.forms if any(k in f['fields'] for k in ['tk','token']) and urllib.parse.urlparse(f['action']).path=='/get.php' and f['fields'].get('datemonth')=='202609' and f['fields'].get('fxpair')=='EURUSD']
print('download_form_count',len(forms),'methods',[f['method'] for f in forms],'field_names',[list(f['fields']) for f in forms])
if len(forms)!=1:raise SystemExit('STOP no unambiguous original download form')
form=forms[0];url=urllib.parse.urljoin(MONTH,form['action']);assert urllib.parse.urlparse(url).hostname in ['www.histdata.com','histdata.com'];assert form['method'].lower()=='post'
request=urllib.request.Request(url,data=urllib.parse.urlencode(form['fields']).encode(),headers={'Referer':MONTH})
rec={'name':'histdata_original_download_POST','url':url,'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'method':'POST','form_fields':'REDACTED_NOT_LOGGED'}
data=b''
try:
 with urllib.request.urlopen(request,timeout=30) as r:
  rec['http_status']=r.status;rec['content_type']=r.headers.get('Content-Type');data=r.read(40000001)
 if len(data)>40000000:raise ValueError('compressed40MB gate exceeds allowed single-file allocation')
 f=B/'raw'/'EURUSD_202609_provider_response.bin';f.write_bytes(data);rec.update(bytes=len(data),sha256=hashlib.sha256(data).hexdigest())
except Exception as e:rec['error']=str(e)
with (B/'histdata_requests.jsonl').open('a') as log:log.write(json.dumps(rec)+'\n')
print(json.dumps(rec))
if not data.startswith(b'PK'):raise SystemExit('STOP nonZIP actual provider response; no retry')
z=zipfile.ZipFile(io.BytesIO(data));files=[i for i in z.infolist() if i.filename.lower().endswith('.csv')];print('archive_CSV_names',[i.filename for i in files])
if len(files)!=1 or 'EURUSD_T_202609' not in files[0].filename.upper():raise SystemExit('STOP wrong archive month/type')
start=datetime.datetime(2026,9,21,tzinfo=datetime.timezone.utc);end=datetime.datetime(2026,9,26,tzinfo=datetime.timezone.utc);est=datetime.timezone(datetime.timedelta(hours=-5))
target=B/'EURUSD_20260921_26_UTC_ticks.csv';warmupfile=B/'EURUSD_preperiod_warmup_UTC.csv';warmupstart=start-datetime.timedelta(hours=5);n=0;wn=0;prev=None;rowschecked=0;days={};maxgap=0
with z.open(files[0]) as stream,target.open('w',newline='') as output,warmupfile.open('w',newline='') as warm:
 writer=csv.writer(output);writer.writerow(['timestamp','bid','ask']);ww=csv.writer(warm);ww.writerow(['timestamp','bid','ask'])
 for r in csv.reader(io.TextIOWrapper(stream)):
  if len(r)!=4:raise ValueError('not GenericASCII ticks')
  t=datetime.datetime.strptime(r[0],'%Y%m%d %H%M%S%f').replace(tzinfo=est).astimezone(datetime.timezone.utc)
  if t<warmupstart:continue
  if t>=end:break
  bid=float(r[1]);ask=float(r[2]);assert 0<bid<=ask
  if t<start:ww.writerow([t.isoformat(),r[1],r[2]]);wn+=1;continue
  if prev is not None:
   if t<prev:raise ValueError('out of order input')
   maxgap=max(maxgap,(t-prev).total_seconds())
  prev=t;n+=1;days[t.strftime('%Y-%m-%d')]=days.get(t.strftime('%Y-%m-%d'),0)+1;writer.writerow([t.isoformat(),r[1],r[2]])
  if n%10000==0 and target.stat().st_size+len(data)>95000000:raise ValueError('stop storage allocation threshold')
receipt={'file':str(target),'sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'ticks':n,'observed_days':days,'maxgap_seconds':maxgap,'warmup_file':str(warmupfile),'warmup_ticks':wn,'warmup_sha256':hashlib.sha256(warmupfile.read_bytes()).hexdigest(),'source_timezone':'fixedEST UTC-5 noDST per official specification','archive_member':files[0].filename,'source_month':'202609','whole_month_extracted':False,'fixed_subset_only':True}
(B/'histdata_import_audit.json').write_text(json.dumps(receipt,indent=2));print(json.dumps(receipt))
