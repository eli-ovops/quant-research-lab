import unittest
from monitor import opportunity_events, delayed_estimate
from decimal import Decimal as D
import time


class MonitorTests(unittest.TestCase):
    def test_delay_keeps_original_quantity_and_reprices_cost(self):
        b=dict(valid=True,ts=time.time()*1000,received=time.monotonic(),asks=[(D(101),D(10))],bids=[(D(100),D(10))])
        s=dict(b,asks=[(D(103),D(10))],bids=[(D(102),D(10))])
        r=delayed_estimate(dict(amount_usdt='100',quantity='1',buy_fee_bps='10',sell_fee_bps='10'),b,s)
        self.assertEqual(D(r['buy_cost_usdt']),101)
        self.assertEqual(D(r['net_usdt']),D('0.7465'))
    def test_only_positive_after_costs_and_no_repeat_spam(self):
        active,last=set(),{}
        r=dict(symbol='ZECUSDT',buy='okx',sell='gate',amount_usdt='100',status='ESTIMATE_ONLY',net_usdt='-0.1')
        self.assertEqual(opportunity_events([r],active,last,100),[])
        r['net_usdt']='0.1'
        self.assertEqual(opportunity_events([r],active,last,101)[0]['event'],'candidate')
        self.assertEqual(opportunity_events([r],active,last,102),[])
        self.assertEqual(opportunity_events([r],active,last,161)[0]['event'],'continuing')
        r['status']='STALE_OR_CLOCK_ERROR'
        self.assertEqual(opportunity_events([r],active,last,162)[0]['event'],'data_unavailable')
        self.assertFalse(active)


if __name__ == '__main__': unittest.main()
