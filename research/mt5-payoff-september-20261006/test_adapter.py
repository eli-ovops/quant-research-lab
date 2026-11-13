import unittest,json,csv,hashlib,datetime as dt
from pathlib import Path
from run_adapter import create_accounts,period_rows
from regime_engine import ms,MIN
B=Path(__file__).resolve().parent
class Tests(unittest.TestCase):
 def test_frozen_trade_source_bytes_equal(self):
  p=json.loads((B/'protocol.json').read_text())
  for n,h in p['source_hashes'].items():self.assertEqual(hashlib.sha256((B/n).read_bytes()).hexdigest(),h)
 def test_continuous_instances_and_sunday_no_outwindow_cash(self):
  accounts=create_accounts();accounts[0].cash=493.21
  Sunday=ms('2026-09-13T22:00:00Z');ctx=(Sunday,1.1,1.1001,Sunday//300000*300000,Sunday//86400000*86400000,1.1,None)
  accounts[0].step_factor(ctx,{'complete':False});self.assertEqual(accounts[0].cash,493.21);self.assertEqual(accounts[0].day_open,0)
  self.assertEqual(accounts[1].cash,500);self.assertEqual(len(accounts),4)
 def test_halfopen_clip_prewarmup_and_equal_timestamp_stable(self):
  s=ms('2026-09-07T00:00:00Z');e=ms('2026-09-19T00:00:00Z');ticks=[(s-1,1.1,1.2),(s,1.2,1.3),(s,1.1,1.2),(e,1.3,1.4)]
  rows=list(period_rows(ticks,s,e));self.assertEqual(rows[0][-1],False);self.assertEqual([r[1] for r in rows[1:]],[1.2,1.1]);self.assertEqual(len(rows),3)
if __name__=='__main__':unittest.main()

