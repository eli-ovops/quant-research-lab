import copy
import json
import tempfile
import unittest
from pathlib import Path
import integration as m

class Tests(unittest.TestCase):
    def setUp(self):
        self.rows=[[str(i*m.DAY),'100','102','99','101','5','0','0','1'] for i in range(65)]
        self.packet=json.dumps({'instrument':'ETH-USDT-SWAP','prepared_ms':1000}).encode()
        self.receipt={'input_sha256':m.digest(self.packet),'instrument':'ETH-USDT-SWAP','started_ms':1001,'completed_ms':1100,'source_kind':'test_fixture','final_state':{'final_rating':'Sell','final_trade_decision':'Rating: Sell\nReduce existing exposure.'}}
    def test_confirmed_and_contiguous(self):
        rows=self.rows+[[str(65*m.DAY),'1','1','1','1','1','0','0','0']]
        self.assertEqual(len(m.closed_rows({'data':rows},65*m.DAY+1)),65)
    def test_gap(self):
        with self.assertRaisesRegex(ValueError,'GAP'):m.closed_rows({'data':self.rows[:20]+self.rows[21:]},65*m.DAY+1)
    def test_future_and_stale(self):
        for t in [64*m.DAY,67*m.DAY]:
            with self.assertRaisesRegex(ValueError,'FUTURE_OR_STALE'):m.closed_rows({'data':self.rows},t)
    def test_invalid_price(self):
        self.rows[-1][2]='NaN'
        with self.assertRaisesRegex(ValueError,'NONFINITE'):m.closed_rows({'data':self.rows},65*m.DAY+1)
    def test_sell_is_not_short(self):
        r=m.accept(self.packet,self.receipt,1200)
        self.assertEqual(r['research_bias'],'BEARISH');self.assertIsNone(r['trade_action']);self.assertFalse(r['paper_execution_allowed'])
        self.assertIn('TEST_FIXTURE_NOT_MODEL_OUTPUT',r['blockers'])
    def test_review_is_not_hold(self):
        self.receipt['final_state']={'final_trade_decision':'unclear'}
        self.assertEqual(m.accept(self.packet,self.receipt,1200)['original_rating'],'REVIEW')
    def test_conflict(self):
        self.receipt['final_state']['final_rating']='Buy'
        with self.assertRaisesRegex(ValueError,'CONFLICT'):m.accept(self.packet,self.receipt,1200)
    def test_hash_and_clock(self):
        r=copy.deepcopy(self.receipt);r['input_sha256']='bad'
        with self.assertRaisesRegex(ValueError,'HASH'):m.accept(self.packet,r,1200)
        r=copy.deepcopy(self.receipt);r['started_ms']=999
        with self.assertRaisesRegex(ValueError,'TIME'):m.accept(self.packet,r,1200)
        with self.assertRaisesRegex(ValueError,'STALE'):m.accept(self.packet,self.receipt,900000)
    def test_claimed_receipt_never_authorizes(self):
        self.receipt['source_kind']='provider_output';self.receipt['provider_receipt']={'request_id':'claimed','model':'claimed','provider':'claimed'}
        r=m.accept(self.packet,self.receipt,1200);self.assertFalse(r['paper_execution_allowed']);self.assertEqual(r['model_receipt_status'],'CLAIMED_PENDING_VERIFICATION')
    def test_no_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'one.json';m.write_new(p,{'a':1})
            with self.assertRaises(FileExistsError):m.write_new(p,{'a':2})
    def test_duplicate_keys(self):
        with self.assertRaisesRegex(ValueError,'DUPLICATE'):m.strict('{"a":1,"a":2}')

if __name__=='__main__':unittest.main()
