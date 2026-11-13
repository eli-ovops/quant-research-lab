import time
import unittest
from decimal import Decimal as D
from detector import Book, evaluate, ingest


def view(bids, asks, ts=10000):
    return dict(bids=[(D(p),D(q)) for p,q in bids],asks=[(D(p),D(q)) for p,q in asks],
                valid=True,ts=ts,received=10)


class DetectorTests(unittest.TestCase):
    def test_common_lot_rounding_and_order_minimum(self):
        b=view([('9','100')],[('10','100')]);s=view([('11','100')],[('12','100')])
        rules={'buy':dict(lot='.2',min_qty='1',min_quote='0',max_quote='1000'),
               'sell':dict(lot='.3',min_qty='1',min_quote='3',max_quote='1000')}
        r=evaluate(b,s,D(101),D(10),D(10),D(5),10000,10,order_rules=rules)
        self.assertEqual(D(r['quantity']),D('9.6'))
        self.assertEqual(D(r['buy_cost_usdt']),D('96'))
        self.assertEqual(D(r['net_usdt']),D('9.3504'))
        rules['sell']['min_qty']='10'
        self.assertEqual(evaluate(b,s,D(101),D(10),D(10),D(5),10000,10,order_rules=rules)['status'],'ORDER_CONSTRAINT')

    def test_okx_missing_previous_rejected_but_noop_and_reset_allowed(self):
        b=Book();bs={'LSKUSDT':b}
        def m(seq,prev,bids=None):
            d=dict(bids=[] if bids is None else bids,asks=[],ts='10000',seqId=seq)
            if prev is not None:d['prevSeqId']=prev
            return dict(arg={'instId':'LSK-USDT'},action='update',data=[d])
        b.apply([['99','1']],[['100','1']],10000,4,True)
        ingest('okx',m(4,4),bs)
        ingest('okx',m(1,4),bs)
        self.assertEqual(b.seq,1)
        with self.assertRaises(ValueError):ingest('okx',m(2,None),bs)
        self.assertFalse(b.valid)

    def test_same_sequence_changed_payload_and_bad_level_invalid(self):
        b=Book();b.apply([['99','1']],[['100','1']],10000,4,True)
        with self.assertRaises(ValueError):
            ingest('okx',dict(arg={'instId':'LSK-USDT'},action='update',data=[dict(bids=[['99','2']],asks=[],ts='10000',seqId=4,prevSeqId=4)]),{'LSKUSDT':b})
        self.assertFalse(b.valid)
        b.apply([['99','1']],[['100','1']],10000,4,True)
        with self.assertRaises(Exception):b.apply([['NaN','1']],[],10000,5,False,4)
        self.assertFalse(b.valid)

    def test_gate_regression_rejected_and_new_connection_resets(self):
        b=Book();bs={'LSKUSDT':b}
        def m(seq):return dict(channel='spot.order_book',event='update',result=dict(s='LSK_USDT',t=10000,lastUpdateId=seq,bids=[['99','1']],asks=[['100','1']]))
        ingest('gate',m(5),bs)
        with self.assertRaises(ValueError):ingest('gate',m(4),bs)
        self.assertFalse(b.valid)
        b.reset('new');ingest('gate',m(1),bs)
        self.assertTrue(b.valid)

    def test_all_costs(self):
        b=view([('99','10')],[('100','10')]);s=view([('102','10')],[('103','10')])
        r=evaluate(b,s,D(100),D(10),D(10),D(5),now_ms=10000,mono=10)
        self.assertEqual(D(r['net_usdt']),D('1.748'))

    def test_depth_not_last_price(self):
        b=view([('99','10')],[('100','1'),('110','10')]);s=view([('105','10')],[('106','10')])
        r=evaluate(b,s,D(210),D(0),D(0),D(0),now_ms=10000,mono=10)
        self.assertEqual(D(r['net_usdt']),0)

    def test_insufficient_depth(self):
        b=view([('99','1')],[('100','1')])
        self.assertEqual(evaluate(b,b,D(200),D(0),D(0),D(0),now_ms=10000,mono=10)['status'],'INSUFFICIENT_DEPTH')

    def test_stale_and_skew(self):
        b=view([('99','10')],[('100','10')]);s=view([('99','10')],[('100','10')],10600)
        for now,status in [(11000,'UNSYNCHRONIZED'),(14000,'STALE_OR_CLOCK_ERROR')]:
            self.assertEqual(evaluate(b,s,D(100),D(0),D(0),D(0),now_ms=now,mono=10)['status'],status)

    def test_sequence_gap_invalidates(self):
        b=Book();b.apply([['99','1']],[['100','1']],10000,4,True)
        with self.assertRaises(ValueError):b.apply([],[],10001,6,False,5)
        self.assertFalse(b.valid)

    def test_snapshot_and_delete(self):
        b=Book();b.apply([['99','1'],['98','1']],[['100','1']],10000,4,True)
        b.apply([['99','0']],[],10001,5,False,4)
        self.assertEqual(max(b.bids),D(98))

    def test_bybit_reset(self):
        b=Book();bs={'BTCUSDT':b}
        m={'topic':'orderbook.50.BTCUSDT','type':'delta','ts':10000,
           'data':{'s':'BTCUSDT','u':1,'b':[['99','1']],'a':[['100','1']]}}
        ingest('bybit',m,bs);self.assertTrue(b.valid)

    def test_no_delta_before_snapshot(self):
        with self.assertRaises(ValueError):Book().apply([],[],10000,3,False,2)

    def test_gate_full_snapshot_replaces_levels(self):
        b=Book();bs={'ZECUSDT':b}
        self.assertIsNone(ingest('gate', {'channel':'spot.order_book','event':'subscribe'}, bs))
        for seq, price in [(1,'99'),(2,'98')]:
            ingest('gate', {'channel':'spot.order_book','event':'update','time_ms':99999,
                           'result':{'s':'ZEC_USDT','t':10000,'lastUpdateId':seq,
                                     'bids':[[price,'2']],'asks':[['100','3']]}},bs)
        self.assertEqual(b.bids,{D(98):D(2)})
        self.assertEqual(b.ts,10000)


if __name__=='__main__':unittest.main()
