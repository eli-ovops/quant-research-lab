from pathlib import Path
import json,unittest,hashlib
B=Path(__file__).resolve().parent
class T(unittest.TestCase):
 def test_frozen_rules_controls_no_parameter_change(self):
  old=B.parent/'phase017_job007_costshock_evaluation'
  for n in ['evaluator.py','frozen_suite.py','frozen_execution_v12.py','controls.py','run_adapter.py','frozen_cost_shock.py','evaluate_shock.py']:self.assertEqual((B/n).read_bytes(),(old/n).read_bytes())
 def test_nine_exact_units_and_unimplemented_new_model_schema(self):
  p=json.loads((B/'protocol.json').read_text());s={x['instId']:x for x in json.loads((B/'instruments.json').read_text())};self.assertEqual(len(s),9);self.assertEqual(s['PEPE-USDT-SWAP']['ctVal'],'10000000');self.assertEqual(s['WIF-USDT-SWAP']['ctVal'],'1');self.assertEqual(s['BONK-USDT-SWAP']['ctVal'],'100000');self.assertTrue(p['model_new3_registry'].startswith('NOT_VALIDATED'));self.assertEqual(hashlib.sha256(Path(p['new3_public_source']).read_bytes()).hexdigest(),p['new3_public_spec_sha256'])
 def test_terminal18_guard_and_no_result_while_live(self):
  p=json.loads((B/'protocol.json').read_text());self.assertIsNone(p['raw_logical_sha256']);self.assertTrue(p['source_hash_pending']);self.assertIn("2*len(p['assets'])",(B/'accept_terminal.py').read_text());self.assertFalse((B/'event_deltas.json').exists())
if __name__=='__main__':unittest.main()
