from pathlib import Path
import json,hashlib,subprocess,datetime
P=Path(__file__).resolve().parent
def validate_root_receipt(p,root):
 if root.get('status')!='PASS_FULL_GZIP_CRC_EOF_IDENTITY_COUNTS_TERMINAL' or root.get('source_run')!=p['expectedrun'] or root.get('raw_logical_sha256')!=p['sourcehash_terminal_pending'] or root.get('pid_absent') is not True or type(root.get('owner_session_exit_code')) is not int or root['owner_session_exit_code']!=0 or root.get('owner_session')!=75708:raise ValueError('ROOT_ACTUAL_TERMINAL_SCHEMA_BINDING')
 if type(root.get('messages')) is not int or root['messages']<=0 or type(root.get('logical_bytes')) is not int or not isinstance(root.get('data_counts'),dict) or len(root['data_counts'])!=18 or not isinstance(root.get('ack_counts'),dict) or len(root['ack_counts'])!=18 or any(type(v) is not int or v!=1 for v in root['ack_counts'].values()):raise ValueError('ROOT_COUNTS_SCHEMA')
 return True
def require_closed(p):
 if p.get('mode')!='AUTHORIZED_CLOSED_TEN_RULE_RETEST':raise RuntimeError('PREPARE_ONLY_NO_LIVE_ECONOMIC_READ')
 if not isinstance(p.get('sourcehash_terminal_pending'),str) or len(p['sourcehash_terminal_pending'])!=64:raise ValueError('SOURCE_HASH_NOT_BOUND')
 if type(p.get('owner_session_exit_code')) is not int or p['owner_session_exit_code']!=0 or not p.get('root_terminal_receipt'):raise ValueError('OWNER_SESSION_OR_ROOT_TERMINAL_NOT_BOUND')
 root=json.loads(Path(p['root_terminal_receipt']).read_text())
 validate_root_receipt(p,root)
 directory=Path(p['source']);identity=json.loads((directory/'collector_identity.json').read_text());final=json.loads((directory/'collector_final.json').read_text());ps=subprocess.run(['ps','-p',str(identity['pid']),'-o','pid=,command='],capture_output=True,text=True)
 if final['status']!='STOPPED' or ps.returncode!=1 or ps.stdout.strip() or ps.stderr.strip() or identity['run_id']!=p['expectedrun'] or identity['clock_domain_id']!=p['expected_domain'] or final['run_id']!=identity['run_id']:raise ValueError('TERMINAL_IDENTITY_OR_PS_UNKNOWN')
 return identity,final
def main():
 p=json.loads((P/'protocol.json').read_text());identity,final=require_closed(p)
 freeze=json.loads((P/'execution_freeze.json').read_text())
 for n,h in freeze['hashes'].items():assert hashlib.sha256((P/n).read_bytes()).hexdigest()==h
 for directory,filename,mode,key in [('eight_fixed','evaluate_shock.py','AUTHORIZED_CLOSED_EVALUATION','raw_logical_sha256'),('pressure_fixed','raw_replication.py','AUTHORIZED_CLOSED_REPLICATION','source_raw_sha256')]:
  cp=json.loads((P/directory/'protocol.json').read_text())
  if cp['mode']!=mode or cp[key]!=p['sourcehash_terminal_pending']:raise ValueError('CHILD_BINDING_MODE_OR_HASH_NOT_FROZEN')
  subprocess.run(['python3',filename],cwd=P/directory,check=True,timeout=1200)
 eight=json.loads((P/'eight_fixed/results.json').read_text());pressure=json.loads((P/'pressure_fixed/results.json').read_text())
 eight.update(status='CLOSED_JOB013_FIXED_EIGHT_CONTEXT_RULES',current_source_run_id=identity['run_id'],current_source_start_utc=identity['start_utc'],current_source_directory=p['source'],source_error=final.get('error'),actual_source_reason=final.get('stop_reason_planned_untilfinal'),schema_cut_later_than_capture_start=datetime.datetime.fromisoformat(json.loads((P/'eight_fixed/protocol.json').read_text())['schema016_freeze_UTC'])>datetime.datetime.fromisoformat(identity['start_utc']))
 result={'status':'CLOSED_JOB013_FIXED_TEN_RULES_CONDITIONAL','source_run':identity['run_id'],'source_error':final.get('error'),'actual_source_reason':final.get('stop_reason_planned_untilfinal'),'eight_fixed_result':eight,'pressure_fixed_result':pressure,'source_episodes_notincome_sums':True,'actualprovider':None,'model_calls':0,'globalgoal':'ACTIVE'}
 (P/'results.json').write_text(json.dumps(result,indent=2)+'\n')
if __name__=='__main__':main()
