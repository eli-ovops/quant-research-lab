"""Synthetic boundary tests only. Never evidence of economic profitability."""
import unittest
from decimal import Decimal as D
import analyze as a

class AccountingTests(unittest.TestCase):
    def test_variable_notional_and_negative_bound(self):
        mark={'o':D(200),'l':D(190),'h':D(220)}
        self.assertEqual(a.fund_event(D(2),{'realizedRate':'.01'},mark),(D(4),D('3.8'),D('4.4')))
        self.assertEqual(a.fund_event(D(2),{'realizedRate':'-.01'},mark),(D(-4),D('-4.4'),D('-3.8')))
        self.assertNotEqual(D(200)*D('.01'),a.fund_event(D(2),{'realizedRate':'.01'},mark)[0])
    def test_deep_book_units_and_exhaustion(self):
        levels=[['100','2'],['101','3']]
        avg,left=a.book_vwap(levels,D('.04'),D('.01'))
        self.assertEqual(avg,D('100.5'));self.assertEqual(left,0)
        self.assertEqual(a.book_vwap(levels,D('.06'),D('.01')),(None,D('.01')))
    def test_base_fee_and_rounding(self):
        sp={'lotSz':'.00000001','minSz':'.00001','maxMktSz':'1000000'}
        fp={'ctVal':'.01','ctMult':'1','lotSz':'.01','minSz':'.01','maxMktSz':'35000'}
        n,q,gross,net=a.size(D(60001),sp,fp,D('.001'))
        self.assertLessEqual(gross*D(60001),800)
        self.assertGreaterEqual(net,q);self.assertLess(net-q,D(sp['lotSz']))
        self.assertEqual(n%D(fp['lotSz']),0)
    def fixture(self,negative=False):
        t0=a.stamp('2026-01-01');t1=a.stamp('2026-01-02')
        bar={'o':D(100),'h':D(101),'l':D(99),'c':D(100),'confirm':'1'}
        series={k:{t:bar.copy() for t in range(t0,t1+a.HOUR,a.HOUR)} for k in ['spot','swap','mark']}
        series['spot_spec'],series['swap_spec']=a.identity('BTC');series['mmr']=D('.004')
        series['funding']={t:{'realizedRate':'-.001' if negative else '.001','fundingRate':'.9','formulaType':'withRate','method':'current_period'} for t in range(t0,t1+1,8*a.HOUR)}
        return series
    def test_boundary_and_independent_cash(self):
        r,e,curve=a.replay('BTC',self.fixture(),'2026-01-01','2026-01-02','synthetic')
        q=r['hedged_base'];gross=r['gross_spot_base'];net=r['net_spot_base']
        funding=q*D(100)*D('.001')*2
        cash=D(2000)-gross*D('100.05')-q*D('99.95')*D('.0005')+net*D('99.95')*D('.999')+q*(D('99.95')-D('100.05'))+funding-q*D('100.05')*D('.0005')
        self.assertLess(abs(cash-r['cash_end']),D('1e-30'))
        self.assertEqual(r['funding_events_interior'],2);self.assertEqual(r['boundary_events_unknown'],2)
        self.assertEqual(r['funding_low_with_boundary'],q*D(99)*D('.001')*2)
        self.assertEqual(r['funding_high_with_boundary'],q*D(101)*D('.001')*4)
        self.assertEqual(r['return_on_2000_proxy'],r['net_pnl_proxy']/2000)
        self.assertLess(r['net_pnl_proxy'],r['funding_proxy'])
    def test_negative_boundaries_and_no_future_signal(self):
        data=self.fixture(True)
        r,_,_=a.replay('BTC',data,'2026-01-01','2026-01-02','synthetic')
        for x in data['funding'].values():x['fundingRate']='-99'
        changed,_,_=a.replay('BTC',data,'2026-01-01','2026-01-02','synthetic')
        self.assertEqual(r['hedged_base'],changed['hedged_base']);self.assertEqual(r['net_pnl_proxy'],changed['net_pnl_proxy'])
        self.assertLess(r['funding_low_with_boundary'],r['funding_proxy'])
        self.assertLess(r['funding_high_with_boundary'],0)
    def test_missing_bar_rejected_and_margin_not_spot_credit(self):
        data=self.fixture();del data['mark'][a.stamp('2026-01-01')+a.HOUR]
        with self.assertRaises(AssertionError):a.replay('BTC',data,'2026-01-01','2026-01-02','synthetic')
        data=self.fixture();t=a.stamp('2026-01-01')+a.HOUR
        data['mark'][t]={'o':D(300),'h':D(300),'l':D(300),'c':D(300),'confirm':'1'}
        data['spot'][t]=data['mark'][t].copy()
        r,_,_=a.replay('BTC',data,'2026-01-01','2026-01-02','synthetic')
        self.assertTrue(r['liquidation_unresolved'])
        self.assertLess(r['isolated_margin_min_buffer_current_mmr_stress'],0)

if __name__=='__main__':unittest.main(verbosity=2)
