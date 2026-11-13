from pathlib import Path
import zipfile,io,csv,json,datetime as dt,hashlib,math
B=Path(__file__).resolve().parent;UTC=dt.timezone.utc;EST=dt.timezone(dt.timedelta(hours=-5));M5=300000;M15=900000;DAY=86400000
p=json.loads((B/'protocol.json').read_text());src=Path(p['source_zip']['path']);assert hashlib.sha256(src.read_bytes()).hexdigest()==p['source_zip']['sha256'];start=dt.datetime(2026,9,7,tzinfo=UTC);end=dt.datetime(2026,9,19,tzinfo=UTC);s=int(start.timestamp()*1000);e=int(end.timestamp()*1000);rows=[];scanned=0;prev=None;globalinversions=0
z=zipfile.ZipFile(src);member='DAT_ASCII_EURUSD_T_202609.csv'
with z.open(member) as f:
 for idx,r in enumerate(csv.reader(io.TextIOWrapper(f))):
  scanned+=1;assert len(r)==4 and r[0][:6]=='202609'
  if prev and r[0]<prev:globalinversions+=1
  prev=r[0]
  if r[0]<'20260906 140000000' or r[0]>='20260918 190000000':continue
  stamp=dt.datetime.strptime(r[0][:15],'%Y%m%d %H%M%S').replace(tzinfo=EST)+dt.timedelta(milliseconds=int(r[0][15:]));t=int(stamp.timestamp()*1000);bid,ask,v=map(float,r[1:]);assert math.isfinite(bid+ask+v) and 0<bid<=ask and v>=0
  if s-5*3600000<=t<e:rows.append((t,idx,bid,ask,v))
rows.sort(key=lambda x:(x[0],x[1]));inputp=B/'EURUSD_Sep07_19_UTC.csv'
with inputp.open('w',newline='') as f:
 w=csv.writer(f);w.writerow(['timestamp','bid','ask'])
 for t,i,b,a,v in rows:w.writerow([dt.datetime.fromtimestamp(t/1000,UTC).isoformat(),format(b,'.6f'),format(a,'.6f')])
assert inputp.stat().st_size<35000000
period=[r for r in rows if r[0]>=s];m5={r[0]//M5*M5 for r in rows};m15={r[0]//M15*M15 for r in rows};days={};gaps=[];repeat=conflicts=0
for a,b in zip(period,period[1:]):
 if a[0]==b[0]:repeat+=1;conflicts+=a[2:4]!=b[2:4]
 if b[0]-a[0]>60000:gaps.append({'from_ms':a[0],'to_ms':b[0],'seconds':(b[0]-a[0])/1000})
for t,*_ in period:
 d=dt.datetime.fromtimestamp(t/1000,UTC).strftime('%Y-%m-%d');days[d]=days.get(d,0)+1
sessions=[]
for day in range(s,e,DAY):
 date=dt.datetime.fromtimestamp(day/1000,UTC)
 if date.weekday()>=5:continue
 k=day+3*3600000;sessions.append({'day':date.strftime('%Y-%m-%d'),'box_missingM15':sum(x not in m15 for x in range(k-4*3600000,k,M15)),'MA_missingM5':sum(x not in m5 for x in range(k-49*M5,k,M5))})
audit={'source_zip_path':str(src),'source_zip_sha256':p['source_zip']['sha256'],'scanned_fullmonth_rows':scanned,'fullscan_noearlybreak':True,'global_timestamp_inversions':globalinversions,'member':member,'period_UTC':p['period_UTC'],'input':{'path':str(inputp.resolve()),'bytes':inputp.stat().st_size,'sha256':hashlib.sha256(inputp.read_bytes()).hexdigest()},'periodquotes':len(period),'prewarmup':len(rows)-len(period),'retains_betweenweeks_Sunday':days.get('2026-09-13',0),'normalization':'stable(timestamp,rawordinal); no dedup all real repeats retained','equal_timestamp_adjacent':repeat,'equal_timestamp_differingquotes':conflicts,'first_ms':period[0][0],'last_ms':period[-1][0],'days':days,'weekday_sessions':sessions,'gaps_gt60s':gaps,'timezone':'fixedEST UTC-5 noDST toUTC','full_market_source_complete':'UNKNOWN','noquote_minutes_not_automatic_missingdata':True}
(B/'dataaudit.json').write_text(json.dumps(audit,indent=2));(B/'dataaudit_freeze.json').write_text(json.dumps({'dataaudit_sha256':hashlib.sha256((B/'dataaudit.json').read_bytes()).hexdigest(),'input_sha256':audit['input']['sha256'],'before_newSepPnL':True,'at_utc':dt.datetime.now(UTC).isoformat()},indent=2));print(json.dumps({k:v for k,v in audit.items() if k not in ['gaps_gt60s']},indent=2))

