from pathlib import Path
import unittest,json
B=Path(__file__).resolve().parent
class T(unittest.TestCase):
 def test_unchanged_rules_and_controls(self):
  root=B.parent
  for n in ['evaluator.py','frozen_suite.py','frozen_execution_v12.py','controls.py','run_adapter.py']:self.assertEqual((B/n).read_bytes(),(root/'phase013_job005_replication_controls'/n).read_bytes())
  self.assertEqual((B/'frozen_cost_shock.py').read_bytes(),(root/'phase015_cost_capable_shock/cost_shock.py').read_bytes())
 def test_cut_evidence_not_fabricated_schema_OS(self):
  p=json.loads((B/'protocol.json').read_text());f=json.loads((B.parent/'phase015_cost_capable_shock/execution_freeze.json').read_text());self.assertEqual(p['cost_rule_OS_shared_ns'],f['frozen_OS_shared_ns']);self.assertIsNone(p['schema016_OS_cut']);self.assertEqual(p['actual_model_calls'],0)
if __name__=='__main__':unittest.main()
