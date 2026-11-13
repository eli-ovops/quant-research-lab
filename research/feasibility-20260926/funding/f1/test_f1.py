"""F1-specific boundary and integration tests. Synthetic, not performance evidence."""
import unittest
from decimal import Decimal as D
from unittest.mock import patch
import analyze_f1 as a

class ExitTests(unittest.TestCase):
    spec={'lotSz':'.01','minSz':'.02','maxMktSz':'10','maxMktAmt':'1000'}
    def assert_retained(self,out,inventory,reason):
        self.assertEqual(out['reason'],reason);self.assertFalse(out['sell_filled'])
        self.assertEqual(out['sold_base'],0);self.assertEqual(out['remaining_base'],inventory)
        self.assertEqual(out['cash_proceeds'],0);self.assertEqual(out['sell_fee'],0)
        self.assertEqual(out['remaining_realizable_value'],0);self.assertFalse(out['fully_flat'])
    def test_dust_and_exact_lot(self):
        r=a.spot_exit(D('1.239'),self.spec,D('.001'),price=D(100))
        self.assertEqual(r['sold_base'],D('1.23'));self.assertEqual(r['remaining_base'],D('.009'))
        self.assertEqual(r['cash_proceeds'],D('122.877'));self.assertEqual(r['remaining_realizable_value'],0)
        self.assertFalse(r['fully_flat']);self.assertEqual(r['sold_base']%D('.01'),0)
        r=a.spot_exit(D('1.23'),self.spec,D('.001'),price=D(100));self.assertTrue(r['fully_flat'])
    def test_below_min_and_no_full_lot(self):
        self.assert_retained(a.spot_exit(D('.019'),self.spec,D('.001'),price=100),D('.019'),'BELOW_MIN_SZ')
        self.assert_retained(a.spot_exit(D('.009'),self.spec,D('.001'),price=100),D('.009'),'NO_VALID_LOT')
        self.assertTrue(a.spot_exit(D('.02'),self.spec,D('.001'),price=100)['sell_filled'])
    def test_max_quantity_and_amount(self):
        self.assert_retained(a.spot_exit(D('10.01'),self.spec,D('.001'),price=100),D('10.01'),'ABOVE_MAX_SZ')
        self.assert_retained(a.spot_exit(D(10),self.spec,D('.001'),price=101),D(10),'ABOVE_MAX_AMOUNT')
        self.assertTrue(a.spot_exit(D(10),self.spec,D('.001'),price=100)['sell_filled'])
    def test_missing_invalid_quote_preserves_position(self):
        for quote in [None,'',0,-1,'NaN','Infinity','bad']:
            with self.subTest(quote=quote):self.assert_retained(a.spot_exit(D('1.239'),self.spec,D('.001'),price=quote),D('1.239'),'NO_VALID_QUOTE')
    def test_multilevel_floor_before_capacity_and_no_partial_assumed(self):
        r=a.spot_exit(D('1.239'),self.spec,D('.001'),levels=[['100','.5'],['99','.73']])
        self.assertTrue(r['sell_filled']);self.assertEqual(r['sold_base'],D('1.23'))
        self.assertEqual(r['cash_proceeds'],(D(50)+D('72.27'))*D('.999'))
        r=a.spot_exit(D('1.239'),self.spec,D('.001'),levels=[['100','.5'],['99','.72']])
        self.assert_retained(r,D('1.239'),'INSUFFICIENT_OR_INVALID_DEPTH')
        for levels in [[],[['0','10']],[['100','-1']],[['NaN','10']]]:
            r=a.spot_exit(D('1.239'),self.spec,D('.001'),levels=levels)
            self.assertFalse(r['sell_filled']);self.assertEqual(r['remaining_base'],D('1.239'))
    def fixture(self):
        t0=a.stamp('2026-01-01');t1=a.stamp('2026-01-02')
        bar={'o':D(100),'h':D(101),'l':D(99),'c':D(100),'confirm':'1'}
        data={k:{t:bar.copy() for t in range(t0,t1+a.HOUR,a.HOUR)} for k in ['spot','swap','mark']}
        data['spot_spec'],data['swap_spec']=a.identity('BTC');data['mmr']=D('.004')
        data['funding']={t:{'realizedRate':'.001','fundingRate':'.9','formulaType':'withRate','method':'current_period'} for t in range(t0,t1+1,8*a.HOUR)}
        return data
    def test_replay_all_cash_inventory_curve_and_benchmark(self):
        r,e,curve=a.replay('BTC',self.fixture(),'2026-01-01','2026-01-02','synthetic')
        sold=(r['net_spot_base']//D('.00000001'))*D('.00000001')
        inventory=r['net_spot_base']-sold
        self.assertEqual(r['sold_spot_base'],sold);self.assertEqual(r['remaining_spot_base'],inventory)
        proceeds=sold*D('99.95')*D('.999')
        cash=D(2000)-r['gross_spot_base']*D('100.05')-r['swap_open_fee']+proceeds+r['hedged_base']*(D('99.95')-D('100.05'))+r['funding_proxy']-r['swap_close_fee']
        self.assertLess(abs(cash-r['cash_end']),D('1e-30'))
        self.assertEqual(r['spot_hold_same_cash_allocation_pnl_proxy'],proceeds-r['spot_cash_used'])
        for row in curve:
            self.assertEqual(row['hypothetical_sold_base'],sold);self.assertEqual(row['retained_base'],inventory)
            self.assertEqual(row['spot_sale_cash'],proceeds)
        self.assertEqual(curve[-1]['equity_proxy'],r['cash_end']);self.assertFalse(r['all_inventory_flat'])
    def test_replay_min_rejection_preserves_full_inventory(self):
        data=self.fixture();_,_,gross,net=a.size(D('100.05'),data['spot_spec'],data['swap_spec'],D('.001'))
        data['spot_spec']['minSz']=str(gross) # gross buy valid, fee-reduced sell too small
        r,_,curve=a.replay('BTC',data,'2026-01-01','2026-01-02','synthetic')
        self.assertFalse(r['spot_order_filled']);self.assertEqual(r['remaining_spot_base'],net)
        self.assertEqual(r['sold_spot_base'],0);self.assertEqual(r['spot_sell_fee'],0)
        self.assertEqual(r['spot_hold_same_cash_allocation_pnl_proxy'],-r['spot_cash_used'])
        self.assertTrue(all(row['hypothetical_sold_base']==0 for row in curve))
        self.assertFalse(r['all_inventory_flat']);self.assertLess(r['net_pnl_proxy'],-700)
    def test_current_snapshot_rejected_spot_keeps_inventory(self):
        original=a.read
        def no_bids(name):
            result=original(name)
            if name=='BTC_spot_book':result[0]['bids']=[]
            return result
        with patch.object(a,'read',side_effect=no_bids):r=a.current_snapshot('BTC')
        self.assertFalse(r['capacity_at_snapshot']);self.assertIsNone(r['instant_roundtrip_cost_snapshot'])
        self.assertEqual(r['roundtrip_status'],'SPOT_EXIT_REJECTED_POSITION_RETAINED')
        self.assertEqual(r['sold_spot_base'],0);self.assertGreater(r['remaining_spot_base'],0)
    def test_variable_funding_and_no_future_signal_unchanged(self):
        self.assertEqual(a.fund_event(D(2),{'realizedRate':'-.01'},{'o':D(200),'h':D(220),'l':D(190)}),(D(-4),D('-4.4'),D('-3.8')))
        data=self.fixture();r,_,_=a.replay('BTC',data,'2026-01-01','2026-01-02','synthetic')
        for x in data['funding'].values():x['fundingRate']='-99'
        other,_,_=a.replay('BTC',data,'2026-01-01','2026-01-02','synthetic')
        self.assertEqual(r['net_pnl_proxy'],other['net_pnl_proxy']);self.assertEqual(r['funding_events_interior'],2)
        self.assertEqual(r['boundary_events_unknown'],2)

if __name__=='__main__':unittest.main(verbosity=2)
