"""Fixed artificial prices for implementation verification; not historical evidence."""
from decimal import Decimal as D
import math,random,copy
H=3600000;START=1577836800000

def make(values=None,n=16,seed=None):
 specs={c:{'instType':'SPOT','baseCcy':c,'quoteCcy':'USDT','lotSz':'.01' if c=='BTC' else '.001','tickSz':'.1' if c=='BTC' else '.01','minSz':'.001','maxMktSz':'1000000','maxMktAmt':'1000000000'} for c in ['BTC','ETH']}
 if values is not None:n=len(values)
 raw={};rng=random.Random(seed or 20260926)
 for c in ['BTC','ETH']:
  rr=[]
  for i in range(-80,n):
   price=D('100') if i<0 else D(str(values[i] if values is not None else round(110+25*math.sin(i/11+(0 if c=='BTC' else .8))+i*.02+rng.uniform(-3,3),3)))
   r=[str(START+i*H),str(price),str(price+1),str(price-1),str(price),'100','10000','10000','1'];rr.append(r)
  raw[c]=rr
 return dict(raw=raw,spec=specs,start=START,end=START+n*H,entry=24,exit=4,condition='baseline',mode='trend',synthetic=True)

def row(case,c,i):return case['raw'][c][80+i]
def fault(case,i,c,phase,**kwargs):case.setdefault('overrides',{})[str(case['start']+i*H)+':'+c+':'+phase]=kwargs
