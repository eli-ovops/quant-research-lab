from pathlib import Path
import json,hashlib,datetime,csv,platform
from decimal import Decimal as D
import analyze
P=Path(__file__).resolve().parent;B=P.parent/'funding';now=datetime.datetime.now(datetime.timezone.utc).isoformat()
def save(n,x):(P/n).write_text(json.dumps(x,ensure_ascii=False,indent=2,default=str)+'\n')
sources=json.loads((P/'sources.json').read_text())
# Reuse immutable official documentation already retrieved by B, preserving original provenance.
bs=json.loads((B/'sources.json').read_text())
for original,name in [('api_docs','docs_api'),('fee_rules','docs_fees')]:
 old=next(x for x in bs if x['name']==original);f=P/'raw'/(name+'.txt');f.write_bytes(Path(old['path']).read_bytes());row=dict(old);row.update(name=name,path=str(f),reuse_original_path=old['path'],reused_at_utc=now);sources.append(row)
save('sources.json',sources)
data,spec,struct=analyze.load();pro=json.loads((P/'protocol.json').read_text());coverage=[];failed=[]
for period,(a,b) in pro['periods'].items():
 row={'period':period,'requested_start':a,'requested_end':b,'assets':{}}
 for c in analyze.COINS:
  needed=list(range(analyze.ts(a)-40*analyze.DAY,analyze.ts(b)+analyze.DAY,analyze.DAY));missing=[t for t in needed if t not in data[c]]
  row['assets'][c]={'expected_days_with_warmup':len(needed),'present_days':len(needed)-len(missing),'missing_days':len(missing),'first_missing':analyze.date(missing[0]) if missing else None,'last_missing':analyze.date(missing[-1]) if missing else None}
 coverage.append(row)
 try:analyze.simulate(data,spec,a,b)
 except AssertionError as e:failed.append({'period':period,'stage':'required completeness gate before PnL','error':str(e),'pnl_computed':False})
 else:raise AssertionError('unexpected complete period')
for r in sources:assert hashlib.sha256(Path(r['path']).read_bytes()).hexdigest()==r['sha256']
independent={}
for c in ['BTC','ETH']:
 rows={}
 for p in (P/'raw').glob(c+'_daily_*.txt'):
  obj=json.loads(p.read_text());assert obj['code']=='0'
  for r in obj['data']:
   assert r[-1]=='1';t=int(r[0]);lo,hi=D(r[3]),D(r[2]);assert lo<=D(r[1])<=hi and lo<=D(r[4])<=hi;assert t not in rows;rows[t]=r
 t=sorted(rows);assert all(b-a==86400000 for a,b in zip(t,t[1:]));independent[c]={'raw_bars':len(rows),'first':analyze.date(t[0]),'last':analyze.date(t[-1]),'no_internal_gaps':True,'duplicates':0,'confirmed':True,'required_old_history_missing':c=='ETH'}
save('data_audit.json',{'structure':struct,'period_completeness':coverage,'independent_raw_check':independent})
save('results_all.json',{'status':'BLOCKED_DATA','verdict':'INSUFFICIENT_EVIDENCE','planned_scenarios':27,'completed_historical_scenarios':0,'failed_period_gates':failed,'net_pnl':None,'drawdown':None,'benchmarks':None,'bootstrap_interval':None,'holdout_executable_samples':0,'actual_orders':0,'reason':'ETH only500 bars; all3 preregistered periods lack required history. No truncated-window or BTC-only replacement.'})
save('validation.json',{'at':now,'source_hashes_checked':len(sources),'independent_raw_check':independent,'unit_tests':{'count':10,'result':'PASS','evidence':'tests.txt','synthetic_only':True},'real_history_cash_replay':'NOT_RUN','historical_signal_completeness':'NOT_RUN','real_accounts_checked':0,'acceptance':'NOT_PASSED'})
save('seal.json',{'recorded_at':now,'sealed_results_opened':False,'status':'NOT_OPENED_DATA_INCOMPLETE','protocol_sha256':hashlib.sha256((P/'protocol.json').read_bytes()).hexdigest(),'analysis_sha256':hashlib.sha256((P/'analyze.py').read_bytes()).hexdigest(),'data_sources_sha256':hashlib.sha256((P/'sources.json').read_bytes()).hexdigest(),'prior_data_access':'Raw arrays structurally parsed and chronology checked; no valid portfolio returns computed. B result summary prior to C freeze disclosed in protocol.'})
for name,fields in [('trades_all.csv',['period','variant','trade_id','coin','entry_date','exit_date','net_pnl']),('equity_all.csv',['period','variant','date','cash','BTC_qty','ETH_qty','liquidation_equity_proxy']),('fills_all.csv',['period','variant','date','coin','side','quantity','cash_delta'])]:
 with (P/name).open('w',newline='') as f:csv.writer(f).writerow(fields)
attempts=json.loads((P/'attempts.json').read_text());attempts.append({'stage':'official alternate host','error':'curl exit28, ETH same cursor, no progress','action':'bounded acquisition stopped; shared portfolio completeness gates reject all3 periods; no historical returns claimed','at':now});save('attempts.json',attempts)
print(json.dumps({'sources':len(sources),'structure':struct,'missing':coverage},ensure_ascii=False,indent=2))
