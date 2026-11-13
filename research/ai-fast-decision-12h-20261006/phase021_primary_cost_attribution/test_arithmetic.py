import unittest
from attribution import best_pair,distribution,summarize
class T(unittest.TestCase):
 def test_censored_and_quantity_mismatch_not_zero(self):
  f={'event_id':1,'family':'F','asset':'A','fee_each_side_bps':5,'status':'censored'};g={**f,'status':'observed','contracts':'1'};self.assertIsNone(best_pair(f,g)['future_only_best_net_USDT']);f={**g,'contracts':'2'};self.assertEqual(best_pair(f,g)['status'],'UNKNOWN_QTY_NOT_MATCHED_KEEP_BOTH')
 def test_empty_null_and_gross_fees_net(self):
  self.assertIsNone(distribution([])['mean']);x={'status':'observed','gross_price_delta_USDT':.4,'fee_USDT':.5,'price_fee_delta_USDT':-.1,'entry_notional_USDT':500,'exit_notional_USDT':500,'actual_entry_delay_ms':100};s=summarize([x]);self.assertEqual(s['future_only_gross_positive_count'],1);self.assertEqual(s['future_only_net_positive_count'],0);self.assertEqual(s['future_only_break_even_eachleg_fee_bps']['mean'],4)
if __name__=='__main__':unittest.main()
