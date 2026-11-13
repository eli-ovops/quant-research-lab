from pathlib import Path
import json,hashlib,datetime,decimal
B=Path(__file__).resolve().parent
SRC=Path('/Volumes/EXTERNAL/量化/research/feasibility-20260926/trend')
DAY=86400000
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def iso(t):return datetime.datetime.fromtimestamp(t/1000,datetime.timezone.utc).isoformat()
def ts(s):return int(datetime.datetime.fromisoformat(s).replace(tzinfo=datetime.timezone.utc).timestamp()*1000)
def load():
 manifests={}
 for m in [SRC/'manifest.json',SRC/'resume_20260926/manifest.json']:
  for r in json.loads(m.read_text())['files']:manifests[r['path']]=r['sha256']
 receipts={r['path']:r for s in [SRC/'sources.json',SRC/'resume_20260926/sources.json'] for r in json.loads(s.read_text())}
 raw={c:{} for c in ['BTC','ETH']};files=[];dup={c:0 for c in raw}
 for c in raw:
  paths=sorted((SRC/'raw').glob(c+'_daily_*.txt'))
  paths+=sorted((SRC/'resume_20260926/raw').glob(c+'_daily_resume_*.txt'))
  for f in paths:
   h=sha(f);assert h==manifests[str(f)]
   receipt=receipts.get(str(f));assert receipt and receipt['sha256']==h
   assert 'bar=1Dutc' in receipt['url']
   obj=json.loads(f.read_text());assert obj['code']=='0'
   files.append({'path':str(f),'sha256':h,'bytes':f.stat().st_size,'url':receipt['url'],'retrieved_utc':receipt.get('received_utc'),'prior_manifest_hash_match':True})
   for r in obj['data']:
    assert len(r)==9 and r[-1]=='1';t=int(r[0]);assert t%DAY==0
    v=list(map(decimal.Decimal,r[1:8]));assert all(x.is_finite() for x in v)
    o,high,low,close=v[:4];assert 0<low<=min(o,close)<=max(o,close)<=high and v[4]>0 and min(v[5:])>=0
    if t in raw[c]:assert raw[c][t]==r;dup[c]+=1
    raw[c][t]=r
 summary={}
 for c,d in raw.items():
  tt=sorted(d);missing=[t for t in range(tt[0],tt[-1]+DAY,DAY) if t not in d]
  assert not missing
  summary[c]={'first':iso(tt[0]),'last':iso(tt[-1]),'days':len(tt),'duplicate_identical_rows':dup[c],'conflicting_duplicates':0,'missing_internal_days':missing,'all_confirmed':True,'all_OHLC_positive_consistent':True,'zero_volume_days':0,'UTC_timestamp_remainder_ms':0}
 return raw,files,summary
if __name__=='__main__':
 raw,files,summary=load()
 bounds=[('2020-2022','2020-01-01','2023-01-01'),('2023-2024','2023-01-01','2025-01-01'),('2025-2026H1','2025-01-01','2026-07-01')]
 earliest=max(min(d)+91*DAY for d in raw.values())
 periods=[]
 for name,s,e in bounds:
  a=max(ts(s),earliest);z=ts(e)
  assert all(t in raw[c] for c in raw for t in range(a-91*DAY,z,DAY))
  periods.append({'id':name,'requested_start':s,'requested_end_exclusive':e,'evaluated_start':iso(a)[:10],'evaluated_end_exclusive':e,'days':(z-a)//DAY,'original_interval_status':'INVALID_HEAD_WARMUP' if a!=ts(s) else 'COMPLETE','shortening_reason':'91 previous closed bars required to compare previous close against 90 days before it; no price/return inspected for range choice' if a!=ts(s) else None})
 audit={'assets':summary,'source_files':files,'source_metadata':[{'path':str(p),'sha256':sha(p)} for p in [SRC/'sources.json',SRC/'resume_20260926/sources.json',SRC/'manifest.json',SRC/'resume_20260926/manifest.json']],'periods':periods,'timezone':'1Dutc plus every ts=00:00 UTC verified','historical_tick_lot_minimum_specs':'UNKNOWN; continuous quantity model','point_in_time_revisions':'UNKNOWN; retrieved September26 2026, reused historical research, not blind/OOS','network_calls':0}
 B.mkdir(exist_ok=True);(B/'dataaudit.json').write_text(json.dumps(audit,indent=2,ensure_ascii=False))
 proto={'frozen_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'routing':{'rule':'ROUTING-2026-09-30-v3','target':'gpt-6.1-sol medium','actual':'UNKNOWN'},'owner':'/root/external_relative_value','strategy_count':1,'assets':['BTC-USDT','ETH-USDT'],'initial_cash_USDT_each_period':500,'allocation':'each asset target0.5 of total post-cost NAV when its signal positive; else0; shared cash, sells then buys; exact postcost NAV root solve','momentum':'At Monday00:00UTC (bar i open), close[i-1]/close[i-91]-1>0. All inputs closed before execution. Signals i-1 and i-91 span90 daily intervals. No stop/threshold search. Next bar open after latest closed Sunday daily bar.','execution':'Monday open only; all orders adverse slip, fee on slipped notional. Terminal forced sale at final close with same costs, excluded from weekly-only constraint.','costs':{'base':{'fee_bps_each_side':10,'slip_bps_each_side':5},'stress':{'fee_bps_each_side':20,'slip_bps_each_side':10},'zero_diagnostic':{'fee_bps_each_side':0,'slip_bps_each_side':0}},'benchmarks':'same-period500USDT 50/50 once buy at first evaluated open; quantities fixed until terminal sale; same costs. Cash benchmark500/no interest.','warmup_bars':91,'periods':periods,'dataaudit_sha256':sha(B/'dataaudit.json'),'source_files':files,'metrics':'net return, daily-close max drawdown (include initial500 and terminal costs), absolute traded reference notional/500 turnover (two sided includes terminal), trades number individual nonzero legs, mean daily close invested-market-value/NAV, active days fraction, worst close-to-close day including initial500, return/DD ratio','acceptance':'stress last net return>0 AND at least one first-two stress net return>0 AND last strategy DD<last hold DD AND last strategy return/DD>last hold return/DD. Otherwise reject fixed rule; no rescue. A pass at most historical conditional candidate, no new independent holdout or promotion.','limitations':'Continuous quantities, account rounding/minimum unknown; daily open/close not real bidask; no depth, latency or partial fills. Stablecoin-denominated, USDT depeg not adjusted. History previously used in other research.','budget':{'minutes':25,'network_calls':0,'install':False,'subagents':False}}
 (B/'protocol.json').write_text(json.dumps(proto,indent=2,ensure_ascii=False));(B/'freeze.json').write_text(json.dumps({'protocol_sha256':sha(B/'protocol.json'),'dataaudit_sha256':sha(B/'dataaudit.json'),'frozen_before_simulation':True},indent=2))
 print(json.dumps({'audit':summary,'periods':periods,'protocol_hash':sha(B/'protocol.json')},indent=2))
