from pathlib import Path
from decimal import Decimal as D,ROUND_FLOOR,ROUND_CEILING,getcontext
import json
getcontext().prec=40
O=Path(__file__).resolve().parent;B=O.parents[1]/'funding'
def raw(n):return json.loads((B/'raw'/(n+'.txt')).read_text())['data'][0]
def floor(x,s):return (x/s).to_integral_value(rounding=ROUND_FLOOR)*s
def ceil(x,s):return (x/s).to_integral_value(rounding=ROUND_CEILING)*s
def sweep(levels,q,unit=D(1)):
 cash=D(0);remaining=q
 for p,size,*rest in levels:
  take=min(remaining,D(size)*unit);cash+=take*D(p);remaining-=take
  if remaining==0:break
 assert remaining==0
 return cash
checks=[]
for r in json.loads((B/'f1/results_all.json').read_text())['current_snapshots']:
 c=r['coin'];s=raw(c+'_spot_spec');f=raw(c+'_swap_spec');sb=raw(c+'_spot_book');fb=raw(c+'_swap_book');lot=D(s['lotSz']);ct=D(f['ctVal'])*D(f['ctMult']);clot=D(f['lotSz']);fee=D('.001');ask=D(sb['asks'][0][0])
 n=floor(800*(1-fee)/ask/ct,clot)
 while True:
  q=n*ct;gross=ceil(q/(1-fee),lot)
  if gross*ask<=800:break
  n-=clot
 net=gross*(1-fee);sold=floor(net,lot);dust=net-sold
 cost=sweep(sb['asks'],gross)-sweep(sb['bids'],sold)*(1-fee)-sweep(fb['bids'],q,ct)+sweep(fb['asks'],q,ct)+(sweep(fb['bids'],q,ct)+sweep(fb['asks'],q,ct))*D('.0005')
 assert cost==D(r['instant_roundtrip_cost_snapshot']) and dust==D(r['remaining_spot_base']) and sold==D(r['sold_spot_base']) and not r['all_inventory_flat']
 checks.append({'coin':c,'independent_roundtrip_cost':str(cost),'dust_retained':str(dust),'sold_base':str(sold),'result':'PASS','qualification':'original saved snapshot only; not fresh quote or actual fill'})
(O/'funding_f1_snapshots.json').write_text(json.dumps(checks,indent=2)+'\n');print(json.dumps(checks))
