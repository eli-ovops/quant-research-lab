import unittest
from audit_accounting import account_check


class Audit(unittest.TestCase):
    def test_mixed_fee_roundtrip_and_bad_balance(self):
        s={'cash':'147.01','positions':{'BTC-USDT':'0','ETH-USDT':'0'},'fills':[
            {'asset':'BTC-USDT','side':'BUY','quantity':'1','notional':'101','fee':'.01','fee_currency':'BTC'},
            {'asset':'BTC-USDT','side':'SELL','quantity':'.99','notional':'99','fee':'.99','fee_currency':'USDT'}]}
        self.assertEqual(account_check(s)['cash'],'147.01')
        s['cash']='148'
        with self.assertRaisesRegex(ValueError,'BALANCE_MISMATCH'):account_check(s)


if __name__=='__main__':unittest.main()
