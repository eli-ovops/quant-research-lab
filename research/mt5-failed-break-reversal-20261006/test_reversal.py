import unittest
from reversal_engine import Reversal,economics,M5,MIN,DAY,ms
T=ms('2026-08-03T03:06:00Z')
def setup(side=1,cost='base'):
 a=Reversal(cost);a.day=T//DAY*DAY;a.day_start=500.;a.pending={'side':side,'entry':1.1101 if side==1 else 1.0899,'sl':1.08,'tp':1.12,'rawhigh':1.11,'rawlow':1.09,'expiry':a.day+13*60*MIN,'placed':T-1};a.open(T,1.1101 if side==1 else 1.0897,1.1102 if side==1 else 1.0898);return a
class Test(unittest.TestCase):
 def test_forming_excluded(self):
  a=setup();k=a.watch['nextbar'];self.assertEqual(k,(T//M5+1)*M5);a.resolve(k,1.109,1.1091,{T//M5*M5:[1.109]*4},{});self.assertIsNotNone(a.watch);self.assertIsNone(a.pos)
 def test_original_down_ask_close(self):
  a=setup(-1);k=a.watch['nextbar'];a.resolve(k+M5,1.091,1.0911,{k:[1.091]*4},{k:[1.089]*4});self.assertIsNone(a.pos);self.assertIsNotNone(a.watch)
 def test_extrema_visible_and_risk(self):
  a=setup(cost='stress');k=a.watch['nextbar'];a.resolve(k+M5,1.109,1.1091,{k:[1.109]*4},{});self.assertIsNotNone(a.pos);self.assertEqual(a.pos['sl'],1.1103);self.assertEqual(a.pos['tp'],1.09);self.assertLessEqual(a.pos['planned_risk'],5);self.assertEqual(a.day_open,1);self.assertEqual(a.events[-1]['TP_basis'],'opposite_rawbox')
 def test_firstquote_cannot_choose(self):
  a=setup();k=a.watch['nextbar'];a.resolve(k+M5,1.1105,1.1106,{k:[1.109]*4},{});a.resolve(k+M5+1000,1.109,1.1091,{k:[1.109]*4},{});self.assertIsNone(a.pos);self.assertIsNone(a.watch);self.assertEqual(a.watch_counts['first_quote_outside'],1)
 def test_missing_expiry(self):
  for expiry in [False,True]:
   a=setup();k=a.watch['nextbar'];t=a.watch['expiry'] if expiry else k+M5;a.resolve(t,1.109,1.1091,{},{});self.assertEqual(a.watch_counts['13_expiry' if expiry else 'missing_bar'],1);self.assertEqual(a.cash,500)
 def test_RR_cost_gate(self):
  a=economics(1,1.11,1.09,1.111,1.108,1.105,1.1051,0);b=economics(1,1.11,1.09,1.111,1.108,1.105,1.1051,.0001);self.assertLess(b['netRR'],a['netRR']);self.assertLess(a['netRR'],3)
if __name__=='__main__':unittest.main()

