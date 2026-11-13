from pathlib import Path
from decimal import Decimal
import json,sys,hashlib,statistics
B=Path(__file__).resolve().parent
sys.path.insert(0,str(B.parent/'phase010_job004_evaluation'))
import frozen_execution_v12 as core
def envelope(asset,kind):
 r=json.loads((B/'raw'/(asset+'_'+kind+'.json')).read_text());response=r.get('response',{});e=response.get('structuredContent')
 if e is None:e=json.loads(response['content'][0]['text'])
 return r,e
def main():
 results=[];registered=[]
 for asset in ['DOGE-USDT-SWAP','XRP-USDT-SWAP','SUI-USDT-SWAP']:
  row={'asset':asset,'qualification':'FAIL_OR_UNKNOWN','reasons':[],'not_alpha_or_15s_PnL':True}
  try:
   _,si=envelope(asset,'instrument');_,bi=envelope(asset,'orderbook');_,ci=envelope(asset,'candles');assert all(e.get('ok') for e in [si,bi,ci]);spec=next(x for x in si['data']['data'] if x['instId']==asset);row['spec']=spec
   assert spec['state']=='live' and spec['ctType']=='linear' and spec['settleCcy']=='USDT' and spec['instType']=='SWAP'
   values={k:Decimal(spec[k]) for k in ['ctVal','ctMult','lotSz','minSz','tickSz']};assert all(v.is_finite() and v>0 for v in values.values());assert spec['ctValCcy']==asset.split('-')[0]
   book=bi['data']['data'][0];valid=core.valid_book(book);assert valid;asks,bids=valid;unit=values['ctVal']*values['ctMult'];capacity=[]
   for fee_bps in [5,10]:
    fee=Decimal(fee_bps)/10000
    for side,levels in [('BUY',asks[:5]),('SELL',bids[:5])]:
     qty=core.size_capacity(levels,unit,values['lotSz'],values['minSz'],fee);assert qty is not None;notional,vwap=core.depthfill(levels,qty,unit);assert notional*(1+fee)<=500;capacity.append({'side':side,'fee_each_side_bps':fee_bps,'contracts':str(qty),'base_units':str(qty*unit),'notional_USDT':str(notional),'entry_fee_USDT':str(notional*fee),'VWAP':str(vwap),'first5_only':True})
   row.update(qualification='PUBLIC_SPEC_AND_ONE_BOOK_CAPACITY_PASS',capacity=capacity,book_ts=book['ts'],spread_bps=float((asks[0][0]-bids[0][0])/((asks[0][0]+bids[0][0])/2)*10000));registered.append({k:spec[k] for k in ['instId','instType','ctType','ctVal','ctValCcy','ctMult','settleCcy','lotSz','minSz','tickSz','state']})
   candles=ci['data']['data'];closed=sorted([x for x in candles if len(x)>=9 and x[8]=='1'],key=lambda x:int(x[0]))[-180:];ranges=[];bad=[]
   for c in closed:
    o,h,l,cl=map(Decimal,c[1:5]);ts=int(c[0]);assert ts%60000==0 and all(v.is_finite() and v>0 for v in [o,h,l,cl]);assert l<=min(o,cl)<=max(o,cl)<=h;ranges.append(float((h-l)/cl*10000))
   gaps=[int(b[0])-int(a[0]) for a,b in zip(closed,closed[1:]) if int(b[0])-int(a[0])!=60000];row['minute_proxy']={'closed_count':len(closed),'first_ts':closed[0][0] if closed else None,'last_ts':closed[-1][0] if closed else None,'grid_gaps_ms':gaps,'range_bps_median':statistics.median(ranges) if ranges else None,'range_bps_p90':sorted(ranges)[int((len(ranges)-1)*.9)] if ranges else None,'range_bps_max':max(ranges) if ranges else None,'range_ge10bps_count':sum(x>=10 for x in ranges),'not_bidask_path_or_alpha':True,'confirm0_excluded':sum(c[8]=='0' for c in candles),'endpoint':ci['data']['endpoint'],'provider_requestTime':ci['data']['requestTime']}
   row['source_requestTime']={k:e['data']['requestTime'] for k,e in [('spec',si),('book',bi),('candles',ci)]}
  except Exception as e:row['reasons'].append(type(e).__name__+':'+str(e))
  results.append(row)
 (B/'results.json').write_text(json.dumps({'status':'PUBLIC_UNIVERSE_READINESS_ONLY','assets':results,'calls':9,'model_calls':0,'fees_paid':0,'capture_result':None,'global_goal':'ACTIVE'},indent=2));(B/'qualified_instruments.json').write_text(json.dumps(registered,indent=2));print([(x['asset'],x['qualification'],x.get('reasons')) for x in results])
if __name__=='__main__':main()
