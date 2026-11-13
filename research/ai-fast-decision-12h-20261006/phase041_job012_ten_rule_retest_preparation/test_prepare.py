import unittest,json,hashlib,importlib.util
from pathlib import Path
from closed_retest import require_closed
P=Path(__file__).resolve().parent
class Tests(unittest.TestCase):
 def test_prepare_no_source_access(self):
  with self.assertRaises(RuntimeError):require_closed({'mode':'PREPARE_ONLY','source':'NOT_READ'})
 def test_hash_missing_no_access(self):
  with self.assertRaises(ValueError):require_closed({'mode':'AUTHORIZED_CLOSED_TEN_RULE_RETEST','sourcehash_terminal_pending':None,'source':'NOT_READ'})
 def test_session_rootmissing_no_access(self):
  with self.assertRaises(ValueError):require_closed({'mode':'AUTHORIZED_CLOSED_TEN_RULE_RETEST','sourcehash_terminal_pending':'a'*64,'owner_session_exit_code':None,'root_terminal_receipt':None,'source':'NOT_READ'})
 def test_readonly_code_parity(self):
  for n,v in json.loads((P/'readonly_parity.json').read_text()).items():
   self.assertEqual((P/n).read_bytes(),Path(v['path']).read_bytes());self.assertEqual(hashlib.sha256((P/n).read_bytes()).hexdigest(),v['sha'])
  source=Path(json.loads((P/'protocol.json').read_text())['source'])
  for name in ['eight_fixed','pressure_fixed']:self.assertEqual((P/name/'instruments.json').read_bytes(),(source/'instruments.json').read_bytes())
 def test_child_eight_hardguard(self):
  s=importlib.util.spec_from_file_location('guard',P/'eight_fixed/prepare_guard.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
  with self.assertRaises(RuntimeError):m.require_authorized()
if __name__=='__main__':unittest.main()
