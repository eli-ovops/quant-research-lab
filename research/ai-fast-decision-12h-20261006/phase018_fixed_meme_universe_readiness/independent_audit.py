from pathlib import Path
from fractions import Fraction as F
from decimal import Decimal
import json,hashlib
B=Path(__file__).resolve().parent
def main():
 results=json.loads((B/'results.json').read_text());count=0
 for asset in results['assets']:
  assert asset['qualification']=='PUBLIC_SPEC_AND_ONE_BOOK_CAPACITY_PASS';spec=asset['spec'];env=json.loads((B/'raw'/(asset['asset']+'_orderbook.json')).read_text())['response']['structuredContent'];book=env['data']['data'][0];unit=F(Decimal(spec['ctVal']))*F(Decimal(spec['ctMult']));step=F(Decimal(spec['lotSz']))
  for x in asset['capacity']:
   left=F(Decimal(x['contracts']));assert left>=F(Decimal(spec['minSz'])) and (left/step).denominator==1;value=F(0)
   for level in book['asks' if x['side']=='BUY' else 'bids'][:5]:
    assert F(Decimal(level[0]))>0 and F(Decimal(level[1]))>0;take=min(left,F(Decimal(level[1])));value+=take*F(Decimal(level[0]))*unit;left-=take
    if left==0:break
   assert left==0 and value==F(Decimal(x['notional_USDT'])) and value*(1+F(x['fee_each_side_bps'],10000))<=500;count+=1
  candles=json.loads((B/'raw'/(asset['asset']+'_candles.json')).read_text())['response']['structuredContent']['data']['data'];closed=sorted((x for x in candles if x[8]=='1'),key=lambda x:int(x[0]))[-180:];assert len(closed)==180 and all(int(b[0])-int(a[0])==60000 for a,b in zip(closed,closed[1:]));assert asset['minute_proxy']['closed_count']==180
 receipt={'status':'PASS_FINITE_PUBLIC_UNITS_CAPACITY_CLOSED_GRID','assets':3,'capacity_side_cost_cases':count,'closed_candle_counts':[180,180,180],'model_or_strategy_results':None,'sameOwner_notthirdparty':True,'limitations':'singlebook capacity, candle range not15s bidask return; realfees/funding/queue execution UNKNOWN'};(B/'audit.json').write_text(json.dumps(receipt,indent=2));print(receipt)
if __name__=='__main__':main()
