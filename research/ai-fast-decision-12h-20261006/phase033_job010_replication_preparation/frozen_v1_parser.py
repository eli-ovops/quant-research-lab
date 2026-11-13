import json,hashlib,math
MODEL='jev-1.13.0';QUESTION_VERSION='impulse_action_v1';ACTIONS=('WAIT','FOLLOW','FADE')
INSTRUCTIONS='Choose one permitted paper action using only the received state. Judge continuation versus impact exhaustion or liquidity recovery. Prefer WAIT if evidence or fee-adjusted space is insufficient. No future outcomes, guaranteed price prediction, or risk increases.'
CRITERIA={'WAIT':'Insufficient or conflicting evidence, stale information, or insufficient fee-adjusted space.','FOLLOW':'Observed flow and book state support continuation in the impulse direction.','FADE':'Observed exhaustion and recovery support a move against the impulse direction.'}
FIELDS={'asset','asof_ordinal','asof_receive_monotonic_ms','asof_receive_wall_ms','quote_age_ms','impulse_bps','flow_imbalance','flow_notional_USDT','direction','asks_contracts','bids_contracts','contract_spec','fee_scenarios_each_side_bps','allowed_actions'}
BANNED={'future','outcome','outcomes','pnl','profit','entry_ordinal','exit_ordinal','entry_vwap','exit_vwap','price_fee_delta_usdt','netr','net_trade_pnl'}
def canonical(obj):return json.dumps(obj,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def digest(obj):return hashlib.sha256(canonical(obj)).hexdigest()
def numeric(value):
 if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value):raise ValueError('nonfinite_or_nonnumeric')
 return value
def no_future(value):
 if isinstance(value,dict):
  for k,v in value.items():
   if k.lower() in BANNED or k.lower().startswith('future_'):raise ValueError('future_field:'+k)
   no_future(v)
 elif isinstance(value,list):
  for x in value:no_future(x)
 elif isinstance(value,float):numeric(value)
def build_request(received_state,feature_completed_monotonic_ns,connection_id,clock_domain_verified=False):
 no_future(received_state);state={k:received_state[k] for k in FIELDS if k in received_state}
 if not FIELDS.issubset(state):raise ValueError('missing_state_field')
 if len(state['allowed_actions'])!=3 or set(state['allowed_actions'])!=set(ACTIONS):raise ValueError('action_slot')
 if isinstance(state['asof_ordinal'],bool) or not isinstance(state['asof_ordinal'],int) or state['asof_ordinal']<1:raise ValueError('invalid_asof')
 numeric(feature_completed_monotonic_ns)
 payload={'model':MODEL,'state':state,'questions':{'action':{'type':'choice','instructions':INSTRUCTIONS,'criteria':CRITERIA}}}
 data=canonical(payload)
 if len(data)>16384:raise ValueError('payload_over16KB')
 meta={'question_version':QUESTION_VERSION,'question_sha256':digest(payload['questions']),'payload_sha256':hashlib.sha256(data).hexdigest(),'payload_bytes':len(data),'source_hash':digest(state),'asof_ordinal':state['asof_ordinal'],'source_asof_monotonic_ns':int(state['asof_receive_monotonic_ms']*1e6),'feature_completed_monotonic_ns':int(feature_completed_monotonic_ns),'connection_id':connection_id,'clock_domain_verified':clock_domain_verified,'provider_adapter':'PREPARED_OFFLINE_ONLY','HTTP_transport':'NOT_IMPLEMENTED'}
 return {'payload':payload,'metadata':meta}
def parse_response(body,allowed_actions=ACTIONS):
 def bad(value):raise ValueError('json_nonfinite:'+value)
 obj=json.loads(body,parse_constant=bad) if isinstance(body,str) else body
 if not isinstance(obj,dict) or set(obj)!={'model','answers','usage'}:raise ValueError('response_shape')
 if obj['model']!=MODEL:raise ValueError('model_mismatch')
 if not isinstance(obj['answers'],dict) or set(obj['answers'])!={'action'}:raise ValueError('answers_shape')
 answer=obj['answers']['action']
 if not isinstance(answer,dict) or set(answer)!={'type','choice','probabilities','confidence'}:raise ValueError('choice_shape')
 if answer['type']!='choice':raise ValueError('choice_type')
 action=answer['choice']
 if action not in ACTIONS or action not in allowed_actions:raise ValueError('unauthorized_action')
 probs=answer['probabilities']
 if not isinstance(probs,dict) or set(probs)!=set(ACTIONS):raise ValueError('probability_shape')
 for val in probs.values():
  if not 0<=numeric(val)<=1:raise ValueError('probability_range')
 if abs(sum(probs.values())-1)>1e-6:raise ValueError('probability_sum')
 if not 0<=numeric(answer['confidence'])<=1:raise ValueError('confidence_range')
 usage=obj['usage']
 if not isinstance(usage,dict) or set(usage)!={'input_tokens','output_tokens'}:raise ValueError('usage_shape')
 for val in usage.values():
  if isinstance(val,bool) or not isinstance(val,int) or val<0:raise ValueError('invalid_usage')
 return {'model':obj['model'],'action':action,'probabilities':dict(probs),'confidence':answer['confidence'],'usage':dict(usage),'confidence_is_not_trade_win_probability':True}
def freshness_gate(parsed,record,runtime):
 m=record['metadata'];reasons=[]
 if record['payload'].get('model')!=MODEL or digest(record['payload']['state'])!=m['source_hash'] or digest(record['payload'])!=m['payload_sha256']:reasons.append('request_integrity')
 if not m['clock_domain_verified'] or not runtime.get('clock_domain_verified'):reasons.append('clock_domain_unverified')
 if runtime.get('source_hash')!=m['source_hash']:reasons.append('source_hash_mismatch')
 if runtime.get('connection_id')!=m['connection_id']:reasons.append('connection_changed')
 if runtime.get('asof_ordinal')!=m['asof_ordinal']:reasons.append('asof_mismatch')
 if runtime.get('state_changed',True):reasons.append('state_changed')
 required=['request_sent_ns','response_completed_ns','new_book_received_ns','now_ns']
 try:
  values={k:numeric(runtime[k]) for k in required};sent,done,book,now=[values[k] for k in required]
  if sent<m['feature_completed_monotonic_ns'] or done<sent:reasons.append('invalid_time_order')
  if done-sent>1000*1e6:reasons.append('response_timeout')
  if not done<book<=now:reasons.append('not_postdecision_book')
  if now-book>250*1e6 or book-done>250*1e6:reasons.append('expired_book')
 except (KeyError,ValueError,TypeError):reasons.append('invalid_runtime_clock')
 if runtime.get('new_book_ordinal',0)<=m['asof_ordinal']:reasons.append('old_book_ordinal')
 if not runtime.get('book_valid',False):reasons.append('invalid_book')
 if not runtime.get('risk_allowed',False) or not runtime.get('cap_allowed',False):reasons.append('risk_or_cap')
 if parsed.get('model')!=MODEL or parsed.get('action') not in ACTIONS:reasons.append('parsed_result_invalid')
 return {'action':'WAIT' if reasons else parsed['action'],'rejected':bool(reasons),'reject_reasons':reasons,'source_hash':m['source_hash'],'no_order_or_transport':True,'probabilities_not_risk_sizing':True}
def transport_disabled(*args,**kwargs):raise RuntimeError('HTTP_TRANSPORT_NOT_IMPLEMENTED_NO_AUTHORIZATION')
DECISIONS_ADAPTER={'status':'NOT_IMPLEMENTED','interface_contract':'UNKNOWN','not_Responses_substitution':True}
