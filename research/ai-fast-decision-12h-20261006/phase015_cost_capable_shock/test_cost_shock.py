import unittest,json
from decimal import Decimal as D
from fractions import Fraction as F
from cost_shock import asof_required_move,qualifies,ExactFlow,run
class T(unittest.TestCase):
 def test_cost_formula_exact_bidask_twosides(self):
  book={'asks':[(D('101'),D('100'))],'bids':[(D('100'),D('100'))]};required,legs=asof_required_move(book,D(1),D('.01'),D('.01'));long=F(101)*(1+F(5,10000))/(F(100)*(1-F(5,10000)))-1;short=1-F(100)*(1-F(5,10000))/(F(101)*(1+F(5,10000)));self.assertEqual(required,max(long,short)*10000);self.assertEqual(len(legs),2)
 def test_depth_missing_WAIT(self):
  self.assertIsNone(asof_required_move({'asks':[(D(100),D('.01'))],'bids':[(D(99),D('.01'))]},D(1),D('.01'),D('.01')))
 def test_gate_exact_boundary_and_cooldown_prerequisite(self):
  self.assertEqual(qualifies(F(20),F(100),F(80),F(15),F(90)),'QUALIFIED');self.assertEqual(qualifies(F(20)-F(1,10**30),F(100),F(80),F(15),F(90)),'WAIT_INSUFFICIENT_PAST_COST_ROOM');self.assertEqual(qualifies(F(20),F(100),F(80),F(15),F(90)+F(1,10**30)),'WAIT_RECEIVED_VOLUME_BELOW_REFERENCE_DEPTH')
 def test_trade_count_not_multiplier_window_causal(self):
  f=ExactFlow();s={'ctVal':'1000','ctMult':'1'};r={'instId':'DOGE-USDT-SWAP','channel':'trades','raw':json.dumps({'data':[{'tradeId':'1','px':'.1','sz':'2','side':'buy','ts':'1','count':'100'}]})};x=f.ingest(r,1000,'c','d',s);self.assertEqual(x['total'],F(200));x=f.ingest(r,1001,'c','d',s);self.assertEqual(x['total'],F(200));x=f.ingest({**r,'channel':'books5'},2000,'c','d',s);self.assertEqual(x['total'],0)
 def test_future_fields_not_used_newcooldown_after_fullqualification(self):
  import pathlib
  source=pathlib.Path('cost_shock.py').read_text();self.assertNotIn('future_path',source);self.assertNotIn('price_fee_delta',source);self.assertLess(source.index("if status!='QUALIFIED'"),source.index("if now-cool.get"));self.assertIn('features.feature(asset,now,1000',source)
 def test_small_early_move_does_not_start_new_cooldown(self):
  rows=[];asset='A';spec={'ctVal':'1','ctMult':'1','lotSz':'.01','minSz':'.01'}
  def append(t,channel,data):rows.append({'instId':asset,'channel':channel,'raw':json.dumps({'data':[data]}),'os_shared_ns':2000000000+int(t*1000000),'receive_wall_ns':1000000000000+int(t*1000000),'receive_wall_ms':1000000+t,'local_ordinal':len(rows)+1,'connectionId':'c','clock_domain_id':'d','run_id':'r'})
  def book(t,bid,ask):append(t,'books5',{'asks':[[str(ask),'20']],'bids':[[str(bid),'20']]})
  book(0,100,100.01);append(0,'trades',{'tradeId':'1','px':'100','sz':'1','side':'buy','ts':'1'})
  book(1000,100.05,100.06);append(1000,'trades',{'tradeId':'2','px':'100','sz':'50','side':'buy','ts':'2'});book(1100,100.5,100.51);book(1200,100.5,100.51)
  events,_,c=run(rows,{asset:spec},'d');self.assertEqual(len(events),1);self.assertEqual(events[0]['asof_ms'],3100);self.assertGreater(c['WAIT_reasons']['WAIT_INSUFFICIENT_PAST_COST_ROOM'],0);self.assertEqual(c['WAIT_reasons']['QUALIFIED_BUT_NEWFAMILY_COOLDOWN'],1)
if __name__=='__main__':unittest.main()
