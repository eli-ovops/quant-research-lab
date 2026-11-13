from pathlib import Path
import csv,json,datetime as dt,hashlib
B=Path(__file__).resolve().parent
configs=[('original_partial','EURUSD_fixedweek_fullscan_UTC.csv','replay_fullscan_commission7'),('week0907','week0907_ticks.csv','week0907_commission7'),('week0914','week0914_ticks.csv','week0914_commission7')]
def t(s):return dt.datetime.fromisoformat(s)
out=[]
for name,inputfile,run in configs:
 events=list(csv.DictReader((B/run/'ledger.csv').open()));trades=[e for e in events if e['event'] in ['OPEN','CLOSE']];pending=[e for e in events if e['event']=='PENDING'];gaps=[];first_after13={};observed_dates=set();previous=None
 with (B/inputfile).open() as f:
  for row in csv.DictReader(f):
   time=t(row['timestamp']);day=time.strftime('%Y-%m-%d');observed_dates.add(day)
   if time.hour>=13 and day not in first_after13:first_after13[day]=row['timestamp']
   if previous:
    diff=(time-t(previous['timestamp'])).total_seconds()
    if diff>60:
     active=None
     for e in trades:
      if t(e['timestamp'])<=t(previous['timestamp']):active=e if e['event']=='OPEN' else None
      else:break
     po=None
     for e in pending:
      if e['timestamp'][:10]==previous['timestamp'][:10] and t(e['timestamp'])<=t(previous['timestamp']):po=e
     if po and (t(previous['timestamp']).hour>=13 or any(e['event']=='OPEN' and e['timestamp'][:10]==po['timestamp'][:10] and t(e['timestamp'])>=t(po['timestamp']) and t(e['timestamp'])<=t(previous['timestamp']) for e in trades)):po=None
     gaps.append({'from':previous['timestamp'],'to':row['timestamp'],'seconds':diff,'holding_position':active is not None,'pending_order':po is not None,'cross_M5':int(t(previous['timestamp']).timestamp())//300!=int(time.timestamp())//300,'intragap_SLTP_or_order_path':'UNKNOWN' if active or po else 'no active modeled risk','quote_absence_not_proof_of_missing_download':True})
   previous=row
 sessions=[]
 for day in sorted(observed_dates):
  pe=[e for e in pending if e['timestamp'][:10]==day];oe=[e for e in trades if e['event']=='OPEN' and e['timestamp'][:10]==day]
  status='traded' if oe else 'pending not triggered then modeled cancel on first quote>=13' if pe and day in first_after13 else 'no pending signal' if day in first_after13 else 'day truncated, cannot assess session'
  sessions.append({'day':day,'pending_count':len(pe),'entry_count':len(oe),'first_quote_at_or_after13':first_after13.get(day),'status':status})
 out.append({'period':name,'input_sha256':hashlib.sha256((B/inputfile).read_bytes()).hexdigest(),'actual_gaps_gt60seconds':gaps,'session_dispositions':sessions,'eventtime_quote_reconstruction':'conditional, not native fills or quote arrival latency','strict_minute_gate_original_preserved':True,'coverage_interpretation':'originalpartial missingFri main session; priorweeks observeall5sessions with quote gaps; provider completenessUNKNOWN'})
(B/'gap_context_audit.json').write_text(json.dumps(out,indent=2));print(json.dumps([{'period':x['period'],'gap_count':len(x['actual_gaps_gt60seconds']),'max_gap_seconds':max([g['seconds'] for g in x['actual_gaps_gt60seconds']] or [0]),'holding_gap_count':sum(g['holding_position'] for g in x['actual_gaps_gt60seconds']),'pending_gap_count':sum(g['pending_order'] for g in x['actual_gaps_gt60seconds']),'sessions':x['session_dispositions']} for x in out],indent=2))
