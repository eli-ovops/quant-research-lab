from pathlib import Path
from decimal import Decimal as D
from collections import defaultdict
import json,hashlib,datetime,itertools
P=Path(__file__).resolve().parents[2]/'trend'/'variants_20260926';OUT=Path(__file__).resolve().parent
read=lambda n:json.loads((P/n).read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();ms=lambda s:int(datetime.datetime.fromisoformat(s).timestamp()*1000)
p=read('protocol.json');assert sha(P/'protocol.json')=='d4a2fef3fc115291e0a9dd62c632c407c1e5bc99a5d59c81df60b83aefb43be4'
counts={}
for name,rows in [('sources',read('sources.json')),('manifest',read('manifest.json')['files'])]:
 for r in rows:assert sha(Path(r['path']) if Path(r['path']).is_absolute() else P/r['path'])==r['sha256']
 counts[name]=len(rows)
expected=set(range(ms(p['data']['start']),ms(p['data']['end_exclusive']),3600000));coins={}
for c in ['BTC','ETH']:
 bars={}
 for rec in read('reuse_hourly_sources.json'):
  if rec['coin']!=c:continue
  f=Path(rec['path']);assert sha(f)==rec['sha256']
  for r in json.loads(f.read_text())['data']:
   t=int(r[0])
   if t not in expected:continue
   if t in bars:assert bars[t]==r
   assert r[-1]=='1' and 0<D(r[3])<=min(D(r[1]),D(r[4]))<=max(D(r[1]),D(r[4]))<=D(r[2]);assert all(D(v)>0 for v in r[5:8]);bars[t]=r
 days=defaultdict(list)
 for t,r in bars.items():days[t//86400000].append(r)
 old={}
 for base in [P.parent,P.parent/'resume_20260926']:
  for f in (base/'raw').glob(c+'_daily_*.txt'):
   for r in json.loads(f.read_text())['data']:old[int(r[0])//86400000]=r
 matches=0
 for day,rows in days.items():
  if len(rows)!=24:continue
  rows.sort(key=lambda r:int(r[0]));agg=[D(rows[0][1]),max(D(r[2]) for r in rows),min(D(r[3]) for r in rows),D(rows[-1][4])]+[sum(D(r[i]) for r in rows) for i in [5,6,7]]
  assert agg==list(map(D,old[day][1:8]));matches+=1
 coins[c]={'expected':len(expected),'available':len(bars),'missing':len(expected-set(bars)),'matching_complete_days':matches}
r=read('results_all.json');sc=r['principal_scenarios'];assert {(x['period'],x['entry_hours'],x['exit_hours'],x['condition']) for x in sc}==set(itertools.product(p['periods_UTC_half_open'],p['entry_hours'],p['exit_hours'],p['conditions']))
assert len(sc)==108 and len(r['auxiliary_hold'])==12
assert all(x['net_pnl'] is None for x in sc+r['auxiliary_hold'])
a=read('attempts.json');assert len(a)==2 and a[0]['error'] and a[1]['exit_code']==28;assert p['frozen_utc']<a[0]['request_utc'];assert a[0]['url']!=a[1]['url']
out={'scope':'blocked package only; no strategy execution or C writes','hashes':counts,'frozen_protocol':True,'freeze_precedes_attempts':True,'coins':coins,'principal_combinations':108,'hold_combinations':12,'all_pnl_null':True,'new_requests_recorded':2,'new_successful_requests_recorded':0,'verdict':'PASS_LIMITED_INSUFFICIENT_EVIDENCE_CONCLUSION; IMPLEMENTATION_AND_RESEARCH_NOT_COMPLETED'}
(OUT/'trend_variants_v2.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
