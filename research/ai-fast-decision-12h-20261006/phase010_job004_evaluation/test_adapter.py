import unittest,json,hashlib
from pathlib import Path
import evaluator,run_adapter
B=Path(__file__).resolve().parent
class T(unittest.TestCase):
 def test_frozen_source_core_bytes(self):
  old=B.parent/'phase008_evaluator'
  for n in ['evaluator.py','frozen_suite.py','frozen_execution_v12.py','original_suite_freeze.json']:self.assertEqual((B/n).read_bytes(),(old/n).read_bytes())
 def test_binding_does_not_move_cut(self):
  o=json.loads((B/'original_suite_freeze.json').read_text());p=json.loads((B/'protocol.json').read_text());binding={**o,'capture_run_id':p['authorized_run']};r={'clock_domain_id':o['clock_domain_id'],'run_id':binding['capture_run_id'],'os_shared_ns':o['forward_cut_OS_shared_ns']};self.assertTrue(evaluator.suite.forward_eligible(r,binding));r['os_shared_ns']-=1;self.assertFalse(evaluator.suite.forward_eligible(r,binding))
 def test_empty_group_not_zero_profit(self):
  self.assertIsNone(run_adapter.stats([])['mean']);self.assertEqual(run_adapter.stats([])['n'],0)
if __name__=='__main__':unittest.main()
