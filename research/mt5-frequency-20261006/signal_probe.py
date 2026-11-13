from pathlib import Path
import csv,json,hashlib
from frequency_engine import Market,ms,norm,MIN
from frozen_prior_engine import load_ticks
B=Path(__file__).resolve().parent;proto=json.loads((B/'protocol.json').read_text());start=ms(proto['period_UTC'][0]);end=ms(proto['period_UTC'][1]);m=Market();signals={}
for t,bid,ask in load_ticks(proto['input_readonly']['path'],'utc'):
 if t>=end:continue
 ctx=m.ingest(t,bid,ask)
 if t<start:continue
 _,_,_,k,day,ma,box=ctx
 if day in signals or not day+3*60*MIN<=t<day+13*60*MIN or ma is None or box is None:continue
 side=1 if bid>ma else -1 if bid<ma else 0
 if not side:continue
 high,low=box;entry=norm(high+.0001 if side==1 else low-.0001,'nearest');sl=norm(low-.0001 if side==1 else high+.0001,'floor' if side==1 else 'ceil');rawentry=high+.0001 if side==1 else low-.0001;rawsl=low-.0001 if side==1 else high+.0001;tp=norm(rawentry+side*abs(rawentry-rawsl)*1.3,'floor' if side==1 else 'ceil')
 if (side==1 and entry<=ask) or (side==-1 and entry>=bid):continue
 signals[day]={'timestamp':__import__('datetime').datetime.fromtimestamp(t/1000,__import__('datetime').timezone.utc).isoformat(),'side':side,'entry':entry,'sl':sl,'tp':tp,'MA':ma}
old=Path('/Volumes/EXTERNAL/量化/research/mt5-asian-august-20261006/base/ledger.csv');prior=[r for r in csv.DictReader(old.open()) if r['event']=='PENDING'];matches=[]
for r,s in zip(prior,signals.values()):
 assert r['timestamp']==s['timestamp'] and int(r['side'])==s['side']
 for f in ['entry','sl','tp','MA']:assert abs(float(r[f])-s[f])<1e-10,(f,r[f],s[f])
 matches.append({'timestamp':s['timestamp'],'first_schedule_levels_and_MA':'PASS'})
assert len(matches)==20==len(signals)
result={'status':'PASS','matches':matches,'prior_ledger_sha256':hashlib.sha256(old.read_bytes()).hexdigest(),'new_signal_only_no_PnL_or_accounts':True,'scope':'firstnormalPENDING initial cadence, not alltrades/risklot nativeparity','cache_equivalence':'49consecutive closedbars chronological sum plus currentquote, matched firstsignalMA'}
(B/'signal_equivalence.json').write_text(json.dumps(result,indent=2));print('20 first signals/levels/MA matched before PnL')

