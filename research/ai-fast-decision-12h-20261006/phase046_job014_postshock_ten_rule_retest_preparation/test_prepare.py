from pathlib import Path
import unittest,json,hashlib
from closed_retest import require_closed,validate_root_receipt
P=Path(__file__).resolve().parent
class Tests(unittest.TestCase):
 def test_prepare_no_read(self):
  with self.assertRaises(RuntimeError):require_closed({'mode':'PREPARE_ONLY','source':'NOT_READ'})
 def test_owner_hash_missing(self):
  with self.assertRaises(ValueError):require_closed({'mode':'AUTHORIZED_CLOSED_TEN_RULE_RETEST','sourcehash_terminal_pending':'a'*64,'owner_session_exit_code':None,'root_terminal_receipt':None})
 def test_real_schema_expectedowner(self):
  p=json.loads((P/'protocol.json').read_text());r=json.loads(Path(p['root_terminal_known_schema_example']).read_text());r['owner_session']=96153;self.assertTrue(validate_root_receipt({'expectedrun':r['source_run'],'sourcehash_terminal_pending':r['raw_logical_sha256']},r));r['owner_session']=75708
  with self.assertRaises(ValueError):validate_root_receipt({'expectedrun':r['source_run'],'sourcehash_terminal_pending':r['raw_logical_sha256']},r)
 def test_sameverifiedmodules_andspecs(self):
  for n,v in json.loads((P/'readonly_parity.json').read_text()).items():self.assertEqual((P/n).read_bytes(),Path(v['source']).read_bytes())
  source=Path(json.loads((P/'protocol.json').read_text())['source'])
  for child in ['eight_fixed','pressure_fixed']:self.assertEqual((P/child/'instruments.json').read_bytes(),(source/'instruments.json').read_bytes())
if __name__=='__main__':unittest.main()
