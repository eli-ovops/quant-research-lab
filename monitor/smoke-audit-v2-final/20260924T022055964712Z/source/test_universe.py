import unittest
from universe import common_markets


class UniverseTests(unittest.TestCase):
    def test_missing_flags_fail_closed_and_deprecated_fee_ignored(self):
        bases=['ABC','OFF','UNKNOWN','BTC','ETH','XYZ3L']
        okx=[dict(baseCcy=b,quoteCcy='USDT',state='live',instId=b+'-USDT') for b in bases]
        gate=[dict(base=b,quote='USDT',trade_status='tradable',id=b+'_USDT',fee='999') for b in bases]
        flags=dict(delisted=False,trade_disabled=False,deposit_disabled=False,withdraw_disabled=False,withdraw_delayed=False)
        currencies=[dict(currency=b,**flags) for b in bases]
        currencies[1]['deposit_disabled']=True
        del currencies[2]['withdraw_disabled']
        markets,excluded=common_markets(okx,gate,currencies)
        self.assertEqual(list(markets),['ABCUSDT'])
        self.assertEqual(markets['ABCUSDT']['gate_fee_bps'],'20')
        self.assertIn('HYPOTHETICAL',markets['ABCUSDT']['fee_basis'])
        self.assertEqual(len(excluded),5)
