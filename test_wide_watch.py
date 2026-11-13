import json
import unittest
from wide_watch import accumulate,deadline_overdue
from wide_replay import canonical_frame


class WideTests(unittest.TestCase):
    def test_shutdown_grace_is_seconds_not_milliseconds(self):
        self.assertFalse(deadline_overdue(1001000,1000000))
        self.assertFalse(deadline_overdue(1040000,1000000))
        self.assertTrue(deadline_overdue(1040001,1000000))

    def test_alias_preserves_raw_evidence_and_unrelated_symbols(self):
        mapping={'gate':{'EDGEUSDT':'EDGEXUSDT','GUSDT':'GUSDT'},'okx':{'EDGEUSDT':'EDGEUSDT','GUSDT':'GUSDT'}}
        r=dict(kind='frame',venue='gate',journal_seq=42,raw=json.dumps({'channel':'spot.order_book','event':'update','result':{'s':'EDGEX_USDT','bids':[['1','2']]}}))
        out=canonical_frame(r,mapping)
        self.assertEqual(json.loads(out['raw'])['result']['s'],'EDGE_USDT')
        self.assertEqual(json.loads(r['raw'])['result']['s'],'EDGEX_USDT')
        self.assertEqual(out['journal_seq'],42)
        r['raw']=json.dumps({'channel':'spot.order_book','event':'update','result':{'s':'G_USDT'}})
        self.assertEqual(json.loads(canonical_frame(r,mapping)['raw'])['result']['s'],'G_USDT')

    def test_invalid_samples_never_count_as_loss_or_profit(self):
        base=dict(symbol='GUSDT',buy='okx',sell='gate',scenario='base',amount_usdt='100')
        rows=[dict(base,status='ESTIMATE_ONLY',net_usdt='0.2'),dict(base,status='STALE_OR_CLOCK_ERROR'),dict(base,status='ESTIMATE_ONLY',net_usdt='-0.1')]
        stats={};accumulate(stats,rows);s=next(iter(stats.values()))
        self.assertEqual((s['observations'],s['valid'],s['positive']),(3,2,1))
        self.assertEqual(s['net_sum'],'0.1')
        self.assertEqual(s['min_net'],'-0.1')
        self.assertEqual(s['above_0_5'],0)


if __name__=='__main__':unittest.main()
