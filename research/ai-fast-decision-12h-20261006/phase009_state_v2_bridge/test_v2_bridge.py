import unittest,copy,json
from v2_bridge import *
def state():
 return {'state_version':VERSION,'question_version':QUESTION,'family':'FLOW_IMPULSE','asset':'BTC-USDT-SWAP','asof_ordinal':2,'clock_view':'OS_SHARED','clock_domain_id':'d','capture_run_id':'r','connectionId':'c','source_asof_shared_ns':100,'source_latest_book_shared_ns':90,'feature_completed_shared_ns':110,'source_receive_wall_ns':1000000100,'is_live':True,'quote_age_ms':.00001,'impulse_bps':3.2,'flow_imbalance':.9,'flow_received_notional_USDT':10000,'direction':1,'asks_contracts':[['101','10']],'bids_contracts':[['100','10']],'contract_spec':{'ctVal':'.01','ctMult':'1','minSz':'.01','lotSz':'.01'},'fee_each_side_bps_assumptions':[5,10],'allowed_actions':['WAIT','FOLLOW','FADE']}
def expected():return {'capture_run_id':'r','connectionId':'c','clock_domain_id':'d'}
def parsed():return parse_response({'model':MODEL,'answers':{'action':{'type':'choice','choice':'FOLLOW','probabilities':{'WAIT':.2,'FOLLOW':.7,'FADE':.1},'confidence':.8}},'usage':{'input_tokens':1,'output_tokens':1}})
def runtime(e):
 m=e['metadata'];return {'capture_run_id':'r','connectionId':'c','clock_domain_id':'d','input_hash':m['input_hash'],'asof_ordinal':2,'request_sent_shared_ns':130,'response_completed_shared_ns':140,'new_book_shared_ns':150,'now_shared_ns':160,'new_book_ordinal':3,'state_changed':False,'risk_allowed':True,'cap_allowed':True,'book_valid':True}
class T(unittest.TestCase):
 def test_explicit_v2_payload_version_and_twoleg_cost(self):
  e=build_envelope(state(),120,expected());self.assertTrue(e['metadata']['live_send_gate']['send_allowed']);self.assertNotIn('asof_receive_monotonic_ms',e['payload']['state']);self.assertIn('both entry and exit',INSTRUCTIONS);self.assertEqual(e['metadata']['input_hash'],digest(state()))
 def test_missing_future_and_legacy_alias_rejected(self):
  for change in ['missing','future','legacy']:
   s=state()
   if change=='missing':del s['capture_run_id']
   if change=='future':s['price_fee_delta_USDT']=1
   if change=='legacy':s['asof_receive_monotonic_ms']=.0001
   with self.assertRaises(ValueError):build_envelope(s)
 def test_history_and_old_namespace_never_send(self):
  s=state();s['is_live']=False;self.assertFalse(build_envelope(s,120,expected())['metadata']['live_send_gate']['send_allowed']);s=state();s['clock_view']='LEGACY_INTERNAL';self.assertFalse(live_send_gate(s,120,expected())['send_allowed'])
 def test_actual_late_send_rechecks_inputTTL(self):
  e=build_envelope(state(),120,expected());r=runtime(e);r.update(request_sent_shared_ns=300000130,response_completed_shared_ns=300000140,new_book_shared_ns=300000150,now_shared_ns=300000160);self.assertIn('ACTUAL_INPUT_TTL',response_gate(parsed(),e,r)['reasons']);self.assertEqual(response_gate(parsed(),e,r)['action'],'WAIT')
 def test_provenance_book_content_run_domain_future(self):
  s=state();s['is_live']=False;e={'asof_ordinal':2,'latest_book_ordinal':1,'capture_run_id':'r','clock_domain_id':'d','source_asof_shared_ns':100,'flow_total_USDT':10000};src={'local_ordinal':2,'instId':'BTC-USDT-SWAP','connectionId':'c','run_id':'r','clock_domain_id':'d','os_shared_ns':100,'receive_wall_ns':1000000100};book={**src,'local_ordinal':1,'os_shared_ns':90,'raw':json.dumps({'data':[{'asks':[['101','10']],'bids':[['100','10']]}]})};out=from_causal_snapshot(s,e,src,book);self.assertFalse(out['is_live'])
  for change in [{'clock_domain_id':'other'},{'run_id':'other'},{'local_ordinal':3},{'os_shared_ns':101},{'raw':json.dumps({'data':[{'asks':[['102','10']],'bids':[['100','10']]}]})}]:
   with self.assertRaises(ValueError):from_causal_snapshot(s,e,src,{**book,**change})
 def test_boolean_runtime_and_binding_failclosed(self):
  e=build_envelope(state(),120,expected());r=runtime(e);self.assertEqual(response_gate(parsed(),e,r)['action'],'FOLLOW')
  for change in [{'risk_allowed':'false'},{'state_changed':'false'},{'clock_domain_id':'other'},{'capture_run_id':'other'},{'new_book_shared_ns':140}]:
   self.assertEqual(response_gate(parsed(),e,{**r,**change})['action'],'WAIT')
 def test_parser_version_and_transport_disabled(self):
  with self.assertRaises(ValueError):parse_response({'model':'jev-latest','answers':{},'usage':{}})
  with self.assertRaises(RuntimeError):transport_disabled()
  self.assertEqual(DECISIONS['endpoint_schema'],'UNKNOWN')
if __name__=='__main__':unittest.main()

