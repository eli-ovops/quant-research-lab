from orchestrator import *
import unittest,copy
BASE=1000000000000
def state(ordinal=1,asof=BASE,candidate='FLOW_V1'):
 f={'flow_imb1':.9,'impulse1_bps':4,'top3_imb':.9,'opposing_ratio':.4,'stable_prices':True,'impulse500_bps':.5,'btc_impulse1_bps':4,'btc_flow_imb1':.9,'leader_gap_bps':3,'follower_impulse1_bps':.5,'ref1_ns':asof-1000000000,'ref500_ns':asof-500000000,'leader_ref1_ns':asof-1000000000}
 return {'schema':VERSION,'candidate':candidate,'asset':'ETH-USDT-SWAP','source':{'run_id':'SYNTHETIC','connectionId':'TEST','clock_domain_id':'SYNTHETIC','boot_identity':'TEST','ordinal':ordinal,'asof_ns':asof,'latest_book_ns':asof,'feature_completed_ns':asof+1000000},'feature_evidence_sha':'a'*64,'features':f,'contract_sha':digest(SPECS['ETH-USDT-SWAP']),'direction':1,'current_book':book(asof,ordinal)}
def response(action='FOLLOW'):
 return {'model':MODEL,'answers':{'action':{'type':'choice','choice':action,'probabilities':{'WAIT':.2,'FOLLOW':.6,'FADE':.2},'confidence':.7}},'usage':{'input_tokens':100,'output_tokens':10}}
def book(ns,ordinal,price=100):
 return {'asset':'ETH-USDT-SWAP','run_id':'SYNTHETIC','connectionId':'TEST','clock_domain_id':'SYNTHETIC','boot_identity':'TEST','ordinal':ordinal,'received_ns':ns,'asks':[[str(price+.01),'1000']],'bids':[[str(price-.01),'1000']]}
class Tests(unittest.TestCase):
 def test_real_never_calls_or_injects(self):
  e=Experiment();id=e.submit(state(),BASE+2000000);self.assertEqual(e.actual_api_calls,0);self.assertTrue(all('DISABLED' in r['status'] for r in e.ledger))
  with self.assertRaises(RuntimeError):e.fixture_response(id,response(),BASE+50000000)
  with self.assertRaises(RuntimeError):real_transport()
 def test_three_candidates_and_nested_extra_rejected(self):
  for c in CANDIDATES:self.assertTrue(validate_state(state(candidate=c)))
  s=state();s['source']['diagnostic_note']='After entry price increases'
  with self.assertRaises(ValueError):request(s)
  s=state();s['features']['future_return']=1
  with self.assertRaises(ValueError):request(s)
 def test_immediate_vs_matched_realcompletion(self):
  e=Experiment(True);id=e.submit(state(),BASE+2000000);e.book(book(BASE+10000000,2));e.fixture_response(id,response(),BASE+100000000,api_cost_quote=.01);e.book(book(BASE+120000000,3));entries=[r for r in e.ledger if r['status']=='PAPER_ENTRY_FIXTURE_ONLY'];times={r['arm']:r['entry_ns'] for r in entries};self.assertEqual(times['RULE_IMMEDIATE_NO_AI'],BASE+10000000);self.assertEqual(times['RULE_MATCHED_NO_AI'],BASE+120000000);self.assertEqual(times['JEV'],BASE+120000000)
 def test_first_after_not_earlier_and_sameqty_accounting(self):
  e=Experiment(True);id=e.submit(state(),BASE+2000000);e.book(book(BASE+90000000,2));e.fixture_response(id,response(),BASE+100000000,api_cost_quote=.01);self.assertFalse(any(r['status']=='PAPER_ENTRY_FIXTURE_ONLY' and r['arm'] in ['JEV','RULE_MATCHED_NO_AI'] for r in e.ledger));e.book(book(BASE+120000000,3));e.book(book(BASE+[REDACTED_PHONE],4,101));rows=[r for r in e.ledger if r['status']=='PAPER_EXIT_FIXTURE_ONLY'];self.assertEqual(len(rows),3)
  for r in rows:self.assertEqual(F(r['price_fee_delta']),F(r['gross'])-F(r['fees']))
  self.assertTrue(any(r['status']=='FIXTURE_API_COST_DEBIT' for r in e.ledger))
 def test_timeout_error_wait_and_api_cost_logged(self):
  e=Experiment(True);id=e.submit(state(),BASE+2000000);e.fixture_response(id,response(),BASE+2000000000,api_cost_quote=.02);self.assertTrue(any(r['status']=='FIXTURE_ERROR_OR_TIMEOUT' for r in e.ledger));self.assertEqual(e.actual_api_calls,0);self.assertEqual(e.cash[('FLOW_V1','JEV')],F(500)-F('.02'))
 def test_expired_first_quote_no_pick_later(self):
  e=Experiment(True);id=e.submit(state(),BASE+2000000);e.fixture_response(id,response(),BASE+100000000);e.book(book(BASE+500000000,2));e.book(book(BASE+510000000,3));self.assertFalse(any(r['status']=='PAPER_ENTRY_FIXTURE_ONLY' for r in e.ledger))
 def test_forward_cut_and_selected_candidate(self):
  e=Experiment(True);e.fixture_freeze('FLOW_V1',BASE)
  with self.assertRaises(ValueError):e.submit(state(),BASE+2000000)
  with self.assertRaises(ValueError):e.submit(state(2,BASE+1000000000,'BOOK_V1'),BASE+1002000000)
  self.assertTrue(e.submit(state(3,BASE+1000000000),BASE+1002000000))
  with self.assertRaises(RuntimeError):e.freeze_selection('FLOW_V1',BASE+1000000000,{'kind':'REAL_JEV_AUDITED_DEVELOPMENT','actual_calls':100,'eligible_trades':20,'api_cost_complete':True})
 def test_end_tail_unresolved_and_risk_oneposition(self):
  e=Experiment(True);id=e.submit(state(),BASE+2000000);e.fixture_response(id,response(),BASE+100000000);e.book(book(BASE+120000000,2));id2=e.submit(state(3,BASE+200000000),BASE+202000000);e.fixture_response(id2,response(),BASE+300000000);e.book(book(BASE+320000000,4));self.assertTrue(any(r['status']=='REJECTED_RISK_ONE_OPEN_ACCOUNT' for r in e.ledger));self.assertTrue(any(r['status']=='CENSORED_END_OPEN_POSITION_UNKNOWN_MARK' for r in e.end()))
 def test_fixed_fee_scenario(self):
  e=Experiment(True,5)
  with self.assertRaises(ValueError):e.book(book(BASE+10000000,2),10)
  self.assertEqual(Experiment(True,10).fee_each_bps,10)
 def test_completion_ttl_no_new_book_wash(self):
  e=Experiment(True);id=e.submit(state(),BASE+2000000);e.fixture_response(id,response(),BASE+300000000,api_cost_quote=.01);e.book(book(BASE+310000000,2));self.assertTrue(any('EXPIRED_AT_COMPLETION' in r.get('error','') for r in e.ledger));self.assertFalse(any(r['status']=='PAPER_ENTRY_FIXTURE_ONLY' and r['arm'] in ['JEV','RULE_MATCHED_NO_AI'] for r in e.ledger))
 def test_wait_cost_unknown_and_state_reject_auditable(self):
  e=Experiment(True);id=e.submit(state(),BASE+2000000);e.fixture_response(id,response('WAIT'),BASE+100000000,api_cost_quote=.03);self.assertEqual(e.cash[('FLOW_V1','JEV')],F(500)-F('.03'));e2=Experiment(True);id=e2.submit(state(),BASE+2000000);e2.fixture_response(id,response('WAIT'),BASE+100000000);self.assertFalse(e2.cash_complete[('FLOW_V1','JEV')]);s=state();s['features']['hidden_note']='later price'
  with self.assertRaises(ValueError):e.submit(s,BASE+2000000)
  self.assertEqual(e.ledger[-1]['status'],'REJECTED_STATE_CONTRACT')
 def test_unknown_then_known_cost_stays_incomplete(self):
  e=Experiment(True);a=e.submit(state(),BASE+2000000);e.fixture_response(a,response('WAIT'),BASE+100000000);b=e.submit(state(),BASE+2000000);e.fixture_response(b,response('WAIT'),BASE+100000000,api_cost_quote=.01);self.assertFalse(e.cash_complete[('FLOW_V1','JEV')]);self.assertEqual(e.cash[('FLOW_V1','JEV')],F(500)-F('.01'))
 def test_cost_input_and_book_provenance(self):
  payload=request(state());self.assertEqual(payload['state']['execution_cost_context']['fee_each_side_bps'],[5,10]);self.assertEqual(len(payload['state']['execution_cost_context']['asof_required_move_bps']),2);s=state();s['current_book']['connectionId']='WRONG'
  with self.assertRaises(ValueError):request(s)
if __name__=='__main__':unittest.main()
