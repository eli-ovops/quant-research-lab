import unittest
from confirmation_engine import Confirm,M5,MIN,DAY,ms
T=ms('2026-08-03T03:06:00Z')
def setup(side=1,cost='base'):
 a=Confirm(cost);a.day=T//DAY*DAY;a.day_start=500;a.pending={'side':side,'entry':1.1,'sl':1.099 if side==1 else 1.101,'tp':1.102,'expiry':a.day+13*60*MIN,'placed':T-1000};a.open(T,1.1001,1.1002);return a
def bars(a,price):return {k:[price]*4 for k in a.watch['starts']}
class Test(unittest.TestCase):
 def test_forming_excluded(self):
  a=setup();self.assertEqual(a.watch['starts'][0],(T//M5+1)*M5);a.resolve(a.watch['starts'][0],1.1002,1.1003,{T//M5*M5:[1.2]*4},{});self.assertIsNone(a.pos);self.assertIsNotNone(a.watch)
 def test_short_ask(self):
  a=setup(-1);bb=bars(a,1.0998);ab=bars(a,1.1001);a.resolve(a.watch['starts'][0]+M5,1.0998,1.0999,bb,ab);self.assertIsNone(a.watch);self.assertEqual(a.confirm_counts['close_back_inside'],1)
 def test_missing_and_failed(self):
  for book,reason in [({},'missing_bar'),(1.0999,'close_back_inside')]:
   a=setup();bb=bars(a,book) if isinstance(book,float) else book;a.resolve(a.watch['starts'][0]+M5,1.1002,1.1003,bb,{});self.assertEqual(a.confirm_counts[reason],1)
 def test_firstquote_no_retry(self):
  a=setup();bb=bars(a,1.1002);t=a.watch['decision_boundary'];a.resolve(t,1.0998,1.0999,bb,{});a.resolve(t+1000,1.1002,1.1003,bb,{});self.assertIsNone(a.pos);self.assertIsNone(a.watch)
 def test_expiry(self):
  a=setup();a.resolve(a.watch['expiry'],1.1002,1.1003,bars(a,1.1002),{});self.assertEqual(a.confirm_counts['13_expiry'],1);self.assertEqual(a.cash,500)
 def test_risk_actualentry5R(self):
  a=setup(cost='stress');bb=bars(a,1.1002);t=a.watch['decision_boundary'];a.resolve(t,1.1003,1.1004,bb,{});self.assertIsNotNone(a.pos);p=a.pos;self.assertLessEqual(p['planned_risk'],5);self.assertAlmostEqual(p['tp'],p['entry']+5*(p['entry']-p['sl']),places=5);self.assertEqual(a.day_open,1);self.assertTrue(900<=((t-T)/1000)<=1200)
if __name__=='__main__':unittest.main()

