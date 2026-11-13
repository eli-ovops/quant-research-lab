from pathlib import Path
import json,unittest,hashlib,subprocess,sys,copy,tempfile
from probe_processing import require_network_authorization,require_completed_020,LocalProbe,validate_registration,absent_pid,physical_write_allowed
B=Path(__file__).resolve().parent
def fixture_rows():
 asset='DOGE-USDT-SWAP';rows=[]
 def add(t,ch,data):rows.append({'local_ordinal':len(rows)+1,'os_shared_ns':2000000000+t*1000000,'receive_wall_ns':1000000000000+t*1000000,'receive_wall_ms':1000000+t,'run_id':'SYNTHETIC','connectionId':'SYNTHETIC','clock_domain_id':'OS_CLOCK_MONOTONIC|boot=SYNTHETIC','boot_identity':'SYNTHETIC','instId':asset,'channel':ch,'raw':json.dumps({'arg':{'instId':asset,'channel':ch},'data':[data]})})
 add(0,'books5',{'asks':[['.10001','20']],'bids':[['.10000','20']]});add(0,'trades',{'tradeId':'1','px':'.10000','sz':'1','side':'buy','ts':'0'});add(1000,'books5',{'asks':[['.10051','20']],'bids':[['.10050','20']]});add(1000,'trades',{'tradeId':'2','px':'.10050','sz':'50','side':'buy','ts':'1000'});add(1100,'books5',{'asks':[['.10051','20']],'bids':[['.10050','20']]});return rows
class T(unittest.TestCase):
 def test_hard_network_prepare_gate_and_template_block(self):
  p=json.loads((B/'protocol.json').read_text());self.assertRaises(RuntimeError,require_network_authorization,p)
  for entry in ['probe_collector.py','collector_template_not_executable.py']:
   r=subprocess.run([sys.executable,str(B/entry)],capture_output=True,text=True);self.assertNotEqual(r.returncode,0);self.assertTrue('NO_NETWORK' in r.stderr);self.assertFalse((B/'collector_once.lock').exists())
 def test_020_prerequisite_default_not_complete(self):
  self.assertRaises(RuntimeError,require_completed_020,B.parent)
 def test_nine_specs_source_original_and_model_gap(self):
  actual=B.parent/'phase006_shared_capture/job008_after_fixed_meme_readiness/instruments.json';self.assertEqual((B/'instruments.json').read_bytes(),actual.read_bytes());s={x['instId']:x for x in json.loads((B/'instruments.json').read_text())};self.assertEqual(len(s),9);self.assertEqual(s['PEPE-USDT-SWAP']['ctVal'],'10000000');self.assertEqual(s['BONK-USDT-SWAP']['ctVal'],'100000');self.assertEqual(s['WIF-USDT-SWAP']['ctVal'],'1')
 def test_interface_cold_samples_1Hz_and_age_is_separate(self):
  rows=fixture_rows();identity={k:rows[0][k] for k in ['run_id','connectionId','clock_domain_id','boot_identity']};probe=LocalProbe(json.loads((B/'instruments.json').read_text()),identity,label='SYNTHETIC_INTERFACE_TEST_NOT_PUBLIC_LATENCY');samples=[]
  for row in rows:
   event=probe.on_received(row)
   if event:samples.append(event)
  self.assertEqual(len(samples),2);self.assertEqual(samples[0]['status'],'COLD');self.assertFalse(samples[0]['state_valid']);self.assertFalse(any(x['ready_state_and_ages'] for x in samples));self.assertTrue(all(x['send_timestamp'] is None and x['provider_model_calls']==0 for x in samples));self.assertEqual(probe.counts['received_rows'],5)
 def test_cold_fresh_age_not_state_ready_and_registration_guard(self):
  row=fixture_rows()[0];identity={k:row[k] for k in ['run_id','connectionId','clock_domain_id','boot_identity']};probe=LocalProbe(json.loads((B/'instruments.json').read_text()),identity,clock=lambda:2010000000,label='SYNTHETIC_INTERFACE_TEST');r=probe.on_received(row);self.assertEqual(r['status'],'COLD');self.assertTrue(r['ages_within250ms']);self.assertFalse(r['ready_state_and_ages']);p=json.loads((B/'protocol.json').read_text());validate_registration(p,json.loads((B/'instruments.json').read_text()));p.pop('assets');self.assertRaises(RuntimeError,validate_registration,p,[])
 def test_real_receipt_not_truthy_and_ps_unknown(self):
  from unittest.mock import patch
  import subprocess
  p={'execution_mode':'AUTHORIZED_PUBLIC_LOCAL_PROBE','network_activation_authorized':True,'root_authorization_evidence':'justaString'};self.assertRaises(RuntimeError,require_network_authorization,p,B.parent)
  with patch('subprocess.run',return_value=subprocess.CompletedProcess([],2,'','ps error')):self.assertRaises(RuntimeError,absent_pid,999)
 def test_caps_combined_and_finite30min_no_pnl(self):
  c=(B/'probe_collector.py').read_text();self.assertIn('startwall+1800',c);self.assertIn('logical+telemetry_bytes+len(enc)',c);self.assertIn('logical+telemetry_bytes+len(encoded)',c);self.assertIn('phase_physical_bytecap',c);self.assertIn('ssl.CERT_REQUIRED',c);self.assertIn("'check_hostname':True",c);self.assertIn('require_completed_020',c);self.assertNotIn('price_fee_delta',c);self.assertLess(c.index("if channel:counts"),c.index('record=probe.on_received'))
 def test_raw_and_telemetry_physical_beforewrite_no_bypass(self):
  self.assertTrue(physical_write_allowed(100,100,20,10,10));self.assertFalse(physical_write_allowed(239000000,100,20,10,1));self.assertFalse(physical_write_allowed(100,2146483648,20,10,1))
if __name__=='__main__':unittest.main()
