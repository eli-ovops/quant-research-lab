from pathlib import Path
import csv,json,zipfile,io,datetime as dt,hashlib,math
B=Path(__file__).resolve().parent;UTC=dt.timezone.utc;EST=dt.timezone(dt.timedelta(hours=-5));MIN=60000;DAY=86400000
START=dt.datetime(2026,8,3,tzinfo=UTC);END=dt.datetime(2026,8,29,tzinfo=UTC);s=int(START.timestamp()*1000);e=int(END.timestamp()*1000);lo=s-5*60*MIN
src=B/'raw/EURUSD_202608_provider_response.bin';z=zipfile.ZipFile(src);member='DAT_ASCII_EURUSD_T_202608.csv';assert member in z.namelist()
rows=[];globalcount=0;inversions=[];prev=None
with z.open(member) as f:
 for idx,r in enumerate(csv.reader(io.TextIOWrapper(f))):
  globalcount+=1;assert len(r)==4 and len(r[0])==18 and r[0][:6]=='202608'
  if prev and r[0]<prev:inversions.append({'raw_index':idx,'prior_timestamp':prev,'timestamp':r[0]})
  prev=r[0]
  if r[0]<'20260802 140000000' or r[0]>='20260828 190000000':continue
  stamp=dt.datetime.strptime(r[0][:15],'%Y%m%d %H%M%S').replace(tzinfo=EST)+dt.timedelta(milliseconds=int(r[0][15:]));t=int(stamp.timestamp()*1000);bid,ask,v=map(float,r[1:]);assert math.isfinite(bid+ask+v) and 0<bid<=ask and v>=0
  if lo<=t<e:rows.append((t,idx,bid,ask,v))
rows.sort(key=lambda x:(x[0],x[1]));path=B/'EURUSD_august_selected_UTC.csv'
with path.open('w',newline='') as f:
 w=csv.writer(f);w.writerow(['timestamp','bid','ask'])
 for t,i,b,a,v in rows:w.writerow([dt.datetime.fromtimestamp(t/1000,UTC).isoformat(),format(b,'.6f'),format(a,'.6f')])
 if path.stat().st_size+src.stat().st_size>95000000:raise ValueError('95MB input allocation guard')
period=[r for r in rows if r[0]>=s];m5={r[0]//(5*MIN)*5*MIN for r in rows};m15={r[0]//(15*MIN)*15*MIN for r in rows};sessions=[];gaps=[];prev=None;zeroMs=eqTime=eqConflicts=0;days={};dayquotes={}
for r in period:
 t=r[0];day=dt.datetime.fromtimestamp(t/1000,UTC).strftime('%Y-%m-%d');days[day]=days.get(day,0)+1;zeroMs+=t%1000==0
 dayquotes.setdefault(t//DAY*DAY,[]).append(t)
 if prev:
  delta=(t-prev[0])/1000
  if delta>60:gaps.append({'from_ms':prev[0],'to_ms':t,'seconds':delta,'cross_M5':prev[0]//(5*MIN)!=t//(5*MIN)})
  if t==prev[0]:eqTime+=1;eqConflicts+=r[2:4]!=prev[2:4]
 prev=r
for day in range(s,e,DAY):
 d=dt.datetime.fromtimestamp(day/1000,UTC)
 if d.weekday()>=5:continue
 close=day+3*60*MIN;box=[k for k in range(close-4*60*MIN,close,15*MIN) if k not in m15];ma=[k for k in range(close-49*5*MIN,close,5*MIN) if k not in m5];quotes=[t for t in dayquotes.get(day,[]) if day+3*60*MIN<=t<day+13*60*MIN+MIN]
 sessions.append({'date':d.strftime('%Y-%m-%d'),'missing_box_M15':len(box),'missing_MA_M5':len(ma),'strategy_hour_quote_count':len(quotes),'first_strategy_quote_ms':min(quotes) if quotes else None,'last_strategy_quote_ms':max(quotes) if quotes else None,'observed_strategy_window':bool(quotes),'data_completeness':'UNKNOWN, minute noquotes not automatically missingdata'})
audit={'source_zip_sha256':hashlib.sha256(src.read_bytes()).hexdigest(),'source_zip_bytes':src.stat().st_size,'archive_member':member,'all_month_stream_rows':globalcount,'fullscan_no_earlybreak':True,'normalization':'eventtime/rawordinal stable, all equal-time originalquotes retained','global_inversion_count':len(inversions),'inversions':inversions,'timezone':'official fixedEST UTC-5 noDST mappedUTC','period_UTC':['2026-08-03T00:00:00Z','2026-08-29T00:00:00Z'],'quote_rows_period':len(period),'warmup_rows':len(rows)-len(period),'all_observed_whole_seconds':zeroMs==len(period),'equal_timestamp_adjacent':eqTime,'equal_timestamp_differingquotes':eqConflicts,'tickdata_not_fullmarket_or_arrivalcertified':True,'volume_allzero_period':all(r[4]==0 for r in period),'ticks_by_UTCdate':days,'sessions':sessions,'actual_gaps_gt60s':gaps,'first_ms':period[0][0],'last_ms':period[-1][0],'input':{'path':str(path.resolve()),'bytes':path.stat().st_size,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()},'full_source_complete':'UNKNOWN'}
p=B/'dataaudit.json';p.write_text(json.dumps(audit,indent=2))
(B/'dataaudit_freeze.json').write_text(json.dumps({'dataaudit_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'input_sha256':audit['input']['sha256'],'at_utc':dt.datetime.now(UTC).isoformat(),'before_august_PnL':True},indent=2))
print(json.dumps({'rows':len(period),'warmup':audit['warmup_rows'],'input_bytes':path.stat().st_size,'days':days,'missing_sessions':[x for x in sessions if x['missing_box_M15'] or x['missing_MA_M5'] or not x['observed_strategy_window']],'first_ms':audit['first_ms'],'last_ms':audit['last_ms'],'gap_count':len(gaps),'allseconds':audit['all_observed_whole_seconds']},indent=2))

