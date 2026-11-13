import unittest,json,hashlib
from pathlib import Path
from source_metadata import terminal_metadata
from raw_replication import require_run
P=Path(__file__).resolve().parent
class Tests(unittest.TestCase):
 def fixture(self):
  i={'run_id':'SYNTHETIC_NOT_CAPTURE','pid':123,'clock_domain_id':'TEST','boot_identity':'TEST','start_utc':'2026-10-06T23:00:00+00:00','stop_at_utc':'2026-10-06T23:45:00+00:00'}
  return i,{**i,'status':'STOPPED','error':None,'stop_reason':'deadline_or_bytecap','finished_utc':'2026-10-06T23:45:00.100000+00:00'}
 def test_prepare_hard_reject(self):
  p=json.loads((P/'protocol.json').read_text())
  with self.assertRaises(RuntimeError):require_run(p)
 def test_actual_deadline(self):
  i,f=self.fixture();self.assertEqual(terminal_metadata(i,f,10,2700000000010)['status'],'DEADLINE_STOPPED_CONDITIONAL_CAPTURE')
 def test_loss_not_exit_success(self):
  i,f=self.fixture();f.update(error={'type':'WebSocketConnectionClosedException','text':'synthetic test loss'},finished_utc='2026-10-06T23:09:00+00:00');r=terminal_metadata(i,f,1,10);self.assertEqual(r['status'],'NETWORK_LOSS_SHORT_COHORT_NOT_COMPLETE');self.assertTrue(r['handler_exit0_not_capture_success'])
 def test_cap_and_unknown(self):
  i,f=self.fixture();f.update(finished_utc='2026-10-06T23:09:00+00:00',stop_reason='bytecap');self.assertEqual(terminal_metadata(i,f,1,10)['status'],'BYTECAP_EARLY_STOPPED_CONDITIONAL_CAPTURE');f['stop_reason']='unknown';self.assertIn('UNKNOWN',terminal_metadata(i,f,1,10)['status'])
 def test_wrong_run(self):
  i,f=self.fixture();f['run_id']='WRONG'
  with self.assertRaises(ValueError):terminal_metadata(i,f,1,10)
 def test_readonly_byte_parity(self):
  old=P.parent/'phase029_fresh_pressure_replication_preparation'
  for n in ['frozen_pressure_rules.py','frozen_execution_v12.py','frozen_summary.py','frozen_suite.py','frozen_cost_shock.py','instruments.json']:
   self.assertEqual((P/n).read_bytes(),(old/n).read_bytes())
  source=Path(json.loads((P/'protocol.json').read_text())['source']);self.assertEqual((P/'instruments.json').read_bytes(),(source/'instruments.json').read_bytes())
if __name__=='__main__':unittest.main()
