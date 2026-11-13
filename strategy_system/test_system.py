import unittest
from decimal import Decimal as D
import system as s

class SafetyAndCausality(unittest.TestCase):
    def fixture(self):
        H=s.engine.H; start=80*H; end=180*H
        raw={c:[] for c in ('BTC','ETH')}
        for c in raw:
            for i in range(180):
                p=D(100)+D(2*(i%40))
                raw[c].append([str(i*H),str(p),str(p+1),str(p-1),str(p), '100','100','100','1'])
        specs={c:dict(instType='SPOT',baseCcy=c,quoteCcy='USDT',lotSz='.0001',tickSz='.01',minSz='.0001',maxMktSz='100000') for c in raw}
        return dict(raw=raw,spec=specs,start=start,end=end,entry=24,exit=4,condition='baseline',mode='trend',synthetic=True)
    def test_independent_full_replay(self):
        for condition in s.POLICY['conditions']:
            case=self.fixture();case['condition']=condition
            a=s.engine.run(**case); self.assertGreater(len(a['fills']),0)
            s.verify(a,s.independent.replay(case),case)
    def test_future_prices_cannot_change_earlier_events(self):
        case=self.fixture(); before=s.engine.run(**case); cut=130*s.engine.H
        for rows in case['raw'].values():
            for r in rows:
                if int(r[0])>=cut:
                    for j in range(1,5):r[j]=str(D(r[j])*2)
        after=s.engine.run(**case)
        for key,time in [('fills','t'),('signals','signal')]:
            self.assertEqual([r for r in before[key] if r[time]<cut],[r for r in after[key] if r[time]<cut])
    def test_gap_fails_closed(self):
        case=self.fixture();case['raw']['ETH'].pop(90)
        with self.assertRaises(ValueError):s.engine.run(**case)
    def test_spot_cannot_impersonate_swap(self):
        case=self.fixture();case['spec']['ETH']['instType']='SWAP'
        with self.assertRaises(ValueError):s.engine.run(**case)
        self.assertFalse(s.futures_gate()['execution_allowed'])
    def test_costs_charged_both_sides(self):
        case=self.fixture();case['mode']='hold';a=s.engine.run(**case)
        self.assertTrue(all(f['base_fee']>0 if f['side']=='buy' else f['quote_fee']>0 for f in a['fills']))
        case['condition']='fee2';b=s.engine.run(**case)
        self.assertLess(b['metrics']['final_equity'],a['metrics']['final_equity'])
    def test_replay_detects_corruption(self):
        case=self.fixture();a=s.engine.run(**case);b=s.independent.replay(case)
        a['fills'][0]['cash_after']+=D(1)
        with self.assertRaises(AssertionError):s.verify(a,b,case)
if __name__=='__main__':unittest.main()
