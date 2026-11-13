"""Second raw event implementation. No engine, gate, metric or order-function imports."""
from decimal import Decimal, ROUND_DOWN, ROUND_UP, getcontext
getcontext().prec=36
Q=Decimal;UNIT=3600000

def replay(case):
 rows={};first=case['start'];last=case['end'];window=case.get('entry',24);outwin=case.get('exit',4);spec=case['spec'];mode=case.get('mode','trend');kind=case.get('condition','baseline')
 fee=Q('.002') if kind=='fee2' else Q('.001');slip=Q('.002') if kind=='slip20' else Q('.0005');lag=2 if kind=='delay1' else 1
 if first%UNIT or last%UNIT or first>=last:raise ValueError('bounds')
 for c in ('BTC','ETH'):
  if (spec[c]['instType'],spec[c]['baseCcy'],spec[c]['quoteCcy'])!=('SPOT',c,'USDT'):raise ValueError('identity')
  book={}
  for r in case['raw'][c]:
   if len(r)!=9 or r[-1]!='1':raise ValueError('fields/confirmation')
   t=int(r[0]);v=[Q(x) for x in r[1:8]]
   if t%UNIT or not all(x.is_finite() for x in v):raise ValueError('time/nonfinite')
   if min(v[:4])<=0 or v[1]<max(v[0],v[3]) or v[2]>min(v[0],v[3]) or v[4]<=0 or min(v[5:])<0:raise ValueError('OHLCV')
   if t in book and book[t]!=v:raise ValueError('duplicate')
   book[t]=v
  for t in range(first-80*UNIT,last,UNIT):
   if t not in book:raise ValueError('missing')
  rows[c]=book
 bal=Q(2000);pos={};crumbs={'BTC':Q(0),'ETH':Q(0)};queue=[];events=[];snap=[];signal=[];bad=[];closed=[]
 def terms(c,t,phase,side,amount,ref):
  rule=spec[c].copy();fault=case.get('overrides',{}).get(str(t)+':'+c+':'+phase,{});rule.update(fault.get('spec',{}))
  try:
   p=Q(fault.get('quote',ref));tick=Q(rule['tickSz']);lot=Q(rule['lotSz']);minimum=Q(rule['minSz']);maximum=Q(rule['maxMktSz'])
   if not all(x.is_finite() and x>0 for x in [p,tick,lot,minimum,maximum]):return None
   price=(p*(1+slip if side=='buy' else 1-slip)/tick).to_integral_value(rounding=ROUND_UP if side=='buy' else ROUND_DOWN)*tick
   if price<=0:return None
   qty=((amount/price if side=='buy' else amount)/lot).to_integral_value(rounding=ROUND_DOWN)*lot;notional=qty*price
   if qty<minimum or qty>maximum:return None
   if rule.get('maxMktAmt') and notional>Q(rule['maxMktAmt']):return None
   if rule.get('minMktAmt') and notional<Q(rule['minMktAmt']):return None
   available=Q(fault.get('available',bal-400 if side=='buy' else pos[c]['qty']))
   if (notional if side=='buy' else qty)>available:return None
   cost=((qty if side=='buy' else notional)*fee/Q('1e-8')).to_integral_value(rounding=ROUND_UP)*Q('1e-8')
   if cost>=(qty if side=='buy' else notional):return None
   return qty,price,cost
  except (ValueError,KeyError,TypeError,ArithmeticError):return None
 def close(c,t,phase,sig):
  nonlocal bal
  ref=rows[c][t][3 if phase=='terminal' else 0];calc=terms(c,t,phase,'sell',pos[c]['qty'],ref)
  if calc is None:bad.append((t,c,'sell',phase));return
  amount,px,f=calc;h=pos.pop(c);net=amount*px-f;bal+=net;crumbs[c]+=h['qty']-amount;et=t+UNIT if phase=='terminal' else t
  closed.append((c,h['time'],et,net-h['spent']))
  events.append((et,c,'sell',amount,px,Q(0),f,bal))
 for t in range(first,last,UNIT):
  due=[x for x in queue if x[0]==t];queue=[x for x in queue if x[0]!=t]
  if mode=='hold' and t==first+(lag-1)*UNIT:due=[(t,c,'buy',None) for c in ('BTC','ETH')]
  for _,c,side,sig in sorted(due):
   if side=='sell' and c in pos:close(c,t,'open',sig)
  buying=[x for x in due if x[2]=='buy' and x[1] not in pos];allocation=min(Q(800),max(Q(0),bal-400)/len(buying)) if buying else Q(0)
  for _,c,side,sig in sorted(buying):
   calc=terms(c,t,'open','buy',allocation,rows[c][t][0])
   if calc is None:bad.append((t,c,'buy','open'));continue
   q,p,f=calc;spent=q*p;bal-=spent;assert bal>=400
   pos[c]={'qty':q-f,'spent':spent,'time':t};events.append((t,c,'buy',q,p,f,Q(0),bal))
  if t==last-UNIT:
   for c in ('BTC','ETH'):
    if c in pos:close(c,t,'terminal',None)
  mark=bal;value=bal;liquid=bal;can=True
  for c,h in pos.items():
   v=h['qty']*rows[c][t][3];mark+=v;calc=terms(c,t,'mark','sell',h['qty'],rows[c][t][3])
   if calc is None:can=False;value+=v
   else:q,p,f=calc;liquid+=q*p-f;value+=q*p-f
  if t==last-UNIT and pos:can=False;value=mark
  snap.append(dict(t=t,cash=bal,raw_equity=mark,valuation_equity=value,liquidation_equity_proxy=liquid if can else None,BTC_qty=pos.get('BTC',{}).get('qty',Q(0)),ETH_qty=pos.get('ETH',{}).get('qty',Q(0)),BTC_dust=crumbs['BTC'],ETH_dust=crumbs['ETH']))
  if mode=='trend' and t!=last-UNIT:
   for c in ('BTC','ETH'):
    if any(x[1]==c for x in queue):continue
    side=None;prev=[rows[c][t-i*UNIT] for i in range(1,(outwin if c in pos else window)+1)];closep=rows[c][t][3]
    if c in pos and all(closep<r[2] for r in prev):side='sell'
    if c not in pos and all(closep>r[1] for r in prev):side='buy'
    if side:queue.append((t+lag*UNIT,c,side,t+UNIT));signal.append((t+UNIT,t+lag*UNIT,c,side))
 values=[Q(2000)]+[r['valuation_equity'] for r in snap];draw=Q(0);hi=Q(2000);ix=0;longest=0
 for i,v in enumerate(values):
  if v>=hi:hi=v;ix=i
  else:draw=max(draw,(hi-v)/hi);longest=max(longest,i-ix)
 # Independent inventory and cash totals from executed fills, including dust.
 assert bal==2000+sum((-q*p if side=='buy' else q*p-f for t,c,side,q,p,bf,f,ba in events),Q(0))
 for c in ('BTC','ETH'):
  inventory=sum((q-bf if side=='buy' else -q for t,coin,side,q,p,bf,f,ba in events if coin==c),Q(0))
  assert abs(inventory-pos.get(c,{}).get('qty',Q(0))-crumbs[c])<Q('1e-24')
 return {'fills':events,'curve':snap,'signals':signal,'rejections':bad,'pending':queue,'closed':closed,'final_equity':values[-1],'max_drawdown':draw,'longest_underwater_hours':longest,'unrecovered_hours_at_end':len(values)-1-ix if values[-1]<hi else 0}
