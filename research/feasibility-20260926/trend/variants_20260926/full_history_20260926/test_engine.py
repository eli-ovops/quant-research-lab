import unittest,copy,json,itertools
from pathlib import Path
from decimal import Decimal as D
import engine,independent,fixtures
P=Path(__file__).resolve().parent;H=engine.H

def compare(case):
 a=engine.run(**case);b=independent.replay(case)
 fills=[(f['t'],f['coin'],f['side'],f['qty'],f['price'],f['base_fee'],f['quote_fee'],f['cash_after']) for f in a['fills']]
 assert fills==b['fills'],'independent_fills'
 assert [(s['signal'],s['due'],s['coin'],s['side']) for s in a['signals']]==b['signals'],'independent_signals'
 assert [(r['t'],r['coin'],r['side'],r['phase']) for r in a['rejections']]==b['rejections'],'independent_rejections'
 assert len(a['curve'])==len(b['curve'])
 for x,y in zip(a['curve'],b['curve']):
  assert {k:x[k] for k in y}==y,'independent_equity_inventory'
 for k in ['final_equity','max_drawdown','longest_underwater_hours','unrecovered_hours_at_end']:
  av=a['metrics'][k];bv=b[k];assert av==bv or (isinstance(av,D) and abs(av-bv)<D('1e-30')),(k,av,bv)
 return a
class BoundaryTests(unittest.TestCase):
 def simple(self):return fixtures.make([120,119,119,119,80,80,80,80,80,80])
 def test_current_and_future_excluded(self):
  f=self.simple();fixtures.row(f,'BTC',0)[2]='500';a=compare(f)
  self.assertEqual(a['signals'][0]['bar_t'],f['start']);self.assertEqual(a['fills'][0]['t'],f['start']+H)
  g=copy.deepcopy(f)
  for c in engine.COINS:
   for i in range(3,10):fixtures.row(g,c,i)[1:5]=['999','1000','998','999']
  b=compare(g);self.assertEqual([x for x in a['fills'] if x['t']<f['start']+3*H],[x for x in b['fills'] if x['t']<f['start']+3*H])
 def test_strict_equality_no_entry(self):
  f=fixtures.make([101]*10);a=compare(f);self.assertFalse(a['fills'])
 def test_delay_queue_no_recheck(self):
  f=fixtures.make([120,80,80,80,80,80]);f['condition']='delay1';a=compare(f)
  self.assertEqual(a['fills'][0]['t'],f['start']+2*H);self.assertEqual(a['fills'][0]['price'],D('80.1'))
  self.assertEqual(len([s for s in a['signals'] if s['coin']=='BTC' and s['side']=='buy']),1)
 def test_shared_cash_and_buy_base_fee(self):
  a=compare(self.simple());buys=[f for f in a['fills'] if f['side']=='buy']
  self.assertEqual(len(buys),2);self.assertLessEqual(sum(-f['cash_delta'] for f in buys),1600)
  self.assertTrue(all(r['cash']>=400 for r in a['curve']));self.assertEqual(a['curve'][1]['BTC_qty'],buys[0]['qty']-buys[0]['base_fee'])
  self.assertGreater(buys[0]['base_fee'],0)
 def test_shared_cash_after_losses(self):
  f=fixtures.make([120]*4+[80]*5+[160]*4+[70]*4);a=compare(f)
  buys=[x for x in a['fills'] if x['side']=='buy'];self.assertEqual(len(buys),4)
  last=buys[-2:];self.assertLess(-last[0]['cash_delta'],800);self.assertLess(-last[1]['cash_delta'],800);self.assertTrue(all(r['cash']>=400 for r in a['curve']))
 def test_sell_lot_dust_attribution(self):
  a=compare(self.simple());self.assertTrue(any(t['dust_qty']>0 for t in a['trades']))
  for t in a['trades']:
   self.assertEqual(t['sold_qty']%D('.01' if t['coin']=='BTC' else '.001'),0)
   self.assertLess(abs(t['net_pnl']-(t['price_pnl']-t['fees']-t['slippage']-t['tick_rounding']-t['dust_writeoff'])),D('1e-22'))
 def test_rejected_sell_retains_until_new_signal(self):
  f=self.simple();fixtures.fault(f,5,'BTC','open',available='0')
  fixtures.row(f,'BTC',6)[1:5]=['70','71','69','70'];a=compare(f)
  self.assertGreater(a['curve'][5]['BTC_qty'],0);self.assertTrue(any(x['side']=='sell' for x in a['rejections']))
  # Flat hour5 no longer breaks the preceding low79: no blind retry at6.
  self.assertFalse(any(x['coin']=='BTC' and x['side']=='sell' and x['t']==f['start']+6*H for x in a['fills']))
  # New lower close70 at6 generates a fresh exit at7.
  self.assertTrue(any(x['coin']=='BTC' and x['side']=='sell' and x['t']==f['start']+7*H for x in a['fills']))
 def test_terminal_rejection_unresolved_not_cash(self):
  f=fixtures.make([120]*6);fixtures.fault(f,5,'BTC','terminal',available='0');a=compare(f)
  self.assertIn('BTC',a['open_positions']);self.assertIsNone(a['metrics']['liquidation_equity_proxy'])
  self.assertGreater(a['curve'][-1]['valuation_equity'],a['curve'][-1]['cash']);self.assertEqual(a['curve'][-1]['valuation_equity'],a['curve'][-1]['raw_equity']);self.assertEqual(a['metrics']['holding_hours_open'],5);self.assertEqual(a['metrics']['holding_hours'],10)
 def test_mark_rejection_retains_risk(self):
  f=self.simple();fixtures.fault(f,2,'BTC','mark',quote='0');a=compare(f)
  self.assertIsNone(a['curve'][2]['liquidation_equity_proxy']);self.assertGreater(a['curve'][2]['BTC_qty'],0)
 def test_buy_invalid_quote_and_no_blind_retry(self):
  f=self.simple();fixtures.fault(f,1,'BTC','open',quote='NaN');a=compare(f)
  self.assertFalse(any(x['coin']=='BTC' and x['side']=='buy' for x in a['fills']));self.assertEqual(len([x for x in a['rejections'] if x['coin']=='BTC']),1)
 def test_terminal_duration_and_pending_cancel(self):
  f=fixtures.make([100,120,120]);f['condition']='delay1';a=compare(f);self.assertFalse(a['fills']);self.assertEqual(len(a['cancellations']),2)
  f=fixtures.make([120]*3);a=compare(f)
  self.assertTrue(all(t['holding_hours']==2 for t in a['trades']));self.assertTrue(all(x['t']==f['end'] for x in a['fills'] if x['side']=='sell'))
 def test_strict_exit_and_delayed_end_sell_cancel(self):
  f=fixtures.make([120,120,120,120,119,119,119]);a=compare(f)
  self.assertTrue(all(t['phase']=='terminal' for t in a['trades']))
  f=fixtures.make([120,120,120,120,80,80]);f['condition']='delay1';a=compare(f)
  self.assertTrue(all(t['phase']=='terminal' for t in a['trades']));self.assertEqual(len(a['cancellations']),2)
  self.assertTrue(all(c['side']=='sell' for c in a['cancellations']))
 def test_terminal_never_generates_new_intent(self):
  a=compare(fixtures.make([100,100,120]));self.assertFalse(a['signals'])
 def test_hold_delay_and_no_warmup_orders(self):
  for cond,lag in [('baseline',0),('delay1',1)]:
   f=fixtures.make([100]*8);f.update(condition=cond,mode='hold');a=compare(f)
   self.assertEqual(len(a['fills']),4);self.assertEqual(a['fills'][0]['t'],f['start']+lag*H)
 def test_minmax_amount_balance_rejections(self):
  for fault in [{'spec':{'minSz':'1000'}},{'spec':{'maxMktSz':'.001'}},{'spec':{'maxMktAmt':'1'}},{'spec':{'minMktAmt':'10000'}},{'available':'0'},{'quote':'0'}]:
   f=self.simple();fixtures.fault(f,1,'BTC','open',**fault);a=compare(f);self.assertTrue(any(x['side']=='buy' and x['coin']=='BTC' for x in a['rejections']))
 def test_sell_size_and_amount_rejections(self):
  for rule in [{'minSz':'1000'},{'maxMktSz':'.001'},{'maxMktAmt':'1'}]:
   f=self.simple();fixtures.fault(f,5,'BTC','open',spec=rule);a=compare(f);self.assertGreater(a['curve'][5]['BTC_qty'],0)
 def test_gaps_warmup_confirmation_zero_invalid(self):
  for change in ['warm','gap','confirm','zero','misalign','nan','conflict','ohlc']:
   f=self.simple()
   if change=='warm':f['raw']['BTC'].pop(0)
   if change=='gap':f['raw']['BTC'].pop(82)
   if change=='confirm':fixtures.row(f,'BTC',2)[8]='0'
   if change=='zero':fixtures.row(f,'BTC',2)[5]='0'
   if change=='misalign':fixtures.row(f,'BTC',2)[0]=str(f['start']+2*H+1)
   if change=='nan':fixtures.row(f,'BTC',2)[1]='NaN'
   if change=='conflict':r=copy.deepcopy(f['raw']['BTC'][0]);r[4]='99';f['raw']['BTC'].append(r)
   if change=='ohlc':fixtures.row(f,'BTC',2)[2]='1'
   with self.assertRaises(ValueError):engine.run(**f)
   with self.assertRaises(ValueError):independent.replay(f)
 def test_identity_and_synthetic_injection_guard(self):
  f=self.simple();f['spec']['BTC']['instType']='SWAP'
  with self.assertRaises(ValueError):engine.run(**f)
  with self.assertRaises(ValueError):independent.replay(f)
  f=self.simple();f['synthetic']=False;fixtures.fault(f,1,'BTC','open',quote='0')
  with self.assertRaises(ValueError):engine.run(**f)
 def test_reset_period_cash(self):
  f=self.simple();a=compare(f);b=compare(copy.deepcopy(f));self.assertEqual(a['fills'],b['fills']);self.assertEqual(a['curve'][0]['cash'],2000)
 def test_known_risk_series(self):
  f=fixtures.make([100]*4);a=engine.run(**f)
  for r,v in zip(a['curve'],[1900,1800,2000,2100]):r['valuation_equity']=D(v)
  m=engine.metrics(a);self.assertEqual(m['max_drawdown'],D('.1'));self.assertEqual(m['longest_underwater_hours'],2);self.assertEqual(m['max_completed_recovery_hours'],3);self.assertEqual(m['unrecovered_hours_at_end'],0)
 def test_all_fixed_configurations_independent(self):
  cases=[];base=fixtures.make(n=360,seed=2026092603)
  for en,ex,cond in itertools.product([24,48,72],[4,8,12],engine.CONDITIONS):
   f=copy.deepcopy(base);f.update(entry=en,exit=ex,condition=cond);a=compare(f);cases.append({'entry':en,'exit':ex,'condition':cond,'fills':len(a['fills']),'curve_rows':len(a['curve']),'pass':True})
  for cond in engine.CONDITIONS:
   f=copy.deepcopy(base);f.update(condition=cond,mode='hold');a=compare(f);cases.append({'mode':'hold','condition':cond,'fills':len(a['fills']),'curve_rows':len(a['curve']),'pass':True})
  engine.dump(P/'synthetic'/'fixed_cases.json',cases);engine.dump(P/'synthetic'/'fixture.json',base)
  example=engine.run(**base);engine.export(P/'synthetic'/'example',example)
if __name__=='__main__':unittest.main(verbosity=2)
