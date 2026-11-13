import unittest
import control_audit as a
class ControlAudit(unittest.TestCase):
 def row(self,signal,gross):return dict(signal=signal,regime='down',month='2024-01',hour=0,gross=gross)
 def test_support_threshold_and_unknown(self):
  signal=self.row(True,.01);controls=[self.row(False,0) for _ in range(4)]
  r,s,u=a.compare(controls+[signal],[signal]);self.assertEqual(r['supported_n'],0);self.assertIsNone(r['excess_bps']);self.assertEqual(len(u),1)
  r,s,u=a.compare(controls+[self.row(False,0),signal],[signal]);self.assertEqual(r['supported_n'],1);self.assertGreater(r['excess_bps'],0)
 def test_same_cost_cancels_for_equal_gross(self):
  signal=self.row(True,.01);r,s,u=a.compare([self.row(False,.01) for _ in range(5)]+[signal],[signal])
  self.assertAlmostEqual(r['excess_bps'],0)
if __name__=='__main__':unittest.main()
