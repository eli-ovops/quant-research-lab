import unittest
from decimal import Decimal as D
from monitor import delayed_estimate, Episodes
from qualification import eligible, REQUIRED


def view(ask,bid='79',qty='1'):
    return dict(valid=True,ts=10000,received=10,asks=[(D(ask),D(qty))],bids=[(D(bid),D(qty))],ref=2,connection_id='a')


class MonitorTests(unittest.TestCase):
    def test_delay_original_quantity_not_original_budget(self):
        r=delayed_estimate(dict(amount_usdt='100',quantity='1',buy_fee_bps='10',sell_fee_bps='20'),
                           view('80'),view('86','85'),10000,10)
        self.assertEqual(D(r['net_usdt']),D('4.71'))
        self.assertEqual(r['affordability'],'UNKNOWN')

    def test_new_data_and_cash_required(self):
        original=dict(amount_usdt='100',quantity='1',buy_fee_bps='10',sell_fee_bps='10',
                      book_refs=[1,1],connection_ids=['a','a'],hypothetical_available_cash_usdt='100.1')
        b,s=view('101','100','10'),view('103','102','10')
        r=delayed_estimate(original,b,s,10000,10)
        self.assertEqual(D(r['net_usdt']),D('.7465'))
        self.assertEqual(r['affordability'],'NO')
        b['ref']=1
        self.assertEqual(delayed_estimate(original,b,s,10000,10)['status'],'NO_NEW_BOOK')
        b['connection_id']='b'
        self.assertEqual(delayed_estimate(original,b,s,10000,10)['status'],'CONNECTION_CHANGED')

    def test_episode_survives_invalid_data_and_groups_amounts(self):
        tracker=Episodes()
        r=dict(symbol='LSKUSDT',buy='okx',sell='gate',amount_usdt='100',scenario='base',status='ESTIMATE_ONLY',net_usdt='1')
        capacities=[r,dict(r,amount_usdt='500'),dict(r,amount_usdt='1000')]
        e=tracker.update(capacities,10000)
        self.assertEqual(len(e),1);self.assertEqual(len(e[0]['capacity_scenarios']),3)
        self.assertEqual(tracker.update(capacities,11000),[])
        r['status']='STALE_OR_CLOCK_ERROR'
        self.assertEqual(tracker.update([r],12000)[0]['event'],'data_unavailable')
        self.assertEqual(tracker.update([r],13000),[])
        r['status']='ESTIMATE_ONLY'
        e=tracker.update([r],14000)[0]
        self.assertEqual(e['event'],'anomaly_resumed');self.assertEqual(e['episode_id'],1)
        r['net_usdt']='-1'
        self.assertEqual(tracker.update([r],15000),[])
        self.assertEqual(tracker.update([r],16000),[])
        self.assertEqual(tracker.update([r],17000)[0]['event'],'ended')
        self.assertEqual(tracker.serial,1)

    def test_unknown_route_fails_closed(self):
        self.assertFalse(eligible({}))
        route={k:{'status':'VERIFIED','evidence':'local snapshot','checked_ms':1000} for k in REQUIRED}
        self.assertTrue(eligible(route))
        route['account_fees_and_fee_currency']['status']='UNKNOWN'
        self.assertFalse(eligible(route))


if __name__=='__main__':unittest.main()
