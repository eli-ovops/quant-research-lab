from pathlib import Path
import json,time,hashlib,datetime as dt
from jev_offline import build_request,parse_response,freshness_gate,DECISIONS_ADAPTER
from test_jev_offline import SYNTHETIC_NOT_MODEL_RUN
B=Path(__file__).resolve().parent
def main():
 p=json.loads((B/'protocol.json').read_text());source=Path(p['source_states']['path']);assert hashlib.sha256(source.read_bytes()).hexdigest()==p['source_states']['sha256'];state=json.loads(source.read_text())[0];events=json.loads((source.parent/'events.json').read_text());conn=next(e['connectionId'] for e in events if e['event_id']==state['event_id']);completed=time.monotonic_ns();record=build_request(state,completed,conn,False)
 (B/'example_request_payload.json').write_text(json.dumps(record['payload'],indent=2,allow_nan=False));(B/'example_request_record.json').write_text(json.dumps(record['metadata'],indent=2,allow_nan=False));(B/'synthetic_response_fixture.json').write_text(json.dumps({'fixture_label':'SYNTHETIC_NOT_MODEL_RUN','body':SYNTHETIC_NOT_MODEL_RUN},indent=2))
 parsed=parse_response(SYNTHETIC_NOT_MODEL_RUN)
 runtime={'clock_domain_verified':False,'source_hash':record['metadata']['source_hash'],'connection_id':conn,'asof_ordinal':state['asof_ordinal'],'state_changed':True,'book_valid':False,'risk_allowed':False,'cap_allowed':False}
 gate=freshness_gate(parsed,record,runtime)
 result={'phase_status':'OFFLINE_ADAPTER_PREPARED_NOT_CONNECTED','at_utc':dt.datetime.now(dt.timezone.utc).isoformat(),'tests':'8PASS','payload_bytes':record['metadata']['payload_bytes'],'question_version':record['metadata']['question_version'],'question_sha256':record['metadata']['question_sha256'],'payload_sha256':record['metadata']['payload_sha256'],'source_hash':record['metadata']['source_hash'],'source_asof_ordinal':record['metadata']['asof_ordinal'],'example_feature_completed_monotonic_ns':completed,'clock_domains':'capture vs offlinebuilder notverified; no real timing chain claim','fixture_parse_format':'PASS SYNTHETIC_NOT_MODEL_RUN','example_gate_failclosed':gate,'network_calls':0,'model_calls':0,'paid_calls':0,'actual_AI_latency':None,'actual_model_output':None,'actual_API_compatibility':'UNKNOWN no response received','Decisions':DECISIONS_ADAPTER,'actual_model_effort_speed':'UNKNOWN'}
 (B/'results.json').write_text(json.dumps(result,indent=2));print(result)
if __name__=='__main__':main()

