from pathlib import Path
import unittest,json,hashlib,copy,importlib.util
from closed_retest import require_closed,validate_root_receipt
P=Path(__file__).resolve().parent
class Tests(unittest.TestCase):
 def test_prepare_before_reads(self):
  with self.assertRaises(RuntimeError):require_closed({'mode':'PREPARE_ONLY','source':'NOT_READ'})
 def test_missing_owner_hash(self):
  for hashvalue,exitvalue in [(None,None),('a'*64,None),('a'*64,False)]:
   with self.assertRaises(ValueError):require_closed({'mode':'AUTHORIZED_CLOSED_TEN_RULE_RETEST','sourcehash_terminal_pending':hashvalue,'owner_session_exit_code':exitvalue,'root_terminal_receipt':None,'source':'NOT_READ'})
 def test_actual_root_schema(self):
  p=json.loads((P/'protocol.json').read_text());r=json.loads(Path(p['root_terminal_known_schema_example']).read_text());fixture=copy.deepcopy(r);fixture['owner_session']=75708
  self.assertTrue(validate_root_receipt({'expectedrun':r['source_run'],'sourcehash_terminal_pending':r['raw_logical_sha256']},fixture))
  for key,value in [('raw_logical_sha256','WRONG'),('source_run','WRONG'),('owner_session_exit_code',False),('owner_session',28459),('status','ACCEPTED_UNRELATED')]:
   x=copy.deepcopy(fixture);x[key]=value
   with self.assertRaises(ValueError):validate_root_receipt({'expectedrun':r['source_run'],'sourcehash_terminal_pending':r['raw_logical_sha256']},x)
 def test_module_spec_byteparity(self):
  for n,v in json.loads((P/'readonly_parity.json').read_text()).items():
   self.assertEqual((P/n).read_bytes(),Path(v['path']).read_bytes());self.assertEqual(hashlib.sha256((P/n).read_bytes()).hexdigest(),v['sha'])
  source=Path(json.loads((P/'protocol.json').read_text())['source'])
  for child in ['eight_fixed','pressure_fixed']:self.assertEqual((P/child/'instruments.json').read_bytes(),(source/'instruments.json').read_bytes())
 def test_childguard(self):
  s=importlib.util.spec_from_file_location('g',P/'eight_fixed/prepare_guard.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
  with self.assertRaises(RuntimeError):m.require_authorized()
if __name__=='__main__':unittest.main()
