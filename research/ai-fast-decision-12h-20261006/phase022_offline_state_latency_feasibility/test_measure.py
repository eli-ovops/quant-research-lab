import unittest
from measure import timed
class T(unittest.TestCase):
 def test_actual_shared_ns_elapsed_matches_receipt(self):
  v,r=timed(lambda:sum(range(1000)));self.assertEqual(v,499500);self.assertGreaterEqual(r['elapsed_ns'],0);self.assertEqual(r['end_actual_OS_ns']-r['start_actual_OS_ns'],r['elapsed_ns']);self.assertEqual(r['elapsed_ns']/1e6,r['elapsed_ms'])
 def test_failure_keeps_error_and_elapsed(self):
  def fail():raise ValueError('SYNTHETIC_TEST_FAILURE')
  v,r=timed(fail);self.assertIsNone(v);self.assertEqual(r['status'],'FAIL');self.assertEqual(r['error']['type'],'ValueError');self.assertEqual(r['error']['message'],'SYNTHETIC_TEST_FAILURE');self.assertGreaterEqual(r['elapsed_ns'],0)
if __name__=='__main__':unittest.main()
