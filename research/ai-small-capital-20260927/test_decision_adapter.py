import copy
import hashlib
import json
import unittest
from decision_adapter import verify,strict_json


class Adapter(unittest.TestCase):
    def setUp(self):
        rows=[[str(i*14400000),'100','101','99','100','1','1','100','1'] for i in range(43)]
        self.packet={'prepared_ms':43*14400000+1000,
                     'assets':{a:{'closed_4h_candles':rows} for a in ('BTC-USDT','ETH-USDT')}}
        self.raw=json.dumps(self.packet).encode();self.sha=hashlib.sha256(self.raw).hexdigest()
        self.receipt={'threadId':'thread','turnId':'turn','messageId':'message',
                      'startedAt':self.packet['prepared_ms']//1000+1,
                      'completedAt':self.packet['prepared_ms']//1000+2,
                      'text':json.dumps({'weights':{'BTC-USDT':.25,'ETH-USDT':0},
                       'rationale':'fixture','invalidation':'fixture','uncertainty':'fixture'})}
        self.runtime={'thread_id':'thread','records':[{'turn_id':'turn','model':'test','effort':'medium'}]}

    def call(self,receipt=None,runtime=None):
        return verify(self.raw,self.sha,receipt or self.receipt,runtime or self.runtime,
                      'thread','turn','test','medium')

    def test_valid_and_route_mismatch(self):
        self.assertEqual(self.call()['input_sha256'],self.sha)
        r=copy.deepcopy(self.runtime);r['records'][0]['model']='changed'
        with self.assertRaisesRegex(ValueError,'RUNTIME_CHANGED'):self.call(runtime=r)
        with self.assertRaisesRegex(ValueError,'WRONG_THREAD'):
            self.call(receipt={**self.receipt,'threadId':'other'})

    def test_hash_late_and_json(self):
        self.sha='tampered'
        with self.assertRaisesRegex(ValueError,'HASH'):self.call()
        self.sha=hashlib.sha256(self.raw).hexdigest()
        with self.assertRaisesRegex(ValueError,'TOO_LATE'):
            self.call(receipt={**self.receipt,'completedAt':self.receipt['completedAt']+1000})
        for text,error in [('{"a":1,"a":2}','DUPLICATE'),('{"a":NaN}','NONFINITE')]:
            with self.assertRaisesRegex(ValueError,error):strict_json(text)


if __name__=='__main__':unittest.main()
