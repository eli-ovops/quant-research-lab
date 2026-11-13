import unittest,json
from decimal import Decimal as D
from opportunity_engine import triggers,outcomes,first_after
A='BTC-USDT-SWAP';S={A:{'ctVal':'.01','ctMult':'1','lotSz':'.01','minSz':'.01'}}
def row(n,t,c,d):return {'instId':A,'connectionId':'x','monotonic_ns':int(t*1e6),'local_ordinal':n,'receive_wall_ms':t,'channel':c,'raw':json.dumps({'data':[d]})}
def b(px):return {'asks':[[str(px+.005),'1000']],'bids':[[str(px-.005),'1000']]}
def bk(t,n=1):return {'time':t,'ordinal':n,'wall_ms':t,'conn':'x','asks':[(D(100),D(1000))],'bids':[(D(99),D(1000))]}
class T(unittest.TestCase):
 def test_reference_over250(self):
  rs=[row(1,0,'books5',b(100)),row(2,0,'trades',{'px':'100','sz':'100','side':'buy'}),row(3,1300,'books5',b(100.04)),row(4,1300,'trades',{'px':'100','sz':'100','side':'buy'})];e,_,c=triggers(rs,S);self.assertEqual(e,[]);self.assertGreater(c['stale_reference'],0)
 def test_entry_wait_251_and250(self):
  e={'asset':A,'event_id':1,'direction':1,'asof_ms':1000,'connectionId':'x'}
  for t,reason in [(1251,'expired_entry_quote'),(1250,'no_posthold_book')]:
   st={A:{'books':[bk(t)],'times':[t]}};rs=outcomes([e],st,S);self.assertTrue(all(r['reason']==reason for r in rs if r['delay_ms']==0))
 def test_exit_wait251(self):
  e={'asset':A,'event_id':1,'direction':1,'asof_ms':1000,'connectionId':'x'};bs=[bk(1001),bk(16252,2)];rs=outcomes([e],{A:{'books':bs,'times':[1001,16252]}},S);self.assertTrue(all(r['reason']=='expired_exit_quote' for r in rs if r['delay_ms']==0 and r['hold_seconds']==15))
 def test_different_conn_stops_search(self):
  bs=[{'time':1,'conn':'new'},{'time':2,'conn':'old'}];self.assertIsNone(first_after(bs,[1,2],0,'old'))
if __name__=='__main__':unittest.main()

