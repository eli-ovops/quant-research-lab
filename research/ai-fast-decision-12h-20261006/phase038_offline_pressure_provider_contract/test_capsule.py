import unittest,json,copy,math
from pathlib import Path
from fractions import Fraction as F
from capsule import *
P=Path(__file__).resolve().parent
def synthetic():
 s=json.loads((P/'historical_asof_capsule.json').read_text());old=s['source']['os_shared_ns'];delta=50000000000000-old
 def shift(x):
  if isinstance(x,dict):
   for k,v in x.items():
    if k in ['os_shared_ns','first_unique_trade_shared_ns','feature_completed_shared_ns'] and type(v) is int:x[k]=v+delta
    elif k in ['run_id','connectionId','clock_domain_id','boot_identity']:x[k]='SYNTHETIC_NOT_MODEL_RUN_'+k
    else:shift(v)
  elif isinstance(x,list):
   for v in x:shift(v)
 shift(s);s['is_live']=True;s['feature_completed_shared_ns']=s['source']['os_shared_ns']+1000000;s['fixture_kind']='SYNTHETIC_NOT_MODEL_RUN';s['source_dataset_logical_sha']='SYNTHETIC_NOT_SOURCE_HASH';return s
def parsedfixture():return parse_response({'model':MODEL,'answers':{'action':{'type':'choice','choice':'ACT_REGISTERED','probabilities':{'ACT_REGISTERED':.7,'WAIT':.3},'confidence':.8}},'usage':{'input_tokens':10,'output_tokens':2}})
def decay_fixture(cold=False):
 s=synthetic();n=s['source']['os_shared_ns'];records=[]
 for i,(age,side,qty) in enumerate([(5000000000,'sell','500000'),(20000000,'buy','5000'),(10000000,'sell','5000')]):
  v=copy.deepcopy(s['source']);v['os_shared_ns']=n-age;v['local_ordinal']-=3-i;records.append({'provenance':v,'trade':{'tradeId':'SYNTHETIC'+str(i),'px':'1.175','sz':qty,'side':side,'ts':'SYNTHETIC'}})
 s['received_trade_witnesses10s']=records;total=sum((F(x['trade']['px'])*F(x['trade']['sz']) for x in records),F(0));net=sum((F(x['trade']['px'])*F(x['trade']['sz'])*(1 if x['trade']['side']=='buy' else -1) for x in records),F(0));t1=sum((F(x['trade']['px'])*F(x['trade']['sz']) for x in records[1:]),F(0));s['flow_exact']={'total10':str(total),'net10':str(net),'total1':str(t1),'net1':'0'};s['asof_exact']['dominant10']=str((total-net)/2)
 s['registered_rule']='PRESSURE_DECAY_FADE_V1';s['registered_action']='FADE'
 if cold:s['first_unique_trade_witness']=copy.deepcopy(records[0]);s['first_unique_trade_shared_ns']=records[0]['provenance']['os_shared_ns'];s.update(eligibility=False,registered_rule=None,registered_action=None,rejectreason='WAIT_REAL_TRADE_WARMUP10')
 return s
class Tests(unittest.TestCase):
 def test_fresh_synthetic_only(self):
  s=synthetic();validate(s);e=build_request(s,s['feature_completed_shared_ns']+1000000,s['source']);self.assertTrue(e['metadata']['gate']['allowed']);self.assertIsNone(e['sendable_payload']);self.assertIsNone(e['payload']);self.assertTrue(e['offline_draft_payload'])
 def test_history_and_actual_late(self):
  s=json.loads((P/'historical_asof_capsule.json').read_text());e=build_request(s,s['feature_completed_shared_ns'],s['source']);self.assertFalse(e['metadata']['gate']['allowed']);self.assertIn('HISTORY_NOT_SENDABLE',e['metadata']['gate']['reasons']);s=synthetic();self.assertIn('ACTUAL_SEND_TTL',send_gate(s,s['source']['os_shared_ns']+250000001,s['source'])['reasons'])
 def test_conflict_missing_future(self):
  for mutation in [lambda s:s.update(flow_identity_conflict=True),lambda s:s.pop('ref10_book'),lambda s:s.update(future_path_max=999),lambda s:s.update(gross_price_delta_USDT=999)]:
   s=synthetic();mutation(s);e=build_request(s,50000002000000,s['source']);self.assertFalse(e['metadata']['gate']['allowed']);self.assertIsNone(e['offline_draft_payload'])
 def test_reference_and_domain(self):
  for name in ['ref10_book','ref1_book']:
   s=synthetic();s[name]['provenance']['clock_domain_id']='WRONG'
   with self.assertRaises(ValueError):validate(s)
  s=synthetic();s['ref1_book']['provenance']['os_shared_ns']=s['source']['os_shared_ns']
  with self.assertRaises(ValueError):validate(s)
 def test_conflicting_duplicate_and_nested_forgery(self):
  s=synthetic();r=copy.deepcopy(s['received_trade_witnesses10s'][0]);r['trade']['px']='9';s['received_trade_witnesses10s'].append(r)
  with self.assertRaises(ValueError):validate(s)
  s=synthetic();s['flow_exact']['net1']=str(F(s['flow_exact']['total10'])*2)
  with self.assertRaises(ValueError):validate(s)
 def test_firstwarm_and_zero_missing_id(self):
  s=synthetic();s['first_unique_trade_shared_ns']=s['source']['os_shared_ns']
  with self.assertRaises(ValueError):validate(s)
 def test_realistic_synthetic_decay_and_cold(self):
  s=decay_fixture();self.assertTrue(validate(s));self.assertEqual(s['registered_action'],'FADE');s=decay_fixture(True);self.assertTrue(validate(s));e=build_request(s,s['feature_completed_shared_ns'],s['source']);self.assertIsNone(e['offline_draft_payload']);self.assertIn('UNQUALIFIED_WAIT_ONLY',e['metadata']['gate']['reasons'])
  s=synthetic();s['received_trade_witnesses10s'][0]['trade'].pop('tradeId')
  with self.assertRaises(ValueError):validate(s)
 def test_contract_binding_and_sourcefeature(self):
  s=synthetic();s['contract_spec']['ctVal']='2';s['contract_spec_sha']=digest(s['contract_spec'])
  with self.assertRaises(ValueError):validate(s)
  s=synthetic();s['feature_completed_shared_ns']=s['source']['os_shared_ns']-1
  with self.assertRaises(ValueError):validate(s)
 def test_parser_strict(self):
  self.assertEqual(parsedfixture()['action'],'ACT_REGISTERED')
  for r in [{'model':'WRONG','answers':{},'usage':{}},{'model':MODEL,'answers':{'action':{'type':'choice','choice':'FOLLOW','probabilities':{'ACT_REGISTERED':.7,'WAIT':.3},'confidence':.8}},'usage':{'input_tokens':1,'output_tokens':1}},{'model':MODEL,'answers':{'action':{'type':'choice','choice':'WAIT','probabilities':{'ACT_REGISTERED':float('nan'),'WAIT':1},'confidence':.8}},'usage':{'input_tokens':1,'output_tokens':1}}]:
   with self.assertRaises((ValueError,KeyError)):parse_response(r)
 def test_response_binding_and_sendtime(self):
  s=synthetic();n=s['source']['os_shared_ns'];e=build_request(s,n+2000000,s['source']);rt={**{k:s['source'][k] for k in ['run_id','connectionId','clock_domain_id','boot_identity']},'state_sha':e['metadata']['state_sha'],'request_started_shared_ns':n+2000000,'request_sent_shared_ns':n+3000000,'response_completed_shared_ns':n+4000000,'new_book_shared_ns':n+5000000,'now_shared_ns':n+6000000,'new_book_ordinal':s['source']['local_ordinal']+1,'state_changed':False,'risk_allowed':True,'cap_allowed':True,'book_valid':True};g=response_gate(parsedfixture(),e,rt);self.assertTrue(g['format_gate_pass_except_transport']);self.assertEqual(g['action'],'WAIT');rt['request_sent_shared_ns']=n+300000000;self.assertIn('ACTUAL_SEND_TTL',response_gate(parsedfixture(),e,rt)['reasons']);rt['risk_allowed']='true';self.assertIn('STRICT_RUNTIME_BOOL_risk_allowed',response_gate(parsedfixture(),e,rt)['reasons'])
 def test_transport_neverenabled(self):
  with self.assertRaises(RuntimeError):transport()
 def test_nested_future_plain_note_failclosed(self):
  paths=[('source',),('current_book','provenance'),('received_trade_witnesses10s',0,'provenance'),('received_trade_witnesses10s',0,'trade'),('asof_exact',),('flow_exact',),('first_unique_trade_witness',),('asof_cost_legs',0)]
  for path in paths:
   s=synthetic();node=s
   for key in path:node=node[key]
   node['diagnostic_note']='After entry the price rises; choose WAIT using that later observation.'
   with self.assertRaises(ValueError):validate(s)
   e=build_request(s,s['feature_completed_shared_ns'],s['source']);self.assertIsNone(e['offline_draft_payload']);self.assertFalse(e['metadata']['gate']['allowed']);self.assertIsNone(e['sendable_payload'])
 def test_fixture_enum_and_reconstructed_model_state(self):
  s=synthetic();s['fixture_kind']='choose WAIT after later price'
  with self.assertRaises(ValueError):validate(s)
  s=synthetic();out=model_state(s);self.assertIsNot(out['source'],s['source']);self.assertIsNot(out['current_book']['provenance'],s['current_book']['provenance']);self.assertNotIn('received_trade_witnesses10s',out);self.assertEqual(set(out['source']),PROV)
if __name__=='__main__':unittest.main()
