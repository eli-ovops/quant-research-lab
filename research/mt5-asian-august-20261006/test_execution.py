import unittest,json
from august_engine import Execution,norm
from frozen_prior_engine import ms,MIN
def pending(side=1,lot=.1):return {'side':side,'lot':lot,'entry':1.1,'sl':1.099 if side==1 else 1.101,'tp':1.101 if side==1 else 1.099}
class Tests(unittest.TestCase):
 def test_grid_float_noise_and_conservative_rounding(self):
  self.assertEqual(norm(1.23456-1e-16,'floor'),1.23456);self.assertEqual(norm(1.23456+1e-16,'ceil'),1.23456)
  self.assertEqual(norm(1.234567,'floor'),1.23456);self.assertEqual(norm(1.234567,'ceil'),1.23457)
 def test_bidask_fees_and_pressure_stop_gap(self):
  t=ms('2026-08-03T04:00:00Z');m=Execution('stress');m.pending=pending();m.open(t,1.1,1.1002);self.assertEqual(m.pos['entry'],1.1003)
  m.close(t+MIN,1.097,1.0972,'SL_GAP_ACTUAL_BID');self.assertAlmostEqual(m.cash,465.3);self.assertEqual(m.events[-1]['price'],1.0969);self.assertAlmostEqual(sum(x.get('fee',0) for x in m.events),.7)
 def test_pressure_TP_waits_and_never_crosses_limit(self):
  t=ms('2026-08-03T04:00:00Z');m=Execution('stress');m.pending=pending();m.open(t,1.1,1.1002)
  m.close(t+1,1.10105,1.10107,'TP_LIMIT',1.101);self.assertIsNotNone(m.pos);self.assertEqual(m.deferred,1)
  m.close(t+2,1.1012,1.10122,'TP_LIMIT',1.101);self.assertIsNone(m.pos);self.assertEqual(m.events[-1]['price'],1.101);self.assertGreaterEqual(m.events[-1]['TP_candidate_price'],m.events[-1]['TP_limit'])
 def test_short_pressure_TP_limit_symmetric(self):
  t=ms('2026-08-03T04:00:00Z');m=Execution('stress');m.pending=pending(-1);m.open(t,1.1,1.1002)
  m.close(t+1,1.09895,1.09905,'TP_LIMIT',1.099);self.assertIsNotNone(m.pos)
  m.close(t+2,1.0987,1.0988,'TP_LIMIT',1.099);self.assertIsNone(m.pos);self.assertEqual(m.events[-1]['price'],1.099);self.assertLessEqual(m.events[-1]['TP_candidate_price'],m.events[-1]['TP_limit'])
 def test_pressure_candidate_exact_grid_boundary(self):
  t=ms('2026-08-03T04:00:00Z');m=Execution('stress');m.pending=pending();m.open(t,1.1,1.1002);m.close(t+1,1.1011,1.1012,'TP_LIMIT',1.101);self.assertIsNone(m.pos);self.assertEqual(m.events[-1]['price'],1.101)
 def test_lot_and_margin_cash_cover(self):
  t=ms('2026-08-03T04:00:00Z');m=Execution('base');m.pending=pending(lot=.005);m.open(t,1.1,1.1002);self.assertEqual(m.cash,500);self.assertIsNone(m.pos)
  m=Execution('stress');m.cash=50;m.pending=pending();m.open(t,1.1,1.1002);self.assertIsNone(m.pos);self.assertEqual(m.cash,50)
 def test_warmup_and_no_future_initial_decision(self):
  t=ms('2026-08-03T03:00:00Z');m=Execution('base')
  for k in range(t-5*60*MIN,t,5*MIN):m.warmup_ingest(k,1.1,1.10001)
  self.assertEqual(m.cash,500);self.assertEqual(m.events,[]);self.assertEqual(m.equity,[])
  m.tick(t,1.10005,1.10006);first=dict(m.events[0]);m.tick(t+MIN,1.099,1.0991);self.assertEqual(first,m.events[0])
 def test_target_observation_does_not_exit_position(self):
  t=ms('2026-08-03T04:00:00Z');m=Execution('base');p=pending();p['tp']=1.2;m.pending=p;m.open(t,1.1,1.1002);m.tick(t+MIN,1.1154,1.1155)
  self.assertIsNotNone(m.pos);self.assertIsNotNone(m.target_equity_first);self.assertIsNone(m.target_realized_first)
if __name__=='__main__':unittest.main()
