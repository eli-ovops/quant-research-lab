from pathlib import Path
import unittest,tempfile,gzip,json
from bounded_gzip import BoundedGzipWriter
from shared_clock import check_parent_child,causal_shared_gate
B=Path(__file__).resolve().parent
class T(unittest.TestCase):
 def test_hard_compressed_cap_and_valid_trailer(self):
  with tempfile.TemporaryDirectory(dir=B) as d:
   p=Path(d)/'new.gz';w=BoundedGzipWriter(p,256);kept=[]
   for i in range(100):
    data=(bytes(range(128))+str(i).encode()+b'\n')
    if not w.append(data):break
    kept.append(data)
   w.close();self.assertLessEqual(p.stat().st_size,256);self.assertEqual(gzip.decompress(p.read_bytes()),b''.join(kept))
 def test_logical_and_stage_budget_code(self):
  s=(B/'collector.py').read_text();p=json.loads((B/'protocol.json').read_text());self.assertIn('logicalmax=240000000',s);self.assertIn('logical+len(enc)>logicalmax',s);self.assertIn('230000000',s);self.assertEqual(p['budget']['logical_jsonl_byteguard'],240000000);self.assertEqual(p['budget']['WS_connections'],1);self.assertEqual(p['budget']['reconnects'],0)
 def test_existing_realproof_namespace_no_newchildren(self):
  p=json.loads((B/'clock_proof.json').read_text());self.assertEqual(len(p['checks']),2)
  for c in p['checks']:self.assertTrue(check_parent_child(c['parent_before'],c['child']['sample'],c['parent_after']))
  d=p['checks'][0]['parent_before']['clock_domain_id'];q={'clock_domain_id':d,'source_asof_shared_ns':10,'feature_completed_shared_ns':20};r={'clock_domain_id':d,'request_sent_shared_ns':30,'response_completed_shared_ns':40,'new_book_shared_ns':50,'now_shared_ns':60};self.assertTrue(causal_shared_gate(q,r,p)['accepted_clock_chain']);self.assertFalse(causal_shared_gate({},r,p)['accepted_clock_chain'])
if __name__=='__main__':unittest.main()

