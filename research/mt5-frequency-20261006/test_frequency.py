import unittest,datetime as dt
from frequency_engine import Account,Market,M5,MIN,DAY,ms
def context(t,bid=1.1005,ask=1.1006,ma=1.1,box=(1.101,1.099)):return (t,bid,ask,t//M5*M5,t//DAY*DAY,ma,box)
def virtual(t,side=1):return {'side':side,'entry':1.1011,'sl':1.0989,'tp':1.10396,'expiry':t//DAY*DAY+13*60*MIN,'placed':t}
class Tests(unittest.TestCase):
 def test_cap_counts_actual_open_not_pending_and_daily_reset(self):
  t=ms('2026-08-03T04:00:00Z');a=Account(1,'base');a.step(context(t));self.assertEqual(a.day_open,0);self.assertIsNotNone(a.pending)
  a.step(context(t+1,1.1011,1.1012));self.assertEqual(a.day_open,1);self.assertIsNotNone(a.pos)
  a.step(context(t+2,1.10396,1.10406));self.assertIsNone(a.pos);a.step(context(t+M5));self.assertIsNone(a.pending);self.assertEqual(a.day_open,1)
  Sunday=ms('2026-08-09T22:00:00Z');a.step(context(Sunday));self.assertEqual(a.day_open,0);self.assertIsNone(a.pending)
 def test_reentry_waits_next_boundary_singleposition_and_illegal_stop(self):
  t=ms('2026-08-03T04:00:00Z');a=Account(5,'base');a.step(context(t));a.step(context(t+1,1.1011,1.1012));a.step(context(t+2,1.10396,1.10406))
  a.step(context(t+2*MIN));self.assertIsNone(a.pending)
  a.step(context(t+M5,1.105,1.1051));self.assertIsNone(a.pending);self.assertIn('illegal_breakout_stop',a.rejections)
  a.step(context(t+M5+1));self.assertIsNone(a.pending)
  a.step(context(t+2*M5));self.assertIsNotNone(a.pending);a.step(context(t+2*M5+1,1.1011,1.1012));self.assertEqual(a.day_open,2);self.assertIsNotNone(a.pos);self.assertIsNone(a.pending)
 def test_risk_fee_slippage_floor_and_margin(self):
  t=ms('2026-08-03T04:00:00Z')
  for cost in ['base','stress']:
   a=Account(5,cost);a.day=t//DAY*DAY;a.day_start=500;a.pending=virtual(t);a.open(t,1.1011,1.1012);e=a.events[-1];self.assertEqual(e['event'],'OPEN');self.assertLessEqual(e['planned_risk'],5+1e-8);self.assertAlmostEqual(e['lot']/.01,round(e['lot']/.01));self.assertAlmostEqual(e['fee'],e['lot']*3.5);self.assertGreaterEqual(e['cash_after'],e['margin'])
  a=Account(15,'stress');a.day=t//DAY*DAY;a.day_start=2;a.cash=2;a.pending=virtual(t);a.open(t,1.1011,1.1012);self.assertEqual(a.day_open,0);self.assertIsNone(a.pos);self.assertIn('minlot_over_riskbudget',a.rejections)
 def test_sticky_daily_loss_pending_cancel_trigger_guard_no_forced_exit(self):
  t=ms('2026-08-03T04:00:00Z');a=Account(15,'base');a.step(context(t));a.cash=474;a.step(context(t+1));self.assertTrue(a.lock);self.assertIsNone(a.pending)
  a.cash=510;a.step(context(t+M5));self.assertTrue(a.lock);self.assertIsNone(a.pending)
  a.pending=virtual(t);a.open(t+M5+1,1.1011,1.1012);self.assertEqual(a.day_open,0);self.assertIsNone(a.pos)
  a.step(context(t+DAY));self.assertFalse(a.lock);self.assertIsNotNone(a.pending)
 def test_first_pending_initial_schedule_and_no_future_context(self):
  t=ms('2026-08-03T04:00:00Z');accounts=[Account(c,'base') for c in [1,5,15]]
  for a in accounts:a.step(context(t));self.assertEqual(a.events[0]['event'],'PENDING');self.assertEqual(a.events[0]['timestamp'],accounts[0].events[0]['timestamp'])
  snapshot=dict(accounts[0].events[0]);accounts[0].step(context(t+1,1.1011,1.1012));self.assertEqual(snapshot,accounts[0].events[0]);self.assertEqual(accounts[1].day_open,0)
 def test_market_MA_uses_current_quote_and_closed49_only(self):
  t=ms('2026-08-03T03:00:00Z');m=Market()
  for k in range(t-5*60*MIN,t,M5):m.ingest(k,1.1,1.1001)
  c=m.ingest(t,1.1005,1.1006);self.assertAlmostEqual(c[5],(49*1.1+1.1005)/50);prior=c
  m.ingest(t+M5,1.2,1.2001);self.assertEqual(prior[5],c[5])
if __name__=='__main__':unittest.main()

