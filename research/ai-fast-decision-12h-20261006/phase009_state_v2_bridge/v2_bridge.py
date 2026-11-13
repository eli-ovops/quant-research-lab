import json,hashlib,math
from decimal import Decimal
from frozen_v1_parser import parse_response,MODEL,ACTIONS,canonical,digest
VERSION='stateV2.1_explicit_shared';QUESTION='impulse_suite_action_v2.1'
REQUIRED={'state_version','question_version','family','asset','asof_ordinal','clock_view','clock_domain_id','capture_run_id','connectionId','source_asof_shared_ns','source_latest_book_shared_ns','feature_completed_shared_ns','source_receive_wall_ns','is_live','quote_age_ms','impulse_bps','flow_imbalance','flow_received_notional_USDT','direction','asks_contracts','bids_contracts','contract_spec','fee_each_side_bps_assumptions','allowed_actions'}
OPTIONAL={'top3_imbalance','opposing_depth_ratio','leader_gap_bps','leader_impulse_bps','self_momentum_baseline_direction','legacy_source_process_monotonic_ns'}
BANNED={'future','outcomes','outcome','pnl','profit','price_fee_delta_usdt','entry_vwap','exit_vwap','gross_price_delta_usdt','net_trade_pnl','netr','control_outcomes','holding_window_overlap','mean_event_delta','asof_receive_monotonic_ms','asof_receive_wall_ms'}
INSTRUCTIONS='Choose WAIT, FOLLOW, or FADE from only the received family state. FOLLOW follows its stated direction; FADE opposes it. Consider both entry and exit taker costs and visible spread/depth. WAIT when evidence or cost-adjusted space is insufficient. Visible book depletion is not proven cancellation or intent; beta1 receive gap is not proven leadership or arbitrage. No future outcomes, guaranteed price prediction, or risk increase.'
CRITERIA={'WAIT':'Uncertain, stale, conflicting, or insufficient space after both legs costs.','FOLLOW':'Current family evidence supports continuation in its stated direction beyond both legs costs.','FADE':'Current family evidence supports reversal against its stated direction beyond both legs costs.'}
def no_future(x):
 if isinstance(x,dict):
  for k,v in x.items():
   if k.lower() in BANNED or k.lower().startswith(('future_','break_even_fee')):raise ValueError('FORBIDDEN_FIELD:'+k)
   no_future(v)
 elif isinstance(x,list):
  for v in x:no_future(v)
 elif isinstance(x,float) and not math.isfinite(x):raise ValueError('NONFINITE')
def from_causal_snapshot(snapshot,event,source_row,book_row,feature_completed_shared_ns=None):
 if source_row['local_ordinal']!=event['asof_ordinal'] or book_row['local_ordinal']!=event['latest_book_ordinal'] or book_row['local_ordinal']>source_row['local_ordinal']:raise ValueError('WRONG_OR_FUTURE_SOURCE_ROW')
 expected_run=source_row.get('run_id',source_row.get('connection_local_id'))
 expected_domain=source_row.get('clock_domain_id') if 'os_shared_ns' in source_row else 'legacy-process|'+str(source_row.get('connection_local_id'))
 for x in [snapshot,event]:
  if x.get('capture_run_id')!=expected_run or x.get('clock_domain_id')!=expected_domain:raise ValueError('PROVENANCE_RUN_OR_DOMAIN')
 if book_row.get('run_id',book_row.get('connection_local_id'))!=expected_run:raise ValueError('BOOK_RUN_MISMATCH')
 if 'os_shared_ns' in source_row:
  if book_row.get('clock_domain_id')!=expected_domain or not isinstance(source_row['os_shared_ns'],int) or not isinstance(book_row.get('os_shared_ns'),int) or not book_row['os_shared_ns']<=source_row['os_shared_ns']:raise ValueError('BOOK_SHARED_DOMAIN_OR_ORDER')
  if snapshot.get('source_asof_shared_ns')!=source_row['os_shared_ns'] or event.get('source_asof_shared_ns')!=source_row['os_shared_ns'] or snapshot.get('source_latest_book_shared_ns')!=book_row['os_shared_ns']:raise ValueError('ASOF_SHARED_CONTENT_MISMATCH')
 else:
  if snapshot.get('clock_view')!='LEGACY_INTERNAL' or snapshot.get('is_live') or book_row.get('monotonic_ns',-1)>source_row['monotonic_ns']:raise ValueError('LEGACY_ONLY_HISTORICAL')
 try:
  data=json.loads(book_row['raw'])['data'][0]
  for side,key in [('asks','asks_contracts'),('bids','bids_contracts')]:
   expected=[[Decimal(x[0]),Decimal(x[1])] for x in data[side]];actual=[[Decimal(x[0]),Decimal(x[1])] for x in snapshot[key]]
   if actual!=expected:raise ValueError('BOOK_CONTENT_MISMATCH')
 except (KeyError,IndexError,TypeError):raise ValueError('BOOK_CONTENT_MISSING')
 if source_row['instId']!=snapshot['asset'] or book_row['instId']!=snapshot['asset'] or source_row['connectionId']!=book_row['connectionId']:raise ValueError('SOURCE_ASSET_OR_CONNECTION')
 s={k:v for k,v in snapshot.items() if k in REQUIRED|OPTIONAL};s.update(state_version=VERSION,question_version=QUESTION,capture_run_id=source_row.get('run_id',source_row.get('connection_local_id')),source_receive_wall_ns=source_row['receive_wall_ns'],flow_received_notional_USDT=event['flow_total_USDT'],source_asof_shared_ns=source_row.get('os_shared_ns'),source_latest_book_shared_ns=book_row.get('os_shared_ns'),feature_completed_shared_ns=feature_completed_shared_ns,is_live=False)
 if 'os_shared_ns' not in source_row:s['legacy_source_process_monotonic_ns']=source_row['monotonic_ns']
 return s
def validate(s):
 no_future(s)
 if not isinstance(s,dict) or not REQUIRED.issubset(s):raise ValueError('V2_MISSING_REQUIRED_FIELDS')
 if set(s)-REQUIRED-OPTIONAL:raise ValueError('V2_UNKNOWN_FIELDS')
 if s['state_version']!=VERSION or s['question_version']!=QUESTION:raise ValueError('VERSION_MISMATCH')
 if s['family'] not in ['FLOW_IMPULSE','BOOK_STATE','BTC_TRANSMISSION']:raise ValueError('FAMILY')
 if len(s['allowed_actions'])!=3 or set(s['allowed_actions'])!=set(ACTIONS):raise ValueError('ACTIONS')
 if not isinstance(s['is_live'],bool):raise ValueError('LIVE_FLAG')
 if isinstance(s['asof_ordinal'],bool) or not isinstance(s['asof_ordinal'],int) or s['asof_ordinal']<1:raise ValueError('ASOF')
 for k in ['quote_age_ms','impulse_bps','flow_imbalance','flow_received_notional_USDT']:
  if isinstance(s[k],bool) or not isinstance(s[k],(int,float)) or not math.isfinite(s[k]):raise ValueError('NUMERIC')
 if s['direction'] not in [-1,1]:raise ValueError('DIRECTION')
 return True
def live_send_gate(s,send_ns,expected):
 reasons=[]
 try:validate(s)
 except Exception as e:return {'send_allowed':False,'action':'WAIT','reasons':[str(e)]}
 if not s['is_live']:reasons.append('HISTORICAL_STATE_NOT_SENDABLE')
 for k in ['capture_run_id','connectionId','clock_domain_id']:
  if not s.get(k) or s[k]!=expected.get(k):reasons.append('BINDING_'+k)
 if s['clock_view']!='OS_SHARED':reasons.append('LEGACY_NAMESPACE_NOT_LIVE')
 try:
  a,b,f=s['source_asof_shared_ns'],s['source_latest_book_shared_ns'],s['feature_completed_shared_ns']
  if any(isinstance(v,bool) or not isinstance(v,int) for v in [a,b,f,send_ns]):raise ValueError('MISSING_ACTUAL_SHARED_NS')
  if not b<=a<=f<=send_ns:reasons.append('CAUSAL_INPUT_ORDER')
  if not 0<=send_ns-a<=250000000 or not 0<=send_ns-b<=250000000:reasons.append('INPUT_TTL')
 except Exception:reasons.append('MISSING_ACTUAL_SHARED_NS')
 return {'send_allowed':not reasons,'action':'WAIT' if reasons else None,'reasons':reasons,'not_transport_enabled':True}
def build_envelope(s,send_ns=None,expected=None):
 validate(s);payload={'model':MODEL,'state':s,'questions':{'action':{'type':'choice','instructions':INSTRUCTIONS,'criteria':CRITERIA}}};data=canonical(payload)
 if len(data)>16384:raise ValueError('PAYLOAD_OVER16KB')
 gate=live_send_gate(s,send_ns,expected or {})
 return {'payload':payload,'metadata':{'state_version':VERSION,'question_version':QUESTION,'question_sha256':digest(payload['questions']),'input_hash':digest(s),'payload_sha256':hashlib.sha256(data).hexdigest(),'payload_bytes':len(data),'capture_run_id':s['capture_run_id'],'connectionId':s['connectionId'],'clock_domain_id':s['clock_domain_id'],'asof_ordinal':s['asof_ordinal'],'source_asof_shared_ns':s['source_asof_shared_ns'],'source_latest_book_shared_ns':s['source_latest_book_shared_ns'],'feature_completed_shared_ns':s['feature_completed_shared_ns'],'intended_send_shared_ns':send_ns,'is_live':s['is_live'],'live_send_gate':gate,'transport':'DISABLED'}}
def response_gate(parsed,envelope,runtime):
 m=envelope['metadata'];reasons=[]
 if digest(envelope['payload']['state'])!=m['input_hash'] or digest(envelope['payload'])!=m['payload_sha256']:reasons.append('INPUT_HASH')
 for k in ['capture_run_id','connectionId','clock_domain_id','input_hash','asof_ordinal']:
  if runtime.get(k)!=m.get(k):reasons.append('RUNTIME_BINDING_'+k)
 if not m['live_send_gate']['send_allowed']:reasons.append('REQUEST_NOT_LIVE_SENDABLE')
 for flag in ['state_changed','risk_allowed','cap_allowed','book_valid']:
  if not isinstance(runtime.get(flag),bool):reasons.append('RUNTIME_FLAG_TYPE_'+flag)
 if runtime.get('state_changed',True):reasons.append('STATE_CHANGED')
 try:
  source,feature,sent,done,book,now=[m['source_asof_shared_ns'],m['feature_completed_shared_ns'],runtime['request_sent_shared_ns'],runtime['response_completed_shared_ns'],runtime['new_book_shared_ns'],runtime['now_shared_ns']]
  if any(isinstance(v,bool) or not isinstance(v,int) for v in [source,feature,sent,done,book,now]):raise ValueError()
  planned=m['intended_send_shared_ns']
  if not isinstance(planned,int) or isinstance(planned,bool) or sent<planned:reasons.append('ACTUAL_SEND_BEFORE_PLAN')
  if not source<=feature<=sent<=done<book<=now:reasons.append('FULL_CAUSAL_ORDER')
  latest=m['source_latest_book_shared_ns']
  if not isinstance(latest,int) or isinstance(latest,bool) or not 0<=sent-source<=250000000 or not 0<=sent-latest<=250000000:reasons.append('ACTUAL_INPUT_TTL')
  if done-sent>1000000000:reasons.append('TIMEOUT')
  if now-book>250000000 or book-done>250000000:reasons.append('NEW_BOOK_TTL')
 except Exception:reasons.append('CLOCK_FIELDS')
 if runtime.get('new_book_ordinal',0)<=m['asof_ordinal']:reasons.append('OLD_BOOK')
 if not runtime.get('risk_allowed',False) or not runtime.get('cap_allowed',False) or not runtime.get('book_valid',False):reasons.append('RISK_CAP_OR_BOOK')
 if parsed.get('model')!=MODEL or parsed.get('action') not in ACTIONS:reasons.append('PARSED_RESULT')
 return {'action':'WAIT' if reasons else parsed['action'],'reasons':reasons,'no_real_order':True,'confidence_never_changes_risk':True}
def transport_disabled(*_args,**_kwargs):raise RuntimeError('V2_TRANSPORT_DISABLED_NO_MODEL_AUTHORIZATION')
DECISIONS={'status':'NOT_IMPLEMENTED','endpoint_schema':'UNKNOWN'}

