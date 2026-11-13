from pathlib import Path
from fractions import Fraction as F
import unittest,json,copy
from pressure_rules import pressure_choice,PressureRules,FOLLOW,FADE
B=Path(__file__).resolve().parent
def registry():return json.loads((B/'instruments.json').read_text())
def fixture_rows():
 result=[];asset='DOGE-USDT-SWAP'
 def add(t,ch,data):result.append({'instId':asset,'channel':ch,'local_ordinal':len(result)+1,'os_shared_ns':2000000000+t*1000000,'receive_wall_ns':1000000000000+t*1000000,'run_id':'SYNTHETIC','connectionId':'SYNTHETIC','clock_domain_id':'OS_CLOCK_MONOTONIC|boot=SYNTHETIC','boot_identity':'SYNTHETIC','raw':json.dumps({'arg':{'instId':asset,'channel':ch},'data':[data]})})
 def book(t,bid='.10000',ask='.10001'):add(t,'books5',{'asks':[[ask,'20']],'bids':[[bid,'20']]})
 book(0);add(0,'trades',{'tradeId':'0','px':'.10000','sz':'1','side':'buy','ts':'0'});add(5000,'trades',{'tradeId':'1','px':'.10000','sz':'90','side':'buy','ts':'5000'});book(9000);add(9900,'trades',{'tradeId':'2','px':'.10000','sz':'10','side':'buy','ts':'9900'});book(10000,'.10050','.10051');book(10100,'.10050','.10051');return result
class T(unittest.TestCase):
 def test_exact_cost_ratio_imbalance_boundaries_mutualexclusion(self):
  self.assertEqual(pressure_choice(F(100),F(80),F(10),F(8),F(20),F(15),F(90),250000000)[0],FOLLOW)
  self.assertEqual(pressure_choice(F(370),F(362),F(10),F(2),F(20),F(15),F(100),0)[0],FADE)
  self.assertIsNone(pressure_choice(F(100),F(80),F(10),F(8),F(20)-F(1,10**30),F(15),F(90),0)[0]);self.assertIsNone(pressure_choice(F(370)+F(1,10**30),F(362),F(10)+F(1,10**30),F(2),F(20),F(15),F(100),0)[0])
  self.assertEqual(pressure_choice(F(370),F(369),F(10),F(2),F(20),F(15),F(100),0)[1],'WAIT_NESTED_WINDOW_INCONSISTENCY')
 def test_zero_messages_stale_unique_trade_and_prior9_WAIT(self):
  for total1,net1,age in [(F(0),F(0),0),(F(10),F(0),250000001),(F(100),F(80),0)]:self.assertIsNone(pressure_choice(F(100),F(80),total1,net1,F(20),F(15),F(50),age)[0])
 def test_warmup10s_reference1s_and_cooldown_causal(self):
  rules=PressureRules(registry(),'OS_CLOCK_MONOTONIC|boot=SYNTHETIC');events=[]
  for row in fixture_rows():
   r=rules.ingest(row)
   if r and r['qualified_rule']:events.append(r)
  self.assertEqual(len(events),1);self.assertEqual(events[0]['qualified_rule'],FOLLOW);self.assertEqual(events[0]['asof_ordinal'],6);self.assertEqual(events[0]['reference10_ordinal'],1);self.assertEqual(events[0]['reference1_ordinal'],4);self.assertGreater(rules.counters['DOGE-USDT-SWAP|WAIT_TRADE_WARMUP10'],0);self.assertEqual(rules.counters['DOGE-USDT-SWAP|WAIT_RULE35_COOLDOWN'],1)
 def test_repeat_doesnotrefresh_age_conflict_and_missingID_unknown(self):
  r=fixture_rows();rules=PressureRules(registry(),'OS_CLOCK_MONOTONIC|boot=SYNTHETIC')
  for row in r:rules.ingest(row)
  originalage=rules.states['DOGE-USDT-SWAP']['lasttrade_ns'];duplicate=copy.deepcopy(r[4]);duplicate.update(local_ordinal=8,os_shared_ns=12200000000,receive_wall_ns=1010200000000);rules.ingest(duplicate);self.assertEqual(rules.states['DOGE-USDT-SWAP']['lasttrade_ns'],originalage);self.assertEqual(rules.counters['EXACT_TRADE_REPEAT'],1)
  conflict=copy.deepcopy(duplicate);conflict.update(local_ordinal=9,os_shared_ns=12300000000);data=json.loads(conflict['raw']);data['data'][0]['sz']='11';conflict['raw']=json.dumps(data);result=rules.ingest(conflict);self.assertEqual(result['rejectreason'],'WAIT_TRADE_IDENTITY_UNKNOWN')
  rules=PressureRules(registry(),'OS_CLOCK_MONOTONIC|boot=SYNTHETIC');missing=fixture_rows()[0];missing.update(channel='trades');missing['raw']=json.dumps({'arg':{'instId':missing['instId'],'channel':'trades'},'data':[{'px':'.1','sz':'1','side':'buy'}]});self.assertEqual(rules.ingest(missing)['rejectreason'],'WAIT_TRADE_IDENTITY_UNKNOWN')
 def test_same_run_domain_and_integer_clock_reject(self):
  for change in [{'clock_domain_id':'legacy-process'},{'connectionId':'other'},{'os_shared_ns':1},{'os_shared_ns':True}]:
   rules=PressureRules(registry(),'OS_CLOCK_MONOTONIC|boot=SYNTHETIC');r=fixture_rows();rules.ingest(r[0]);self.assertRaises(ValueError,rules.ingest,{**r[1],**change})
 def test_exact1s_and10s_expiration_with_reference_tolerance(self):
  r=fixture_rows();rules=PressureRules(registry(),'OS_CLOCK_MONOTONIC|boot=SYNTHETIC')
  for row in r:rules.ingest(row)
  now=rules.last_ns;self.assertTrue(all(x[0]>now-10000000000 for x in rules.states['DOGE-USDT-SWAP']['flow']));self.assertTrue(all(x[0]<=now for x in rules.states['DOGE-USDT-SWAP']['flow']));self.assertEqual(rules.states['DOGE-USDT-SWAP']['firsttrade_ns'],2000000000)
 def test_precut_warmup_cannot_consume_future_cooldown(self):
  rules=PressureRules(registry(),'OS_CLOCK_MONOTONIC|boot=SYNTHETIC',forward_cut_ns=12100000000);events=[]
  for row in fixture_rows():
   result=rules.ingest(row)
   if row['os_shared_ns']<12100000000:self.assertFalse(rules.cool);self.assertIsNone(result['qualified_rule'])
   if result['qualified_rule']:events.append(result)
  self.assertEqual(len(events),1);self.assertEqual(events[0]['asof_ordinal'],7);self.assertEqual(events[0]['shadow_actions'],['FOLLOW','FADE'])
if __name__=='__main__':unittest.main()
