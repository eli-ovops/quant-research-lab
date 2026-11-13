from pathlib import Path
import json,datetime,subprocess
B=Path(__file__).resolve().parent
def metadata_for_source(protocol,identity):
 if protocol['run_id']!=identity['run_id']:raise ValueError('CURRENT_SOURCE_RUN_MISMATCH')
 start=datetime.datetime.fromisoformat(identity['start_utc']);schema=datetime.datetime.fromisoformat(protocol['schema016_freeze_UTC']);rule=datetime.datetime.fromisoformat(protocol['cost_rule_UTC'])
 return {'status':'CLOSED_JOB008_NINE_ASSET_FIXED_EIGHT_RULES_CONTEXT_AND_CONTROLS','current_source_run_id':identity['run_id'],'current_source_directory':protocol['source'],'current_source_start_utc':identity['start_utc'],'rule_cut_earlier_than_capture':rule<start,'schema_cut_later_than_capture_start':schema>start,'schema016_freeze_UTC':protocol['schema016_freeze_UTC'],'model_new3_registry':'NOT_VALIDATED V3.1originalsixonly','no_whole_source_model_or_blind_OOS':True,'actual_AI':None}
def main():
 p=json.loads((B/'protocol.json').read_text())
 if p.get('mode')!='AUTHORIZED_CLOSED_EVALUATION':raise RuntimeError('PREPARATION_ONLY_EVALUATION_NOT_AUTHORIZED_YET')
 directory=Path(p['source']);identity=json.loads((directory/'collector_identity.json').read_text());final=json.loads((directory/'collector_final.json').read_text());ps=subprocess.run(['ps','-p',str(identity['pid']),'-o','pid=,command='],text=True,capture_output=True)
 if final['status']!='STOPPED' or final['run_id']!=identity['run_id'] or ps.returncode!=1 or ps.stdout.strip() or ps.stderr.strip():raise RuntimeError('SOURCE_TERMINAL_NOT_VERIFIED')
 metadata=metadata_for_source(p,identity)
 import evaluate_shock
 evaluate_shock.main()
 r=json.loads((B/'results.json').read_text());r.update(metadata);r['publication_wrapper_revision']='CURRENT_IDENTITY_TIMING_METADATA_ONLY_V1';r['original_numeric_rule_core_unchanged']=True;(B/'results.json').write_text(json.dumps(r,indent=2))
if __name__=='__main__':main()
