"""Safety-relevant screening boundaries; no network or monitor mutations."""
import unittest
from decimal import Decimal as D
from screen_markets import common_catalog, network_status, order_rules, summarize, needs_recheck, view


def market(base='ABC'):
    okx=dict(baseCcy=base,quoteCcy='USDT',instId=base+'-USDT',state='live',ruleType='normal',
             lotSz='.01',minSz='1',maxMktSz='100000',maxMktAmt='100000')
    gate=dict(base=base,quote='USDT',id=base+'_USDT',trade_status='tradable',type='normal',
              amount_precision=1,min_base_amount=None,min_quote_amount=None)
    return common_catalog([okx],[gate],[])[0]


def observation(net,quality='VALID',within=True):
    return dict(symbol='ABCUSDT',quality=quality,results=[dict(buy='okx',sell='gate',
        amount_usdt='100',scenario='higher_gate',status='ESTIMATE_ONLY' if quality=='VALID' else quality,
        net_usdt=str(net),capital_with_200_usdt_reserve='401',within_2000_budget=within)])


class ScreeningTests(unittest.TestCase):
    def test_common_codes_are_not_verified_assets(self):
        m=market()
        self.assertTrue(m['depth_screen_enabled'])
        self.assertEqual(m['identity'],'UNKNOWN')
        self.assertEqual(m['route_eligibility'],'BLOCKED_UNKNOWN')
        self.assertEqual(m['gate_deposit'],'UNKNOWN')

    def test_all_common_no_top_n_and_user_exclusions(self):
        ms=[market('T'+str(i)) for i in range(70)]+[market('BTC'),market('ETH')]
        catalog=common_catalog([m['okx_instrument'] for m in ms],[m['gate_pair'] for m in ms],[])
        self.assertEqual(len(catalog),72)
        self.assertEqual(sum(m['depth_screen_enabled'] for m in catalog),70)
        o=dict(ms[0]['okx_instrument'],quoteCcy='USDC')
        self.assertEqual(common_catalog([o],[ms[0]['gate_pair']],[]),[])

    def test_directional_flags_and_missing_data(self):
        self.assertEqual(network_status({'deposit_disabled':False},'deposit'),'UNKNOWN')
        self.assertEqual(network_status({'chains':[{}]},'withdraw'),'UNKNOWN')
        c={'chains':[{'deposit_disabled':True,'withdraw_disabled':False,'withdraw_delayed':False}]}
        self.assertEqual(network_status(c,'deposit'),'PUBLIC_BLOCKED_ALL_NETWORKS')
        self.assertEqual(network_status(c,'withdraw'),'PUBLIC_ENABLED_SOME_NETWORK')
        c['chains'][0].pop('withdraw_delayed')
        self.assertEqual(network_status(c,'withdraw'),'UNKNOWN')

    def test_null_minimum_is_not_missing_precision(self):
        m=market();r=order_rules(m)
        self.assertEqual(D(r['gate']['lot']),D('.1'))
        self.assertEqual(r['gate']['min_quote'],'0')
        del m['gate_pair']['amount_precision']
        self.assertEqual(order_rules(m),{})

    def test_positive_stale_lead_rechecked_but_never_profit(self):
        self.assertTrue(needs_recheck({'quality':'STALE_RESPONSE','raw_top_gross_bps':{'okx>gate':'100'}}))
        row=summarize([market()],[observation('500','STALE_RESPONSE')])[0]
        self.assertIsNone(row['best_assumed_net'])
        self.assertEqual(row['research_signal'],'NO_VALID_ESTIMATE')

    def test_repeated_requires_enough_valid_coverage(self):
        ms=[market()]
        self.assertEqual(summarize(ms,[observation('1')])[0]['research_signal'],'ISOLATED_ASSUMED_MARGIN')
        ps=[observation('1') for _ in range(3)]+[observation('5','UNSYNCHRONIZED') for _ in range(3)]
        self.assertEqual(summarize(ms,ps)[0]['research_signal'],'ISOLATED_ASSUMED_MARGIN')
        repeated=summarize(ms,[observation('1'),observation('2'),observation('3')])[0]
        self.assertEqual(repeated['research_signal'],'REPEATED_ASSUMED_MARGIN')
        self.assertEqual(repeated['priority_median_net'],'2')

    def test_capital_over_budget_excluded_from_margin(self):
        row=summarize([market()],[observation('1000',within=False)])[0]
        self.assertIsNone(row['best_assumed_net'])
        self.assertEqual(row['directions'][0]['amounts'][0]['quality_valid_over_budget'],1)

    def test_gate_generation_does_not_replace_last_change(self):
        row=dict(received_mono=10,response={'bids':[['1','10']], 'asks':[['2','10']],
                                          'update':1000,'current':3000})
        book=view(row,'gate')
        self.assertEqual(book['ts'],1000)
        self.assertEqual(book['generation_ms'],3000)


if __name__=='__main__':unittest.main()
