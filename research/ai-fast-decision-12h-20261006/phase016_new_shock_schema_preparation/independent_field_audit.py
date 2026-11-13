from pathlib import Path
from decimal import Decimal as D
from fractions import Fraction as F
import gzip,json,hashlib
B=Path(__file__).resolve().parent
def main():
 p=json.loads((B/'protocol.json').read_text());fr=json.loads((B/'execution_freeze.json').read_text())
 for n,h in fr['hashes'].items():assert hashlib.sha256((B/n).read_bytes()).hexdigest()==h
 receipt=json.loads((B/'historical_provenance_receipt.json').read_text());s=json.loads((B/'historical_WAIT_state.json').read_text());rows=[]
 with gzip.open(receipt['source_readonly'],'rb') as f:
  for line in f:
   rows.append(json.loads(line))
   if len(rows)==113:break
 source=rows[-1];assert s['source']['os_shared_ns']==source['os_shared_ns'] and s['source']['local_ordinal']==113
 for key in ['current_book','reference_book']:
  obj=s[key];row=rows[obj['provenance']['local_ordinal']-1];record=json.loads(row['raw'])['data'][0];assert obj['asks']==record['asks'] and obj['bids']==record['bids'];assert obj['raw_record']==record;assert obj['provenance']['run_id']==row['run_id'] and obj['provenance']['os_shared_ns']==row['os_shared_ns']
 unit=F(D(s['contract_spec']['ctVal']))*F(D(s['contract_spec']['ctMult']));total=net=F(0)
 for r in rows:
  if r['instId']!=s['asset'] or r['channel']!='trades' or not source['os_shared_ns']-1000000000<r['os_shared_ns']<=source['os_shared_ns']:continue
  for tr in json.loads(r['raw']).get('data',[]):
   amount=F(D(tr['px']))*F(D(tr['sz']))*unit;total+=amount;net+=amount*(1 if tr['side']=='buy' else -1)
 assert total==F(s['received_flow_total_exact']) and net==F(s['received_flow_net_exact']);assert not s['eligibility'] and not s['is_live']
 env=json.loads((B/'historical_WAIT_envelope.json').read_text());assert env['payload'] is None and env['sendable_payload'] is None;synthetic=json.loads((B/'SYNTHETIC_NOT_MODEL_RUN_qualified_history_DRAFT_ONLY.json').read_text());assert synthetic['state']['evidence_label']=='SYNTHETIC_NOT_MODEL_RUN' and synthetic['payload'] is None and synthetic['sendable_payload'] is None and synthetic['offline_draft_payload'] is not None
 audit={'status':'PASS_FINITE_ORIGINAL_PREFIX_FIELDS_FLOW_AND_DRAFT_ISOLATION','raw_prefix_rows':113,'source_current_reference_content_match':True,'received1s_exact_total_net_recomputed':True,'historic_unqualified_requestpayload_null':True,'qualified_historic_fixture_onlydraft':True,'transport_disabled':True,'actual_new_execution_book_hash_capacity':'NOT_IMPLEMENTED runtimeclaimsnotrealquoteverification','real_provider_or_latency':None,'not_thirdparty_fullpipeline':True};(B/'audit.json').write_text(json.dumps(audit,indent=2));print(audit)
if __name__=='__main__':main()
