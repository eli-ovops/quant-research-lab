import unittest
import cross_asset as a
class InputGate(unittest.TestCase):
 def rows(self):return [[str(i*a.s.H),'10','11','9','10','1','1','1','1'] for i in range(4)]
 def test_complete(self):self.assertEqual(len(a.gate(self.rows(),0,4*a.s.H)),4)
 def test_gap(self):
  with self.assertRaisesRegex(ValueError,'missing_hours'):a.gate(self.rows()[:-1],0,4*a.s.H)
 def test_zero_volume(self):
  r=self.rows();r[1][5]='0'
  with self.assertRaises(ValueError):a.gate(r,0,4*a.s.H)
 def test_duplicate_conflict(self):
  r=self.rows();x=r[0].copy();x[4]='10.5';r.append(x)
  with self.assertRaisesRegex(ValueError,'conflicting'):a.gate(r,0,4*a.s.H)
 def test_unclosed(self):
  r=self.rows();r[1][8]='0'
  with self.assertRaises(ValueError):a.gate(r,0,4*a.s.H)
if __name__=='__main__':unittest.main()
