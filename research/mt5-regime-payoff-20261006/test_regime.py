import unittest
from regime_engine import Arm,Factors,gate,ARMS,ms,MIN,DAY
from frozen_frequency_engine import Account,M5
def ctx(t,bid=1.1005,ask=1.1006):return (t,bid,ask,t//M5*M5,t//DAY*DAY,1.1,(1.101,1.099))
GOOD={'complete':True,'ER':.5,'ATR':.001,'direction':1,'latest_start':0,'completed_at':0}
def virtual(t):return {'side':1,'entry':1.1011,'sl':1.0989,'tp':1.10396,'expiry':t//DAY*DAY+13*60*MIN,'placed':t}
class Tests(unittest.TestCase):
 def test_precise61_closed_and_TR_not_forming(self):
  t=ms('2026-08-03T03:00:00Z');m=Factors()
  for i,k in enumerate(range(t-60*M5,t,M5)):m.ingest(k,1.1+i*.00001,1.1001+i*.00001)
  _,s=m.ingest(t,1.101,1.1011);self.assertFalse(s['complete'])
  m=Factors()
  for i,k in enumerate(range(t-61*M5,t,M5)):m.ingest(k,1.1+i*.00001,1.1001+i*.00001)
  _,s1=m.ingest(t,1.101,1.1011);_,s2=m.ingest(t+1,9.,9.0001);self.assertTrue(s1['complete']);self.assertEqual(s1,s2);self.assertAlmostEqual(s1['ER'],1);self.assertLess(s1['ATR'],.00002);self.assertLess(s1['latest_start'],t);self.assertEqual(s1['completed_at'],t)
 def test_gate_threshold_direction_and_spread(self):
  self.assertTrue(gate(GOOD,1,1.1,1.10001)[0]);self.assertFalse(gate(GOOD,-1,1.1,1.10001)[0]);bad={**GOOD,'ER':.34};self.assertFalse(gate(bad,1,1.1,1.10001)[0]);self.assertFalse(gate(GOOD,1,1.1,1.1002)[0])
 def test_filter_reject_wait_and_trigger_recheck(self):
  t=ms('2026-08-03T04:00:00Z');a=Arm('B','base');a.step_factor(ctx(t),{**GOOD,'ER':.2});self.assertIsNone(a.pending);a.step_factor(ctx(t+1),GOOD);self.assertIsNone(a.pending);a.step_factor(ctx(t+M5),GOOD);self.assertIsNotNone(a.pending);a.step_factor(ctx(t+M5+1,1.1011,1.1012),{**GOOD,'ER':.2});self.assertEqual(a.day_open,0);self.assertIsNone(a.pending);self.assertEqual(a.cash,500)
 def test_actualentry5R_and_21_delayed_exit(self):
  t=ms('2026-08-03T04:00:00Z');a=Arm('C','base');a.day=t//DAY*DAY;a.day_start=500;a.pending=virtual(t);a.open(t,1.1011,1.1012);self.assertAlmostEqual(a.pos['tp'],1.1127);self.assertEqual(a.pos['expiry'],t//DAY*DAY+21*60*MIN)
  a.step_factor(ctx(t//DAY*DAY+21*60*MIN+7000,1.105,1.1051),GOOD);self.assertIsNone(a.pos);self.assertEqual(a.events[-1]['reason'],'TIME21');self.assertEqual(a.events[-1]['exit_delay_seconds'],7)
 def test_A_core_book_equivalent_and_diagnostic_not_income(self):
  t=ms('2026-08-03T04:00:00Z');old=Account(1,'base');a=Arm('A','base')
  for c in [ctx(t),ctx(t+1,1.1011,1.1012),ctx(t+2,1.10396,1.10406)]:old.step(c);a.step_factor(c,GOOD)
  self.assertEqual(old.cash,a.cash)
  for o,n in zip(old.events,a.events):
   for k,v in o.items():self.assertEqual(v,n[k])
  cash=a.cash;a.step_factor(ctx(t+10*60*MIN,1.12,1.1201),GOOD);self.assertEqual(a.cash,cash);self.assertGreater(a.diagnostics[0]['MFE_net'],a.diagnostics[0]['actual_net'])
 def test_TP_pressure_limit_still_holds_with_new_exit(self):
  t=ms('2026-08-03T04:00:00Z');a=Arm('C','stress');a.day=t//DAY*DAY;a.day_start=500;a.pending=virtual(t);a.open(t,1.1011,1.1012);tp=a.pos['tp'];a.close(t+1,tp+.00005,tp+.00006,'TP');self.assertIsNotNone(a.pos);a.close(t+2,tp+.0001,tp+.0002,'TP');self.assertIsNone(a.pos);self.assertEqual(a.events[-1]['price'],tp)
if __name__=='__main__':unittest.main()

