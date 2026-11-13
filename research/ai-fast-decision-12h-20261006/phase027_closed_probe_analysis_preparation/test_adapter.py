from pathlib import Path
import json,unittest
from analyze import require_execution,check_timing,check_invalid_timing,stats,pressure_summaries
from frozen_pressure_rules import PressureRules
B=Path(__file__).resolve().parent
class T(unittest.TestCase):
 def test_prepare_gate_and_original_rulecut_bound(self):
  p=json.loads((B/'protocol.json').read_text());self.assertRaises(RuntimeError,require_execution,p);fr=json.loads((B.parent/'phase026_shock_pressure_transition_preparation/execution_freeze.json').read_text());self.assertEqual(p['rule_cut_OS_shared_ns'],fr['frozen_OS_shared_ns']);self.assertEqual((B/'frozen_pressure_rules.py').read_bytes(),(B.parent/'phase026_shock_pressure_transition_preparation/pressure_rules.py').read_bytes());self.assertEqual(p['rule_cut_OS_shared_ns'],29136966188000)
 def test_clockchain_ages_state_separate(self):
  row={'local_ordinal':1,'run_id':'r','connectionId':'c','clock_domain_id':'d','boot_identity':'b','os_shared_ns':10,'receive_wall_ns':1000};r={'source':row,'ingest':{'start_OS_ns':11,'end_OS_ns':12,'elapsed_ns':1,'error':None},'snapshot':{'start_OS_ns':13,'end_OS_ns':14,'elapsed_ns':1,'error':{'type':'COLD'}},'validate':None,'canonical':None,'ready_actual_OS_ns':15,'source_age_at_ready_ns':5,'latest_book_shared_ns':10,'latest_book_age_at_ready_ns':5,'ages_within250ms':True,'state_valid':False,'ready_state_and_ages':False,'provider_model_calls':0,'send_timestamp':None,'is_live':False};self.assertTrue(check_timing(r,row));r['ready_state_and_ages']=True;self.assertRaises(ValueError,check_timing,r,row)
 def test_null_zeroevent_and_cut_constructor(self):
  self.assertIsNone(stats([])['mean']);p=json.loads((B/'protocol.json').read_text());rules=PressureRules(json.loads((B/'instruments.json').read_text()),p['rule_domain'],forward_cut_ns=p['rule_cut_OS_shared_ns']);self.assertEqual(rules.forward_cut_ns,p['rule_cut_OS_shared_ns']);self.assertFalse(rules.cool)
  aa,ss=pressure_summaries([],[],p['assets']);self.assertEqual(len(aa),540);self.assertEqual(len(ss),1080);self.assertTrue(all(x['total']==0 and x['mean'] is None for x in aa+ss))
 def test_invalid_ingest_source_timing_not_skipped(self):
  row={'local_ordinal':1,'run_id':'r','connectionId':'c','clock_domain_id':'d','os_shared_ns':10};r={'source':row,'ingest':{'start_OS_ns':11,'end_OS_ns':12,'elapsed_ns':1,'error':{'type':'INVALID'}}};self.assertTrue(check_invalid_timing(r,row));r['ingest']['elapsed_ns']=2;self.assertRaises(ValueError,check_invalid_timing,r,row)
if __name__=='__main__':unittest.main()
