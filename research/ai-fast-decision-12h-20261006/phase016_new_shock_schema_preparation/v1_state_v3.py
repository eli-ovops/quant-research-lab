from pathlib import Path
from decimal import Decimal
from fractions import Fraction as F
import json,hashlib,math
from frozen_v1_parser import parse_response,canonical,digest,MODEL,ACTIONS
import frozen_suite as suite
from frozen_cost_shock import ExactFlow,asof_required_move,qualifies
B=Path(__file__).resolve().parent
VERSION='stateV3_costshock';QUESTION='questionV3_costshock';FAMILY='COST_CAPABLE_SHOCK_V1'
RULE_SHA=hashlib.sha256((B/'frozen_cost_shock.py').read_bytes()).hexdigest()
REQUIRED={'schemaVersion','state_version','question_version','family','qualified_rule_sha','asset','contract_registry','contract_spec','source','current_book','reference_book','feature_completed_shared_ns','is_live','past_impulse_exact','received_flow_total_exact','received_flow_net_exact','received_flow_records','dominant_exact','reference_opposing_depth_exact','asof_cost_proxy_legs','required_move_max_exact','fixed_buffer_bps','eligibility','rejectreason','allowed_actions','evidence_label','causal_prefix_sha256'}
BANNED={'pnl','profit','outcome','outcomes','price_fee_delta_usdt','entry_vwap','exit_vwap','gross_price_delta_usdt','netr','response_prediction','winrate','expected_return','future'}
INSTRUCTIONS='Choose WAIT, FOLLOW, or FADE only from this qualified past received costshock state. Qualification and necessary cost displacement are past proxies, not predicted future profit, liquidation, or guaranteed edge. FOLLOW follows received direction; FADE opposes it. Consider both legs fees, spread, depth and uncertainty; WAIT unless future net opportunity is defensible. Confidence never changes risk.'
CRITERIA={'WAIT':'Unqualified, stale, uncertain, or future cost-adjusted edge is not defensible.','FOLLOW':'Qualified past shock supports continuation as a hypothesis only, after both legs costs.','FADE':'Qualified past shock supports exhaustion/reversal as a hypothesis only, after both legs costs.'}
def forbidden(x):
 if isinstance(x,dict):
  for k,v in x.items():
   if k.lower() in BANNED or k.lower().startswith(('future_path','future_','price_fee_delta','break_even_fee')):raise ValueError('FUTURE_OR_OUTCOME_FIELD:'+k)
   forbidden(v)
 elif isinstance(x,list):
  for y in x:forbidden(y)
 elif isinstance(x,float) and not math.isfinite(x):raise ValueError('NONFINITE')
def provenance(row,record=None):
 fields=['run_id','connectionId','clock_domain_id','boot_identity','local_ordinal','os_shared_ns','receive_wall_ns']
 if any(k not in row for k in fields):raise ValueError('MISSING_ACTUAL_SOURCE_FIELD')
 if any(not isinstance(row[k],int) or isinstance(row[k],bool) for k in ['local_ordinal','os_shared_ns','receive_wall_ns']):raise ValueError('SOURCE_CLOCK_TYPE')
 body=record if record is not None else {**{k:row[k] for k in fields},'instId':row['instId'],'channel':row['channel'],'raw_frame':row['raw']}
 return {**{k:row[k] for k in fields},'content_sha256':digest(body),**({'instId':row['instId'],'channel':row['channel'],'raw_frame':row['raw']} if record is None else {})}
def from_causal_prefix(rows,registry,feature_ns=None,is_live=False):
 if not rows or not isinstance(is_live,bool):raise ValueError('PREFIX_OR_LIVE_FLAG')
 source=rows[-1];a=source['instId'];specs={x['instId']:x for x in registry}
 if a not in specs:raise ValueError('UNKNOWN_ASSET')
 identity=provenance(source);features=suite.Features(specs,identity['clock_domain_id']);flow=ExactFlow();rawmap={};last=-1
 for index,row in enumerate(rows,1):
  pr=provenance(row)
  if row['local_ordinal']!=index or row['os_shared_ns']<last:raise ValueError('PREFIX_ORDER')
  if any(pr[k]!=identity[k] for k in ['run_id','connectionId','clock_domain_id','boot_identity']):raise ValueError('PREFIX_PROVENANCE_MISMATCH')
  last=row['os_shared_ns'];rawmap[row['local_ordinal']]=row;v=features.ingest(row)
  if v is not None:flow.ingest(row,v[1],v[4],v[3],specs[v[0]])
 now=source['os_shared_ns']/1e6;f=features.feature(a,now,1000,identity['connectionId'],identity['clock_domain_id'])
 if f is None or a not in flow.states or flow.states[a]['unknown']:raise ValueError('MISSING_CAUSAL_REFERENCE_OR_FLOW')
 cur,ref=f['book'],f['reference'];cr=rawmap[cur['ordinal']];rr=rawmap[ref['ordinal']];current=json.loads(cr['raw'])['data'][0];reference=json.loads(rr['raw'])['data'][0];unit=Decimal(specs[a]['ctVal'])*Decimal(specs[a]['ctMult']);proxy=asof_required_move(cur,unit,Decimal(specs[a]['lotSz']),Decimal(specs[a]['minSz']))
 if proxy is None:raise ValueError('COST_DEPTH_MISSING_CANNOT_PREPARE_MODEL_STATE')
 required,legs=proxy;total,net=flow.states[a]['total'],flow.states[a]['net'];mid=(F(cur['asks'][0][0])+F(cur['bids'][0][0]))/2;refmid=(F(ref['asks'][0][0])+F(ref['bids'][0][0]))/2;impulse=(mid/refmid-1)*10000;direction=1 if net>0 else -1 if net<0 else 0;dominant=(total+direction*net)/2;depth=sum((F(px)*F(q)*F(unit) for px,q in (ref['asks'] if direction==1 else ref['bids'])[:5]),F(0));status=qualifies(impulse,total,net,required,depth)
 records=[]
 for row in rows:
  if row['instId']==a and row['channel']=='trades' and identity['os_shared_ns']-1000000000<row['os_shared_ns']<=identity['os_shared_ns']:
   for trade in json.loads(row['raw']).get('data',[]):records.append({k:row[k] for k in ['run_id','connectionId','clock_domain_id','local_ordinal','os_shared_ns']}|{'raw_trade':trade})
 return {'schemaVersion':VERSION,'state_version':VERSION,'question_version':QUESTION,'family':FAMILY,'qualified_rule_sha':RULE_SHA,'asset':a,'contract_registry':registry,'contract_spec':specs[a],'source':identity,'current_book':{'asks':current['asks'],'bids':current['bids'],'raw_record':current,'provenance':provenance(cr,current)},'reference_book':{'asks':reference['asks'],'bids':reference['bids'],'raw_record':reference,'provenance':provenance(rr,reference)},'feature_completed_shared_ns':feature_ns,'is_live':is_live,'past_impulse_exact':str(impulse),'received_flow_total_exact':str(total),'received_flow_net_exact':str(net),'received_flow_records':records,'dominant_exact':str(dominant),'reference_opposing_depth_exact':str(depth),'asof_cost_proxy_legs':legs,'required_move_max_exact':str(required),'fixed_buffer_bps':5,'eligibility':status=='QUALIFIED','rejectreason':None if status=='QUALIFIED' else status,'allowed_actions':list(ACTIONS),'evidence_label':'REAL_RECEIVED_HISTORICAL_NOT_MODEL_RUN','causal_prefix_sha256':digest(rows)}
def validate(s):
 forbidden(s)
 if not isinstance(s,dict) or set(s)!=REQUIRED:raise ValueError('V3_REQUIRED_OR_UNKNOWN_FIELDS')
 if s['schemaVersion']!=VERSION or s['state_version']!=VERSION or s['question_version']!=QUESTION or s['family']!=FAMILY or s['qualified_rule_sha']!=RULE_SHA:raise ValueError('SCHEMA_FAMILY_RULE_VERSION')
 if not isinstance(s['is_live'],bool) or not isinstance(s['eligibility'],bool):raise ValueError('FLAGS_NOT_BOOL')
 if set(s['allowed_actions'])!=set(ACTIONS) or len(s['allowed_actions'])!=3:raise ValueError('ACTIONS')
 registry={x['instId']:x for x in s['contract_registry']}
 if registry.get(s['asset'])!=s['contract_spec']:raise ValueError('SPEC_REGISTRY_MISMATCH')
 if digest(s['contract_registry'])!=digest(json.loads((B/'instruments.json').read_text())):raise ValueError('REGISTERED_SPEC_CONTENT_MISMATCH')
 src=s['source'];book=s['current_book'];ref=s['reference_book'];bp=book['provenance'];rp=ref['provenance']
 sourcebody={k:v for k,v in src.items() if k!='content_sha256'}
 if digest(sourcebody)!=src.get('content_sha256') or src.get('instId')!=s['asset']:raise ValueError('SOURCE_CONTENT_HASH_OR_ASSET')
 rawsource=json.loads(src['raw_frame']);forbidden(rawsource)
 if rawsource.get('arg',{}).get('instId')!=s['asset'] or rawsource.get('arg',{}).get('channel')!=src['channel']:raise ValueError('SOURCE_RAW_ARG')
 for x in [book,ref]:
  if digest(x['raw_record'])!=x['provenance'].get('content_sha256') or any(x[k]!=x['raw_record'].get(k) for k in ['asks','bids']):raise ValueError('BOOK_RAW_CONTENT_HASH')
 for obj in [src,bp,rp]:
  for key in ['run_id','connectionId','clock_domain_id','boot_identity','local_ordinal','os_shared_ns','receive_wall_ns','content_sha256']:
   if key not in obj:raise ValueError('MISSING_PROVENANCE')
  if any(not isinstance(obj[k],int) or isinstance(obj[k],bool) for k in ['local_ordinal','os_shared_ns','receive_wall_ns']):raise ValueError('CLOCK_OR_ORDINAL_TYPE')
  for k in ['run_id','connectionId','clock_domain_id','boot_identity']:
   if obj[k]!=src[k] or not obj[k]:raise ValueError('RUN_CONN_DOMAIN_BOOT_MISMATCH')
 if not rp['local_ordinal']<=bp['local_ordinal']<=src['local_ordinal'] or not rp['os_shared_ns']<=bp['os_shared_ns']<=src['os_shared_ns']:raise ValueError('SOURCE_REFERENCE_ORDER')
 age=src['os_shared_ns']-bp['os_shared_ns'];refage=src['os_shared_ns']-1000000000-rp['os_shared_ns']
 if not 0<=age<=250000000 or not 0<=refage<=250000000:raise ValueError('CAUSAL_BOOK_OR_1S_REFERENCE_TTL')
 def valid(x):
  for side in ['asks','bids']:
   if not isinstance(x[side],list) or not x[side] or len(x[side])>5:raise ValueError('BOOK_SHAPE')
   for lv in x[side]:
    if len(lv)<2 or not all(Decimal(z).is_finite() and Decimal(z)>0 for z in lv[:2]):raise ValueError('BOOK_PRICE_SIZE')
  vv=suite.execution.valid_book(x)
  if vv is None:raise ValueError('CROSSED_OR_UNSORTED_BOOK')
  return vv
 ca,cb=valid(book);ra,rb=valid(ref);spec=s['contract_spec'];unit=Decimal(spec['ctVal'])*Decimal(spec['ctMult']);proxy=asof_required_move({'asks':ca,'bids':cb},unit,Decimal(spec['lotSz']),Decimal(spec['minSz']))
 if proxy is None or proxy[1]!=s['asof_cost_proxy_legs'] or proxy[0]!=F(s['required_move_max_exact']):raise ValueError('COST_FORMULA_CONTENT_MISMATCH')
 total_check=net_check=F(0);seen={}
 if not isinstance(s['received_flow_records'],list):raise ValueError('FLOW_RECORDS_SHAPE')
 for rec in s['received_flow_records']:
  if any(rec.get(k)!=src[k] for k in ['run_id','connectionId','clock_domain_id']):raise ValueError('FLOW_PROVENANCE')
  if not isinstance(rec.get('os_shared_ns'),int) or isinstance(rec['os_shared_ns'],bool) or not src['os_shared_ns']-1000000000<rec['os_shared_ns']<=src['os_shared_ns'] or not isinstance(rec.get('local_ordinal'),int) or isinstance(rec['local_ordinal'],bool) or not 0<rec['local_ordinal']<=src['local_ordinal']:raise ValueError('FLOW_CAUSAL_WINDOW')
  trade=rec['raw_trade'];identity=(trade.get('tradeId'),trade.get('source'));signature=tuple(trade.get(k) for k in ['px','sz','side','ts','count'])
  if identity[0] is None or trade.get('side') not in ['buy','sell'] or not all(Decimal(trade[k]).is_finite() and Decimal(trade[k])>0 for k in ['px','sz']):raise ValueError('FLOW_RECORD_CONTENT')
  if identity in seen:
   if signature!=seen[identity]:raise ValueError('FLOW_IDENTITY_CONFLICT')
   continue
  seen[identity]=signature;amount=F(Decimal(trade['px']))*F(Decimal(trade['sz']))*F(unit);total_check+=amount;net_check+=amount*(1 if trade['side']=='buy' else -1)
 mid=(F(ca[0][0])+F(cb[0][0]))/2;refmid=(F(ra[0][0])+F(rb[0][0]))/2;impulse=(mid/refmid-1)*10000;total,net=F(s['received_flow_total_exact']),F(s['received_flow_net_exact']);direction=1 if net>0 else -1 if net<0 else 0;dominant=(total+direction*net)/2;depth=sum((F(px)*F(q)*F(unit) for px,q in (ra if direction==1 else rb)),F(0))
 if total!=total_check or net!=net_check:raise ValueError('FLOW_TOTAL_NET_CONTENT_MISMATCH')
 if total<0 or abs(net)>total or F(s['past_impulse_exact'])!=impulse or F(s['dominant_exact'])!=dominant or F(s['reference_opposing_depth_exact'])!=depth or s['fixed_buffer_bps']!=5:raise ValueError('ASOF_IMPULSE_FLOW_DEPTH_CONTENT_MISMATCH')
 status=qualifies(impulse,total,net,proxy[0],depth)
 if s['eligibility']!=(status=='QUALIFIED') or s['rejectreason']!=(None if status=='QUALIFIED' else status):raise ValueError('ELIGIBILITY_CONTENT_MISMATCH')
 return True
def send_gate(s,actual_send_ns,expected):
 reasons=[]
 try:validate(s)
 except Exception as e:return {'allowed':False,'action':'WAIT','reasons':[str(e)]}
 if not s['is_live']:reasons.append('HISTORY_NOT_SENDABLE')
 if not s['eligibility']:reasons.append('RULE_NOT_QUALIFIED')
 source=s['source'];book=s['current_book']['provenance']
 for k in ['run_id','connectionId','clock_domain_id','boot_identity']:
  if source[k]!=expected.get(k):reasons.append('LIVE_BINDING_'+k)
 feature=s['feature_completed_shared_ns']
 if any(not isinstance(x,int) or isinstance(x,bool) for x in [feature,actual_send_ns]):reasons.append('MISSING_ACTUAL_SHARED_CLOCK')
 elif not source['os_shared_ns']<=feature<=actual_send_ns:reasons.append('SOURCE_FEATURE_SEND_ORDER')
 elif not 0<=actual_send_ns-source['os_shared_ns']<=250000000 or not 0<=actual_send_ns-book['os_shared_ns']<=250000000:reasons.append('LIVE_INPUT_TTL')
 return {'allowed':not reasons,'action':'WAIT' if reasons else None,'reasons':reasons,'transport':'DISABLED'}
def build_request(s,planned_send_ns=None,expected=None):
 validate(s);gate=send_gate(s,planned_send_ns,expected or {});payload=None
 if s['eligibility']:payload={'model':MODEL,'state':s,'questions':{'action':{'type':'choice','instructions':INSTRUCTIONS,'criteria':CRITERIA}}}
 if payload is not None and len(canonical(payload))>32768:raise ValueError('PAYLOAD_TOO_LARGE')
 return {'payload':payload,'metadata':{'state_sha256':digest(s),'payload_sha256':digest(payload),'question_version':QUESTION,'planned_send_shared_ns':planned_send_ns,'send_gate':gate,'source':s['source'],'current_book_provenance':s['current_book']['provenance'],'feature_completed_shared_ns':s['feature_completed_shared_ns'],'is_live':s['is_live'],'eligibility':s['eligibility'],'transport':'DISABLED'},'state':s}
def response_gate(parsed,envelope,runtime):
 m=envelope['metadata'];s=envelope['state'];reasons=[]
 if digest(s)!=m['state_sha256'] or digest(envelope['payload'])!=m['payload_sha256']:reasons.append('INPUT_HASH')
 expected={k:runtime.get(k) for k in ['run_id','connectionId','clock_domain_id','boot_identity']};gate=send_gate(s,runtime.get('request_sent_shared_ns'),expected);reasons+=gate['reasons']
 if runtime.get('state_sha256')!=m['state_sha256']:reasons.append('STATE_HASH_BINDING')
 for flag in ['state_changed','risk_allowed','cap_allowed','book_valid']:
  if not isinstance(runtime.get(flag),bool):reasons.append('RUNTIME_BOOL_'+flag)
 if runtime.get('state_changed',True):reasons.append('STATE_CHANGED')
 try:
  start,sent,done,book,now=[runtime[k] for k in ['request_started_shared_ns','request_sent_shared_ns','response_completed_shared_ns','new_book_shared_ns','now_shared_ns']];feature=s['feature_completed_shared_ns'];planned=m['planned_send_shared_ns']
  if any(not isinstance(x,int) or isinstance(x,bool) for x in [start,sent,done,book,now,feature,planned]):raise ValueError()
  if not feature<=start<=sent<=done<book<=now or sent<planned:reasons.append('FULL_CLOCK_CHAIN')
  if done-start>1000000000:reasons.append('RESPONSE_TIMEOUT')
  if now-book>250000000 or book-done>250000000:reasons.append('NEW_BOOK_TTL')
 except Exception:reasons.append('MISSING_CLOCK_CHAIN')
 ordinal=runtime.get('new_book_ordinal')
 if not isinstance(ordinal,int) or isinstance(ordinal,bool) or ordinal<=s['source']['local_ordinal']:reasons.append('NEW_BOOK_ORDINAL')
 if not runtime.get('risk_allowed',False) or not runtime.get('cap_allowed',False) or not runtime.get('book_valid',False):reasons.append('RISK_CAP_OR_BOOK')
 if parsed.get('model')!=MODEL or parsed.get('action') not in ACTIONS:reasons.append('MODEL_OR_ACTION')
 return {'action':'WAIT' if reasons else parsed['action'],'reasons':reasons,'not_real_order':True,'confidence_never_changes_risk':True}
def transport_disabled(*args,**kwargs):raise RuntimeError('STATEV3_TRANSPORT_DISABLED_NO_AUTHORIZATION')
DECISIONS={'status':'NOT_IMPLEMENTED','contract':'UNKNOWN'}
