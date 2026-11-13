import unittest,json
from pathlib import Path
from shared_clock import pair_delta,check_parent_child,in_deadline,causal_shared_gate
B=Path(__file__).resolve().parent
class T(unittest.TestCase):
 def test_pair_missing_domain_timeout(self):
  s={'os_shared_ns':1,'clock_domain':'d','boot_identity':'b','run_id':'r'};e={**s,'os_shared_ns':3}
  self.assertEqual(pair_delta(s,e),2)
  for bad in [{k:v for k,v in e.items() if k!='os_shared_ns'},{**e,'clock_domain':'x'}]:
   with self.assertRaises((ValueError,KeyError)):pair_delta(s,bad)
  with self.assertRaises(ValueError):pair_delta(s,e,1)
 def test_real_parent_child_receipt(self):
  p=json.loads((B/'clock_proof.json').read_text());self.assertEqual(len(p['checks']),2)
  for c in p['checks']:self.assertTrue(check_parent_child(c['parent_before'],c['child']['sample'],c['parent_after']))
 def test_explicit_domain_and_full_chain(self):
  p=json.loads((B/'clock_proof.json').read_text());d=p['checks'][0]['parent_before']['clock_domain_id'];req={'clock_domain_id':d,'source_asof_shared_ns':10,'feature_completed_shared_ns':20};run={'clock_domain_id':d,'request_sent_shared_ns':30,'response_completed_shared_ns':40,'new_book_shared_ns':50,'now_shared_ns':60};self.assertTrue(causal_shared_gate(req,run,p)['accepted_clock_chain'])
  for changes in [{'clock_domain_id':'legacy-processmono'},{'feature_completed_shared_ns':9},{'source_asof_shared_ns':None}]:
   q={**req,**changes};self.assertFalse(causal_shared_gate(q,run,p)['accepted_clock_chain'])
  for changes in [{'clock_domain_id':None},{'new_book_shared_ns':40},{'response_completed_shared_ns':1000000031,'new_book_shared_ns':1000000040,'now_shared_ns':1000000050}]:
   self.assertFalse(causal_shared_gate(req,{**run,**changes},p)['accepted_clock_chain'])
 def test_bounded_single_connection_code(self):
  p=json.loads((B/'protocol.json').read_text());self.assertEqual(p['WS']['reconnects'],0);self.assertEqual(p['WS']['total_deadline_seconds'],15);self.assertEqual(p['budget']['additional_keyless_WS_connections_max'],1);self.assertFalse(in_deadline(15,15))
if __name__=='__main__':unittest.main()

