import unittest
from copy import deepcopy
from engine import run, HOUR, FOUR

COINS = ['BTC','ETH','SOL','XRP','DOGE','ADA','LINK','LTC']
BASE = dict(fee=.001, slip=.0005, delay_hours=0)


def synthetic(bars=170, change=None):
    rows=[]
    for i in range(bars*4):
        b=i//4
        close = 100 + b*.2 if change is None else change(b)
        rows.append([str(i*HOUR),str(close),str(close+.02),str(close-.02),str(close),'100','100','10000','1'])
    return {c:deepcopy(rows) for c in COINS}


class EngineTests(unittest.TestCase):
    def test_double_cost_and_cash_conservation(self):
        data=synthetic(change=lambda _:100)
        result=run(data,{},dict(family='hold'),BASE,126*FOUR,132*FOUR)
        cash=2000.0
        quantities={c:0.0 for c in COINS}
        for f in result['fills']:
            cash+=f['cash_delta']
            quantities[f['coin']]+=f['asset_delta']
            self.assertAlmostEqual(cash,f['cash_after'],places=8)
            self.assertAlmostEqual(quantities[f['coin']],f['asset_after'],places=8)
            self.assertGreaterEqual(cash,0)
            self.assertGreaterEqual(quantities[f['coin']],-1e-10)
        expected=200 + 1800/100.05*(1-.001)*99.95*(1-.001)
        self.assertAlmostEqual(expected,result['metrics']['final_equity'],places=8)
        self.assertEqual(result['metrics']['closed_trades'],8)
        buys=[f for f in result['fills'] if f['side']=='buy']
        self.assertAlmostEqual(sum(-f['cash_delta'] for f in buys),1800)

    def test_future_perturbation_does_not_change_history(self):
        original=synthetic(change=lambda b: 100 + b*.4 if b<145 else 150-(b-145))
        altered=deepcopy(original)
        boundary=145*FOUR
        for rows in altered.values():
            for r in rows:
                if int(r[0])>=boundary:
                    for j in range(1,5): r[j]=str(float(r[j])*30)
        candidate=dict(family='trend',entry_bars=12,exit_bars=3)
        a=run(original,{},candidate,BASE,126*FOUR,165*FOUR)
        b=run(altered,{},candidate,BASE,126*FOUR,165*FOUR)
        self.assertEqual([s for s in a['signals'] if s['timestamp']<=boundary],
                         [s for s in b['signals'] if s['timestamp']<=boundary])
        self.assertEqual([f for f in a['fills'] if f['timestamp']<boundary],
                         [f for f in b['fills'] if f['timestamp']<boundary])

    def test_execution_delay(self):
        data=synthetic()
        c=dict(family='hold')
        result=run(data,{},c,dict(BASE,delay_hours=1),127*FOUR,132*FOUR)
        signal=result['signals'][0]
        buys=[f for f in result['fills'] if f['side']=='buy']
        self.assertEqual(buys[0]['timestamp'],signal['timestamp']+HOUR)
        self.assertEqual(buys[0]['reference_price'],float(data['BTC'][buys[0]['timestamp']//HOUR][1]))

    def test_no_hourly_rebalance_or_overlapping_entries(self):
        data=synthetic()
        result=run(data,{},dict(family='trend',entry_bars=12,exit_bars=3),BASE,127*FOUR,165*FOUR)
        buys=[f for f in result['fills'] if f['side']=='buy' and f['status']=='filled']
        self.assertEqual(len(buys),8)
        self.assertLessEqual(sum(-f['cash_delta'] for f in buys),1800+1e-8)
        for f in buys:
            self.assertLessEqual(-f['cash_delta'],f['portfolio_equity_at_order']*.1125+1e-8)

    def test_rejected_orders_have_no_virtual_holdings(self):
        data=synthetic()
        specs={c:dict(lotSz='1',minSz='1000000',tickSz='.01') for c in COINS}
        result=run(data,specs,dict(family='hold'),BASE,127*FOUR,132*FOUR)
        self.assertEqual(result['metrics']['closed_trades'],0)
        self.assertEqual(result['metrics']['final_equity'],2000)
        self.assertTrue(all(f['status']=='rejected' for f in result['fills']))
        self.assertTrue(all(q==0 for q in result['equity'][-1]['positions'].values()))

    def test_rotation_cap_and_invalid_features(self):
        data=synthetic()
        c=dict(family='rotation',lookback_bars=126,top_k=2,rebalance_bars=1)
        data['BTC'][20*4][5]='0'
        result=run(data,{},c,BASE,127*FOUR,135*FOUR)
        self.assertTrue(any(s['reason']=='invalid_feature_input' for s in result['signals']))
        self.assertFalse(any(f['side']=='buy' for f in result['fills']))
        valid=run(synthetic(),{},c,BASE,127*FOUR,135*FOUR)
        buys=[f for f in valid['fills'] if f['side']=='buy']
        self.assertEqual(len(buys),2)
        self.assertTrue(all(-f['cash_delta']<=.25*f['portfolio_equity_at_order']+1e-8 for f in buys))

    def test_reversion_hold_and_no_same_bar_reentry(self):
        def close(b):
            if b < 106: return 110
            if b < 127: return 110-(b-106)*1.5 if b<126 else 65
            return 85
        data=synthetic(change=close)
        candidate=dict(family='reversion',band_bars=20,z=1.5,hold_bars=6)
        result=run(data,{},candidate,dict(BASE,delay_hours=1),126*FOUR,145*FOUR)
        buys=[f for f in result['fills'] if f['side']=='buy' and f['status']=='filled']
        sells=[f for f in result['fills'] if f['side']=='sell' and f['status']=='filled']
        self.assertEqual(len(buys),8)
        self.assertEqual(len(sells),8)
        self.assertEqual(sells[0]['timestamp']-buys[0]['timestamp'],6*FOUR)
        self.assertEqual(result['metrics']['closed_trades'],8)

    def test_async_entries_preserve_cash_reserve(self):
        data=synthetic()
        for c in COINS[4:]:
            data[c]=synthetic(change=lambda b: 200-b*.5 if b<140 else 130+(b-140)*4)[c]
        result=run(data,{},dict(family='trend',entry_bars=12,exit_bars=3),BASE,127*FOUR,160*FOUR)
        buys=[f for f in result['fills'] if f['side']=='buy' and f['status']=='filled']
        self.assertEqual(len(buys),8)
        last_by_time={f['timestamp']:f for f in buys}
        self.assertGreater(len(last_by_time),1)
        self.assertTrue(all(f['cash_after']>=.1*f['portfolio_equity_at_order']-1e-8
                            for f in last_by_time.values()))

    def test_decimal_slippage_at_exact_tick_boundary(self):
        # Binary float 70 * .999 is 69.92999999999999; sell tick must be
        # 69.93, without an extra adverse tick caused by float precision.
        import replay
        for reference,tick,expected_sell in [(70,'.01',69.93),(.09,'.00001',.08991)]:
            with self.subTest(reference=reference):
                data=synthetic(change=lambda _:reference)
                specs={c:dict(tickSz=tick,lotSz='.001',minSz='.001') for c in COINS}
                condition=dict(fee=.002,slip=.001,delay_hours=0)
                candidate=dict(family='hold')
                start,end=127*FOUR,132*FOUR
                result=run(data,specs,candidate,condition,start,end)
                sells=[f for f in result['fills'] if f['side']=='sell' and f['status']=='filled']
                self.assertTrue(sells)
                self.assertTrue(all(f['price']==expected_sell for f in sells))
                self.assertEqual(replay.verify(data,specs,candidate,condition,start,end,result)['status'],'PASS')

    def test_only_completed_4h_bar(self):
        data=synthetic()
        # Mutating hours at/after the signal boundary cannot affect that signal.
        altered=deepcopy(data)
        for rows in altered.values():
            rows[127*4][4]='1'
        candidate=dict(family='trend',entry_bars=12,exit_bars=3)
        a=run(data,{},candidate,BASE,127*FOUR,128*FOUR)
        b=run(altered,{},candidate,BASE,127*FOUR,128*FOUR)
        self.assertEqual(a['signals'][0],b['signals'][0])


if __name__=='__main__':
    unittest.main()
