import time
def shared_ns():
 if not hasattr(time,'CLOCK_MONOTONIC') or not hasattr(time,'clock_gettime_ns'):raise RuntimeError('SHARED_OS_CLOCK_UNAVAILABLE')
 return time.clock_gettime_ns(time.CLOCK_MONOTONIC)
def sample(run_id,boot_identity):
 return {'os_shared_ns':shared_ns(),'process_monotonic_ns':time.monotonic_ns(),'wall_ns':time.time_ns(),'clock_domain':'OS_CLOCK_MONOTONIC|boot='+boot_identity,'clock_domain_id':'OS_CLOCK_MONOTONIC|boot='+boot_identity,'boot_identity':boot_identity,'run_id':run_id}
def pair_delta(start,end,max_ns=None):
 for s in [start,end]:
  if not isinstance(s.get('os_shared_ns'),int):raise ValueError('MISSING_SHARED_CLOCK')
 if start.get('clock_domain')!=end.get('clock_domain') or start.get('boot_identity')!=end.get('boot_identity') or start.get('run_id')!=end.get('run_id'):raise ValueError('CLOCK_DOMAIN_MISMATCH')
 delta=end['os_shared_ns']-start['os_shared_ns']
 if delta<0:raise ValueError('NEGATIVE_SHARED_DELTA')
 if max_ns is not None and delta>max_ns:raise ValueError('TIMEOUT')
 return delta
def check_parent_child(before,child,after):
 if child['clock_domain']!=before['clock_domain'] or after['clock_domain']!=before['clock_domain']:raise ValueError('CLOCK_DOMAIN_MISMATCH')
 if not before['os_shared_ns']<=child['os_shared_ns']<=after['os_shared_ns']:raise ValueError('CHILD_OUTSIDE_PARENT_INTERVAL')
 return True
def in_deadline(now_ns,deadline_ns):return now_ns<deadline_ns
def causal_shared_gate(request,runtime,proof):
 reasons=[]
 try:
  checks=proof['checks'];expected=checks[0]['parent_before']['clock_domain_id']
  if len(checks)<2:raise ValueError('INSUFFICIENT_REAL_CLOCK_PROOF')
  for c in checks:check_parent_child(c['parent_before'],c['child']['sample'],c['parent_after'])
  if request.get('clock_domain_id')!=expected or runtime.get('clock_domain_id')!=expected:reasons.append('CLOCK_DOMAIN_MISSING_OR_MISMATCH')
 except (KeyError,ValueError,TypeError):reasons.append('CLOCK_PROOF_INVALID')
 keys=['source_asof_shared_ns','feature_completed_shared_ns','request_sent_shared_ns','response_completed_shared_ns','new_book_shared_ns','now_shared_ns']
 try:
  vals=[request[k] for k in keys[:2]]+[runtime[k] for k in keys[2:]]
  if any(isinstance(v,bool) or not isinstance(v,int) for v in vals):raise ValueError('MISSING_SHARED_CLOCK')
  source,feature,sent,done,book,now=vals
  if not source<=feature<=sent<=done<book<=now:reasons.append('CAUSAL_SHARED_TIME_ORDER')
  if done-sent>1000000000:reasons.append('RESPONSE_TIMEOUT')
  if now-book>250000000 or book-done>250000000:reasons.append('EXPIRED_NEW_BOOK')
 except (KeyError,TypeError,ValueError):reasons.append('SHARED_FIELDS_MISSING_OR_INVALID')
 return {'accepted_clock_chain':not reasons,'action_on_failure':'WAIT','reasons':reasons,'not_complete_risk_or_provider_validation':True}
