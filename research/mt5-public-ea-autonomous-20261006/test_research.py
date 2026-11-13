import unittest,json
from pathlib import Path
from asian_research import Research,ms,MIN,window_ticks
B=Path(__file__).resolve().parent
def seed(t):
 m=Research(7);end=t//86400000*86400000+3*60*MIN
 for k in range(end-4*60*MIN,end,15*MIN):m.m15[k]=[1.1,1.101,1.099,1.1]
 cur=t//(5*MIN)*5*MIN
 for k in range(cur-49*5*MIN,cur,5*MIN):m.m5[k]=[1.1]*4
 return m
class Tests(unittest.TestCase):
 def test_decision_is_causal_and_pending_uses_point(self):
  t=ms('2026-09-22T03:00:00Z');m=seed(t);m.tick(t,1.1005,1.1006)
  self.assertIsNotNone(m.pending);self.assertEqual(m.pending['side'],1);self.assertAlmostEqual(m.pending['entry'],1.1011);self.assertAlmostEqual(m.pending['sl'],1.0989)
  self.assertFalse(m.pos);self.assertEqual(len(m.events),1)
 def test_true_ask_entry_and_bid_exit_spread(self):
  t=ms('2026-09-22T04:00:00Z');m=Research(0);m.pending={'side':1,'lot':.1,'entry':1.1,'sl':1.09,'tp':1.12};m.open(t,1.1,1.1002);m.close(t+1,1.1,1.1002,'manualsynthetic')
  self.assertAlmostEqual(m.cash,498);self.assertEqual(m.events[0]['price'],1.1002);self.assertEqual(m.events[-1]['price'],1.1)
 def test_stopgap_uses_worse_actual_quote(self):
  t=ms('2026-09-22T04:00:00Z');m=Research(0);m.pending={'side':1,'lot':.1,'entry':1.1,'sl':1.099,'tp':1.105};m.open(t,1.1,1.1002);m.tick(t+MIN,1.097,1.0972)
  self.assertIsNone(m.pos);self.assertEqual(m.events[-1]['price'],1.097);self.assertAlmostEqual(m.cash,468)
 def test_fees_and_independent_cash_book(self):
  t=ms('2026-09-22T04:00:00Z');m=Research(7);m.pending={'side':-1,'lot':.1,'entry':1.1,'sl':1.11,'tp':1.09};m.open(t,1.1,1.1002);m.close(t+1,1.099,1.0992,'manualsynthetic')
  cash=500.;pos=None
  for e in m.events:
   self.assertAlmostEqual(e['cash_before'],cash)
   if e['event']=='OPEN':pos=e;cash-=e['lot']*7/2
   else:cash+=pos['side']*(e['price']-pos['price'])*e['lot']*100000-e['lot']*7/2
   self.assertAlmostEqual(cash,e['cash_after'])
  self.assertAlmostEqual(m.cash,507.3)
  (B/'synthetic_ledger.json').write_text(json.dumps({'data':'SYNTHETIC_NOT_FOREX_HISTORY','events':m.events,'independent_cash':cash},indent=2))
 def test_lot_and_margin_reject_without_capital_reuse(self):
  t=ms('2026-09-22T04:00:00Z')
  for lot,balance,key in [(.005,500,'lot_min_step'),(.1,50,'insufficient_margin')]:
   m=Research(7,balance,lot);m.pending={'side':1,'lot':lot,'entry':1.1,'sl':1.09,'tp':1.12};m.open(t,1.1,1.1002);self.assertIsNone(m.pos);self.assertEqual(m.cash,balance);self.assertIn(key,m.rejections)
 def test_preperiod_warmup_never_trades_and_first_session_available(self):
  start=ms('2026-09-21T00:00:00Z');m=Research(7)
  for t in range(start-2*60*MIN,start,5*MIN):m.warmup_ingest(t,1.1,1.10001)
  self.assertEqual(m.cash,500);self.assertEqual(m.events,[]);self.assertEqual(m.equity,[])
  for t in range(start,start+3*60*MIN,5*MIN):m.tick(t,1.1,1.10001)
  m.tick(start+3*60*MIN,1.10005,1.10006)
  self.assertIsNotNone(m.pending);self.assertNotIn('incomplete_session_box',m.rejections)
 def test_same_timestamp_warmup_order_is_preserved(self):
  m=Research(7);t=ms('2026-09-20T23:59:59Z')
  m.warmup_ingest(t,1.2,1.2001);m.warmup_ingest(t,1.1,1.1001)
  self.assertEqual(m.m5[t//(5*MIN)*5*MIN][3],1.1);self.assertEqual(m.cash,500);self.assertEqual(m.events,[])
 def test_date_parameter_window_and_warmup_not_pnl(self):
  s=ms('2026-09-07T00:00:00Z');e=ms('2026-09-12T00:00:00Z');rr=[(s-1,1.1,1.2),(s,1.1,1.2),(e-1,1.1,1.2),(e,1.1,1.2)]
  window,warmup=window_ticks(rr,s,e);self.assertEqual([x[0] for x in window],[s,e-1]);self.assertEqual([x[0] for x in warmup],[s-1]);self.assertRaises(ValueError,window_ticks,rr,e,s)
if __name__=='__main__':unittest.main()
