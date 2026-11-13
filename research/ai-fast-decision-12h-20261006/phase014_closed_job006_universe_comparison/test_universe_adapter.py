from pathlib import Path
import unittest,json,hashlib
from cohort_adapter import classify
B=Path(__file__).resolve().parent
class T(unittest.TestCase):
 def test_frozen_core_and_controls_byte_equal(self):
  old=B.parent/'phase013_job005_replication_controls'
  for n in ['evaluator.py','frozen_suite.py','frozen_execution_v12.py','controls.py','run_adapter.py']:self.assertEqual((B/n).read_bytes(),(old/n).read_bytes())
 def test_six_asset_units_match_registered_public_source(self):
  p=json.loads((B/'protocol.json').read_text());self.assertEqual(hashlib.sha256(Path(p['qualification_source']).read_bytes()).hexdigest(),p['qualification_sha256']);s={x['instId']:x for x in json.loads((B/'instruments.json').read_text())};self.assertEqual(len(s),6);self.assertEqual(s['DOGE-USDT-SWAP']['ctVal'],'1000');self.assertEqual(s['SUI-USDT-SWAP']['lotSz'],'1');self.assertEqual(s['XRP-USDT-SWAP']['ctVal'],'100');self.assertEqual(p['LEAD_only'],['ETH-USDT-SWAP','SOL-USDT-SWAP'])
 def test_actual_wall_and_shared_cuts_separate_no_backfill(self):
  cut={'phase013_control_cut_utc':'1970-01-01T00:00:01+00:00','phase014_cut_OS_shared_ns':20};a=classify(999999999,19,cut);b=classify(1000000000,20,cut);self.assertTrue(a['control13_cohort'].startswith('PRE_'));self.assertTrue(b['control13_cohort'].startswith('POST_'));self.assertTrue(a['phase014_cohort'].startswith('PRE_'));self.assertTrue(b['phase014_cohort'].startswith('POST_'))
if __name__=='__main__':unittest.main()
