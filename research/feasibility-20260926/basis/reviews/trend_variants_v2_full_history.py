from pathlib import Path
from decimal import Decimal as D
from collections import Counter
import json,hashlib,datetime
P=Path(__file__).resolve().parents[2]/'trend'/'variants_20260926'/'full_history_20260926';O=P.parent;OUT=Path(__file__).resolve().parent
rd=lambda p:json.loads(p.read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();H=3600000
counts={};mismatches=[]
for label,base,rows in [('manifest',P,rd(P/'manifest.json')['files']),('sources',P,rd(P/'sources.json')['reused_inputs'])]:
 for r in rows:
  f=Path(r['path']);f=f if f.is_absolute() else base/f
  if sha(f)!=r['sha256']:mismatches.append({'path':str(f),'expected':r['sha256'],'actual':sha(f)})
 counts[label]=len(rows)
seal=rd(P/'seal.json');assert sha(P/'manifest.json')==seal['manifest_sha256'];assert sha(O/'protocol.json')==seal['original_protocol_sha256']
for n,h in rd(P/'analysis_freeze.json')['files'].items():assert sha(P/n)==h
plans={r['id']:r for name in ['request_plan.json','gap_plan_v1.json'] for r in rd(P/name)['pages']};attempts=rd(P/'attempts.json');assert len(attempts)==388;assert len({json.dumps(r['args'],sort_keys=True) for r in attempts})==388
bars={c:{} for c in ['BTC','ETH']};dup=Counter();failed=[];hashed=0
for a in attempts:
 assert a['args']==plans[a['id']]['args'];raw=P/'raw'/(a['id']+'.json');assert sha(raw)==a['raw_sha256'];hashed+=1;env=rd(raw);obj=env.get('structuredContent') or json.loads(env['content'][0]['text'])
 if not a.get('success'):assert obj.get('error');failed.append(a['id']);continue
 nr=P/'raw'/(a['id']+'_normalized.json');assert sha(nr)==a['normalized_sha256'];hashed+=1;rows=obj['data']['data'];assert rows==rd(nr)['data'];plan=plans[a['id']];assert sorted(int(r[0]) for r in rows)==list(range(plan['start'],plan['end'],H))
 c=a['args']['instId'].split('-')[0];assert a['args']['bar']=='1H'
 for r in rows:
  t=int(r[0]);v=list(map(D,r[1:8]));assert r[-1]=='1' and len(r)==9 and all(x.is_finite() for x in v) and 0<v[2]<=min(v[0],v[3])<=max(v[0],v[3])<=v[1] and min(v[4:])>=0
  if t in bars[c]:assert bars[c][t]==r;dup[c]+=1
  bars[c][t]=r
ms=lambda s:int(datetime.datetime.fromisoformat(s).timestamp()*1000);proto=rd(O/'protocol.json');summary=[]
for c,d in bars.items():
 assert set(d)==set(range(ms(proto['data']['start']),ms(proto['data']['end_exclusive']),H))
 daily={int(r[0]):r for base in [O.parent,O.parent/'resume_20260926'] for f in (base/'raw').glob(c+'_daily_*.txt') for r in rd(f)['data']}
 for period,(a,b) in proto['periods_UTC_half_open'].items():
  lo=ms(a)-80*H;hi=ms(b);times=list(range(lo,hi,H));zero=[t for t in times if D(d[t][5])==0];pricebad=[];volbad=[];days=0
  for day in range(((lo+24*H-1)//(24*H))*24*H,hi,24*H):
   rows=[d[day+j*H] for j in range(24)];agg=[D(rows[0][1]),max(D(r[2]) for r in rows),min(D(r[3]) for r in rows),D(rows[-1][4])]+[sum(D(r[k]) for r in rows) for k in [5,6,7]];delta=[x-D(y) for x,y in zip(agg,daily[day][1:8])];days+=1
   if any(delta[:4]):pricebad.append({'day':day,'delta':list(map(str,delta))})
   if any(delta[4:]):volbad.append(day)
  summary.append({'coin':c,'period':period,'required_hours':len(times),'zeros':len(zero),'complete_days':days,'OHLC_discrepancies':pricebad,'volume_mismatch_days':len(volbad),'pass':not zero and not pricebad and not volbad})
assert all(x['pass']==(x['period']!='early') for x in summary)
r=rd(P/'results_not_computed.json');print('result keys',list(r))
# Check all outcome records recursively without assuming presentation container names.
net=[]
def walk(x):
 if isinstance(x,dict):
  if 'net_pnl' in x:net.append(x['net_pnl'])
  for v in x.values():walk(v)
 elif isinstance(x,list):
  for v in x:walk(v)
walk(r);assert len(net)>=108 and all(v is None for v in net)
assert not (P/'first_real_PnL_run.json').exists()
out={'source_mismatches':mismatches,'hash_counts':counts,'raw_normalized_hashes':hashed,'failed_original':failed,'attempts':len(attempts),'unique_hours':{c:len(d) for c,d in bars.items()},'duplicates':dict(dup),'period_quality':summary,'null_pnl_records':len(net),'PnL_marker_absent':True,'no_C_code_run_or_written':True}
(OUT/'trend_variants_v2_full_history.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
