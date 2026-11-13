import unittest
from decimal import Decimal as D
from path_engine import diagnostic,quote_delta
def b(t,bid,ask,ordinal):return {'time':t,'ordinal':ordinal,'bids':[(D(str(bid)),D('10'))],'asks':[(D(str(ask)),D('10'))]}
class T(unittest.TestCase):
 def test_doublefees_and_sameqty(self):
  self.assertEqual(quote_delta(b(100,102,103,2),D(2),D(1),1,D(200),D('.005')),D('1.98'))
 def test_gap_breaks_observed_span(self):
  bb=[b(0,99,100,1),b(100,101,102,2),b(200,101,102,3),b(800,101,102,4),b(1001,99,100,5)];r=diagnostic(bb,[x['time'] for x in bb],bb[0],D(1),D(1),1,D(100),D(0),1)
  self.assertEqual(r['future_path_positive_observed_spans_ms'],[[100,200],[800,800]]);self.assertEqual(len(r['future_path_gaps_over250ms']),1);self.assertTrue(r['future_path_window_complete'])
 def test_first_after_crossing_not_future_best(self):
  bb=[b(0,99,100,1),b(100,101,102,2),b(101,99,100,3),b(200,110,111,4),b(1001,99,100,5)];r=diagnostic(bb,[x['time'] for x in bb],bb[0],D(1),D(1),1,D(100),D(0),1)
  self.assertFalse(r['future_path_crossing_delay_quotes'][0]['still_nonnegative']);self.assertEqual(r['future_path_crossing_delay_quotes'][0]['ordinal'],3)
 def test_missingdepth_and_incomplete_tail_not_zero(self):
  bb=[b(0,99,100,1),b(100,101,102,2)];bb[1]['bids']=[(D(101),D('.1'))];r=diagnostic(bb,[0,100],bb[0],D(1),D(1),1,D(100),D(0),1);self.assertFalse(r['future_path_window_complete']);self.assertIsNone(r['future_path_observable_max_USDT']);self.assertEqual(r['future_path_no_exit_depth_quotes'],1)
if __name__=='__main__':unittest.main()
