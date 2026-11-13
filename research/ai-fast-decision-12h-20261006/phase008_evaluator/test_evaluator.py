from pathlib import Path
from unittest.mock import patch
from types import SimpleNamespace
import unittest,json,gzip,tempfile,copy
from evaluator import guard_row,mature_source,select_matches
B=Path(__file__).resolve().parent;A='BTC-USDT-SWAP'
def identity():return {'pid':999999,'job_id':'SYNTHETIC','run_id':'r','clock_domain_id':'d','boot_identity':'b','source_sha256':'s'}
def good(n=1,conn='c'):
 return {'local_ordinal':n,'os_shared_ns':n*1000,'receive_wall_ns':1000000000+n,'receive_wall_ms':(1000000000+n)/1e6,'connectionId':conn,'clock_domain_id':'d','boot_identity':'b','run_id':'r','channel':'books5','instId':A,'raw':json.dumps({'arg':{'channel':'books5','instId':A},'data':[{'asks':[['101','10']],'bids':[['100','10']]}]})}
def source(d,rows):
 p=Path(d);p.mkdir(exist_ok=True);i=identity();(p/'collector_identity.json').write_text(json.dumps(i));data=b''.join((json.dumps(x)+'\n').encode() for x in rows);(p/'raw').mkdir();(p/'raw/ws_messages.jsonl.gz').write_bytes(gzip.compress(data));(p/'collector_final.json').write_text(json.dumps({**i,'status':'STOPPED','messages':len(rows),'logical_JSONL_bytes':len(data),'gzip_file_bytes':(p/'raw/ws_messages.jsonl.gz').stat().st_size,'error':None}))
class T(unittest.TestCase):
 def test_bad_shapes_no_crash(self):
  r=good()
  for raw in ['[]','null',json.dumps({'arg':{},'data':None}),json.dumps({'arg':{'channel':'books5','instId':A},'data':[42]}),json.dumps({'arg':{'channel':'books5','instId':A},'data':[{'asks':[None],'bids':['x']} ]})]:
   self.assertTrue(guard_row({**r,'raw':raw},identity(),0,-1,[A]))
  self.assertTrue(guard_row([],identity(),0,-1,[A]))
 def test_prices_asset_clock_outer_and_wall(self):
  r=good()
  for change in [{'receive_wall_ms':float('nan')},{'receive_wall_ms':'1'},{'receive_wall_ms':0},{'os_shared_ns':None},{'os_shared_ns':'2'},{'instId':'wrong'}]:self.assertTrue(guard_row({**r,**change},identity(),0,-1,[A]))
  x=json.loads(r['raw']);x['data'][0]['asks'][0][0]='0';self.assertTrue(guard_row({**r,'raw':json.dumps(x)},identity(),0,-1,[A]));self.assertEqual(guard_row(r,identity(),0,-1,[A]),[])
  ctrl={**r,'channel':None,'instId':None,'raw':'pong'};self.assertEqual(guard_row(ctrl,identity(),0,-1,[A]),[]);del ctrl['instId'];self.assertTrue(guard_row(ctrl,identity(),0,-1,[A]))
 def test_bad_cursor_cannot_poison_later(self):
  with tempfile.TemporaryDirectory(dir=B) as d:
   bad={**good(2),'local_ordinal':'2','os_shared_ns':None};source(d,[good(1),bad,good(3)])
   with patch('evaluator.subprocess.run',return_value=SimpleNamespace(returncode=1,stdout='',stderr='')):
    seg,receipt=mature_source(d,[A],'d')
   self.assertTrue(receipt['invalid_rows']);self.assertEqual(receipt['rows'],3)
 def test_ps_error_and_mixed_receipt_unknown(self):
  with tempfile.TemporaryDirectory(dir=B) as d:
   source(d,[good()])
   with patch('evaluator.subprocess.run',return_value=SimpleNamespace(returncode=2,stdout='',stderr='error')):self.assertEqual(mature_source(d,[A],'d')[1]['status'],'PS_QUERY_UNKNOWN')
   p=Path(d)/'collector_final.json';f=json.loads(p.read_text());f['run_id']='other';p.write_text(json.dumps(f));self.assertEqual(mature_source(d,[A],'d')[1]['status'],'MATURITY_RECEIPT_IDENTITY_MISMATCH')
 def test_connection_segments_closed_no_crossfill(self):
  with tempfile.TemporaryDirectory(dir=B) as d:
   source(d,[good(1,'old'),good(2,'new')])
   with patch('evaluator.subprocess.run',return_value=SimpleNamespace(returncode=1,stdout='',stderr='')):segs,rec=mature_source(d,[A],'d')
   self.assertEqual(len(segs),2);self.assertEqual(segs[0][0]['connectionId'],'old')
 def test_match_first_before_unmatched_notzero(self):
  target={'event_id':1,'family':'BTC_TRANSMISSION','asset':'ETH-USDT-SWAP','asof_ordinal':3,'asof_ms':300,'self_momentum_baseline_direction':0};byord={3:{'receive_wall_ns':1300000000}};key=('ETH-USDT-SWAP',1,0)
  m=select_matches({key:{'control_id':1,'asof_ordinal':1,'asof_ms':100}},[target],byord);self.assertEqual(m[0]['control']['control_id'],1)
  m=select_matches({key:{'control_id':4,'asof_ordinal':4,'asof_ms':400}},[target],byord);self.assertIsNone(m[0]['control']);self.assertEqual(m[0]['match_status'],'UNMATCHED')
 def test_unmature_no_result_not_empty_profit(self):
  with tempfile.TemporaryDirectory(dir=B) as d:self.assertIsNone(mature_source(d,[A],'d')[0])
if __name__=='__main__':unittest.main()

