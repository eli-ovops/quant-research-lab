import unittest
from decimal import Decimal as D
from paper_experiment import initial_experiment,step
from paper_ledger import ASSETS


def fixture(t,price='100'):
    p=D(price)
    books={a:{'ts':t+1,'asks':[[str(p+D('.1')),'100']],
              'bids':[[str(p-D('.1')),'100']]} for a in ASSETS}
    specs={a:{'lotSz':'.001','minSz':'.001'} for a in ASSETS}
    decision={'slot':str(t),'committed_ms':t,'weights':{'BTC-USDT':'.5','ETH-USDT':0},
              'input_sha256':'fixture','rationale':'scripted fixture'}
    return decision,books,specs,t+2


class Experiment(unittest.TestCase):
    def test_loss_halts_then_never_rebuys(self):
        initial=initial_experiment()
        s=step(initial,*fixture(1000))
        self.assertEqual(initial,initial_experiment())
        self.assertEqual(s['observations'][-1]['scenarios']['base_quote']['business_net_usdt'],'UNKNOWN')
        s=step(s,*fixture(2000,'50'))
        for arm in s['scenarios'].values():
            self.assertTrue(arm['risk_halted'])
            self.assertLess(D(arm['account']['positions']['BTC-USDT']),D('.001'))
        counts={k:len(v['account']['fills']) for k,v in s['scenarios'].items()}
        s=step(s,*fixture(3000,'200'),operating_cost_usdt='1.25')
        for k,arm in s['scenarios'].items():
            self.assertEqual(len(arm['account']['fills']),counts[k])
            row=s['observations'][-1]['scenarios'][k]
            self.assertEqual(D(row['trade_net_usdt'])-D(row['business_net_usdt']),D('1.25'))

    def test_invalid_window_unknown_consumed_no_benchmark_backfill(self):
        d,books,specs,now=fixture(1000)
        books['BTC-USDT']['ts']=0
        s=step(initial_experiment(),d,books,specs,now)
        self.assertEqual(s['observations'][-1]['equity'],'UNKNOWN')
        with self.assertRaisesRegex(ValueError,'DUPLICATE'):step(s,d,books,specs,now)
        s=step(s,*fixture(2000))
        for arm in s['scenarios'].values():
            self.assertEqual(arm['baselines']['buy_hold']['fills'],[])
            self.assertFalse(arm['baselines']['buy_hold_comparison_valid'])


if __name__=='__main__':unittest.main()
