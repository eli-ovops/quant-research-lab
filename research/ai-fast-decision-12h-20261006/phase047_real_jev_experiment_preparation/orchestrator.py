from pathlib import Path
from fractions import Fraction as F
from decimal import Decimal as D
import json,hashlib,math,datetime
P=Path(__file__).resolve().parent
SPECS={x['instId']:x for x in json.loads((P/'instruments.json').read_text())}
CANDIDATES=('FLOW_V1','BOOK_V1','LEAD_V1');ARMS=('JEV','RULE_MATCHED_NO_AI','RULE_IMMEDIATE_NO_AI','WAIT_NO_AI');ACTIONS={'WAIT','FOLLOW','FADE'}
MODEL='jev-1.13.0';VERSION='REAL_JEV_FORWARD_EXPERIMENT_V1'
def canonical(x):return json.dumps(x,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def digest(x):return hashlib.sha256(canonical(x)).hexdigest()
def integer(v):return type(v) is int and v>=0
def exact_keys(x,keys):
 if not isinstance(x,dict) or set(x)!=set(keys):raise ValueError('SCHEMA_EXTRA_OR_MISSING')
SOURCE=('run_id','connectionId','clock_domain_id','boot_identity','ordinal','asof_ns','latest_book_ns','feature_completed_ns')
FEATURES=('flow_imb1','impulse1_bps','top3_imb','opposing_ratio','stable_prices','impulse500_bps','btc_impulse1_bps','btc_flow_imb1','leader_gap_bps','follower_impulse1_bps','ref1_ns','ref500_ns','leader_ref1_ns')
def validate_state(s):
 exact_keys(s,('schema','candidate','asset','source','feature_evidence_sha','features','contract_sha','direction','current_book'))
 if s['schema']!=VERSION or s['candidate'] not in CANDIDATES or s['asset'] not in SPECS:raise ValueError('VERSION_CANDIDATE_ASSET')
 if s['contract_sha']!=digest(SPECS[s['asset']]) or len(s['feature_evidence_sha'])!=64:raise ValueError('INPUT_EVIDENCE_CONTRACT')
 exact_keys(s['source'],SOURCE);exact_keys(s['features'],FEATURES);src=s['source'];f=s['features']
 if any(not isinstance(src[k],str) or not src[k] for k in SOURCE[:4]) or not all(integer(src[k]) for k in SOURCE[4:]):raise ValueError('PROVENANCE_TYPES')
 if not src['latest_book_ns']<=src['asof_ns']<=src['feature_completed_ns'] or src['asof_ns']-src['latest_book_ns']>250000000:raise ValueError('SOURCE_BOOK_FEATURE_CLOCK')
 if s['direction'] not in [-1,1] or type(s['direction']) is not int or type(f['stable_prices']) is not bool:raise ValueError('DIRECTION_BOOL')
 for k in FEATURES:
  if k=='stable_prices':continue
  if k.endswith('_ns'):
   if not integer(f[k]):raise ValueError('REFERENCE_CLOCK_TYPE')
  elif type(f[k]) not in [int,float] or not math.isfinite(f[k]):raise ValueError('NUMERIC_FEATURE')
 def ref(k,delta):return 0<=src['asof_ns']-delta-f[k]<=250000000
 if any(abs(f[k])>1 for k in ['flow_imb1','top3_imb','btc_flow_imb1']) or f['opposing_ratio']<0:raise ValueError('FEATURE_RANGE')
 b=s['current_book'];validate_book(b)
 if b['asset']!=s['asset'] or b['received_ns']!=src['latest_book_ns'] or b['ordinal']>src['ordinal'] or any(b[k]!=src[k] for k in SOURCE[:4]):raise ValueError('ASOF_BOOK_BINDING')
 side=s['direction']
 if s['candidate']=='FLOW_V1':qualified=ref('ref1_ns',1000000000) and abs(f['flow_imb1'])>=.8 and abs(f['impulse1_bps'])>=3 and f['flow_imb1']*side>0 and f['impulse1_bps']*side>0
 elif s['candidate']=='BOOK_V1':qualified=ref('ref500_ns',500000000) and ref('ref1_ns',1000000000) and f['stable_prices'] and abs(f['top3_imb'])>=.8 and f['top3_imb']*side>0 and f['opposing_ratio']<=.5 and abs(f['flow_imb1'])>=.5 and f['flow_imb1']*side>0 and abs(f['impulse500_bps'])<=1
 else:qualified=s['asset'] in ['ETH-USDT-SWAP','SOL-USDT-SWAP'] and ref('ref1_ns',1000000000) and ref('leader_ref1_ns',1000000000) and abs(f['btc_impulse1_bps'])>=3 and abs(f['btc_flow_imb1'])>=.8 and abs(f['leader_gap_bps'])>=2 and f['leader_gap_bps']*side>0 and f['btc_impulse1_bps']*side>0 and f['btc_flow_imb1']*side>0 and abs(f['follower_impulse1_bps'])<=1
 if not qualified:raise ValueError('CANDIDATE_NOT_QUALIFIED')
 return True
def request(s):
 validate_state(s)
 modelstate=json.loads(canonical(s));modelstate['execution_cost_context']={'capacity_USDT':500,'fee_each_side_bps':[5,10],'asof_required_move_bps':cost_context(s),'API_actual_USD_cost':'UNKNOWN_UNTIL_AUTHORIZED_RECEIPT','USDT_USD_conversion':'UNKNOWN'}
 return {'model':MODEL,'state':modelstate,'questions':{'action':{'type':'choice','instructions':'Choose WAIT, FOLLOW the fixed observed direction, or FADE it. Past received features are not future labels. Consider two-leg execution cost and abstain when evidence is insufficient. Confidence is not a win probability or sizing rule.','criteria':{'WAIT':'No position; evidence or after-cost space is insufficient.','FOLLOW':'Endorse continuation of the observed direction under the registered candidate.','FADE':'Endorse reversal of the observed direction under the registered candidate.'}}}}
def parse_response(r):
 if r.get('model')!=MODEL:raise ValueError('MODEL_MISMATCH')
 a=r['answers']['action'];p=a['probabilities'];confidence=a['confidence'];u=r['usage']
 if a.get('type')!='choice' or a.get('choice') not in ACTIONS or set(p)!=ACTIONS:raise ValueError('CHOICE_SCHEMA')
 if any(type(v) not in [int,float] or not math.isfinite(v) or not 0<=v<=1 for v in list(p.values())+[confidence]) or abs(sum(p.values())-1)>1e-6:raise ValueError('PROBABILITIES')
 if any(type(u.get(k)) is not int or u[k]<0 for k in ['input_tokens','output_tokens']):raise ValueError('USAGE')
 return {'action':a['choice'],'probabilities':p,'confidence':confidence,'usage':u,'confidence_not_winrate':True}
def cost_context(s):
 spec=SPECS[s['asset']];unit=F(spec['ctVal'])*F(spec['ctMult']);a,b=validate_book(s['current_book']);f=F(5,10000);result=[]
 for side,entry,exit in [(1,a,b),(-1,b,a)]:
  q=capacity(entry,F(500),unit,F(spec['lotSz']),F(spec['minSz']),f)
  if q is None:result.append(None);continue
  E=fill(entry,q,unit);X=fill(exit,q,unit)
  result.append(None if X is None else float((E*(1+f)/(X*(1-f))-1)*10000 if side==1 else (1-E*(1-f)/(X*(1+f)))*10000))
 return result
def real_transport(*args,**kwargs):raise RuntimeError('REAL_JEV_TRANSPORT_DISABLED_PERMISSION_BUDGET_UNANSWERED')
def select_development(metrics):
 if len(metrics)!=len(CANDIDATES) or {m['candidate'] for m in metrics}!=set(CANDIDATES):raise ValueError('ALL_DEVELOPMENT_CANDIDATES_REQUIRED')
 eligible=[]
 for m in metrics:
  exact_keys(m,('candidate','actual_calls','observed_trades','api_cost_complete','net_allcost_quote','jev_minus_matched_rule','jev_minus_wait','development_data_sha','evidence_kind'))
  if type(m['actual_calls']) is not int or type(m['observed_trades']) is not int or type(m['api_cost_complete']) is not bool:raise ValueError('METRICS_TYPES')
  value=F(str(m['net_allcost_quote']))
  if m['actual_calls']>=40 and m['observed_trades']>=20 and m['api_cost_complete'] and value>0:eligible.append((value,m['candidate']))
 chosen=sorted(eligible,key=lambda x:(-x[0],x[1]))[0][1] if eligible else None
 return {'selected':chosen,'all_candidates_metrics_sha':digest(metrics),'selection_score':'DEV_JEV_NET_ALLCOST_THEN_LEXICAL_ID','validation_metrics_never_input':True,'profit_and_increment_separate':[{'candidate':m['candidate'],'dev_net':m['net_allcost_quote'],'dev_increment_matched':m['jev_minus_matched_rule'],'dev_increment_wait':m['jev_minus_wait']} for m in metrics],'real_metric_authenticity_verifier':'NOT_IMPLEMENTED_DO_NOT_TREAT_KIND_STRING_AS_PROOF'}
def levels(book,side):
 out=[]
 for lv in book[side]:
  if not isinstance(lv,list) or len(lv)!=2:raise ValueError('BOOK_LEVEL')
  px,q=map(lambda x:F(D(str(x))),lv)
  if px<=0 or q<=0:raise ValueError('BOOK_NONPOSITIVE')
  out.append((px,q))
 if not out or len(out)>5:raise ValueError('BOOK_DEPTH')
 return out
def validate_book(book):
 exact_keys(book,('asset','run_id','connectionId','clock_domain_id','boot_identity','ordinal','received_ns','asks','bids'))
 if book['asset'] not in SPECS or not integer(book['ordinal']) or not integer(book['received_ns']):raise ValueError('BOOK_ID_TIME')
 asks,bids=levels(book,'asks'),levels(book,'bids')
 if asks[0][0]<=bids[0][0] or asks!=sorted(asks) or bids!=sorted(bids,reverse=True):raise ValueError('BOOK_SORT_CROSS')
 return asks,bids
def fill(ls,quantity,unit):
 left=quantity;cash=F(0)
 for px,q in ls:
  take=min(left,q);cash+=take*px*unit;left-=take
  if left==0:return cash
 return None
def capacity(ls,budget,unit,step,minimum,fee):
 left=budget/(1+fee);q=F(0)
 for px,available in ls:
  take=min(available,left/(px*unit));q+=take;left-=take*px*unit
  if left==0:break
 if left>0:return None
 q=(q//step)*step
 return q if q>=minimum else None
class Experiment:
 def __init__(self,fixture=False,fee_each_bps=5):
  if fee_each_bps not in [5,10] or type(fee_each_bps) is not int:raise ValueError('FEE_SCENARIO')
  self.fee_each_bps=fee_each_bps;self.cash_complete={};self.last_book=None
  self.fixture=fixture;self.stage='DEVELOPMENT';self.selected=None;self.cut=None;self.events={};self.ledger=[];self.seen=set();self.nextid=1;self.position={};self.cash={(c,a):F(500) for c in CANDIDATES for a in ARMS};self.actual_api_calls=0
 def record(self,e,arm,status,**extra):
  r={'event_id':e['id'],'candidate':e['state']['candidate'],'asset':e['state']['asset'],'stage':self.stage,'arm':arm,'status':status,'evidence_kind':'SYNTHETIC_NOT_MODEL_RUN' if self.fixture else 'REAL_PROVIDER_NOT_CONNECTED','state_sha':e['sha'],'actual_api_calls':self.actual_api_calls,'fixed_fee_each_bps':self.fee_each_bps,**extra};self.ledger.append(r);return r
 def submit(self,s,actual_sent_ns):
  try:validate_state(s)
  except Exception as exc:
   self.ledger.append({'event_id':self.nextid,'arm':'ALL','status':'REJECTED_STATE_CONTRACT','evidence_kind':'SYNTHETIC_NOT_MODEL_RUN' if self.fixture else 'REAL_PROVIDER_NOT_CONNECTED','error_type':type(exc).__name__,'reason':str(exc),'actual_api_calls':0,'raw_unvalidated_input_not_logged':True});self.nextid+=1;raise
  src=s['source'];h=digest(s)
  if h in self.seen:raise ValueError('DUPLICATE_STATE')
  if self.stage=='VALIDATION' and (s['candidate']!=self.selected or src['asof_ns']<=self.cut):raise ValueError('UNSELECTED_OR_PRE_FREEZE_VALIDATION')
  self.seen.add(h);e={'id':self.nextid,'state':json.loads(canonical(s)),'sha':h,'sent_ns':actual_sent_ns,'completion_ns':None,'action':None};self.nextid+=1;self.events[e['id']]=e
  if not integer(actual_sent_ns) or not src['feature_completed_ns']<=actual_sent_ns or actual_sent_ns-src['asof_ns']>250000000 or actual_sent_ns-src['latest_book_ns']>250000000:
   for arm in ARMS:self.record(e,arm,'REJECTED_SEND_TTL_OR_CLOCK',api_attempted=False,api_cost_USD=0)
   return e['id']
  if not self.fixture:
   for arm in ARMS:self.record(e,arm,'NOT_RUN_PERMISSION_BUDGET_TRANSPORT_DISABLED',api_attempted=False,api_cost_USD=0)
   return e['id']
  e['decision_clocks']={'RULE_IMMEDIATE_NO_AI':src['feature_completed_ns']};self.record(e,'RULE_IMMEDIATE_NO_AI','RULE_READY_IMMEDIATE_FEATURE_COMPLETION',completed_ns=src['feature_completed_ns'],action='FOLLOW',api_cost_quote=0)
  self.record(e,'JEV','FIXTURE_REQUEST_PREPARED_NOT_SENT',request_sha=digest(request(s)),api_attempted=False,api_cost_USD=0);return e['id']
 def fixture_response(self,id,response,completed_ns,error=None,api_cost_quote=None):
  if not self.fixture:raise RuntimeError('FIXTURE_INJECTION_DISABLED_FOR_REAL_EXPERIMENT')
  e=self.events[id]
  if e['completion_ns'] is not None:raise ValueError('DUPLICATE_COMPLETION')
  if not integer(completed_ns) or completed_ns<e['sent_ns']:raise ValueError('COMPLETION_BEFORE_SEND')
  e['completion_ns']=completed_ns;e['api_cost_quote']=api_cost_quote;self.cash_complete[(e['state']['candidate'],'JEV')]=self.cash_complete.get((e['state']['candidate'],'JEV'),True) and api_cost_quote is not None;e['matched_execution_clock']=completed_ns;e.setdefault('decision_clocks',{}).update(JEV=completed_ns,RULE_MATCHED_NO_AI=completed_ns)
  if api_cost_quote is not None:
   cost=F(str(api_cost_quote))
   if cost<0:raise ValueError('NEGATIVE_API_COST')
   acct=(e['state']['candidate'],'JEV');self.cash[acct]-=cost;self.record(e,'JEV','FIXTURE_API_COST_DEBIT',api_cost_quote=str(cost),cash_after_api=str(self.cash[acct]))
  try:
   if error:raise ValueError('PROVIDER_ERROR:'+error)
   if completed_ns-e['sent_ns']>1000000000:raise ValueError('PROVIDER_TIMEOUT')
   if completed_ns-e['state']['source']['asof_ns']>250000000 or completed_ns-e['state']['source']['latest_book_ns']>250000000:raise ValueError('DECISION_INPUT_EXPIRED_AT_COMPLETION')
   parsed=parse_response(response);e['action']=parsed['action'];self.record(e,'JEV','FIXTURE_ACCEPTED' if e['action']!='WAIT' else 'FIXTURE_WAIT',completed_ns=completed_ns,parsed=parsed,api_cost_quote=api_cost_quote,api_attempted=False)
  except Exception as exc:e['action']='WAIT';self.record(e,'JEV','FIXTURE_ERROR_OR_TIMEOUT',completed_ns=completed_ns,error=str(exc),api_cost_quote=api_cost_quote,api_attempted=False)
  if completed_ns-e['state']['source']['asof_ns']>250000000:e['decision_clocks'].pop('RULE_MATCHED_NO_AI',None);self.record(e,'RULE_MATCHED_NO_AI','REJECTED_MATCHED_INPUT_TTL',completed_ns=completed_ns)
  if 'RULE_MATCHED_NO_AI' in e['decision_clocks']:self.record(e,'RULE_MATCHED_NO_AI','RULE_READY_MATCHED_COMPLETION',completed_ns=completed_ns,action='FOLLOW',api_cost_quote=0)
  self.record(e,'WAIT_NO_AI','NO_TRADE',completed_ns=completed_ns,price_fee_delta=0,api_cost_quote=0)
 def book(self,b,fee_each_bps=None):
  if fee_each_bps is not None and fee_each_bps!=self.fee_each_bps:raise ValueError('FEE_SCENARIO_CHANGE')
  fee_each_bps=self.fee_each_bps
  asks,bids=validate_book(b)
  cursor=(b['ordinal'],b['received_ns'])
  if self.last_book is not None and (cursor[0]<=self.last_book[0] or cursor[1]<self.last_book[1]):raise ValueError('BOOK_ORDER')
  self.last_book=cursor
  for e in self.events.values():
   s=e['state'];src=s['source']
   if b['asset']!=s['asset']:continue
   if any(b[k]!=src[k] for k in SOURCE[:4]):continue
   if b['ordinal']<=src['ordinal']:continue
   for arm,action in [('JEV',e['action']),('RULE_MATCHED_NO_AI','FOLLOW'),('RULE_IMMEDIATE_NO_AI','FOLLOW')]:
    decision=e.get('decision_clocks',{}).get(arm)
    if decision is None or b['received_ns']<=decision:continue
    key=(e['id'],arm)
    if key in e.get('finished',set()):continue
    acct=(s['candidate'],arm);fee=F(fee_each_bps,10000);spec=SPECS[s['asset']];unit=F(spec['ctVal'])*F(spec['ctMult'])
    if key not in self.position:
     if action=='WAIT':e.setdefault('finished',set()).add(key);continue
     e.setdefault('entry_checked',set())
     if key in e['entry_checked']:continue
     e['entry_checked'].add(key)
     if b['received_ns']-decision>250000000:self.record(e,arm,'CENSORED_FIRST_BOOK_EXPIRED');e.setdefault('finished',set()).add(key);continue
     if any(pos['acct']==acct for pos in self.position.values()):self.record(e,arm,'REJECTED_RISK_ONE_OPEN_ACCOUNT');e.setdefault('finished',set()).add(key);continue
     if self.cash[acct]<=0:self.record(e,arm,'REJECTED_NONPOSITIVE_CASH');e.setdefault('finished',set()).add(key);continue
     side=s['direction']*(1 if action=='FOLLOW' else -1);ls=asks if side==1 else bids;q=capacity(ls,min(F(500),self.cash[acct]),unit,F(spec['lotSz']),F(spec['minSz']),fee)
     if q is None:self.record(e,arm,'REJECTED_MINLOT_OR_DEPTH');e.setdefault('finished',set()).add(key);continue
     en=fill(ls,q,unit);reserved=en*(1+fee);self.cash[acct]-=reserved;self.position[key]={'acct':acct,'qty':q,'side':side,'entry':en,'reserved':reserved,'fee':fee,'entry_ns':b['received_ns'],'unit':unit};self.record(e,arm,'PAPER_ENTRY_FIXTURE_ONLY',entry_ns=b['received_ns'],quote_ordinal=b['ordinal'],contracts=str(q),entry_fee=str(en*fee),cash_free=str(self.cash[acct]),collateral_proxy_reserved=str(reserved))
    else:
     pos=self.position[key];target=pos['entry_ns']+[REDACTED_PHONE]
     if b['received_ns']<=target:continue
     if b['received_ns']-target>250000000:self.record(e,arm,'CENSORED_FIRST_EXIT_BOOK_EXPIRED_POSITION_UNRESOLVED');e.setdefault('finished',set()).add(key);continue
     ex=fill(bids if pos['side']==1 else asks,pos['qty'],pos['unit'])
     if ex is None:self.record(e,arm,'CENSORED_EXIT_DEPTH_POSITION_UNRESOLVED');e.setdefault('finished',set()).add(key);continue
     gross=pos['side']*(ex-pos['entry']);fees=(ex+pos['entry'])*pos['fee'];net=gross-fees;self.cash[acct]+=pos['reserved']+net;del self.position[key];e.setdefault('finished',set()).add(key);api=e.get('api_cost_quote') if arm=='JEV' else 0
     self.record(e,arm,'PAPER_EXIT_FIXTURE_ONLY',exit_ns=b['received_ns'],quote_ordinal=b['ordinal'],price_fee_delta=str(net),gross=str(gross),fees=str(fees),api_cost_quote=api,allcost_delta=None if api is None else str(net-F(str(api))),paper_proxy_cash_after_pricefee_and_known_api=str(self.cash[acct]),api_cost_complete=self.cash_complete.get(acct,True),real_funding_fee_fill_verified=False)
 def end(self):
  for e in self.events.values():
   if e['completion_ns'] is None:self.record(e,'JEV','INCOMPLETE_NO_REAL_RESPONSE_OR_BLOCKED')
   for key,pos in self.position.items():
    if key[0]==e['id']:self.record(e,key[1],'CENSORED_END_OPEN_POSITION_UNKNOWN_MARK',reserved=str(pos['reserved']))
  return self.ledger
 def fixture_freeze(self,candidate,freeze_ns):
  if not self.fixture or candidate not in CANDIDATES or not integer(freeze_ns):raise ValueError('FIXTURE_FREEZE_ONLY')
  self.stage='VALIDATION';self.selected=candidate;self.cut=freeze_ns
  return {'kind':'SYNTHETIC_NOT_REAL_FREEZE','candidate':candidate,'cut':freeze_ns,'all_development_ledger_sha':digest(self.ledger),'protocol_parameters_sha':digest({'model':MODEL,'version':VERSION,'candidates':CANDIDATES,'arms':ARMS})}
 def freeze_selection(self,candidate,freeze_ns,development_receipt):
  if self.fixture:raise RuntimeError('SYNTHETIC_DEVELOPMENT_CANNOT_FREEZE_REAL_SELECTION')
  if candidate not in CANDIDATES or not integer(freeze_ns) or development_receipt.get('kind')!='REAL_JEV_AUDITED_DEVELOPMENT':raise ValueError('NO_REAL_DEVELOPMENT_SELECTION_RECEIPT')
  if development_receipt.get('actual_calls',0)<40 or development_receipt.get('eligible_trades',0)<20 or development_receipt.get('api_cost_complete') is not True:raise ValueError('INSUFFICIENT_DEVELOPMENT')
  raise RuntimeError('REAL_DEVELOPMENT_RECEIPT_VERIFIER_NOT_IMPLEMENTED_FAIL_CLOSED')
if __name__=='__main__':
 print(json.dumps({'status':'OFFLINE_ORCHESTRATOR_TRANSPORT_DISABLED','actual_Jev_calls':0,'permission_budget':'PENDING','no_network_or_credentials_read':True}))
