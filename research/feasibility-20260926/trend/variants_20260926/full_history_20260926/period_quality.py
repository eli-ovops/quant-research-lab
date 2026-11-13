from pathlib import Path
from decimal import Decimal as D
import json,datetime,math,hashlib
P=Path(__file__).resolve().parent;OLD=P.parent;H=3600000;DAY=24*H
ms=lambda s:int(datetime.datetime.fromisoformat(s).timestamp()*1000)
proto=json.loads((OLD/'protocol.json').read_text());raw={c:{} for c in ['BTC','ETH']}
for a in json.loads((P/'attempts.json').read_text()):
 if a.get('success'):
  c=a['args']['instId'].split('-')[0]
  for r in json.loads((P/'raw'/(a['id']+'_normalized.json')).read_text())['data']:raw[c][int(r[0])]=r
out=[];details=[]
for period,(s,e) in proto['periods_UTC_half_open'].items():
 start,end=ms(s),ms(e);lo=start-80*H
 for c in ['BTC','ETH']:
  d=raw[c];wanted=set(range(lo,end,H));gaps=wanted-set(d);zero=[t for t in wanted if D(d[t][5])==0];bad=[]
  for t in wanted:
   r=d[t];v=list(map(D,r[1:8]))
   if t%H or r[-1]!='1' or len(r)!=9 or not all(x.is_finite() for x in v) or not(0<v[2]<=min(v[0],v[3])<=max(v[0],v[3])<=v[1]) or min(v[4:])<0:bad.append(t)
  old={int(r[0]):r for f in list((OLD.parent/'raw').glob(c+'_daily_*.txt'))+list((OLD.parent/'resume_20260926'/'raw').glob(c+'_daily_*.txt')) for r in json.loads(f.read_text())['data']}
  sums={'OHLC_days':0,'base_days':0,'quote_days':0,'quote2_days':0,'compared_full_days_including_warmup':0};maxdelta=[D(0)]*3;maxrelative=[D(0)]*3;outside=[0]*3
  for t in range(((lo+DAY-1)//DAY)*DAY,end,DAY):
   rr=[d[t+j*H] for j in range(24)];vals=[D(rr[0][1]),max(D(r[2]) for r in rr),min(D(r[3]) for r in rr),D(rr[-1][4])]+[sum(D(r[k]) for r in rr) for k in [5,6,7]];prev=list(map(D,old[t][1:8]));delta=[a-b for a,b in zip(vals,prev)];sums['OHLC_days']+=any(delta[:4]);sums['compared_full_days_including_warmup']+=1
   for j,label in enumerate(['base_days','quote_days','quote2_days']):
    diff=abs(delta[j+4]);sums[label]+=diff!=0;maxdelta[j]=max(maxdelta[j],diff);relative=diff/max(abs(vals[j+4]),abs(prev[j+4]));maxrelative[j]=max(maxrelative[j],relative)
    inputs=[D(r[j+5]) for r in rr];unit=2.**-53;gamma=23*unit/(1-23*unit)
    bound=sum(D(str(math.ulp(float(v))))/2 for v in inputs)+D(str(math.ulp(float(prev[j+4]))))/2+D(str(gamma))*sum(abs(v) for v in inputs)
    compatible=diff<=bound;outside[j]+=not compatible
    if diff:details.append({'period':period,'coin':c,'day':t,'field':['base','quote','quote2'][j],'delta':str(delta[j+4]),'relative':str(relative),'hypothetical_binary64_sum_error_bound':str(bound),'compatible_with_bound':compatible,'cause_proven':False})
  hard=not(gaps or zero or bad or sums['OHLC_days']);out.append({'period':period,'coin':c,'period_start':s,'period_end_exclusive':e,'warmup_start_UTC':datetime.datetime.fromtimestamp(lo/1000,datetime.timezone.utc).isoformat(),'required_hours_with_warmup':len(wanted),'missing':len(gaps),'invalid_or_unconfirmed':len(bad),'zero_volume_hours':len(zero),'zero_times':sorted(zero),**sums,'max_abs_volume_delta':list(map(str,maxdelta)),'max_relative_volume_delta':list(map(str,maxrelative)),'outside_hypothetical_binary64_bound_by_field':outside,'hard_price_grid_confirmation_zero_gate_pass':hard,'original_protocol_full_gate':'FAIL' if not hard else ('VOLUME_EXPLANATION_REVIEW_REQUIRED' if any(sums[k] for k in ['base_days','quote_days','quote2_days']) else 'PASS'),'current_strict_implementation_gate':'FAIL' if any(sums[k] for k in ['OHLC_days','base_days','quote_days','quote2_days']) or not hard else 'PASS','PnL_released':False})
(P/'period_quality.json').write_text(json.dumps({'periods':out,'volumetric_explanation':'Hypothetical binary64 inputs and sequential positive summation bound:sum halfULPs(input)+halfULP(daily)+gamma23*sumabs. Compatible values are evidence of numerical scale only, not proof of the exchange implementation or a silently accepted tolerance. Original protocol has no numeric tolerance; PMO/A review needed.','independence':'Original periods each reset cash2000/flat/pending;exact80h warmup supplies prices only, no prior-period holdings or signals. No shorter windows or data deletion. Early remains UNKNOWN even if later separately admissible.'},indent=2)+'\n');(P/'volume_precision_diagnostics.json').write_text(json.dumps(details,indent=2)+'\n');print(json.dumps(out,indent=2))
