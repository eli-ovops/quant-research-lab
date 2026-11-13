"""Local immutable-ZIP import; declared provider event-time normalization before PnL."""
from pathlib import Path
import json,hashlib,zipfile,csv,io,datetime as dt,math
B=Path(__file__).resolve().parent;UTC=dt.timezone.utc;EST=dt.timezone(dt.timedelta(hours=-5))
START=dt.datetime(2026,9,21,tzinfo=UTC);END=dt.datetime(2026,9,26,tzinfo=UTC);WARM=START-dt.timedelta(hours=5)
source=B/'raw/EURUSD_202609_provider_response.bin';sha=hashlib.sha256(source.read_bytes()).hexdigest()
rows=[];previous=None;bad=[];invalid=[];counts={};first=None;last=None;global_previous=None;global_bad=[];global_count=0;selected_after_first_end=0;seen_end=False
z=zipfile.ZipFile(source);member=next(x for x in z.namelist() if x=='DAT_ASCII_EURUSD_T_202609.csv')
with z.open(member) as f:
 for idx,r in enumerate(csv.reader(io.TextIOWrapper(f))):
  if len(r)!=4:raise ValueError('invalid fields')
  global_count+=1
  if global_previous is not None and r[0]<global_previous:global_bad.append({'previous_raw_timestamp':global_previous,'current_raw_timestamp':r[0],'raw_index':idx})
  global_previous=r[0]
  if r[0]>='20260925 190000000':seen_end=True;continue
  if r[0]<'20260920 140000000':continue
  if seen_end:selected_after_first_end+=1
  stamp=dt.datetime.strptime(r[0][:15],'%Y%m%d %H%M%S').replace(tzinfo=EST)+dt.timedelta(milliseconds=int(r[0][15:]))
  t=int(stamp.timestamp()*1000);bid=float(r[1]);ask=float(r[2]);vol=float(r[3]);assert math.isfinite(bid+ask+vol) and 0<bid<=ask and vol>=0
  if previous is not None and t<previous[0]:bad.append({'prior_raw_index':previous[1],'raw_index':idx,'backward_ms':previous[0]-t,'cross_M5_bucket':previous[0]//300000!=t//300000})
  previous=(t,idx);rows.append((t,idx,bid,ask,vol))
 # No data rows invented or dropped; equal timestamp original order remains.
rows.sort(key=lambda x:(x[0],x[1]));fixed=[x for x in rows if START.timestamp()*1000<=x[0]<END.timestamp()*1000];warm=[x for x in rows if WARM.timestamp()*1000<=x[0]<START.timestamp()*1000]
def save(name,rr):
 p=B/name
 with p.open('w',newline='') as f:
  w=csv.writer(f);w.writerow(['timestamp','bid','ask'])
  for t,idx,bid,ask,vol in rr:w.writerow([dt.datetime.fromtimestamp(t/1000,UTC).isoformat(),format(bid,'.6f'),format(ask,'.6f')])
 return {'path':str(p),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'rows':len(rr)}
for t,idx,bid,ask,vol in fixed:
 d=dt.datetime.fromtimestamp(t/1000,UTC).strftime('%Y-%m-%d');counts[d]=counts.get(d,0)+1
gaps=[{'from':dt.datetime.fromtimestamp(a[0]/1000,UTC).isoformat(),'to':dt.datetime.fromtimestamp(b[0]/1000,UTC).isoformat(),'seconds':(b[0]-a[0])/1000} for a,b in zip(fixed,fixed[1:]) if b[0]-a[0]>300000]
audit={'source_zip_sha256':sha,'member':member,'official_timezone':'fixedEST UTC-5 noDST','period_UTC':['2026-09-21T00:00:00Z','2026-09-26T00:00:00Z'],'normalization':'stable ascending provider event timestamp, equal timestamps retain raw order; not arrival-time replay','all_rows_retained':True,'full_month_stream_rows':global_count,'global_timestamp_inversions':global_bad,'global_timestamp_inversion_count':len(global_bad),'selected_rows_after_first_out_of_window_end':selected_after_first_end,'inversions':bad,'inversion_count':len(bad),'cross_M5_inversions':sum(x['cross_M5_bucket'] for x in bad),'max_backward_ms':max([x['backward_ms'] for x in bad] or [0]),'ticks_by_day':counts,'gaps_gt5minutes':gaps,'first':dt.datetime.fromtimestamp(fixed[0][0]/1000,UTC).isoformat() if fixed else None,'last':dt.datetime.fromtimestamp(fixed[-1][0]/1000,UTC).isoformat() if fixed else None,'zero_volume_is_provider_unknown_not_trade_volume':sum(x[4]==0 for x in fixed),'quote_data_not_trade_data':True,'market_session_tail_outside_observed_quotes':'UNKNOWN; no fill','input':save('EURUSD_fixedweek_fullscan_UTC.csv',fixed),'warmup':save('EURUSD_warmup_fullscan_UTC.csv',warm),'replaces_prior_audit':'real_data_audit.json; completeZIP scan now removes earlybreak sortedness assumption'}
(B/'real_data_audit_fullscan.json').write_text(json.dumps(audit,indent=2));print(json.dumps({k:v for k,v in audit.items() if k!='global_timestamp_inversions'},indent=2))
