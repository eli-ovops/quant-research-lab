"""Independent complete raw-tool-envelope audit. No main gate/engine imports."""
from pathlib import Path
from decimal import Decimal as D
import json,hashlib,datetime,collections
P=Path(__file__).resolve().parent;OLD=P.parent;H=3600000;START=1577548800000;END=1782864000000
sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
requests=json.loads((P/'attempts.json').read_text());planned=json.loads((P/'request_plan.json').read_text())['pages']+json.loads((P/'gap_plan_v1.json').read_text())['pages'];plan={p['id']:p for p in planned};raws={'BTC':{},'ETH':{}};duplicates=collections.Counter();locations={'BTC':{},'ETH':{}};verified=0
assert len(requests)==len(planned)==388
assert len({json.dumps(a['args'],sort_keys=True) for a in requests})==len(requests),'duplicate request parameters'
for rec in requests:
 f=P/'raw'/(rec['id']+'.json');assert sha(f)==rec['raw_sha256'];page=plan[rec['id']];assert rec['args']==page['args'];env=json.loads(f.read_text());o=env.get('structuredContent') or json.loads(env['content'][0]['text']);verified+=1
 if not rec.get('success'):assert o.get('error');continue
 norm=P/'raw'/(rec['id']+'_normalized.json');assert sha(norm)==rec['normalized_sha256'];rr=o['data']['data'];assert rr==json.loads(norm.read_text())['data'];verified+=1
 assert o['ok'] and o['data']['endpoint']=='GET /api/v5/market/history-candles'
 assert sorted(int(r[0]) for r in rr)==list(range(page['start'],page['end'],H))
 c=rec['args']['instId'].split('-')[0];assert rec['args']['instId']==c+'-USDT' and rec['args']['bar']=='1H'
 for r in rr:
  t=int(r[0]);assert len(r)==9 and r[8]=='1';v=list(map(D,r[1:8]));assert all(x.is_finite() for x in v) and v[2]>0 and v[1]>=max(v[0],v[3]) and v[2]<=min(v[0],v[3]) and min(v[4:])>=0
  if t in raws[c]:assert raws[c][t]==r;duplicates[c]+=1
  raws[c][t]=r;locations[c].setdefault(t,[]).append(rec['id'])
report=[];anomalies=[];material=[];zero=[]
for c in ['BTC','ETH']:
 d=raws[c];assert set(d)==set(range(START,END,H))
 daily={int(r[0]):r for f in list((OLD.parent/'raw').glob(c+'_daily_*.txt'))+list((OLD.parent/'resume_20260926'/'raw').glob(c+'_daily_*.txt')) for r in json.loads(f.read_text())['data']}
 cprice=0;cvol=0;maxdelta=[D(0)]*7
 for day in range(1577836800000,END,24*H):
  rr=[d[day+h*H] for h in range(24)];cols=list(zip(*rr));agg=[D(cols[1][0]),max(map(D,cols[2])),min(map(D,cols[3])),D(cols[4][-1])]+[sum(map(D,cols[j])) for j in [5,6,7]]
  old=list(map(D,daily[day][1:8]));delta=[x-y for x,y in zip(agg,old)];cprice+=any(delta[:4]);cvol+=any(delta[4:]);maxdelta=[max(a,abs(b)) for a,b in zip(maxdelta,delta)]
  if any(delta):anomalies.append({'coin':c,'t':day,'delta':list(map(str,delta))})
  if any(delta[:4]) or abs(delta[4])>1 or any(abs(x)>1 for x in delta[5:]):material.append({'coin':c,'UTC_day':datetime.datetime.fromtimestamp(day/1000,datetime.timezone.utc).date().isoformat(),'hour_aggregation':list(map(str,agg)),'old_daily':daily[day][1:8],'delta':list(map(str,delta)),'hour_source_pages':sorted(set(p for t in range(day,day+24*H,H) for p in locations[c][t])),'cause':'UNKNOWN; not assigned to rounding or outage without additional evidence'})
 zeros=[]
 for t,r in sorted(d.items()):
  if D(r[5])==0:
   zeros.append(t);zero.append({'coin':c,'UTC':datetime.datetime.fromtimestamp(t/1000,datetime.timezone.utc).isoformat(),'raw_row':r,'source_pages':locations[c][t],'fields5to7_allzero':all(D(x)==0 for x in r[5:8]),'frozen_protocol_result':'BLOCK_PNL'})
 report.append({'coin':c,'unique_hours':len(d),'equal_boundary_duplicates':duplicates[c],'zero_hours':len(zeros),'daily_OHLC_mismatch_days':cprice,'daily_volume_mismatch_days':cvol,'maximum_absolute_deltas':list(map(str,maxdelta)),'complete_grid':True,'protocol_data_quality_pass':False})
main=json.loads((P/'data_gate.json').read_text())
for a,b in zip(report,main['coverage']):assert a['unique_hours']==b['rows'] and a['zero_hours']==b['zero_volume'] and a['daily_OHLC_mismatch_days']==b['daily_OHLC_differences'] and a['daily_volume_mismatch_days']==b['daily_volume_differences']
assert sorted(anomalies,key=lambda x:(x['coin'],x['t']))==sorted(json.loads((P/'daily_differences.json').read_text()),key=lambda x:(x['coin'],x['t']))
result={'audit':'PASS_INDEPENDENT_CONFIRMATION_OF_COMPLETE_GRID_AND_FAILED_QUALITY_GATE','verified_raw_and_normalized_hashes':verified,'total_explicit_calls_including_prior6':len(requests)+6,'failed_original_pages':[r['id'] for r in requests if not r.get('success')],'gap_pages_successful':sum(r.get('success',False) for r in requests if '_gap_' in r['id']),'coins':report,'zero_source_rows':zero,'material_daily_differences':material,'true_profitability':'NOT_COMPUTED_INSUFFICIENT_EVIDENCE'}
(P/'independent_data_audit.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k not in ['zero_source_rows','material_daily_differences']},indent=2))
