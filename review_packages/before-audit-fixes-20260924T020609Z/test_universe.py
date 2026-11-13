import unittest
from universe import common_markets


class UniverseTests(unittest.TestCase):
    def test_restrictions_and_conservative_pair_fee(self):
        bases=['ABC','OFF','BTC','ETH','XYZ3L']
        okx=[dict(baseCcy=b,quoteCcy='USDT',state='live',instId=b+'-USDT') for b in bases]
        gate=[dict(base=b,quote='USDT',trade_status='tradable',id=b+'_USDT',fee='0.2') for b in bases]
        currencies=[dict(currency=b,deposit_disabled=(b=='OFF')) for b in bases]
        markets,excluded=common_markets(okx,gate,currencies)
        self.assertEqual(list(markets),['ABCUSDT'])
        self.assertEqual(float(markets['ABCUSDT']['gate_fee_bps']),20)
        self.assertFalse(markets['ABCUSDT']['identity_verified'])
        self.assertEqual(len(excluded),4)
