import unittest,datetime
from engine import simulate,ts,DAY,metrics
class Tests(unittest.TestCase):
 def data(self,gap=100):
  start=ts('2024-01-01');raw={c:{} for c in ['BTC','ETH']}
  for c in raw:
   for t in range(start-91*DAY,start+7*DAY,DAY):
    price=100. if t<start else float(gap);close=110. if t==start-DAY else price
    raw[c][t]=[str(t),str(price),str(max(price,close)),str(min(price,close)),str(close),'1','1','1','1']
  return raw,start,start+7*DAY
 def test_constant_price_pays_two_side_cost(self):
  raw,s,e=self.data();led,day=simulate(raw,s,e,'hold',.002,.001)
  expected=500*(1-.001)*(1-.002)/((1+.001)*(1+.002))
  self.assertAlmostEqual(day[-1]['equity'],expected,9);self.assertLess(expected,500);self.assertEqual(len(led),4)
 def test_gap_executes_next_open_not_signal_close(self):
  raw,s,e=self.data(200);led,day=simulate(raw,s,e,'trend',0,0)
  buys=[x for x in led if x['side']=='BUY'];self.assertEqual(len(buys),2)
  for l in buys:self.assertEqual(l['reference_price'],200);self.assertAlmostEqual(l['quantity'],1.25);self.assertEqual(l['timestamp'],'2024-01-01T00:00:00+00:00')
 def test_future_mutation_does_not_change_initial_orders(self):
  raw,s,e=self.data();led,_=simulate(raw,s,e,'trend',.001,.0005);first=led[:2]
  for c in raw:
   for t in range(s,e,DAY):raw[c][t][4]='99999'
  amended,_=simulate(raw,s,e,'trend',.001,.0005);self.assertEqual(first,amended[:2])
 def test_no_signal_holds_cash_no_cost(self):
  raw,s,e=self.data()
  for c in raw:raw[c][s-DAY][4]='100'
  led,day=simulate(raw,s,e,'trend',.002,.001);self.assertEqual(led,[]);self.assertEqual(day[-1]['equity'],500);self.assertIsNone(metrics(led,day)['return_drawdown_ratio'])
 def test_fees_cash_covered_at_full_allocation(self):
  raw,s,e=self.data();led,day=simulate(raw,s,e,'trend',.002,.001)
  self.assertTrue(all(x['cash_after']>=-1e-9 for x in led));self.assertLess(day[-1]['equity'],500)
  for l in led:self.assertAlmostEqual(l['fee_USDT'],l['quantity']*l['execution_price']*.002)
if __name__=='__main__':unittest.main()
