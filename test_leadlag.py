import unittest
from decimal import Decimal as D
from leadlag_engine import Study

def book(p,t,ref):
 return dict(bids=[(D(str(p)),D('10000'))],asks=[(D(str(p))+D('.0001'),D('10000'))],valid=True,ts=int(t*1000),received=t,ref=ref,connection_id='a')
def views(t,ref,leader=1,follower=1):return {'okx':{'X':book(leader,t,ref)},'gate':{'X':book(follower,t,ref)}}
def study():
 rule=dict(lot='.001',min_qty='.001',min_quote='1',max_qty='100000',max_quote='100000')
 return Study(dict(symbols=['X'],order_rules={'okx':{'X':rule},'gate':{'X':rule}}))
class Tests(unittest.TestCase):
 def test_causal_entry_and_same_venue_costs(self):
  s=study();s.step(views(10,1),10000,10);e=s.step(views(12,2,1.01),12000,12)
  self.assertEqual([x['event'] for x in e],['lead_signal']);self.assertEqual(e[0]['venue'],'gate')
  self.assertEqual(s.step(views(12.5,3,1.01),12500,12.5),[])
  e=s.step(views(13,4,1.01),13000,13);self.assertEqual(e[0]['event'],'entry_observation')
  e=s.step(views(14,5,1.2,1),14000,14);out=next(x for x in e if x['event']=='outcome')
  self.assertTrue(all(D(x['net_usdt'])<0 for x in out['scenarios']))
 def test_stale_not_profit(self):
  s=study();s.step(views(10,1),10000,10);s.step(views(12,2,1.01),12000,12)
  e=s.step(views(12,2,1.01),13000,13);self.assertEqual(e[0]['quality'],'NO_NEW_MESSAGE');self.assertEqual(e[0]['scenarios'],[])
 def test_no_signal_on_reconnect(self):
  s=study();s.step(views(10,1),10000,10);v=views(12,2,1.1);v['gate']['X']['connection_id']='b';self.assertEqual(s.step(v,12000,12),[])
 def test_late_execution_invalid(self):
  s=study();s.step(views(10,1),10000,10);s.step(views(12,2,1.01),12000,12);e=s.step(views(14,3,1.01),14000,14);self.assertEqual(e[0]['quality'],'SCHEDULE_LATE')
if __name__=='__main__':unittest.main()
