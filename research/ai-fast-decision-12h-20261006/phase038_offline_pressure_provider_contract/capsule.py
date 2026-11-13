import json,hashlib,math
import re
from pathlib import Path
from fractions import Fraction as F
from decimal import Decimal as D
from frozen_pressure_rules import pressure_choice
from frozen_execution_v12 import valid_book
from frozen_cost_shock import asof_required_move
P=Path(__file__).resolve().parent
REGISTRY={r['instId']:r for r in json.loads((P/'instruments.json').read_text())}
CLOCK_PROOF=json.loads((P/'clock_proof.json').read_text());KNOWN_DOMAIN=CLOCK_PROOF['checks'][0]['parent_before']['clock_domain_id'];KNOWN_BOOT=CLOCK_PROOF['boot_identity']
MODEL='jev-1.13.0';SCHEMA='PRESSURE_PROVIDER_DRAFT_V1';QUESTION='PRESSURE_ACT_REGISTERED_WAIT_V1'
ACTIONS={'ACT_REGISTERED','WAIT'}
def canonical(x):return json.dumps(x,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode()
def digest(x):return hashlib.sha256(canonical(x)).hexdigest()
def integer(x):return type(x) is int and x>=0
PROV={'run_id','connectionId','clock_domain_id','boot_identity','local_ordinal','os_shared_ns','receive_wall_ns','asset'}
TRADE={'instId','tradeId','px','sz','side','ts','count','source','seqId'}
FLOW={'total10','net10','total1','net1'}
ASOF={'impulse10_bps','required_move_max_bps','dominant10','reference_opposing_top5'}
LEG={'side','contracts','entry_notional_USDT','asof_reverse_notional_USDT','required_move_bps','required_exact_fraction'}
def shape(x,required,allowed=None):
 if not isinstance(x,dict) or not required<=set(x) or set(x)-(allowed if allowed is not None else required):raise ValueError('NESTED_SCHEMA_EXTRA_OR_MISSING')
def trade_shape(t):
 shape(t,{'tradeId','px','sz','side'},TRADE)
 for k in ['tradeId','ts','count','source','seqId']:
  if k in t and (type(t[k]) not in [str,int] or not re.fullmatch(r'[A-Za-z0-9_-]+',str(t[k]))):raise ValueError('TRADE_SCALAR_FORMAT')
 if 'instId' in t and t['instId'] not in REGISTRY:raise ValueError('TRADE_SYMBOL')
def strict_nested(s):
 shape(s['source'],PROV);shape(s['flow_exact'],FLOW);shape(s['asof_exact'],ASOF)
 if s['source']['clock_domain_id'] not in [KNOWN_DOMAIN,'SYNTHETIC_NOT_MODEL_RUN_clock_domain_id'] or s['source']['boot_identity'] not in [KNOWN_BOOT,'SYNTHETIC_NOT_MODEL_RUN_boot_identity']:raise ValueError('UNKNOWN_CLOCK_NAMESPACE')
 if not re.fullmatch(r'[0-9a-f]{64}',s['source_dataset_logical_sha']) and not (s.get('fixture_kind')=='SYNTHETIC_NOT_MODEL_RUN' and s['source_dataset_logical_sha']=='SYNTHETIC_NOT_SOURCE_HASH'):raise ValueError('SOURCE_HASH_FORMAT')
 if s.get('fixture_kind','HISTORY_ASOF_ONLY') not in ['HISTORY_ASOF_ONLY','SYNTHETIC_NOT_MODEL_RUN']:raise ValueError('FIXTURE_ENUM')
 for name in ['current_book','ref10_book','ref1_book']:
  b=s[name];shape(b,{'asks','bids','provenance','content_sha'});shape(b['provenance'],PROV)
  for side in ['asks','bids']:
   if not isinstance(b[side],list):raise ValueError('BOOK_NESTED_LIST')
   for level in b[side]:
    if not isinstance(level,list) or not 2<=len(level)<=4 or any(not D(str(x)).is_finite() for x in level):raise ValueError('BOOK_NESTED_NUMERIC')
 if not isinstance(s['received_trade_witnesses10s'],list) or not isinstance(s['asof_cost_legs'],list):raise ValueError('NESTED_LIST')
 for rec in s['received_trade_witnesses10s']+[s['first_unique_trade_witness']]:
  shape(rec,{'provenance','trade'});shape(rec['provenance'],PROV);trade_shape(rec['trade'])
 for leg in s['asof_cost_legs']:shape(leg,LEG)
 for v in [s['source']]+[s[n]['provenance'] for n in ['current_book','ref10_book','ref1_book']]+[r['provenance'] for r in s['received_trade_witnesses10s']]+[s['first_unique_trade_witness']['provenance']]:
  for k in ['run_id','connectionId']:
   if not isinstance(v[k],str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,128}',v[k]):raise ValueError('PROVENANCE_IDENTIFIER_SYNTAX')
def model_state(s):
 scalar={'schemaVersion','questionVersion','qualified_rule_sha','asset','contract_spec_sha','source_dataset_logical_sha','is_live','flow_identity_conflict','feature_completed_shared_ns','first_unique_trade_shared_ns','fixed_buffer_bps','capacity_USDT','mainfee_eachleg_bps','eligibility','registered_rule','registered_action','rejectreason'}
 out={k:s[k] for k in sorted(scalar)};out['fixture_kind']=s.get('fixture_kind','HISTORY_ASOF_ONLY');out['contract_spec']=json.loads(canonical(REGISTRY[s['asset']]));out['source']={k:s['source'][k] for k in sorted(PROV)}
 out['flow_exact']={k:s['flow_exact'][k] for k in sorted(FLOW)};out['asof_exact']={k:s['asof_exact'][k] for k in sorted(ASOF)};out['asof_cost_legs']=[{k:r[k] for k in sorted(LEG)} for r in s['asof_cost_legs']]
 for name in ['current_book','ref10_book','ref1_book']:
  b=s[name];out[name]={'asks':[list(r[:2]) for r in b['asks']],'bids':[list(r[:2]) for r in b['bids']],'raw_content_sha':b['content_sha'],'provenance':{k:b['provenance'][k] for k in sorted(PROV)}}
 rec=s['first_unique_trade_witness'];out['first_unique_trade_witness']={'provenance':{k:rec['provenance'][k] for k in sorted(PROV)},'trade':{k:rec['trade'][k] for k in sorted(TRADE) if k in rec['trade']}}
 out['received_trade_witnesses10s_sha']=digest(s['received_trade_witnesses10s']);out['received_trade_witnesses10s_count']=len(s['received_trade_witnesses10s']);return out
def no_future(x):
 if isinstance(x,dict):
  for k,v in x.items():
   if any(term in k.lower() for term in ['future','outcome','price_fee_delta','pnl','profit','winning','label']):raise ValueError('FORBIDDEN_FUTURE_OR_INCOME_FIELD:'+k)
   no_future(v)
 elif isinstance(x,list):
  for v in x:no_future(v)
def validate(s):
 no_future(s)
 allowed={'schemaVersion','questionVersion','qualified_rule_sha','asset','contract_spec','contract_spec_sha','source','source_dataset_logical_sha','is_live','flow_identity_conflict','feature_completed_shared_ns','first_unique_trade_shared_ns','first_unique_trade_witness','current_book','ref10_book','ref1_book','received_trade_witnesses10s','flow_exact','asof_exact','fixed_buffer_bps','capacity_USDT','mainfee_eachleg_bps','asof_cost_legs','eligibility','registered_rule','registered_action','rejectreason','fixture_kind'}
 if set(s)-allowed:raise ValueError('UNEXPECTED_STATE_FIELDS')
 strict_nested(s)
 if s['schemaVersion']!=SCHEMA or s['questionVersion']!=QUESTION:raise ValueError('SCHEMA_VERSION')
 if type(s['is_live']) is not bool or type(s['flow_identity_conflict']) is not bool:raise ValueError('STRICT_BOOL')
 if s['flow_identity_conflict']:raise ValueError('FLOW_IDENTITY_UNKNOWN')
 source=s['source'];a=s['asset'];spec=s['contract_spec']
 if a not in REGISTRY or canonical(spec)!=canonical(REGISTRY[a]) or s['contract_spec_sha']!=digest(spec):raise ValueError('CONTRACT_REGISTRY_BINDING')
 if s['qualified_rule_sha']!=hashlib.sha256((P/'frozen_pressure_rules.py').read_bytes()).hexdigest():raise ValueError('RULE_HASH')
 ids=['run_id','connectionId','clock_domain_id','boot_identity']
 if any(not isinstance(source.get(k),str) or not source[k] for k in ids) or source['asset']!=a:raise ValueError('SOURCE_IDENTITY')
 for k in ['os_shared_ns','receive_wall_ns','local_ordinal']:
  if not integer(source.get(k)):raise ValueError('SOURCE_CLOCK_ORDINAL')
 if not integer(s['feature_completed_shared_ns']) or s['feature_completed_shared_ns']<source['os_shared_ns']:raise ValueError('FEATURE_BEFORE_SOURCE')
 books=[];now=source['os_shared_ns'];gate=[]
 for name,seconds in [('current_book',0),('ref10_book',10),('ref1_book',1)]:
  b=s[name];v=b['provenance']
  if any(v.get(k)!=source[k] for k in ids) or v.get('asset')!=a:raise ValueError('BOOK_PROVENANCE')
  if not integer(v.get('os_shared_ns')) or not integer(v.get('local_ordinal')) or v['local_ordinal']>source['local_ordinal'] or v['os_shared_ns']>now-seconds*1000000000:raise ValueError('BOOK_CAUSAL_REFERENCE')
  if b['content_sha']!=digest({'asks':b['asks'],'bids':b['bids']}):raise ValueError('BOOK_HASH')
  for side in ['asks','bids']:
   if not isinstance(b[side],list) or not 1<=len(b[side])<=5:raise ValueError('BOOK_SHAPE')
   if any(not D(str(z)).is_finite() or D(str(z))<=0 for level in b[side] for z in level[:2]):raise ValueError('BOOK_PRICE_SIZE')
  parsed=valid_book(b)
  if parsed is None:raise ValueError('BOOK_SORT_CROSS')
  books.append(parsed);gate.append(now-seconds*1000000000-v['os_shared_ns']<=250000000)
 total=net=t1=n1=F(0);seen={};last=None
 for rec in s['received_trade_witnesses10s']:
  v=rec['provenance'];t=rec['trade']
  if any(v.get(k)!=source[k] for k in ids) or v.get('asset')!=a or not integer(v.get('os_shared_ns')) or not integer(v.get('local_ordinal')) or not now-10000000000<v['os_shared_ns']<=now or v['local_ordinal']>source['local_ordinal']:raise ValueError('FLOW_PROVENANCE_WINDOW')
  if t.get('tradeId') is None or t.get('side') not in ['buy','sell']:raise ValueError('FLOW_ID_SIDE')
  if any(not D(str(t[k])).is_finite() or D(str(t[k]))<=0 for k in ['px','sz']):raise ValueError('FLOW_NUMERIC')
  key=(t['tradeId'],t.get('source'));sig=tuple(t.get(k) for k in ['px','sz','side','ts','count'])
  if key in seen:
   if seen[key]!=sig:raise ValueError('FLOW_ID_CONFLICT')
   continue
  seen[key]=sig;amt=F(D(t['px']))*F(D(t['sz']))*F(D(spec['ctVal']))*F(D(spec['ctMult']));signed=amt*(1 if t['side']=='buy' else -1);total+=amt;net+=signed;last=v['os_shared_ns'] if last is None else max(last,v['os_shared_ns'])
  if v['os_shared_ns']>now-1000000000:t1+=amt;n1+=signed
 declared=s['flow_exact']
 for k,v in [('total10',total),('net10',net),('total1',t1),('net1',n1)]:
  if F(declared[k])!=v:raise ValueError('FLOW_CONTENT_'+k)
 if abs(net-n1)>total-t1:raise ValueError('NESTED_WINDOW_INCONSISTENCY')
 first=s['first_unique_trade_shared_ns']
 if not integer(first) or first>now or (last is not None and first>last):raise ValueError('FIRST_UNIQUE_CLOCK')
 proof=s['first_unique_trade_witness'];v=proof['provenance'];t=proof['trade']
 if any(v.get(k)!=source[k] for k in ids) or v.get('asset')!=a or v.get('os_shared_ns')!=first or not integer(v.get('local_ordinal')) or v['local_ordinal']>source['local_ordinal'] or t.get('tradeId') is None or t.get('side') not in ['buy','sell'] or any(not D(str(t[k])).is_finite() or D(str(t[k]))<=0 for k in ['px','sz']):raise ValueError('FIRST_UNIQUE_PROVENANCE_CONTENT')
 if any(first>r['provenance']['os_shared_ns'] for r in s['received_trade_witnesses10s']):raise ValueError('FIRST_AFTER_WITNESS')
 unit=D(spec['ctVal'])*D(spec['ctMult']);asks,bids=books[0];ra,rb=books[1];proxy=asof_required_move({'asks':asks,'bids':bids},unit,D(spec['lotSz']),D(spec['minSz']))
 if proxy is None:raise ValueError('BOTH_CAPACITY_UNAVAILABLE')
 required,legs=proxy;mid=(F(asks[0][0])+F(bids[0][0]))/2;refmid=(F(ra[0][0])+F(rb[0][0]))/2;imp=(mid/refmid-1)*10000;shock=1 if net>0 else -1 if net<0 else 0;depth=sum((F(px)*F(q)*F(unit) for px,q in (ra if shock==1 else rb)),F(0));age=now-last if last is not None else None
 d=s['asof_exact']
 for k,v in [('impulse10_bps',imp),('required_move_max_bps',required),('dominant10',(total+shock*net)/2),('reference_opposing_top5',depth)]:
  if F(d[k])!=v:raise ValueError('ASOF_CONTENT_'+k)
 if s['fixed_buffer_bps']!=5 or s['capacity_USDT']!=500 or s['mainfee_eachleg_bps']!=5 or s['asof_cost_legs']!=legs:raise ValueError('COST_CAPACITY_CONTENT')
 rule,reason=pressure_choice(total,net,t1,n1,imp,required,depth,age)
 if not all(gate):rule=None;reason='WAIT_CURRENT_OR_REFERENCE_TTL'
 if now-first<10000000000:rule=None;reason='WAIT_REAL_TRADE_WARMUP10'
 expected_action='FOLLOW' if rule=='CONTINUATION_FOLLOW_V1' else 'FADE' if rule=='PRESSURE_DECAY_FADE_V1' else None
 if type(s['eligibility']) is not bool or s['eligibility']!=(rule is not None) or s['registered_rule']!=rule or s['registered_action']!=expected_action or s['rejectreason']!=(None if rule else reason):raise ValueError('REGISTRATION_CONTENT')
 return True
def send_gate(s,actualsend,expected):
 reasons=[]
 try:validate(s)
 except Exception as e:return {'allowed':False,'action':'WAIT','reasons':[str(e)]}
 if not s['is_live']:reasons.append('HISTORY_NOT_SENDABLE')
 if not s['eligibility']:reasons.append('UNQUALIFIED_WAIT_ONLY')
 src=s['source'];book=s['current_book']['provenance']
 if any(expected.get(k)!=src[k] for k in ['run_id','connectionId','clock_domain_id','boot_identity']):reasons.append('LIVE_BINDING')
 if not integer(actualsend) or not src['os_shared_ns']<=s['feature_completed_shared_ns']<=actualsend:reasons.append('SOURCE_FEATURE_ACTUAL_SEND')
 elif actualsend-src['os_shared_ns']>250000000 or actualsend-book['os_shared_ns']>250000000:reasons.append('ACTUAL_SEND_TTL')
 return {'allowed':not reasons,'action':'WAIT' if reasons else 'ACT_REGISTERED','reasons':reasons}
def build_request(s,planned_send,expected):
 gate=send_gate(s,planned_send,expected);draft=None
 try:
  validate(s)
  if s['eligibility']:
   compact=model_state(s);draft={'model':MODEL,'state':compact,'questions':{'action':{'type':'choice','instructions':'Choose ACT_REGISTERED only to endorse the frozen registered rule; otherwise WAIT. Past flow, movement and cost proxies do not guarantee future edge. Never reverse direction, change risk, or infer liquidation. No future labels are supplied.','criteria':{'ACT_REGISTERED':'Endorse the pre-registered action under stated uncertainty and two-leg costs; no sizing change.','WAIT':'Abstain when evidence, freshness or uncertainty makes endorsement unsuitable.'}}}}
 except Exception:pass
 return {'offline_draft_payload':draft,'payload':None,'sendable_payload':None,'state':s,'metadata':{'state_sha':digest(s),'draft_sha':digest(draft),'planned_send_shared_ns':planned_send,'gate':gate,'transport':'DISABLED','questionVersion':QUESTION}}
def parse_response(r):
 if r.get('model')!=MODEL:raise ValueError('MODEL_VERSION')
 a=r['answers']['action'];probs=a['probabilities'];confidence=a['confidence'];usage=r['usage']
 if a.get('type')!='choice' or a.get('choice') not in ACTIONS or set(probs)!=ACTIONS:raise ValueError('CHOICE_SCHEMA')
 if any(type(v) not in [int,float] or not math.isfinite(v) or not 0<=v<=1 for v in list(probs.values())+[confidence]) or abs(sum(probs.values())-1)>1e-6:raise ValueError('PROBABILITIES_OR_CONFIDENCE')
 if any(type(usage.get(k)) is not int or usage[k]<0 for k in ['input_tokens','output_tokens']):raise ValueError('USAGE')
 return {'model':MODEL,'action':a['choice'],'probabilities':probs,'confidence':confidence,'usage':usage,'confidence_not_winrate_orrisk':True}
def response_gate(parsed,envelope,runtime):
 reasons=[];s=envelope['state'];m=envelope['metadata'];expected={k:runtime.get(k) for k in ['run_id','connectionId','clock_domain_id','boot_identity']};reasons+=send_gate(s,runtime.get('request_sent_shared_ns'),expected)['reasons']
 if digest(s)!=m['state_sha'] or digest(envelope['offline_draft_payload'])!=m['draft_sha'] or runtime.get('state_sha')!=m['state_sha']:reasons.append('HASH_BINDING')
 for flag in ['state_changed','risk_allowed','cap_allowed','book_valid']:
  if type(runtime.get(flag)) is not bool:reasons.append('STRICT_RUNTIME_BOOL_'+flag)
 if runtime.get('state_changed',True) or not all(runtime.get(x) is True for x in ['risk_allowed','cap_allowed','book_valid']):reasons.append('STATE_RISK_CAP')
 try:
  start,sent,done,newbook,now=[runtime[k] for k in ['request_started_shared_ns','request_sent_shared_ns','response_completed_shared_ns','new_book_shared_ns','now_shared_ns']]
  if not all(integer(v) for v in [start,sent,done,newbook,now,m['planned_send_shared_ns']]) or not s['feature_completed_shared_ns']<=start<=sent<=done<newbook<=now or sent<m['planned_send_shared_ns']:reasons.append('FULL_ACTUAL_CLOCK_CHAIN')
  if done-start>1000000000:reasons.append('RESPONSE_TIMEOUT')
  if now-newbook>250000000 or newbook-done>250000000:reasons.append('POST_RESPONSE_BOOK_TTL')
 except Exception:reasons.append('MISSING_ACTUAL_CLOCK')
 if not integer(runtime.get('new_book_ordinal')) or runtime['new_book_ordinal']<=s['source']['local_ordinal']:reasons.append('NEW_BOOK_ORDINAL')
 if parsed.get('model')!=MODEL or parsed.get('action') not in ACTIONS:reasons.append('PARSED_ACTION_MODEL')
 reasons.append('TRANSPORT_AND_REAL_NEW_BOOK_EXECUTION_NOT_IMPLEMENTED')
 return {'action':'WAIT','reasons':reasons,'format_gate_pass_except_transport':len(reasons)==1,'confidence_does_not_change_risk':True,'sendable_payload':None}
def transport(*args,**kwargs):raise RuntimeError('PRESSURE_PROVIDER_TRANSPORT_HARD_DISABLED')
