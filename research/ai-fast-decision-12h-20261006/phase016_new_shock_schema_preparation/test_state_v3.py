import unittest,json,copy
from pathlib import Path
from state_v3 import *
def fixture():
 registry=json.loads((B/'instruments.json').read_text());asset='DOGE-USDT-SWAP';rows=[]
 def add(t,channel,record):
  rows.append({'instId':asset,'channel':channel,'local_ordinal':len(rows)+1,'os_shared_ns':2000000000+t*1000000,'receive_wall_ns':1000000000000+t*1000000,'receive_wall_ms':1000000+t,'run_id':'SYNTHETIC_RUN','connectionId':'SYNTHETIC_CONN','clock_domain_id':'OS_CLOCK_MONOTONIC|boot=SYNTHETIC_BOOT','boot_identity':'SYNTHETIC_BOOT','raw':json.dumps({'arg':{'instId':asset,'channel':channel},'data':[record]})})
 def book(t,bid,ask):add(t,'books5',{'asks':[[ask,'20','0','1']],'bids':[[bid,'20','0','1']],'ts':str(t)})
 book(0,'.10000','.10001');add(0,'trades',{'tradeId':'1','px':'.10000','sz':'1','side':'buy','ts':'0'});book(1000,'.10005','.10006');add(1000,'trades',{'tradeId':'2','px':'.10005','sz':'50','side':'buy','ts':'1000','count':'100'});book(1100,'.10050','.10051')
 s=from_causal_prefix(rows,registry,3100000010,True);s['evidence_label']='SYNTHETIC_NOT_MODEL_RUN';return s,rows
def expected(s):return {k:s['source'][k] for k in ['run_id','connectionId','clock_domain_id','boot_identity']}
def parsed():return parse_response({'model':MODEL,'answers':{'action':{'type':'choice','choice':'FOLLOW','probabilities':{'WAIT':.2,'FOLLOW':.7,'FADE':.1},'confidence':.8}},'usage':{'input_tokens':1,'output_tokens':1}})
def runtime(e):
 return {**expected(e['state']),'state_sha256':e['metadata']['state_sha256'],'request_started_shared_ns':3100000020,'request_sent_shared_ns':3100000030,'response_completed_shared_ns':3100000040,'new_book_shared_ns':3100000050,'now_shared_ns':3100000060,'new_book_ordinal':6,'state_changed':False,'risk_allowed':True,'cap_allowed':True,'book_valid':True}
class T(unittest.TestCase):
 def test_new_family_fields_and_valid_formula_fixture(self):
  s,_=fixture();self.assertTrue(validate(s));self.assertTrue(s['eligibility']);e=build_request(s,3100000020,expected(s));self.assertEqual(e['payload']['state']['family'],'COST_CAPABLE_SHOCK_V1');self.assertIn('not predicted future profit',INSTRUCTIONS);self.assertEqual(e['metadata']['transport'],'DISABLED')
 def test_missing_actual_field_and_future_labels_rejected(self):
  s,_=fixture()
  for label in ['missing','future','alias']:
   x=copy.deepcopy(s)
   if label=='missing':del x['source']['os_shared_ns']
   if label=='future':x['future_path_max_USDT']=100
   if label=='alias':x['family']='FLOW_IMPULSE'
   with self.assertRaises(Exception):build_request(x)
 def test_provenance_and_raw_content_mismatch(self):
  s,rows=fixture();bad=copy.deepcopy(rows);bad[0]['clock_domain_id']='legacy-process';self.assertRaises(ValueError,from_causal_prefix,bad,s['contract_registry'])
  for key,value in [('run_id','OTHER_RUN'),('os_shared_ns',3200000000)]:
   x=copy.deepcopy(s);x['reference_book']['provenance'][key]=value;self.assertRaises(ValueError,validate,x)
  x=copy.deepcopy(s);x['current_book']['asks'][0][0]='.10052';self.assertRaises(ValueError,validate,x)
 def test_flow_witness_future_or_forged_total_rejected(self):
  s,_=fixture();x=copy.deepcopy(s);x['received_flow_records'][0]['os_shared_ns']=s['source']['os_shared_ns']+1;self.assertRaises(ValueError,validate,x);x=copy.deepcopy(s);x['received_flow_total_exact']='999999';self.assertRaises(ValueError,validate,x)
 def test_history_no_send_and_unqualified_no_payload(self):
  s,rows=fixture();s['is_live']=False;e=build_request(s,3100000020,expected(s));self.assertFalse(e['metadata']['send_gate']['allowed']);self.assertIsNone(e['payload']);self.assertIsNotNone(e['offline_draft_payload']);self.assertIsNone(e['sendable_payload']);rows[-1]['raw']=rows[2]['raw'];u=from_causal_prefix(rows,s['contract_registry']);self.assertFalse(u['eligibility']);self.assertIsNone(build_request(u)['payload'])
 def test_planned_stale_has_only_offline_draft(self):
  s,_=fixture();e=build_request(s,3500000020,expected(s));self.assertIsNone(e['payload']);self.assertIsNotNone(e['offline_draft_payload']);self.assertIsNone(e['sendable_payload'])
 def test_actual_late_send_and_runtime_flags_fail_closed(self):
  s,_=fixture();e=build_request(s,3100000020,expected(s));r=runtime(e);self.assertEqual(response_gate(parsed(),e,r)['action'],'FOLLOW')
  for changes in [{'request_sent_shared_ns':3400000030,'response_completed_shared_ns':3400000040,'new_book_shared_ns':3400000050,'now_shared_ns':3400000060},{'risk_allowed':'false'},{'clock_domain_id':'OTHER'},{'new_book_ordinal':'6'},{'response_completed_shared_ns':5100000040,'new_book_shared_ns':5100000050,'now_shared_ns':5100000060}]:self.assertEqual(response_gate(parsed(),e,{**r,**changes})['action'],'WAIT')
 def test_parser_and_transport_not_real_run(self):
  self.assertRaises(ValueError,parse_response,{'model':'other','answers':{},'usage':{}});self.assertRaises(RuntimeError,transport_disabled);self.assertEqual(DECISIONS['contract'],'UNKNOWN')
if __name__=='__main__':unittest.main()
