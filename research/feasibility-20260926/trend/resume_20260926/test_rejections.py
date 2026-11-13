import unittest
from decimal import Decimal as D
from analyze import simulate,sell_quote
from test_analysis import make,SPEC
class RejectedExit(unittest.TestCase):
 def test_rejected_then_later_sold(self):
  d,a,b=make(['120','130','50','49','48']+['47']*45)
  override={('2020-01-04',c):{'available_qty':'0'} for c in ['BTC','ETH']}
  r=simulate(d,SPEC,a,b,execution_overrides=override)
  self.assertEqual(len(r['trades']),2);self.assertTrue(all(t['exit_date']=='2020-01-05' for t in r['trades']))
  self.assertTrue(all(x['reason']=='exit_rejected_position_retained' for x in r['rejections']))
  day=r['curve'][3];self.assertGreater(day['BTC_qty'],0);self.assertTrue(day['exit_unresolved']);self.assertIsNone(day['liquidation_equity_proxy']);self.assertGreater(day['valuation_equity'],day['cash'])
  self.assertEqual(sum(x['side']=='buy' for x in r['fills']),2)
 def test_terminal_rejection_retains_price_risk(self):
  d,a,b=make(['120']*49+['240']);over={(b,c):{'quote':None} for c in ['BTC','ETH']};r=simulate(d,SPEC,a,b,execution_overrides=over)
  self.assertFalse(r['all_trade_positions_closed']);self.assertEqual(len(r['open_positions']),2);self.assertEqual(r['trades'],[]);self.assertGreater(r['curve'][-1]['valuation_equity'],r['curve'][-2]['valuation_equity']);self.assertEqual(r['dust_base']['BTC'],0)
 def test_each_rejection_guard(self):
  for spec,quote,avail in [(dict(SPEC['BTC'],minSz='100'),100,None),(dict(SPEC['BTC'],maxMktSz='.01'),100,None),(dict(SPEC['BTC'],maxMktAmt='10'),100,None),(SPEC['BTC'],None,None),(SPEC['BTC'],'NaN',None),(SPEC['BTC'],'-1',None),(SPEC['BTC'],100,'0.5')]:
   r=sell_quote(D(1),quote,spec,D('.001'),D('.0005'),avail);self.assertEqual(r[0],0);self.assertEqual(r[3],0);self.assertEqual(r[4],1)
 def test_rejected_hold_benchmark(self):
  d,a,b=make(['100']*49+['200']);r=simulate(d,SPEC,a,b,budgets={'BTC':D(800),'ETH':D(800)},execution_overrides={(b,c):{'spec':{'maxMktAmt':'1'}} for c in ['BTC','ETH']});self.assertEqual(len(r['open_positions']),2);self.assertGreater(r['curve'][-1]['valuation_equity'],3000);self.assertEqual(len(r['fills']),2)
if __name__=='__main__':unittest.main(verbosity=2)
