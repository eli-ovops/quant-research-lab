"""Read-only historical data gate. This continuation NEVER runs historical PnL."""
from pathlib import Path
from decimal import Decimal as D
import json,hashlib,datetime,itertools
P=Path(__file__).resolve().parent;OLD=P.parent;H=3600000

def main():
 proto=json.loads((OLD/'protocol.json').read_text());assert hashlib.sha256((OLD/'protocol.json').read_bytes()).hexdigest()=='d4a2fef3fc115291e0a9dd62c632c407c1e5bc99a5d59c81df60b83aefb43be4'
 ms=lambda s:int(datetime.datetime.fromisoformat(s).timestamp()*1000)
 start=ms(proto['data']['start']);end=ms(proto['data']['end_exclusive']);ref=json.loads((OLD/'reuse_hourly_sources.json').read_text());coverage={}
 extra=json.loads((P/'normalized_sources.json').read_text()) if (P/'normalized_sources.json').exists() else []
 for c in ['BTC','ETH']:
  data={};duplicates=0;errors=[]
  for item in ref+extra:
   if item['coin']!=c:continue
   f=Path(item['path']);assert hashlib.sha256(f.read_bytes()).hexdigest()==item['sha256']
   obj=json.loads(f.read_text());rr=obj['data']
   for r in rr:
    t=int(r[0])
    if not start<=t<end:continue
    if t in data:
     if data[t]!=r:errors.append('conflicting_duplicate:'+str(t))
     duplicates+=1
    data[t]=r
  expected=set(range(start,end,H));missing=expected-set(data)
  for t,r in data.items():
   v=list(map(D,r[1:8]))
   if len(r)!=9 or str(r[-1])!='1' or t%H or not all(x.is_finite() for x in v) or not(0<v[2]<=min(v[0],v[3])<=max(v[0],v[3])<=v[1]) or v[4]<=0 or min(v[5:])<0:errors.append('bad_bar:'+str(t))
  daily={int(r[0]):r for f in list((OLD.parent/'raw').glob(c+'_daily_*.txt'))+list((OLD.parent/'resume_20260926'/'raw').glob(c+'_daily_*.txt')) for r in json.loads(f.read_text())['data']}
  matched=0;volume_differences=[]
  for t in range(ms(proto['periods_UTC_half_open']['early'][0]),end,24*H):
   if not all(t+i*H in data for i in range(24)):continue
   rr=[data[t+i*H] for i in range(24)];agg=[D(rr[0][1]),max(D(r[2]) for r in rr),min(D(r[3]) for r in rr),D(rr[-1][4])]+[sum(D(r[k]) for r in rr) for k in [5,6,7]]
   if t not in daily:errors.append('missing_daily:'+str(t));continue
   old=list(map(D,daily[t][1:8]))
   if agg[:4]!=old[:4]:errors.append('daily_OHLC_mismatch:'+str(t))
   else:matched+=1
   if agg[4:]!=old[4:]:volume_differences.append({'t':t,'deltas':list(map(str,[a-b for a,b in zip(agg[4:],old[4:])]))})
  coverage[c]={'expected':len(expected),'present':len(data),'missing':len(missing),'duplicates_equal':duplicates,'errors':errors,'daily_matches':matched,'volume_differences':volume_differences,'pass':not missing and not errors and not volume_differences}
 result={'historical_gate':all(x['pass'] for x in coverage.values()),'coverage':coverage,'historical_PnL_runs':0,'reason':'This continuation only implements, tests synthetic fixtures and checks at most4 tiny public-tool windows; no historical outcome release authorized in this phase.'}
 (P/'historical_gate.json').write_text(json.dumps(result,indent=2)+'\n')
 rows=json.loads((OLD/'results_all.json').read_text());assert all(x['net_pnl'] is None for x in rows['principal_scenarios']);(P/'historical_results.json').write_text(json.dumps(rows,indent=2)+'\n')
 print(json.dumps(result,indent=2))
if __name__=='__main__':main()
