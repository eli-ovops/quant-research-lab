from datetime import datetime
def terminal_metadata(identity,final,first_ns,last_ns):
 if final.get('status')!='STOPPED':raise ValueError('SOURCE_NOT_TERMINAL')
 for k in ['run_id','pid','clock_domain_id','boot_identity','stop_at_utc']:
  if identity.get(k)!=final.get(k):raise ValueError('FINAL_IDENTITY_MISMATCH:'+k)
 if type(first_ns) is not int or type(last_ns) is not int or last_ns<first_ns:raise ValueError('INVALID_REAL_CAPTURE_SPAN')
 error=final.get('error');reason=final.get('stop_reason',final.get('stop_reason_planned_untilfinal'));finished=final.get('finished_utc')
 if not finished:raise ValueError('MISSING_ACTUAL_FINISHED')
 end=datetime.fromisoformat(finished);stop=datetime.fromisoformat(identity['stop_at_utc'])
 if error:
  status='EARLY_FAILED_COHORT_NOT_COMPLETE'
  if error.get('type')=='WebSocketConnectionClosedException':status='NETWORK_LOSS_SHORT_COHORT_NOT_COMPLETE'
 elif reason in ['deadline','deadline_or_bytecap'] and end>=stop:status='DEADLINE_STOPPED_CONDITIONAL_CAPTURE'
 elif reason in ['bytecap','compressed_bytecap','compressed_or_global_bytecap']:status='BYTECAP_EARLY_STOPPED_CONDITIONAL_CAPTURE'
 else:status='STOPPED_REASON_UNKNOWN_NOT_FULL_DURATION_CERTIFIED'
 return {'status':status,'run_id':identity['run_id'],'pid':identity['pid'],'error':error,'stop_reason':reason,'start_utc':identity['start_utc'],'stop_at_utc':identity['stop_at_utc'],'finished_utc':finished,'actual_saved_span_seconds':(last_ns-first_ns)/1e9,'handler_exit0_not_capture_success':True,'point_diagnostic_not_rootcause_repaired':True,'not_blind_OOS_or_independentN':True}
