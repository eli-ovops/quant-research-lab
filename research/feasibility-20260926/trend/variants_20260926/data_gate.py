from pathlib import Path
from decimal import Decimal as D
import json,datetime,csv,hashlib
P=Path(__file__).resolve().parent;ROOT=P.parent;H=3600000;DAY=24*H
def stamp(s):return int(datetime.datetime.fromisoformat(s).timestamp()*1000)
def load():
 proto=json.loads((P/'protocol.json').read_text());start=stamp(proto['data']['start']);end=stamp(proto['data']['end_exclusive']);data={};aud=[];diffs=[];problems=[]
 for c in ['BTC','ETH']:
  d={};dups=0;old={}
  files=sorted((P/'raw').glob(c+'_*.json'))+[Path(x['path']) for x in json.loads((P/'reuse_hourly_sources.json').read_text()) if x['coin']==c]
  for f in files:
   rows=json.loads(f.read_text())['data'];assert all(int(a[0])>int(b[0]) for a,b in zip(rows,rows[1:])),f
   for r in rows:
    t=int(r[0])
    if not start<=t<end:continue
    v=[D(x) for x in r[1:8]]
    assert t%H==0 and r[-1]=='1' and 0<v[2]<=min(v[0],v[3])<=max(v[0],v[3])<=v[1] and all(x>=0 for x in v[4:]),(c,t,r)
    if t in d:assert d[t]==r;dups+=1
    d[t]=r
  gaps=[t for t in range(start,end,H) if t not in d];zero=[t for t,r in d.items() if D(r[5])==0]
  if gaps:problems.append({'coin':c,'issue':'missing_hours','count':len(gaps),'first':gaps[:10]})
  if zero:problems.append({'coin':c,'issue':'zero_volume','count':len(zero),'first':zero[:10]})
  for f in list((ROOT/'raw').glob(c+'_daily_*.txt'))+list((ROOT/'resume_20260926'/'raw').glob(c+'_daily_*.txt')):
   for r in json.loads(f.read_text())['data']:
    t=int(r[0]);assert t not in old or old[t]==r;old[t]=r
  comparisons=0;ohlc_bad=0;volume_bad=0
  for t in range(stamp('2020-01-01T00:00:00+00:00'),end,DAY):
   if t not in old or not all(t+j*H in d for j in range(24)):continue
   rr=[d[t+j*H] for j in range(24)];agg=[D(rr[0][1]),max(D(r[2]) for r in rr),min(D(r[3]) for r in rr),D(rr[-1][4])]+[sum((D(r[k]) for r in rr),D(0)) for k in range(5,8)]
   dv=[a-D(b) for a,b in zip(agg,old[t][1:8])];comparisons+=1
   if any(dv):
    diffs.append({'coin':c,'utc_day':datetime.datetime.fromtimestamp(t/1000,datetime.timezone.utc).date().isoformat(),'ohlc_delta':list(map(str,dv[:4])),'volume_delta':list(map(str,dv[4:]))})
   ohlc_bad+=bool(any(dv[:4]));volume_bad+=bool(any(dv[4:]))
  if ohlc_bad:problems.append({'coin':c,'issue':'daily_OHLC_discrepancy','count':ohlc_bad})
  if comparisons!=(end-stamp('2020-01-01T00:00:00+00:00'))//DAY:problems.append({'coin':c,'issue':'incomplete_daily_comparison','count':comparisons})
  aud.append({'coin':c,'hours':len(d),'expected':(end-start)//H,'duplicate_equal_rows':dups,'gaps':len(gaps),'zero_volume':len(zero),'daily_comparisons':comparisons,'OHLC_discrepancies':ohlc_bad,'volume_rounding_discrepancies':volume_bad})
  data[c]={t:dict(zip(['o','h','l','c','vol'],map(D,r[1:6]))) for t,r in d.items()}
 return data,aud,diffs,problems
if __name__=='__main__':
 data,aud,diffs,problems=load()
 result={'pass':not problems,'coverage':aud,'problems':problems,'volume_note':'Hourly/daily reported volumes may differ by aggregation rounding; exact deltas preserved. Not execution-depth evidence.'}
 (P/'data_gate.json').write_text(json.dumps(result,indent=2)+'\n');(P/'daily_comparison_differences.json').write_text(json.dumps(diffs,indent=2)+'\n')
 with (P/'data_coverage.csv').open('w') as f:
  w=csv.DictWriter(f,fieldnames=list(aud[0]));w.writeheader();w.writerows(aud)
 print(json.dumps(result,indent=2))
