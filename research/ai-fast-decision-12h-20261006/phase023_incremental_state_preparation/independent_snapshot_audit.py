from pathlib import Path
from decimal import Decimal as D
from fractions import Fraction as F
import json,gzip,hashlib
from incremental_state import IncrementalState
B=Path(__file__).resolve().parent
def main():
 p=json.loads((B/'protocol.json').read_text());f=json.loads((B/'execution_freeze.json').read_text())
 for n,h in f['hashes'].items():assert hashlib.sha256((B/n).read_bytes()).hexdigest()==h
 timing=json.loads((B/'timing_records.json').read_text());registry=json.loads((B/'instruments.json').read_text());cache=IncrementalState(registry);rows=[];checks=[]
 with gzip.open(p['source'],'rb') as raw:
  for line in raw:
   row=json.loads(line);rows.append(row);cache.ingest(row)
   if len(rows) in p['fixedprefix_points']:
    state=cache.snapshot();encoded=json.dumps(state,sort_keys=True,separators=(',',':'),allow_nan=False).encode();golden=[x for x in timing if x['rows']==len(rows)];assert all(hashlib.sha256(encoded).hexdigest()==x['reference_state_sha256']==x['entire_state_sha256'] for x in golden);prefix=json.dumps(rows,sort_keys=True,separators=(',',':'),allow_nan=False).encode();assert hashlib.sha256(prefix).hexdigest()==state['causal_prefix_sha256'];source=rows[-1];assert state['source']['os_shared_ns']==source['os_shared_ns'] and state['source']['receive_wall_ns']==source['receive_wall_ns']
    for side in ['current_book','reference_book']:
     obj=state[side];r=rows[obj['provenance']['local_ordinal']-1];record=json.loads(r['raw'])['data'][0];assert obj['raw_record']==record and obj['asks']==record['asks'] and obj['bids']==record['bids'];assert obj['provenance']['run_id']==r['run_id'] and obj['provenance']['clock_domain_id']==r['clock_domain_id']
    total=net=F(0);seen={};unit=F(D(state['contract_spec']['ctVal']))*F(D(state['contract_spec']['ctMult']))
    for r in rows:
     if r['instId']!=state['asset'] or r['channel']!='trades':continue
     for tr in json.loads(r['raw']).get('data',[]):
      key=(tr['tradeId'],tr.get('source'));signature=tuple(tr.get(k) for k in ['px','sz','side','ts','count'])
      if key in seen:assert signature==seen[key];continue
      seen[key]=signature
      if not source['os_shared_ns']-1000000000<r['os_shared_ns']<=source['os_shared_ns']:continue
      amount=F(D(tr['px']))*F(D(tr['sz']))*unit;total+=amount;net+=amount*(1 if tr['side']=='buy' else -1)
    assert F(state['received_flow_total_exact'])==total and F(state['received_flow_net_exact'])==net;(B/('audited_snapshot_'+str(len(rows))+'.json')).write_text(json.dumps(state,indent=2));checks.append({'rows':len(rows),'canonical_state_sha256':hashlib.sha256(encoded).hexdigest(),'original_reference_hash_same':True,'independent_fullprefix_json_SHA_same':True,'actual_raw_source_books_exactflow_checked':True})
   if len(rows)==max(p['fixedprefix_points']):break
 for x in timing:
  for key in ['hot_snapshot','validate','serialize']:
   r=x[key];assert r['elapsed_ms']==(r['end_OS_ns']-r['start_OS_ns'])/1e6
 assert all(x['canonical_equal'] and x['prefix_hash_equal'] and x['validate']['error'] is None for x in timing)
 result={'status':'PASS_FINITE_SNAPSHOT_SOURCE_HASH_FLOW_TIMING_AUDIT','checks':checks,'measured_samples':9,'old_reference_factory_not_rerun_by_audit':True,'audit_incremental_reingest_rows':len(rows),'measurement_ingest_once_separate':True,'broader_invalid_input_behavior':'newstrictsource guards safetystronger, not allinvalid errors equivalent','actual_API_or_liveTTL':None,'not_thirdparty_complete_live_replay':True};(B/'audit.json').write_text(json.dumps(result,indent=2));print(result)
if __name__=='__main__':main()
