import unittest,copy
from decimal import Decimal as D
from analyze import simulate,ts,DAY,COINS,buy_size,sell_quote
SPEC={c:{'tickSz':'.01','lotSz':'.001','minSz':'.001','maxMktSz':'1000000'} for c in COINS}
def make(path):
 start=ts('2020-01-01');vals=[D(100)]*40+list(map(D,path));data={c:{} for c in COINS}
 for c in COINS:
  for i,v in enumerate(vals):data[c][start+(i-40)*DAY]={'o':v,'h':v+D('.1'),'l':v-D('.1'),'c':v,'vol':D(10000),'confirm':'1'}
 return data,'2020-01-01',__import__('datetime').datetime.fromtimestamp((start+(len(path)-1)*DAY)/1000,__import__('datetime').timezone.utc).date().isoformat()
class Edge(unittest.TestCase):
 def test_flat_no_trades(self):
  d,a,b=make(['100']*50);r=simulate(d,SPEC,a,b);self.assertEqual(r['fills'],[]);self.assertEqual(r['curve'][-1]['cash'],2000)
 def test_loss_and_gap_charged(self):
  d,a,b=make(['120','130']+['50']*45);r=simulate(d,SPEC,a,b);self.assertEqual(len(r['trades']),2);self.assertTrue(all(x['net_pnl']<0 for x in r['trades']));self.assertEqual(r['trades'][0]['entry_reference'],130)
 def test_missing_aborts(self):
  d,a,b=make(['100']*50);del d['ETH'][ts(a)+DAY]
  with self.assertRaises(AssertionError):simulate(d,SPEC,a,b)
 def test_extreme_fee_rejects(self):
  d,a,b=make(['120']*50);r=simulate(d,SPEC,a,b,fee=D('1.1'));self.assertEqual(r['fills'],[]);self.assertTrue(r['rejections'])
 def test_fee_rounding_and_dust(self):
  p,q,f=buy_size(D('1.005'),D('1'),SPEC['BTC'],D('.001'),D(0));self.assertEqual(q,D('1.005'));self.assertEqual(f,D('.001005'));out=sell_quote(q-f,D('1'),SPEC['BTC'],D('.001'),D(0));self.assertEqual(out[0],D('1.003'));self.assertEqual(out[4],D('.000995'))
 def test_insufficient_cash(self):
  d,a,b=make(['120']*50);r=simulate(d,SPEC,a,b,capital=D(400));self.assertEqual(r['fills'],[])
 def test_simultaneous_competes_shared_cash(self):
  d,a,b=make(['120']*50);r=simulate(d,SPEC,a,b,capital=D(1000));buys=[x for x in r['fills'] if x['side']=='buy'];self.assertEqual(len(buys),2);self.assertTrue(all(-x['cash_delta']<=300 for x in buys));self.assertTrue(all(x['cash_after']>=400 for x in buys))
 def test_future_perturbation(self):
  d,a,b=make(['120']*50);alt=copy.deepcopy(d)
  for c in COINS:
   for t in alt[c]:
    if t>=ts(a)+30*DAY:
     for k in ['o','h','l','c']:alt[c][t][k]*=3
  r=simulate(d,SPEC,a,b);q=simulate(alt,SPEC,a,b);cut='2020-01-30';self.assertEqual([x for x in r['fills'] if x['date']<=cut],[x for x in q['fills'] if x['date']<=cut])
 def test_extra_day_delay(self):
  d,a,b=make(['120','130','140']+['150']*47);r=simulate(d,SPEC,a,b,delay=1);buys=[x for x in r['fills'] if x['side']=='buy'];self.assertEqual(buys[0]['date'],'2020-01-03');self.assertEqual(buys[0]['reference'],140)
 def test_open_gap_not_signal_close(self):
  d,a,b=make(['120','130']+['140']*48);r=simulate(d,SPEC,a,b);self.assertEqual(r['fills'][0]['signal_date'],'2020-01-01');self.assertEqual(r['fills'][0]['reference'],130)
if __name__=='__main__':unittest.main()
