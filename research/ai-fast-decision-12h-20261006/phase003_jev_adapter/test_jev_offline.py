import unittest,json,copy
from jev_offline import *
SAFE={'asset':'BTC-USDT-SWAP','asof_ordinal':1,'asof_receive_monotonic_ms':0.,'asof_receive_wall_ms':0.,'quote_age_ms':0.,'impulse_bps':3.2,'flow_imbalance':.9,'flow_notional_USDT':10000,'direction':1,'asks_contracts':[['100','100','0','1']],'bids_contracts':[['99','100','0','1']],'contract_spec':{'ctVal':'.01','ctMult':'1','lotSz':'.01','minSz':'.01'},'fee_scenarios_each_side_bps':[5,10],'allowed_actions':['WAIT','FOLLOW','FADE']}
SYNTHETIC_NOT_MODEL_RUN={'model':MODEL,'answers':{'action':{'type':'choice','choice':'FOLLOW','probabilities':{'WAIT':.2,'FOLLOW':.7,'FADE':.1},'confidence':.81}},'usage':{'input_tokens':10,'output_tokens':3}}
def record():return build_request(SAFE,10,'synthetic_conn',True)
def clock(r):return {'clock_domain_verified':True,'source_hash':r['metadata']['source_hash'],'connection_id':'synthetic_conn','asof_ordinal':1,'state_changed':False,'request_sent_ns':20,'response_completed_ns':30,'new_book_received_ns':40,'now_ns':50,'new_book_ordinal':2,'book_valid':True,'risk_allowed':True,'cap_allowed':True}
class Test(unittest.TestCase):
 def test_request_fixed_and_no_future(self):
  r=record();self.assertEqual(r['payload']['model'],MODEL);self.assertEqual(set(r['payload']),{'model','state','questions'});self.assertEqual(r['metadata']['source_hash'],digest(r['payload']['state']))
  s=copy.deepcopy(SAFE);s['price_fee_delta_USDT']=1
  with self.assertRaises(ValueError):build_request(s,10,'x')
 def test_legal_fixture_format_only(self):
  a=parse_response(json.dumps(SYNTHETIC_NOT_MODEL_RUN));self.assertEqual(a['action'],'FOLLOW');self.assertTrue(a['confidence_is_not_trade_win_probability'])
 def test_probability_nan_range_sum_missing(self):
  for changes in [{'WAIT':float('nan'),'FOLLOW':.9,'FADE':.1},{'WAIT':-.1,'FOLLOW':1.,'FADE':.1},{'WAIT':.1,'FOLLOW':.1,'FADE':.1},{'WAIT':.1,'FOLLOW':.9}]:
   b=copy.deepcopy(SYNTHETIC_NOT_MODEL_RUN);b['answers']['action']['probabilities']=changes
   with self.assertRaises(ValueError):parse_response(json.dumps(b))
 def test_unknown_action_model_type_usage(self):
  for kind in ['action','model','type','usage']:
   b=copy.deepcopy(SYNTHETIC_NOT_MODEL_RUN)
   if kind=='action':b['answers']['action']['choice']='BUY'
   if kind=='model':b['model']='jev-latest'
   if kind=='type':b['answers']['action']['type']='score'
   if kind=='usage':b['usage']['input_tokens']=-1
   with self.assertRaises(ValueError):parse_response(b)
 def test_old_source_connection_asof(self):
  r=record();a=parse_response(SYNTHETIC_NOT_MODEL_RUN)
  for key,val in [('source_hash','old'),('connection_id','new'),('asof_ordinal',0),('state_changed',True)]:
   c=clock(r);c[key]=val;self.assertEqual(freshness_gate(a,r,c)['action'],'WAIT')
 def test_timeout_stale_and_before_response(self):
  r=record();a=parse_response(SYNTHETIC_NOT_MODEL_RUN)
  for changes in [{'response_completed_ns':1000000021,'new_book_received_ns':1000000030,'now_ns':1000000040},{'new_book_received_ns':30},{'new_book_received_ns':300000031,'now_ns':300000050},{'now_ns':300000050},{'new_book_ordinal':1}]:
   c=clock(r);c.update(changes);self.assertTrue(freshness_gate(a,r,c)['rejected'])
 def test_risk_never_increased_by_confidence(self):
  r=record();a=parse_response(SYNTHETIC_NOT_MODEL_RUN);self.assertFalse(freshness_gate(a,r,clock(r))['rejected']);c=clock(r);c['risk_allowed']=False;self.assertIn('risk_or_cap',freshness_gate(a,r,c)['reject_reasons'])
 def test_transport_disabled_and_Decisions_unknown(self):
  with self.assertRaises(RuntimeError):transport_disabled()
  self.assertEqual(DECISIONS_ADAPTER['status'],'NOT_IMPLEMENTED')
if __name__=='__main__':unittest.main()

