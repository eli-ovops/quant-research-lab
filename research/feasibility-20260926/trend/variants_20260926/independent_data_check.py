"""Independent raw coverage verifier; deliberately imports no collector/gate/strategy code."""
from pathlib import Path
import json,hashlib,datetime,decimal,itertools
P=Path(__file__).resolve().parent;D=decimal.Decimal
proto=json.loads((P/'protocol.json').read_text());freeze=json.loads((P/'protocol_freeze.json').read_text());assert hashlib.sha256((P/'protocol.json').read_bytes()).hexdigest()==freeze['sha256']
def milliseconds(s):return round(datetime.datetime.fromisoformat(s).timestamp()*1000)
start=milliseconds(proto['data']['start']);end=milliseconds(proto['data']['end_exclusive']);expected=set(range(start,end,3600000));assert len(expected)==57032
assert milliseconds(proto['periods_UTC_half_open']['early'][0])-start==80*3600000
sources=json.loads((P/'sources.json').read_text());verified=0
for src in sources:
 f=Path(src['path']);assert hashlib.sha256(f.read_bytes()).hexdigest()==src['sha256'],f;verified+=1
reused=json.loads((P/'reuse_hourly_sources.json').read_text());out={}
for coin in ['BTC','ETH']:
 bars={}
 files=[Path(x['path']) for x in reused if x['coin']==coin]+list((P/'raw').glob(coin+'_*.json'))
 for f in files:
  obj=json.loads(f.read_text());assert obj['code']=='0'
  for row in obj['data']:
   t=int(row[0])
   if t not in expected:continue
   if t in bars:assert bars[t]==row
   assert row[8]=='1';o,h,l,c=map(D,row[1:5]);assert 0<l<=o<=h and l<=c<=h;assert all(D(v)>0 for v in row[5:8]);bars[t]=row
 days={}
 for t,row in bars.items():days.setdefault(t//86400000,[]).append(row)
 old={int(r[0])//86400000:r for f in list((P.parent/'raw').glob(coin+'_daily_*.txt'))+list((P.parent/'resume_20260926'/'raw').glob(coin+'_daily_*.txt')) for r in json.loads(f.read_text())['data']}
 matches=0
 for day,rr in days.items():
  if len(rr)!=24:continue
  rr.sort(key=lambda r:int(r[0]));a=[D(rr[0][1]),max(D(r[2]) for r in rr),min(D(r[3]) for r in rr),D(rr[-1][4])]+[sum(D(r[col]) for r in rr) for col in [5,6,7]]
  assert a==list(map(D,old[day][1:8]));matches+=1
 out[coin]={'eligible_hours':len(bars),'missing':len(expected-set(bars)),'full_days_exact_OHLC_volume':matches,'data_complete':set(bars)==expected}
 assert len(bars)==110 and len(expected-set(bars))==56922 and matches==4
res=json.loads((P/'results_all.json').read_text());rr=res['principal_scenarios'];assert len(rr)==108 and len(res['auxiliary_hold'])==12
actual={(r['period'],r['entry_hours'],r['exit_hours'],r['condition']) for r in rr}
assert actual==set(itertools.product(proto['periods_UTC_half_open'],[24,48,72],[4,8,12],proto['conditions']))
assert all(r['net_pnl'] is None and r['status']=='NOT_COMPUTED_DATA_BLOCKED' for r in rr)
a=json.loads((P/'attempts.json').read_text());assert len(a)==2 and a[0].get('error') and a[1]['exit_code']==28
assert datetime.datetime.fromisoformat(freeze['frozen_utc'])<datetime.datetime.fromisoformat(a[0]['request_utc'])
result={'verification':'PASS_FOR_BLOCKED_PACKAGE_ONLY','protocol_hash_unchanged':True,'freeze_precedes_new_requests':True,'verified_source_hashes':verified,'by_coin':out,'principal_combinations':108,'principal_computed':0,'auxiliary_hold_planned':12,'public_attempts':2,'strategy_independent_replay':'NOT_IMPLEMENTED_NOT_RUN','limitation':'Verifier independently supports coverage and missing-output claims only, not strategy correctness or profitability'}
(P/'independent_data_check.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
