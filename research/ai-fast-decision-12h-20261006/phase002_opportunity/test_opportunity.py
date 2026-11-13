import unittest,json
from decimal import Decimal as D
from opportunity_engine import triggers,floorlot,depthfill,first_after,outcomes
A='BTC-USDT-SWAP';S={A:{'ctVal':'.01','ctMult':'1','lotSz':'.01','minSz':'.01'}}
def row(n,t,c,d):
 return {'instId':A,'connectionId':'x','monotonic_ns':int(t*1000000),'local_ordinal':n,'receive_wall_ms':t,'channel':c,'raw':json.dumps({'data':[d]})}
def book(px):return {'asks':[[str(px+.005),'1000','0','1']],'bids':[[str(px-.005),'1000','0','1']]}
def trade():return {'px':'100','sz':'100','side':'buy'}
class T(unittest.TestCase):
 def test_causal_warmup(self):
  rs=[row(1,0,'books5',book(100)),row(2,0,'trades',trade()),row(3,1001,'books5',book(100.04)),row(4,1001,'trades',trade())]
  e,_,_=triggers(rs,S);self.assertEqual(len(e),1);self.assertEqual(e[0]['asof_ordinal'],4)
  e2,_,_=triggers(rs[2:],S);self.assertEqual(len(e2),0)
 def test_cooldown(self):
  rs=[row(1,0,'books5',book(100)),row(2,0,'trades',trade()),row(3,1001,'books5',book(100.04)),row(4,1001,'trades',trade()),row(5,2002,'books5',book(100.08)),row(6,2002,'trades',trade())];e,_,c=triggers(rs,S);self.assertEqual(len(e),1);self.assertGreater(c['cooldown'],0)
 def test_after_quotes_not_old(self):
  bs=[{'time':t,'conn':'x'} for t in [0,250,251,15001]];self.assertEqual(first_after(bs,[0,250,251,15001],250,'x')['time'],251);self.assertIsNone(first_after(bs,[0,250,251,15001],15001,'x'))
 def test_contract_VWAP_and_same_qty(self):
  self.assertEqual(floorlot(D('1.239'),D('.01')),D('1.23'));n,v=depthfill([(D(100),D(1)),(D(110),D(1))],D(2),D('.01'));self.assertEqual(n,D('2.10'));self.assertEqual(v,D(105));self.assertIsNone(depthfill([(D(100),D(1))],D(2),D('.01')))
 def test_censored_without_future(self):
  e={'asset':A,'event_id':1,'direction':1,'asof_ms':1000,'connectionId':'x'};s={A:{'books':[],'times':[]}};r=outcomes([e],s,S);self.assertTrue(all(x['status']=='censored' and x['price_fee_delta_USDT'] is None for x in r))
 def test_fees_twolegs_same_qty(self):
  levels=[(D(100),D(1000))];entry,_=depthfill(levels,D(2),D('.01'));exit,_=depthfill([(D(110),D(1000))],D(2),D('.01'));net=exit-entry-(entry+exit)*D('.0005');self.assertEqual(net,D('.19790'))
if __name__=='__main__':unittest.main()

