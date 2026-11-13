from pathlib import Path
import json,hashlib
B=Path(__file__).resolve().parent
p=json.loads((B/'protocol.json').read_text());f=json.loads((B/'execution_freeze.json').read_text())
for n,h in f['hashes'].items():assert hashlib.sha256((B/n).read_bytes()).hexdigest()==h
records=json.loads((B/'timing_records.json').read_text());assert [(x['prefix_rows'],x['repetition']) for x in records]==[(n,r) for n in p['prefix_points'] for r in [1,2,3]]
receipts=0
for record in records:
 last=0
 for name in ['factory','validate','serialize_state','envelope','serialize_envelope']:
  x=record[name]
  if x is None:continue
  assert x['end_actual_OS_ns']>=x['start_actual_OS_ns']>=last;last=x['end_actual_OS_ns'];assert x['elapsed_ns']==x['end_actual_OS_ns']-x['start_actual_OS_ns'];assert x['elapsed_ms']==x['elapsed_ns']/1e6
  assert (x['status']=='PASS')==(x['error'] is None);receipts+=1
 assert record['historical_never_sent'];assert record['local_factory_within_250ms']==(record['factory']['elapsed_ns']<=250000000)
components=json.loads((B/'loading_components.json').read_text());loadchecked=0
for name in ['compressed_file_read_only','SHA_integrity_only','whole_closed_source_gzip_decompress_only','whole_closed_source_splitlines_only']:
 x=components[name];assert x['elapsed_ns']==x['end_actual_OS_ns']-x['start_actual_OS_ns'] and x['elapsed_ms']==x['elapsed_ns']/1e6;loadchecked+=1
for x in components['JSON_parse_fixedprefix_checkpoints']:assert x['JSON_parse_cumulative_ms']==(x['parse_end_actual_OS_ns']-x['parse_start_actual_OS_ns'])/1e6
assert [x['rows'] for x in components['JSON_parse_fixedprefix_checkpoints']]==p['prefix_points']
result={'status':'PASS_FINITE_REAL_TIMING_LOG_ARITHMETIC','fixed9repetitions_exact':True,'stage_receipts_checked':receipts,'loading_component_receipts_checked':loadchecked,'JSON_parse_points_checked':3,'load_not_in_factory_startend':True,'failure_test_receipt':'tests_stderr.log syntheticfailure only, noactualfactoryfailures','clock_namespace':'actual explicitOS CLOCK_MONOTONIC receipts; no mock provider clocks','source_core_rules_unchanged':True,'real_API_latency':None,'not_independent_livepipeline_benchmark':True};(B/'audit.json').write_text(json.dumps(result,indent=2));print(result)
