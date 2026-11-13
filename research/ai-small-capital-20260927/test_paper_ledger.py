import copy
import tempfile
import unittest
import json
import time
from pathlib import Path
from decimal import Decimal as D
from paper_ledger import initial, fill, liquidation_value, executable_liquidation, commit_decision, rebalance, settle

BOOK={'ts':2000,'asks':[['101','1'],['102','10']],'bids':[['100','10']]}
SPEC={'lotSz':'.01','minSz':'.01'}

class Accounting(unittest.TestCase):
    def test_depth_and_quote_fee(self):
        s=fill(initial(),{'asset':'BTC-USDT','side':'BUY','quantity':'1.2'},BOOK,SPEC,1000,2000,10,0)
        self.assertEqual(D(s['cash']),D('28.4786'))
        self.assertEqual(D(s['positions']['BTC-USDT']),D('1.2'))

    def test_base_fee_and_round_trip(self):
        s=fill(initial(),{'asset':'BTC-USDT','side':'BUY','quantity':'1'},BOOK,SPEC,1000,2000,100,0,'base')
        self.assertEqual(D(s['positions']['BTC-USDT']),D('.99'))
        s=fill(s,{'asset':'BTC-USDT','side':'SELL','quantity':'.99'},BOOK,SPEC,1000,2000,100,0)
        self.assertEqual(D(s['cash']),D('147.01'))
        self.assertEqual(D(s['positions']['BTC-USDT']),0)

    def test_rejects_without_mutation(self):
        s=initial(); before=copy.deepcopy(s)
        for side,q,error in [('BUY','2','INSUFFICIENT_CASH'),('SELL','1','INSUFFICIENT_POSITION'),('BUY','12','INSUFFICIENT_DEPTH'),('BUY','.001','INVALID_SIZE')]:
            with self.assertRaisesRegex(ValueError,error):
                fill(s,{'asset':'BTC-USDT','side':side,'quantity':q},BOOK,SPEC,1000,2000)
            self.assertEqual(s,before)

    def test_future_stale_predecision(self):
        for ts in [1000,10000,-1]:
            with self.assertRaisesRegex(ValueError,'STALE'):
                fill(initial(),{'asset':'BTC-USDT','side':'BUY','quantity':'.1'},{**BOOK,'ts':ts},SPEC,1000,9000)

    def test_liquidation_uses_bid_and_cost(self):
        s=initial();s['cash']='0';s['positions']['BTC-USDT']='1'
        self.assertEqual(liquidation_value(s,{'BTC-USDT':BOOK},1000,2000,100,100),D('98.01'))
        s['positions']['BTC-USDT']='11'
        with self.assertRaisesRegex(ValueError,'DEPTH'):
            liquidation_value(s,{'BTC-USDT':BOOK},1000,2000)

    def test_duplicate_decision_is_not_overwritten(self):
        d={'slot':'20260927T080000Z','weights':{'BTC-USDT':0,'ETH-USDT':0},'input_sha256':'fixture','rationale':'fixture only'}
        with tempfile.TemporaryDirectory() as root:
            p=commit_decision(root,d); original=p.read_bytes()
            with self.assertRaises(FileExistsError):commit_decision(root,d)
            self.assertEqual(p.read_bytes(),original)

    def test_invalid_weights(self):
        d={'slot':'1','weights':{'BTC-USDT':'.5','ETH-USDT':'.5'},'input_sha256':'fixture','rationale':'fixture'}
        with self.assertRaisesRegex(ValueError,'EXPOSURE'):
            rebalance(initial(),d,{}, {},2000)

    def test_cash_decision_and_target_attempts(self):
        d={'committed_ms':1000,'weights':{'BTC-USDT':0,'ETH-USDT':0},'input_sha256':'fixture','rationale':'fixture'}
        args=({a:BOOK for a in d['weights']},{a:SPEC for a in d['weights']},2000)
        self.assertEqual(rebalance(initial(),d,*args),initial())
        d['weights']['BTC-USDT']='.25'
        s=rebalance(initial(),d,*args)
        self.assertGreater(D(s['positions']['BTC-USDT']),0)
        self.assertEqual(s['attempts'][0]['result'],'PAPER_FILLED')

    def test_persisted_settlement_idempotency_and_integrity(self):
        d={'slot':'20260927T080000Z','weights':{'BTC-USDT':'.25','ETH-USDT':0},'input_sha256':'fixture','rationale':'fixture'}
        with tempfile.TemporaryDirectory() as root:
            path=commit_decision(root,d)
            time.sleep(.005)
            books={a:{**BOOK,'ts':time.time_ns()//1000000} for a in d['weights']}
            specs={a:SPEC for a in d['weights']}
            s=settle(root,path,books,specs)
            journal=Path(root)/'journal.jsonl'
            original=journal.read_bytes()
            self.assertEqual(json.loads(original)['state'],s)
            with self.assertRaisesRegex(ValueError,'ALREADY_SETTLED'):settle(root,path,books,specs)
            self.assertEqual(journal.read_bytes(),original)
            with self.assertRaisesRegex(ValueError,'CONFIG_CHANGED'):settle(root,path,books,specs,20)
            event=json.loads(original);event['state']['cash']='999'
            journal.write_text(json.dumps(event)+'\n')
            with self.assertRaisesRegex(ValueError,'JOURNAL_HASH'):settle(root,path,books,specs)

    def test_tampered_decision_rejected(self):
        d={'slot':'20260927T080000Z','weights':{'BTC-USDT':0,'ETH-USDT':0},'input_sha256':'fixture','rationale':'fixture'}
        with tempfile.TemporaryDirectory() as root:
            path=commit_decision(root,d);e=json.loads(path.read_text());e['decision']['weights']['BTC-USDT']='.5';path.write_text(json.dumps(e))
            with self.assertRaisesRegex(ValueError,'DECISION_HASH'):settle(root,path,{}, {})

    def test_full_risk_target_is_resized_after_cost(self):
        d={'committed_ms':1000,'weights':{'BTC-USDT':'.5','ETH-USDT':0},'input_sha256':'fixture','rationale':'fixture'}
        s=rebalance(initial(),d,{a:BOOK for a in d['weights']},{a:SPEC for a in d['weights']},2000)
        q=D(s['positions']['BTC-USDT']);mid=D('100.5')
        self.assertGreater(q,0)
        self.assertLessEqual(q*mid,D(s['cash']))
        next_size=q+D('.01')
        next_state=fill(initial(),{'asset':'BTC-USDT','side':'BUY','quantity':str(next_size)},BOOK,SPEC,1000,2000)
        self.assertGreater(next_size*mid,D(next_state['cash']))

    def test_dust_is_not_counted_as_cash(self):
        s=initial();s['cash']='10';s['positions']['BTC-USDT']='.015'
        specs={a:SPEC for a in s['positions']}
        v=executable_liquidation(s,{'BTC-USDT':BOOK},specs,1000,2000,0,0)
        self.assertEqual(D(v['liquidatable_cash']),D('11'))
        self.assertEqual(D(v['unsellable_dust']['BTC-USDT']),D('.005'))
        specs['BTC-USDT']={**SPEC,'minSz':'.02'}
        v=executable_liquidation(s,{},specs,1000,2000,0,0)
        self.assertEqual(D(v['liquidatable_cash']),10)

    def test_preexisting_old_decision_cannot_settle_later(self):
        d={'slot':'1','weights':{'BTC-USDT':0,'ETH-USDT':0},'input_sha256':'fixture','rationale':'fixture'}
        with tempfile.TemporaryDirectory() as root:
            old=commit_decision(root,d);time.sleep(.003)
            new=commit_decision(root,{**d,'slot':'2'});time.sleep(.003)
            books={a:{**BOOK,'ts':time.time_ns()//1000000} for a in d['weights']}
            specs={a:SPEC for a in d['weights']}
            settle(root,new,books,specs)
            with self.assertRaisesRegex(ValueError,'OUT_OF_ORDER'):settle(root,old,books,specs)

if __name__=='__main__':unittest.main()
