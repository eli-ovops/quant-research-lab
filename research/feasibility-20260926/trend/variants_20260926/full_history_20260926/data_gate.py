from pathlib import Path
from decimal import Decimal as D
import json,datetime,hashlib,csv
P=Path(__file__).resolve().parent;OLD=P.parent;H=3600000;DAY=24*H
ms=lambda s:int(datetime.datetime.fromisoformat(s).timestamp()*1000)
sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
def load():
 proto=json.loads((OLD/'protocol.json').read_text());assert sha(OLD/'protocol.json')=='d4a2fef3fc115291e0a9dd62c632c407c1e5bc99a5d59c81df60b83aefb43be4'
 start,end=ms(proto['data']['start']),ms(proto['data']['end_exclusive']);attempts=json.loads((P/'attempts.json').read_text());data={};reports=[];differences=[];sources=[]
 for c in ['BTC','ETH']:
  d={};duplicates=0;issues=[]
  for a in attempts:
   if not a.get('success') or a['args']['instId']!=c+'-USDT':continue
   raw=P/'raw'/(a['id']+'.json');norm=P/'raw'/(a['id']+'_normalized.json');assert sha(raw)==a['raw_sha256'] and sha(norm)==a['normalized_sha256']
   env=json.loads(raw.read_text());o=env.get('structuredContent') or json.loads(env['content'][0]['text']);rr=json.loads(norm.read_text())['data'];assert rr==o['data']['data'];sources.append({'path':str(raw),'sha256':sha(raw),'normalized_path':str(norm),'normalized_sha256':sha(norm),'id':a['id']})
   for r in rr:
    t=int(r[0]);assert start<=t<end
    if t in d:
     assert d[t]==r,('conflicting_overlap',c,t);duplicates+=1
    d[t]=r
  expected=set(range(start,end,H));gaps=sorted(expected-set(d));zero=[]
  for t,r in d.items():
   assert len(r)==9 and r[-1]=='1' and t%H==0;v=list(map(D,r[1:8]));assert all(x.is_finite() for x in v) and 0<v[2]<=min(v[0],v[3])<=max(v[0],v[3])<=v[1] and min(v[4:])>=0
   if D(r[5])==0:zero.append(t)
  cached={}
  # Entire previous same-product cached page rows within frozen dates, not later dates.
  for ref in json.loads((OLD/'reuse_hourly_sources.json').read_text()):
   if ref['coin']==c:
    for r in json.loads(Path(ref['path']).read_text())['data']:
     if start<=int(r[0])<end:cached[int(r[0])]=r
  for f in (OLD/'resume_implementation_20260926'/'raw').glob('probe*_normalized.json'):
   num=int(f.stem.split('_')[0][5:]);coin='BTC' if num<3 else 'ETH'
   if coin==c:
    for r in json.loads(f.read_text())['data']:cached[int(r[0])]=r
  overlap=0
  for t,r in cached.items():
   if t in d:assert d[t]==r,('prior_cache_difference',c,t);overlap+=1
  daily={int(r[0]):r for f in list((OLD.parent/'raw').glob(c+'_daily_*.txt'))+list((OLD.parent/'resume_20260926'/'raw').glob(c+'_daily_*.txt')) for r in json.loads(f.read_text())['data']}
  compared=0;ohlc_bad=0;vol_bad=0
  for t in range(ms(proto['periods_UTC_half_open']['early'][0]),end,DAY):
   if not all(t+i*H in d for i in range(24)):continue
   if t not in daily:issues.append('missing_daily:'+str(t));continue
   rr=[d[t+i*H] for i in range(24)];a=[D(rr[0][1]),max(D(r[2]) for r in rr),min(D(r[3]) for r in rr),D(rr[-1][4])]+[sum(D(r[j]) for r in rr) for j in [5,6,7]];old=list(map(D,daily[t][1:8]));delta=[x-y for x,y in zip(a,old)];compared+=1
   if any(delta):differences.append({'coin':c,'t':t,'delta':list(map(str,delta))})
   ohlc_bad+=bool(any(delta[:4]));vol_bad+=bool(any(delta[4:]))
  report={'coin':c,'rows':len(d),'expected':len(expected),'gaps':len(gaps),'gap_first':gaps[:10],'duplicate_equal':duplicates,'zero_volume':len(zero),'zero_volume_times':zero,'prior_cache_equal':overlap,'prior_cache_expected':len(cached),'daily_compared':compared,'daily_expected':2373,'daily_OHLC_differences':ohlc_bad,'daily_volume_differences':vol_bad,'issues':issues}
  report['pass']=not(gaps or zero or issues or ohlc_bad or vol_bad) and compared==2373 and overlap==len(cached)
  reports.append(report);data[c]=[d[t] for t in sorted(d)]
 return data,{'pass':all(r['pass'] for r in reports),'coverage':reports,'volume_policy':'Any difference requires explicit documented assessment before release; none silently overwritten'},differences,sources
if __name__=='__main__':
 data,a,d,s=load()
 for name,x in [('data_gate.json',a),('daily_differences.json',d),('market_sources.json',s)]: (P/name).write_text(json.dumps(x,indent=2)+'\n')
 print(json.dumps(a,indent=2))
