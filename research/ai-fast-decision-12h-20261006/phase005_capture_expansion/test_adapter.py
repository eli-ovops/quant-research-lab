import unittest,json,hashlib
from pathlib import Path
from run_adapter import cohort,utc_ns,dedup_records
B=Path(__file__).resolve().parent
class T(unittest.TestCase):
 def test_strict_cohort_cut(self):
  cut=utc_ns('2026-10-06T15:41:45.496551Z');self.assertEqual(cohort(20000,cut,'unused'),'dev_prefix');self.assertEqual(cohort(20001,cut-1,cut),'prefreeze_remainder');self.assertEqual(cohort(20001,cut,cut),'postfreeze_new')
 def test_core_byte_same(self):
  p=json.loads((B/'protocol.json').read_text());self.assertEqual(hashlib.sha256((B/'frozen_core.py').read_bytes()).hexdigest(),p['core_sha256']);self.assertEqual((B/'frozen_core.py').read_bytes(),Path(p['core_origin']).read_bytes())
 def test_trade_exactrepeat_not_count_multiply(self):
  row={'channel':'trades','instId':'BTC-USDT-SWAP','raw':json.dumps({'data':[{'tradeId':'1','source':'0','sz':'2','px':'100','side':'buy','ts':'10','count':'3'}]})};seen={};a,d,c=dedup_records(row,seen);self.assertEqual(json.loads(a['raw'])['data'][0]['sz'],'2');a,d,c=dedup_records(row,seen);self.assertEqual(d,1);self.assertEqual(json.loads(a['raw'])['data'],[]);o=json.loads(row['raw']);o['data'][0]['sz']='4';a,d,c=dedup_records({**row,'raw':json.dumps(o)},seen);self.assertEqual(c,1)
if __name__=='__main__':unittest.main()

