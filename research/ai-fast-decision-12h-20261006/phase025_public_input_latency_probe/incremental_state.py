from collections import deque
from bisect import bisect_left
from decimal import Decimal
from fractions import Fraction as F
import json,hashlib,math
import state_v3 as original
class IncrementalState:
 def __init__(self,registry,expected_identity=None):
  self.registry=json.loads(original.canonical(registry));self.specs={x['instId']:x for x in self.registry};self.identity=expected_identity;self.features=None;self.flow=None;self.last_row=None;self.count=0;self.last_shared=-1;self.last_wall=-1;self.invalid=None;self.prefix_hasher=hashlib.sha256();self.prefix_hasher.update(b'[');self.raw_books={a:{} for a in self.specs};self.witness={a:deque() for a in self.specs}
 def prefix_sha256(self):h=self.prefix_hasher.copy();h.update(b']');return h.hexdigest()
 def ingest(self,row):
  if self.invalid:raise ValueError('STREAM_INVALID:'+self.invalid)
  try:
   original.forbidden(row);pr=original.provenance(row)
   if row['local_ordinal']!=self.count+1 or row['os_shared_ns']<self.last_shared or row['receive_wall_ns']<self.last_wall:raise ValueError('SOURCE_CLOCK_OR_ORDINAL_BACKSTEP')
   if self.identity is None:self.identity={k:pr[k] for k in ['run_id','connectionId','clock_domain_id','boot_identity']};self.features=original.suite.Features(self.specs,pr['clock_domain_id']);self.flow=original.ExactFlow()
   if any(not pr[k] or pr[k]!=self.identity[k] for k in ['run_id','connectionId','clock_domain_id','boot_identity']):raise ValueError('SOURCE_RUN_CONN_DOMAIN_BOOT_MISMATCH')
   if self.features is None:self.features=original.suite.Features(self.specs,self.identity['clock_domain_id']);self.flow=original.ExactFlow()
   if not isinstance(row.get('receive_wall_ms'),(int,float)) or isinstance(row['receive_wall_ms'],bool) or not math.isfinite(row['receive_wall_ms']) or abs(row['receive_wall_ms']-row['receive_wall_ns']/1e6)>.001:raise ValueError('WALL_MS_NS_MISMATCH')
   if row['raw']=='pong':raw={}
   else:raw=json.loads(row['raw']);original.forbidden(raw)
   if not isinstance(raw,dict):raise ValueError('RAW_NOT_OBJECT')
   arg=raw.get('arg',{})
   if arg.get('instId')!=row['instId'] or arg.get('channel')!=row['channel']:raise ValueError('RAW_ARG_SOURCE_MISMATCH')
   for record in raw.get('data',[]):
    if row['instId'] not in self.specs:raise ValueError('UNREGISTERED_DATA_ASSET')
    if row['channel']=='books5':
     if original.suite.execution.valid_book(record) is None or any(not Decimal(z).is_finite() or Decimal(z)<=0 for side in ['asks','bids'] for lv in record[side] for z in lv[:2]):raise ValueError('INVALID_BOOK')
    elif row['channel']=='trades':
     if record.get('side') not in ['buy','sell'] or any(not Decimal(record[k]).is_finite() or Decimal(record[k])<=0 for k in ['px','sz']):raise ValueError('INVALID_TRADE')
    else:raise ValueError('UNREGISTERED_CHANNEL')
   encoded=original.canonical(row);copy=json.loads(encoded)
   if self.count:self.prefix_hasher.update(b',')
   self.prefix_hasher.update(encoded);self.count+=1;self.last_shared=copy['os_shared_ns'];self.last_wall=copy['receive_wall_ns'];self.last_row=copy
   result=self.features.ingest(copy)
   if result is not None:
    asset,now,_,domain,conn=result;self.flow.ingest(copy,now,conn,domain,self.specs[asset]);state=self.features.states[asset]
    if copy['channel']=='books5' and raw.get('data'):self.raw_books[asset][copy['local_ordinal']]=copy
    if copy['channel']=='trades':
     for trade in raw.get('data',[]):self.witness[asset].append((copy['os_shared_ns'],{k:copy[k] for k in ['run_id','connectionId','clock_domain_id','local_ordinal','os_shared_ns']}|{'raw_trade':trade}))
    while self.witness[asset] and self.witness[asset][0][0]<=copy['os_shared_ns']-1000000000:self.witness[asset].popleft()
    while state['flow'] and state['flow'][0][0]<=now-1000:state['flow'].popleft()
    start=max(0,bisect_left(state['times'],now-1250)-1)
    if start:state['times']=state['times'][start:];state['books']=state['books'][start:]
    keep={b['ordinal'] for b in state['books']};self.raw_books[asset]={k:v for k,v in self.raw_books[asset].items() if k in keep}
  except Exception as e:self.invalid=type(e).__name__+':'+str(e);raise
 def snapshot(self,feature_ns=None,is_live=False):
  if self.invalid:raise ValueError('STREAM_INVALID:'+self.invalid)
  if not self.last_row or not isinstance(is_live,bool):raise ValueError('PREFIX_OR_LIVE_FLAG')
  source=self.last_row;asset=source['instId']
  if asset not in self.specs:raise ValueError('UNKNOWN_ASSET')
  identity=original.provenance(source);now=source['os_shared_ns']/1e6;f=self.features.feature(asset,now,1000,identity['connectionId'],identity['clock_domain_id'])
  if f is None or asset not in self.flow.states or self.flow.states[asset]['unknown']:raise ValueError('MISSING_CAUSAL_REFERENCE_OR_FLOW')
  cur,ref=f['book'],f['reference'];cr=self.raw_books[asset][cur['ordinal']];rr=self.raw_books[asset][ref['ordinal']];current=json.loads(cr['raw'])['data'][0];reference=json.loads(rr['raw'])['data'][0];spec=self.specs[asset];unit=Decimal(spec['ctVal'])*Decimal(spec['ctMult']);proxy=original.asof_required_move(cur,unit,Decimal(spec['lotSz']),Decimal(spec['minSz']))
  if proxy is None:raise ValueError('COST_DEPTH_MISSING_CANNOT_PREPARE_MODEL_STATE')
  required,legs=proxy;total,net=self.flow.states[asset]['total'],self.flow.states[asset]['net'];mid=(F(cur['asks'][0][0])+F(cur['bids'][0][0]))/2;refmid=(F(ref['asks'][0][0])+F(ref['bids'][0][0]))/2;impulse=(mid/refmid-1)*10000;direction=1 if net>0 else -1 if net<0 else 0;dominant=(total+direction*net)/2;depth=sum((F(px)*F(q)*F(unit) for px,q in (ref['asks'] if direction==1 else ref['bids'])[:5]),F(0));status=original.qualifies(impulse,total,net,required,depth)
  return {'schemaVersion':original.VERSION,'state_version':original.VERSION,'question_version':original.QUESTION,'family':original.FAMILY,'qualified_rule_sha':original.RULE_SHA,'asset':asset,'contract_registry':self.registry,'contract_spec':spec,'source':identity,'current_book':{'asks':current['asks'],'bids':current['bids'],'raw_record':current,'provenance':original.provenance(cr,current)},'reference_book':{'asks':reference['asks'],'bids':reference['bids'],'raw_record':reference,'provenance':original.provenance(rr,reference)},'feature_completed_shared_ns':feature_ns,'is_live':is_live,'past_impulse_exact':str(impulse),'received_flow_total_exact':str(total),'received_flow_net_exact':str(net),'received_flow_records':[r for _,r in self.witness[asset]],'dominant_exact':str(dominant),'reference_opposing_depth_exact':str(depth),'asof_cost_proxy_legs':legs,'required_move_max_exact':str(required),'fixed_buffer_bps':5,'eligibility':status=='QUALIFIED','rejectreason':None if status=='QUALIFIED' else status,'allowed_actions':list(original.ACTIONS),'evidence_label':'REAL_RECEIVED_HISTORICAL_NOT_MODEL_RUN','causal_prefix_sha256':self.prefix_sha256()}
 def retention(self):
  if self.features is None:return {}
  return {'ingested_rows':self.count,'cached_book_records':{a:len(s['books']) for a,s in self.features.states.items()},'cached_raw_book_rows':{a:len(v) for a,v in self.raw_books.items()},'received1s_trade_witnesses':{a:len(v) for a,v in self.witness.items()},'full_seen_trade_ids_features':{a:len(s['seen_trades']) for a,s in self.features.states.items()},'full_seen_trade_ids_exactflow':{a:len(s['seen']) for a,s in self.flow.states.items()},'permanent_constant_space':False}
