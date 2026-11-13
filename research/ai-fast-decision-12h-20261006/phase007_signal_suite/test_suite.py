from pathlib import Path
import unittest,json
from decimal import Decimal as D
from signal_suite import *
B=Path(__file__).resolve().parent;A='BTC-USDT-SWAP';E='ETH-USDT-SWAP';S='SOL-USDT-SWAP'
SPECS={a:{'ctVal':'.01','ctMult':'1','lotSz':'.01','minSz':'.01'} for a in [A,E,S]}
def book(mid):return {'asks':[[str(mid+.01+i*.01),'100'] for i in range(3)],'bids':[[str(mid-.01-i*.01),'100'] for i in range(3)]}
def row(a,n,t,ch,d):
 if ch=='trades':d={**d,'tradeId':str(n)}
 return {'instId':a,'monotonic_ns':int(t*1e6),'local_ordinal':n,'receive_wall_ms':t,'receive_wall_ns':int(t*1e6),'connection_local_id':'SYNTHETIC_NOT_EXCHANGE_RUN','connectionId':'x','channel':ch,'raw':json.dumps({'data':[d]})}
class T(unittest.TestCase):
 def test_book_price_level_change_not_depletion(self):
  cur={'bids':[(D(100-i),D(100)) for i in range(3)],'asks':[(D(101+i),D(1)) for i in range(3)]};ref={'bids':cur['bids'],'asks':[(D(101+i),D(10)) for i in range(3)]};f={'book':cur,'reference':ref,'unit':D(1),'flow_imbalance':.6,'impulse_bps':0};self.assertIsNotNone(book_predicate(f));cur['asks'][2]=(D(104),D(1));self.assertIsNone(book_predicate(f))
 def test_three_assets_no_future_reference(self):
  f=Features(SPECS)
  for n,a in enumerate([A,E,S]):
   f.ingest(row(a,n*2+1,0,'books5',book(100)));f.ingest(row(a,n*2+2,0,'trades',{'px':'100','sz':'100','side':'buy'}))
  r=row(E,7,1001,'books5',book(100));_,now,_,dom,conn=f.ingest(r)
  self.assertIsNone(f.feature(A,now,1000,conn,dom))
  f.ingest(row(A,8,2000,'books5',book(120)));self.assertIsNone(f.feature(A,1001,1000,conn,dom))
 def test_beta1_is_fixed_observed_not_arbitrage(self):
  lead={'flow_imbalance':.9,'impulse_bps':4.,'connectionId':'x','clock_domain_id':'d'};follow={'impulse_bps':.5,'connectionId':'x','clock_domain_id':'d'};p=leader_predicate(lead,follow);self.assertEqual(p['beta'],1);self.assertTrue(p['not_arbitrage_or_true_lead']);self.assertEqual(p['self_momentum_baseline_direction'],1);follow['connectionId']='other';self.assertIsNone(leader_predicate(lead,follow))
 def test_cold_stale_reference_connection_WAIT(self):
  f=Features(SPECS);self.assertIsNone(f.feature(A,1000,500,'x','d'));f.ingest(row(A,1,0,'books5',book(100)));f.ingest(row(A,2,0,'trades',{'px':'100','sz':'100','side':'buy'}));_,n,_,d,c=f.ingest(row(A,3,1001,'books5',book(100.04)));self.assertIsNotNone(f.feature(A,n,1000,c,d));self.assertIsNone(f.feature(A,1400,1000,c,d));self.assertIsNone(f.feature(A,n,500,c,d));self.assertIsNone(f.feature(A,n,1000,'other',d))
 def test_v12_amount_math_preserved(self):
  self.assertEqual(execution.size_capacity([(D(100),D(5))],D(1),D('.01'),D('.01'),D(0)),D(5));p=json.loads((B/'protocol.json').read_text());self.assertEqual(hashlib.sha256((B/'frozen_execution_v12.py').read_bytes()).hexdigest(),p['execution_core_v12_sha256'])
 def test_cut_requires_actual_shared_namespace(self):
  freeze={'clock_domain_id':'OSd','forward_cut_OS_shared_ns':10,'capture_run_id':'job'};self.assertFalse(forward_eligible({'monotonic_ns':99},freeze));self.assertFalse(forward_eligible({'clock_domain_id':'wrong','os_shared_ns':100,'run_id':'job'},freeze));self.assertTrue(forward_eligible({'clock_domain_id':'OSd','os_shared_ns':10,'run_id':'job'},freeze));self.assertFalse(forward_eligible({'clock_domain_id':'OSd','os_shared_ns':9,'run_id':'job'},freeze))
 def test_live_input_TTL_is_not_just_causal_chain(self):
  s={'is_live':True,'clock_view':'OS_SHARED','clock_domain_id':'d','source_asof_shared_ns':100,'source_latest_book_shared_ns':90,'feature_completed_shared_ns':110};self.assertTrue(live_input_gate(s,120,'d')['may_send_live_state']);self.assertFalse(live_input_gate(s,300000000,'d')['may_send_live_state']);self.assertFalse(live_input_gate({**s,'is_live':False},120,'d')['may_send_live_state']);self.assertFalse(live_input_gate({**s,'source_latest_book_shared_ns':None},120,'d')['may_send_live_state'])
if __name__=='__main__':unittest.main()
