import copy
import unittest
from decimal import Decimal as D
from paper_baselines import initial_baselines,step_baselines
from test_paper_ledger import BOOK,SPEC


class Baselines(unittest.TestCase):
    def test_once_only_entry_and_costed_exit_value(self):
        d={'committed_ms':1000,'input_sha256':'fixture','weights':{'BTC-USDT':0,'ETH-USDT':0},'rationale':'fixture'}
        books={a:BOOK for a in d['weights']};specs={a:SPEC for a in d['weights']}
        original=initial_baselines()
        s,v=step_baselines(original,d,books,specs,2000)
        self.assertFalse(original['entry_attempted'])
        self.assertEqual(D(v['cash']['liquidatable_cash']),150)
        self.assertLess(D(v['buy_hold']['liquidatable_cash']),150)
        self.assertEqual(len(s['buy_hold']['fills']),2)
        later={a:{'ts':4000,'asks':[['201','10']],'bids':[['200','10']]} for a in books}
        before=copy.deepcopy(s)
        s2,v2=step_baselines(s,{**d,'committed_ms':3000},later,specs,4000)
        self.assertEqual(s2,before)
        self.assertGreater(D(v2['buy_hold']['liquidatable_cash']),150)

    def test_cost_scenarios_do_not_share_state(self):
        d={'committed_ms':1000,'input_sha256':'fixture','weights':{'BTC-USDT':0,'ETH-USDT':0},'rationale':'fixture'}
        args=(d,{a:BOOK for a in d['weights']},{a:SPEC for a in d['weights']},2000)
        base=initial_baselines()
        s,v=step_baselines(base,*args)
        stress,vs=step_baselines(base,*args,fee_bps=20,buffer_bps=20)
        self.assertEqual(base,initial_baselines())
        self.assertLess(D(vs['buy_hold']['liquidatable_cash']),D(v['buy_hold']['liquidatable_cash']))


if __name__=='__main__':unittest.main()
