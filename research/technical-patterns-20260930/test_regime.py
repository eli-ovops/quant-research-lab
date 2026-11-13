import unittest
import regime as r
class Checks(unittest.TestCase):
 def test_past_only(self):
  bars=[{'c':100+i} for i in range(40)]
  self.assertEqual(r.regime(bars,30),('up',1.0))
  bars[30]['c']=-99999
  self.assertEqual(r.regime(bars,30),('up',1.0))
 def test_flat_range(self):
  self.assertEqual(r.regime([{'c':100} for _ in range(40)],30),('range',0))
 def test_down(self):
  self.assertEqual(r.regime([{'c':100-i} for i in range(40)],30),('down',1.0))
 def test_overlap(self):
  rows=[{'t':i,'exit_t':i+3} for i in range(6)]
  self.assertEqual([x['t'] for x in r.nonoverlap(rows)],[0,3])
 def test_empty_gate(self):
  v,e=r.evaluate([],'range')
  self.assertFalse(v['screen_pass']);self.assertIsNone(v['mean_bps'])
if __name__=='__main__':unittest.main()
