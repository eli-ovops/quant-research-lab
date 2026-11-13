from pathlib import Path
import unittest,json,hashlib
from closed_retest import require_closed
import importlib.util
P=Path(__file__).resolve().parent
class Tests(unittest.TestCase):
 def test_prepare_gate_before_source_read(self):
  with self.assertRaises(RuntimeError):require_closed({'mode':'PREPARE_ONLY','source':'/NOT_READ'})
 def test_missing_hash_before_terminal_read(self):
  with self.assertRaises(ValueError):require_closed({'mode':'AUTHORIZED_CLOSED_TEN_RULE_RETEST','source':'/NOT_READ','sourcehash_terminal_pending':None})
 def test_eight_child_prepare_guard(self):
  spec=importlib.util.spec_from_file_location('guard',P/'eight_fixed/prepare_guard.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
  with self.assertRaises(RuntimeError):mod.require_authorized()
 def test_rule_spec_byte_parity(self):
  for relative,v in json.loads((P/'readonly_parity.json').read_text()).items():
   self.assertEqual(hashlib.sha256((P/relative).read_bytes()).hexdigest(),v['sha']);self.assertEqual((P/relative).read_bytes(),Path(v['source']).read_bytes())
  source=Path(json.loads((P/'protocol.json').read_text())['source'])
  self.assertEqual((P/'eight_fixed/instruments.json').read_bytes(),(source/'instruments.json').read_bytes());self.assertEqual((P/'pressure_fixed/instruments.json').read_bytes(),(source/'instruments.json').read_bytes())
if __name__=='__main__':unittest.main()
