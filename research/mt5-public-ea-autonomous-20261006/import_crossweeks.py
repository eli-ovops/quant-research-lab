from pathlib import Path
import csv,json,zipfile,io,datetime as dt,hashlib,math
B=Path(__file__).resolve().parent;UTC=dt.timezone.utc;EST=dt.timezone(dt.timedelta(hours=-5));MIN=60000;DAY=86400000
windows=[('week0907','2026-09-07T00:00:00Z','2026-09-12T00:00:00Z'),('week0914','2026-09-14T00:00:00Z','2026-09-19T00:00:00Z')]
def millis(x):return int(dt.datetime.fromisoformat(x.replace('Z','+00:00')).timestamp()*1000)
source=B/'raw/EURUSD_202609_provider_response.bin';z=zipfile.ZipFile(source);member='DAT_ASCII_EURUSD_T_202609.csv';allrows={name:[] for name,s,e in windows};bounds={name:(millis(s),millis(e)) for name,s,e in windows}
with z.open(member) as f:
 for idx,r in enumerate(csv.reader(io.TextIOWrapper(f))):
  # whole source scanned, never earlybreak on a time presumed sorted
  rawday=r[0][:8]
  if not ('20260906'<=rawday<='20260918'):continue
  t=dt.datetime.strptime(r[0][:15],'%Y%m%d %H%M%S').replace(tzinfo=EST)+dt.timedelta(milliseconds=int(r[0][15:]));t=int(t.timestamp()*1000)
  for name,(s,e) in bounds.items():
   if s-5*60*MIN<=t<e:
    bid,ask=float(r[1]),float(r[2]);assert math.isfinite(bid+ask) and 0<bid<=ask;allrows[name].append((t,idx,bid,ask))
def write(name,rows):
 p=B/name
 with p.open('w',newline='') as f:
  w=csv.writer(f);w.writerow(['timestamp','bid','ask'])
  for t,i,b,a in rows:w.writerow([dt.datetime.fromtimestamp(t/1000,UTC).isoformat(),format(b,'.6f'),format(a,'.6f')])
 return {'path':str(p),'rows':len(rows),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
for name,sstr,estr in windows:
 s,e=bounds[name];rr=allrows[name];inversions=sum(a[0]>b[0] for a,b in zip(rr,rr[1:]));rr.sort(key=lambda x:(x[0],x[1]));fixed=[r for r in rr if s<=r[0]<e];warm=[r for r in rr if r[0]<s];m5={r[0]//(5*MIN)*5*MIN for r in rr};m15={r[0]//(15*MIN)*15*MIN for r in rr};minutes={r[0]//MIN*MIN for r in rr};sessions=[]
 for day in range(s,e,DAY):
  sesend=day+3*60*MIN;k=sesend//(5*MIN)*5*MIN
  boxmiss=[x for x in range(sesend-4*60*MIN,sesend,15*MIN) if x not in m15];mamiss=[x for x in range(k-49*5*MIN,k,5*MIN) if x not in m5];tradmiss=[x for x in range(sesend,day+13*60*MIN+MIN,MIN) if x not in minutes]
  sessions.append({'date':dt.datetime.fromtimestamp(day/1000,UTC).strftime('%Y-%m-%d'),'box_missing_M15':len(boxmiss),'MA_missing_M5':len(mamiss),'trade_missing_minutes_03_to13inclusive':len(tradmiss),'pass':not boxmiss and not mamiss and not tradmiss})
 audit={'period_UTC':[sstr,estr],'source_zip_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'source_timezone':'fixedEST UTC-5 noDST','member':member,'normalization':'eventtime stable/rawordinal; all same-time quote original order retained','inversion_count':inversions,'observed_timestamp_resolution':'seconds, not fullmarket tick','sessions':sessions,'all_five_sessions_data_pass':all(x['pass'] for x in sessions),'input':write(name+'_ticks.csv',fixed),'warmup':write(name+'_warmup.csv',warm),'first':dt.datetime.fromtimestamp(fixed[0][0]/1000,UTC).isoformat() if fixed else None,'last':dt.datetime.fromtimestamp(fixed[-1][0]/1000,UTC).isoformat() if fixed else None,'source_completeness':'providerfullmonth ZIP, actual observed session bins audit; nativebroker coverage UNKNOWN'}
 p=B/(name+'_dataaudit.json');p.write_text(json.dumps(audit,indent=2));(B/(name+'_dataaudit_freeze.json')).write_text(json.dumps({'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'at_utc':dt.datetime.now(UTC).isoformat(),'before_that_period_PnL':True},indent=2));print(json.dumps(audit,indent=2))
