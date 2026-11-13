import unittest,copy,tempfile,json,time
from pathlib import Path
import runner as r
from decimal import Decimal as D
class LedgerTests(unittest.TestCase):
 def setUp(self):
  self.s={'received_ms':10000,'book':{'ts':'10000','asks':[['100','1000']],'bids':[['99','1000']]},'mark':{'ts':'10000','markPx':'100'},'funding_history':[]}
  self.spec={'ctVal':'1','ctMult':'1','lotSz':'.01','minSz':'.01'}
 def test_sweep_depth(self):
  self.assertEqual(r.sweep([['100','1'],['101','1']],'2',D(1)),D(201))
  with self.assertRaisesRegex(ValueError,'INSUFFICIENT'):r.sweep([['100','1']],'2',D(1))
 def test_margin(self):
  a=r.enter(self.s,self.spec,1,5,D('.0005'),D('.0005'))
  self.assertLessEqual(D(a['entry_notional']),D(600));self.assertGreater(D(a['entry_notional']),D(590))
 def test_both_fees_long(self):
  a=r.enter(self.s,self.spec,1,5,D('.001'),D(0));self.assertEqual(r.value(a,self.s),D('142.806'))
 def test_short_rise_loses(self):
  a=r.enter(self.s,self.spec,-1,5,D(0),D(0));s=copy.deepcopy(self.s);s['book']['asks']=[['110','1000']]
  self.assertLess(r.value(a,s),D(100))
 def test_funding_direction_dedup(self):
  a=r.enter(self.s,self.spec,1,5,D(0),D(0));self.assertEqual(r.charge(a,'.001','100'),D('.6'))
  s=copy.deepcopy(self.s);s['received_ms']=20000;s['funding_history']=[{'fundingTime':'15000','realizedRate':'.001'}]
  r.update(a,s,999999);r.update(a,s,999999);self.assertEqual(D(a['funding_estimate']),D('.6'))
  a['side']=-1;self.assertEqual(r.charge(a,'.001','100'),D('-.6'))
 def test_stale_and_predecision(self):
  with self.assertRaisesRegex(ValueError,'BEFORE'):r.validate(self.s,10000)
  s=copy.deepcopy(self.s);s['received_ms']=20000
  with self.assertRaisesRegex(ValueError,'STALE'):r.validate(s)
 def test_deadline_censor(self):
  a=r.enter(self.s,self.spec,1,5,D(0),D(0));s=copy.deepcopy(self.s);s['received_ms']=999999
  r.update(a,s,20000);self.assertTrue(a['closed']);self.assertTrue(a['deadline_censored']);self.assertIsNone(a['validated_equity'])
 def test_target_and_loss(self):
  for price,reason in [('150','TARGET'),('80','LOSS_THRESHOLD')]:
   a=r.enter(self.s,self.spec,1,5,D(0),D(0));s=copy.deepcopy(self.s);s['book']['bids']=[[price,'1000']]
   r.update(a,s,99999);self.assertEqual(a['exit_reason'],reason)
 def test_start_ingest_duplicate_and_invalid(self):
  oldroot,oldnow=r.ROOT,r.now
  try:
   with tempfile.TemporaryDirectory() as d:
    r.ROOT=Path(d);r.now=lambda:10000
    (r.ROOT/'PROTOCOL.md').write_text('test')
    spec=dict(self.spec,ctType='linear',settleCcy='USDT')
    (r.ROOT/'decision-input.json').write_text(json.dumps({'markets':{'BTC-USDT-SWAP':{'spec':spec}}}))
    p=r.ROOT/'decision.json';p.write_text(json.dumps({'action':'LONG','instrument':'BTC-USDT-SWAP','input_sha256':r.sha(r.ROOT/'decision-input.json')}))
    r.init(p)
    with self.assertRaisesRegex(ValueError,'EXISTING'):r.init(p)
    s=copy.deepcopy(self.s);s['instrument']='BTC-USDT-SWAP';s['received_ms']=10001;s['book']['ts']='10001'
    p=r.ROOT/'sample.json';p.write_text(json.dumps(s));a=r.ingest(p)
    self.assertEqual(a['status'],'RUNNING_CONDITIONAL');self.assertEqual(len(a['accounts']),12)
    self.assertEqual(len(r.ingest(p)['samples']),1)
    s['received_ms']=900000;s['book']['ts']='1';r.now=lambda:900000;p=r.ROOT/'invalid.json';p.write_text(json.dumps(s))
    a=r.ingest(p);self.assertEqual(len(a['samples']),1);self.assertEqual(len(a['errors']),1)
  finally:r.ROOT,r.now=oldroot,oldnow
if __name__=='__main__':unittest.main()
