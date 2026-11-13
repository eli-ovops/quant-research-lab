from pathlib import Path
import unittest,json
from raw_replication import require_run
from frozen_summary import pressure_summaries
B=Path(__file__).resolve().parent
class T(unittest.TestCase):
 def test_prepare_gate_and_rawonly_not_failure(self):
  p=json.loads((B/'protocol.json').read_text());self.assertRaises(RuntimeError,require_run,p);self.assertFalse(p['source_has_telemetry']);self.assertIsNone(p['source_raw_sha256'])
 def test_originalrules_summaries_and_specs(self):
  self.assertEqual((B/'frozen_pressure_rules.py').read_bytes(),(B.parent/'phase026_shock_pressure_transition_preparation/pressure_rules.py').read_bytes());self.assertEqual((B/'frozen_summary.py').read_bytes(),(B.parent/'phase027_closed_probe_analysis_preparation/analyze.py').read_bytes());self.assertEqual((B/'instruments.json').read_bytes(),(B.parent/'phase006_shared_capture/job009_after_pressure_freeze/instruments.json').read_bytes());aa,ss=pressure_summaries([],[],json.loads((B/'protocol.json').read_text())['assets']);self.assertEqual(len(aa),540);self.assertEqual(len(ss),1080);self.assertTrue(all(x['mean'] is None for x in aa+ss))
if __name__=='__main__':unittest.main()
