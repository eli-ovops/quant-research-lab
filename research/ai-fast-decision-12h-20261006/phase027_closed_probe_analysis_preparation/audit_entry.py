from pathlib import Path
import json,gzip,hashlib
import state_v3 as schema
from incremental_state import IncrementalState
from analyze import check_timing
B=Path(__file__).resolve().parent
def main():
 p=json.loads((B/'protocol.json').read_text())
 if p.get('mode')!='AUTHORIZED_CLOSED_ANALYSIS':raise RuntimeError('PREPARE_ONLY_NO_AUDIT_RUN')
 source=Path(p['source']);records=[json.loads(x) for x in (source/'local_processing_timing.jsonl').read_text().splitlines()];selected={}
 for asset in p['assets']:
  allasset=[r for r in records if r.get('asset')==asset]
  if not allasset:continue
  for r in [allasset[0],allasset[len(allasset)//2],allasset[-1]]:selected[r['source']['local_ordinal']]=r
 registry=json.loads((B/'instruments.json').read_text());cache=IncrementalState(registry);hash_checked=fail_checked=0
 with gzip.open(source/'raw/ws_messages.jsonl.gz','rb') as raw:
  for line in raw:
   row=json.loads(line);cache.ingest(row)
   if row['local_ordinal'] not in selected:continue
   record=selected[row['local_ordinal']];check_timing(record,row)
   if record['state_valid']:
    state=cache.snapshot(feature_ns=record['snapshot']['end_OS_ns'],is_live=False);state['evidence_label']=record['kind'];schema.validate(state);assert schema.digest(state)==record['state_sha256'];hash_checked+=1
   else:assert record['state_sha256'] is None;fail_checked+=1
 (B/'local_timing_field_audit.json').write_text(json.dumps({'status':'PASS_FINITE_FIXED_FIRST_MIDDLE_LAST_PER_ASSET_STATE_HASH_AND_TIME','valid_hash_samples':hash_checked,'invalid_unavailable_samples':fail_checked,'sourceordinals':sorted(selected),'no_audit_now_clock_substituted':True,'actual_model_latency':None,'not_full_live_or_trade_certification':True},indent=2))
if __name__=='__main__':main()
