from pathlib import Path
import unittest,json,copy
import state_v3 as old
from incremental_state import IncrementalState
B=Path(__file__).resolve().parent
def rows():
 result=[];asset='DOGE-USDT-SWAP'
 def add(ms,ch,data):result.append({'instId':asset,'channel':ch,'local_ordinal':len(result)+1,'os_shared_ns':2000000000+ms*1000000,'receive_wall_ns':1000000000000+ms*1000000,'receive_wall_ms':1000000+ms,'run_id':'TEST_RUN','connectionId':'TEST_CONN','clock_domain_id':'OS_CLOCK_MONOTONIC|boot=TEST_BOOT','boot_identity':'TEST_BOOT','raw':json.dumps({'arg':{'instId':asset,'channel':ch},'data':[data]})})
 def book(ms,bid,ask):add(ms,'books5',{'asks':[[ask,'20','0','1']],'bids':[[bid,'20','0','1']],'ts':str(ms)})
 book(0,'.10000','.10001');add(0,'trades',{'tradeId':'1','px':'.10000','sz':'1','side':'buy','ts':'0'});book(1000,'.10005','.10006');add(1000,'trades',{'tradeId':'2','px':'.10005','sz':'50','side':'buy','ts':'1000','count':'100'});book(1100,'.10050','.10051');return result
def registry():return json.loads((B/'instruments.json').read_text())
class T(unittest.TestCase):
 def test_fullcanonical_hash_and_state_equivalence(self):
  r=rows();cache=IncrementalState(registry())
  for index,row in enumerate(r,1):cache.ingest(row);self.assertEqual(cache.prefix_sha256(),old.digest(r[:index]))
  self.assertEqual(old.canonical(cache.snapshot()),old.canonical(old.from_causal_prefix(r,registry())));old.validate(cache.snapshot())
 def test_cold_and_history_TTL_no_fake_send(self):
  cache=IncrementalState(registry());cache.ingest(rows()[0]);self.assertRaises(ValueError,cache.snapshot)
  cache=IncrementalState(registry())
  for row in rows():cache.ingest(row)
  s=cache.snapshot();e=old.build_request(s);self.assertIsNone(e['sendable_payload']);self.assertFalse(e['metadata']['send_gate']['allowed'])
 def test_repeat_witness_not_doubled_conflict_not_hidden(self):
  r=rows();repeat=copy.deepcopy(r[3]);repeat.update(local_ordinal=6,os_shared_ns=3200000000,receive_wall_ns=1001200000000,receive_wall_ms=1001200);r.append(repeat);cache=IncrementalState(registry())
  for row in r:cache.ingest(row)
  self.assertEqual(old.canonical(cache.snapshot()),old.canonical(old.from_causal_prefix(r,registry())));conflict=copy.deepcopy(repeat);conflict.update(local_ordinal=7,os_shared_ns=3250000000,receive_wall_ns=1001250000000,receive_wall_ms=1001250);raw=json.loads(conflict['raw']);raw['data'][0]['sz']='51';conflict['raw']=json.dumps(raw);cache.ingest(conflict);self.assertRaises(ValueError,cache.snapshot)
 def test_clock_identity_and_invalid_price_fail_closed(self):
  for change in [{'clock_domain_id':'legacy-process'},{'connectionId':'other'},{'os_shared_ns':1},{'local_ordinal':99},{'future_path_PnL':1}]:
   cache=IncrementalState(registry());r=rows();cache.ingest(r[0]);bad={**r[1],**change};self.assertRaises(ValueError,cache.ingest,bad);self.assertRaises(ValueError,cache.snapshot)
  cache=IncrementalState(registry());bad=rows()[0];o=json.loads(bad['raw']);o['data'][0]['asks'][0][0]='-1';bad['raw']=json.dumps(o);self.assertRaises(ValueError,cache.ingest,bad)
 def test_reference_and_exact_window_boundary(self):
  r=rows();later=copy.deepcopy(r[-1]);later.update(local_ordinal=6,os_shared_ns=4000000000,receive_wall_ns=1002000000000,receive_wall_ms=1002000);r.append(later);cache=IncrementalState(registry())
  for row in r:cache.ingest(row)
  self.assertEqual(old.canonical(cache.snapshot()),old.canonical(old.from_causal_prefix(r,registry())));self.assertEqual(cache.snapshot()['received_flow_records'],[])
 def test_ingest_failure_timing_saved_before_stop(self):
  import tempfile
  from measure_incremental import save_ingest_failure
  with tempfile.TemporaryDirectory(dir=B) as directory:
   receipt={'start_OS_ns':1,'end_OS_ns':2,'elapsed_ms':.000001,'error':{'type':'SYNTHETIC','message':'TEST_ONLY'}};save_ingest_failure(directory,{'local_ordinal':3},receipt,[]);r=json.loads((Path(directory)/'failure_receipt.json').read_text());self.assertEqual(r['row_ordinal'],3);self.assertEqual(r['timing'],receipt);self.assertEqual(r['prior_completed_samples'],0)
if __name__=='__main__':unittest.main()
