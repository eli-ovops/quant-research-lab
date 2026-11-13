"""Offline-tested preparation. No secrets/env reads; default transport disabled."""
import datetime, hashlib, http.client, json, math, ssl, time
from decimal import Decimal
from dataclasses import dataclass
HOST='api.typesafe.ai'; PATH='/v1/systemone'; MODEL='jev-1.13.0'
TTL_NS=250_000_000; MAX_RESPONSE=1_000_000

def canonical(x):return json.dumps(x,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def sha(x):return hashlib.sha256(x).hexdigest()
def clock():return time.clock_gettime_ns(time.CLOCK_MONOTONIC)
def integer(x):return type(x) is int and x>=0
def money(x):
 v=Decimal(str(x))
 if not v.is_finite() or v<0:raise ValueError('INVALID_MONEY')
 return v
@dataclass(frozen=True)
class Authorization:
 permission:bool=False
 allowed_model:str=MODEL
 expires_wall_ns:int=0
 receipt_sha256:str=''
@dataclass(frozen=True)
class PricingBound:
 maximum_USD:str=''
 verified:bool=False
 evidence_sha256:str=''
 request_sha256:str=''
 model:str=MODEL
class Budget:
 def __init__(self,dollars,call_limit):
  self.limit=money(dollars)
  if type(call_limit) is not int or call_limit<0:raise ValueError('CALL_LIMIT')
  self.call_limit=call_limit;self.attempts=0;self.committed=Decimal(0);self.reservations={}
 def reserve(self,bound):
  if bound.verified is not True or len(bound.evidence_sha256)!=64:raise ValueError('WORST_PRICING_NOT_VERIFIED')
  maximum=money(bound.maximum_USD)
  if maximum<=0:raise ValueError('WORST_PRICING_NOT_VERIFIED')
  if self.attempts>=self.call_limit or self.committed+maximum>self.limit:raise ValueError('BUDGET_EXHAUSTED')
  self.attempts+=1;id=self.attempts;self.committed+=maximum;self.reservations[id]={'maximum':maximum,'charge':None};return id
 def settle(self,id,actual_USD,verified_receipt_sha256):
  # External billing evidence, not inferred from undocumented response fields.
  if not isinstance(verified_receipt_sha256,str) or len(verified_receipt_sha256)!=64:raise ValueError('BILLING_EVIDENCE_REQUIRED')
  r=self.reservations[id]
  if r['charge'] is not None:raise ValueError('DUPLICATE_SETTLEMENT')
  charge=money(actual_USD)
  if charge>r['maximum']:raise ValueError('PRICING_BOUND_BREACHED_KEEP_RESERVATION')
  self.committed-=r['maximum']-charge;r['charge']=charge

def real_http(payload,token,timeout):
 # http.client does not follow redirects or retry; TLS defaults verify hostname/cert.
 context=ssl.create_default_context();context.check_hostname=True;context.verify_mode=ssl.CERT_REQUIRED
 conn=http.client.HTTPSConnection(HOST,443,timeout=timeout,context=context)
 try:
  conn.request('POST',PATH,body=payload,headers={'Authorization':'Bearer '+token,'Content-Type':'application/json'})
  response=conn.getresponse();status=response.status
  if 300<=status<400:return status,b'' # Do not read or follow Location.
  body=response.read(MAX_RESPONSE+1)
  if len(body)>MAX_RESPONSE:raise ValueError('RESPONSE_SIZE_LIMIT')
  return status,body
 finally:conn.close()

def parse_choice(r):
 if not isinstance(r,dict) or r.get('model')!=MODEL:raise ValueError('MODEL_MISMATCH')
 a=r['answers']['action'];p=a['probabilities'];u=r['usage']
 if a['type']!='choice' or a['choice'] not in ['WAIT','FOLLOW','FADE'] or set(p)!=set(['WAIT','FOLLOW','FADE']):raise ValueError('CHOICE_SCHEMA')
 values=list(p.values())+[a['confidence']]
 if any(type(x) not in [int,float] or not math.isfinite(x) or not 0<=x<=1 for x in values) or abs(sum(p.values())-1)>1e-6:raise ValueError('PROBABILITIES')
 if any(type(u.get(k)) is not int or u[k]<0 for k in ['input_tokens','output_tokens']):raise ValueError('USAGE')
 return {'choice':a['choice'],'probabilities':p,'confidence':a['confidence'],'usage':{k:u[k] for k in ['input_tokens','output_tokens']},'confidence_not_winrate':True}
class Transport:
 def __init__(self,budget,journal_path,enabled=False,http=None,now=clock,wall=time.time_ns,clock_domain_id=None):
  self.budget=budget;self.path=journal_path;self.enabled=enabled;self.http=http or real_http;self.fake=http is not None;self.now=now;self.wall=wall;self.domain=clock_domain_id;self.records=[]
 def record(self,r):
  self.records.append(r)
  if self.path:
   with open(self.path,'ab') as f:f.write(canonical(r)+b'\n')
 def call(self,request,token=None,authorization=None,pricing=None,source_asof_ns=None,latest_book_ns=None,feature_completed_ns=None,clock_domain_id=None,deadline_ns=None,timeout_s=1):
  row={'kind':'FAKE_HTTP_NOT_MODEL_RUN' if self.fake else 'REAL_TRANSPORT_PREPARATION','status':'REJECTED','actual_provider_verified':False,'endpoint':'https://'+HOST+PATH,'model':MODEL,'clock_domain_id':self.domain,'request_sha256':None,'response_sha256':None,'attempt_count':0,'actual_api_cost_USD':None,'billing_complete':False}
  try:
   if self.enabled is not True:raise ValueError('TRANSPORT_DISABLED')
   if authorization is None or authorization.permission is not True or authorization.allowed_model!=MODEL or not isinstance(authorization.receipt_sha256,str) or len(authorization.receipt_sha256)!=64 or not integer(authorization.expires_wall_ns) or self.wall()>=authorization.expires_wall_ns:raise ValueError('AUTHORIZATION_REQUIRED')
   if not isinstance(token,str) or not token or '\r' in token or '\n' in token:raise ValueError('TOKEN_MEMORY_ARGUMENT_REQUIRED')
   if not self.domain or clock_domain_id!=self.domain:raise ValueError('CLOCK_DOMAIN_MISMATCH')
   if not all(integer(x) for x in [source_asof_ns,latest_book_ns,feature_completed_ns,deadline_ns]):raise ValueError('CLOCK_FIELDS')
   if not latest_book_ns<=source_asof_ns<=feature_completed_ns:raise ValueError('CAUSAL_CLOCK_CHAIN')
   if type(timeout_s) not in [int,float] or not math.isfinite(timeout_s) or not 0<timeout_s<=10:raise ValueError('TIMEOUT_RANGE')
   now=self.now()
   if not feature_completed_ns<=now or now-source_asof_ns>TTL_NS or now-latest_book_ns>TTL_NS:raise ValueError('SEND_INPUT_EXPIRED')
   if now>=deadline_ns:raise ValueError('DEADLINE_BEFORE_SEND')
   if not isinstance(request,dict) or set(request)!=set(['model','state','questions']) or request['model']!=MODEL:raise ValueError('REQUEST_SCHEMA')
   q=request['questions']
   if not isinstance(q,dict) or set(q)!=set(['action']) or q['action'].get('type')!='choice' or set(q['action'].get('criteria',{}))!=set(['WAIT','FOLLOW','FADE']):raise ValueError('REQUEST_QUESTION')
   payload=canonical(request);row['request_sha256']=sha(payload)
   if pricing is None:raise ValueError('WORST_PRICING_NOT_VERIFIED')
   if pricing.model!=MODEL or pricing.request_sha256!=row['request_sha256']:raise ValueError('PRICING_REQUEST_BINDING_REQUIRED')
   reservation=self.budget.reserve(pricing);row.update(reservation_id=reservation,reserved_maximum_USD=str(self.budget.reservations[reservation]['maximum']),attempt_count=1,status='ATTEMPT_RESERVED')
   row['request_started_shared_ns']=self.now();row['request_started_wall_ns']=self.wall()
   if row['request_started_shared_ns']>=deadline_ns or row['request_started_shared_ns']-source_asof_ns>TTL_NS or row['request_started_shared_ns']-latest_book_ns>TTL_NS:raise ValueError('PRE_HTTP_DEADLINE_OR_TTL_KEEP_RESERVATION')
   row['status']='HTTP_ATTEMPT';self.record({**row,'journal_phase':'BEFORE_HTTP','budget_committed_USD':str(self.budget.committed)});effective=min(timeout_s,(deadline_ns-row['request_started_shared_ns'])/1e9)
   status,body=self.http(payload,token,effective)
   row['http_status']=status;row['response_completed_shared_ns']=self.now();row['response_completed_wall_ns']=self.wall();row['response_sha256']=sha(body)
   if 300<=status<400:raise ValueError('REDIRECT_REJECTED')
   if status!=200:raise ValueError('HTTP_STATUS_REJECTED')
   parsed=parse_choice(json.loads(body));row['parsed']=parsed
   if row['response_completed_shared_ns']>=deadline_ns:raise ValueError('COMPLETION_DEADLINE_EXPIRED')
   if row['response_completed_shared_ns']-row['request_started_shared_ns']>int(timeout_s*1e9):raise ValueError('COMPLETION_TIMEOUT')
   if row['response_completed_shared_ns']-source_asof_ns>TTL_NS or row['response_completed_shared_ns']-latest_book_ns>TTL_NS:raise ValueError('COMPLETION_INPUT_EXPIRED')
   row['status']='FAKE_VALID_RESPONSE' if self.fake else 'RESPONSE_PARSED_NOT_EXECUTION_VERIFIED';row['decision']=parsed['choice']
  except Exception as exc:
   row['error_type']=type(exc).__name__;row['decision']='WAIT'
   # Raw exception strings/headers/body/token never logged; known errors only code.
   row['reason']=str(exc) if type(exc) is ValueError and str(exc) in SAFE_CODES else 'UNTRUSTED_ERROR_TEXT_REDACTED'
   if row['attempt_count']:row.setdefault('response_completed_shared_ns',self.now());row.setdefault('response_completed_wall_ns',self.wall());row['status']='ATTEMPT_FAILED_RESERVATION_RETAINED'
  finally:
   row['budget_committed_USD']=str(self.budget.committed);row['journal_phase']='FINAL';self.record(row)
  return row
SAFE_CODES=set('TRANSPORT_DISABLED AUTHORIZATION_REQUIRED TOKEN_MEMORY_ARGUMENT_REQUIRED CLOCK_DOMAIN_MISMATCH CLOCK_FIELDS CAUSAL_CLOCK_CHAIN TIMEOUT_RANGE SEND_INPUT_EXPIRED DEADLINE_BEFORE_SEND REQUEST_SCHEMA REQUEST_QUESTION WORST_PRICING_NOT_VERIFIED PRICING_REQUEST_BINDING_REQUIRED BUDGET_EXHAUSTED PRE_HTTP_DEADLINE_OR_TTL_KEEP_RESERVATION REDIRECT_REJECTED HTTP_STATUS_REJECTED COMPLETION_DEADLINE_EXPIRED COMPLETION_TIMEOUT COMPLETION_INPUT_EXPIRED MODEL_MISMATCH CHOICE_SCHEMA PROBABILITIES USAGE RESPONSE_SIZE_LIMIT'.split())
if __name__=='__main__':print(json.dumps({'status':'DISABLED_NO_NETWORK_NO_KEY_READ','actual_Jev_calls':0}))
