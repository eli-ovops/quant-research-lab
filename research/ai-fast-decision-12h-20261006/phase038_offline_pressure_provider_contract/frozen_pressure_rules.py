from pathlib import Path
from fractions import Fraction as F
from decimal import Decimal as D
from collections import deque,Counter
from bisect import bisect_right,bisect_left
import json,math
from frozen_execution_v12 import valid_book
from frozen_cost_shock import asof_required_move
FOLLOW='CONTINUATION_FOLLOW_V1';FADE='PRESSURE_DECAY_FADE_V1'
def pressure_choice(total10,net10,total1,net1,impulse10,required,depth10,last_trade_age_ns):
 if total10<=0 or abs(net10)>total10 or total1<0 or total1>total10 or abs(net1)>total1:return None,'WAIT_INVALID_FLOW'
 if abs(net10-net1)>total10-total1:return None,'WAIT_NESTED_WINDOW_INCONSISTENCY'
 if abs(net10)/total10<F(4,5) or impulse10*net10<=0:return None,'WAIT_SHOCK_DIRECTION'
 if abs(impulse10)<required+5:return None,'WAIT_10S_COST_ROOM'
 shock=1 if net10>0 else -1;dominant=(total10+shock*net10)/2
 if depth10<=0 or dominant<depth10:return None,'WAIT_DOMINANT10_BELOW_REFERENCE_DEPTH'
 if total1<=0 or last_trade_age_ns is None or not 0<=last_trade_age_ns<=250000000:return None,'WAIT_NO_REAL_FRESH_1S_TRADE'
 prior9=total10-total1
 if prior9<=0:return None,'WAIT_NO_PRIOR9'
 ratio=9*total1/prior9;imb1=net1/total1
 if ratio>=1 and abs(imb1)>=F(4,5) and net1*shock>0:return FOLLOW,None
 if ratio<=F(1,4) and abs(imb1)<=F(1,5):return FADE,None
 return None,'WAIT_PRESSURE_NEITHER_FIXED_REGIME'
class PressureRules:
 def __init__(self,registry,expected_domain,forward_cut_ns=None):
  if forward_cut_ns is not None and (not isinstance(forward_cut_ns,int) or isinstance(forward_cut_ns,bool) or forward_cut_ns<0):raise ValueError('INVALID_ACTUAL_FORWARD_CUT')
  self.specs={x['instId']:x for x in registry};self.expected=expected_domain;self.forward_cut_ns=forward_cut_ns;self.identity=None;self.ordinal=0;self.last_ns=-1;self.invalid=None;self.cool={};self.counters=Counter();self.states={a:{'books':[],'times':[],'flow':deque(),'seen':{},'firsttrade_ns':None,'lasttrade_ns':None,'conflict':False} for a in self.specs}
 def ingest(self,row):
  if self.invalid:raise ValueError('PRESSURE_STREAM_INVALID:'+self.invalid)
  try:
   for k in ['local_ordinal','os_shared_ns','receive_wall_ns']:
    if not isinstance(row.get(k),int) or isinstance(row[k],bool):raise ValueError('MISSING_ACTUAL_CLOCK_OR_ORDINAL')
   if row['local_ordinal']!=self.ordinal+1 or row['os_shared_ns']<self.last_ns:raise ValueError('SOURCE_PROGRESS')
   identity=(row['run_id'],row['connectionId'],row['clock_domain_id'],row['boot_identity'])
   if any(not x for x in identity) or identity[2]!=self.expected:raise ValueError('SOURCE_CLOCK_DOMAIN')
   if self.identity is None:self.identity=identity
   if self.identity!=identity:raise ValueError('RUN_CONN_DOMAIN_BOOT_CHANGED')
   self.ordinal=row['local_ordinal'];self.last_ns=row['os_shared_ns'];a=row['instId']
   if a not in self.states:return None
   raw=json.loads(row['raw']);arg=raw.get('arg',{})
   if arg.get('instId')!=a or arg.get('channel')!=row['channel']:raise ValueError('RAW_ARG_MISMATCH')
   s=self.states[a];now=row['os_shared_ns'];unit=F(D(self.specs[a]['ctVal']))*F(D(self.specs[a]['ctMult']))
   for data in raw.get('data',[]):
    if row['channel']=='books5':
     b=valid_book(data)
     if b is None or any(not D(z).is_finite() or D(z)<=0 for side in ['asks','bids'] for level in data[side] for z in level[:2]):raise ValueError('INVALID_BOOK')
     asks,bids=b;s['books'].append({'ns':now,'ordinal':row['local_ordinal'],'asks':asks,'bids':bids,'mid':(F(asks[0][0])+F(bids[0][0]))/2});s['times'].append(now)
    elif row['channel']=='trades':
     if data.get('tradeId') is None:s['conflict']=True;self.counters['MISSING_TRADE_ID_UNKNOWN']+=1;continue
     if data.get('side') not in ['buy','sell'] or any(not D(data[k]).is_finite() or D(data[k])<=0 for k in ['px','sz']):raise ValueError('INVALID_TRADE')
     key=(data['tradeId'],data.get('source'));signature=tuple(data.get(k) for k in ['px','sz','side','ts','count'])
     if key in s['seen']:
      if s['seen'][key]!=signature:s['conflict']=True;self.counters['TRADE_IDENTITY_CONFLICT']+=1
      else:self.counters['EXACT_TRADE_REPEAT']+=1
      continue
     s['seen'][key]=signature;amount=F(D(data['px']))*F(D(data['sz']))*unit;s['flow'].append((now,amount,amount*(1 if data['side']=='buy' else -1),row['local_ordinal']));s['firsttrade_ns']=now if s['firsttrade_ns'] is None else s['firsttrade_ns'];s['lasttrade_ns']=now
   while s['flow'] and s['flow'][0][0]<=now-10000000000:s['flow'].popleft()
   start=max(0,bisect_left(s['times'],now-10250000000)-1)
   if start:s['times']=s['times'][start:];s['books']=s['books'][start:]
   return self.candidate(a,row)
  except Exception as e:self.invalid=str(e);raise
 def candidate(self,asset,row):
  s=self.states[asset];now=row['os_shared_ns']
  def wait(reason):self.counters[asset+'|'+reason]+=1;return {'asset':asset,'asof_ordinal':row['local_ordinal'],'qualified_rule':None,'rejectreason':reason,'is_live':False,'provider_adapter':'NOT_IMPLEMENTED'}
  if self.forward_cut_ns is not None and now<self.forward_cut_ns:return wait('WAIT_PRE_CUT_WARMUP_ONLY_NO_COOLDOWN')
  if s['conflict']:return wait('WAIT_TRADE_IDENTITY_UNKNOWN')
  if s['firsttrade_ns'] is None or now-s['firsttrade_ns']<10000000000:return wait('WAIT_TRADE_WARMUP10')
  if not s['books'] or now-s['books'][-1]['ns']>250000000:return wait('WAIT_CURRENT_BOOK_STALE')
  i10=bisect_right(s['times'],now-10000000000)-1;i1=bisect_right(s['times'],now-1000000000)-1
  if i10<0 or i1<0 or now-10000000000-s['books'][i10]['ns']>250000000 or now-1000000000-s['books'][i1]['ns']>250000000:return wait('WAIT_REFERENCE10_OR1')
  book,ref10,ref1=s['books'][-1],s['books'][i10],s['books'][i1];total10=sum((x[1] for x in s['flow']),F(0));net10=sum((x[2] for x in s['flow']),F(0));one=[x for x in s['flow'] if x[0]>now-1000000000];total1=sum((x[1] for x in one),F(0));net1=sum((x[2] for x in one),F(0));impulse=(book['mid']/ref10['mid']-1)*10000;spec=self.specs[asset];unit=D(spec['ctVal'])*D(spec['ctMult']);proxy=asof_required_move(book,unit,D(spec['lotSz']),D(spec['minSz']))
  if proxy is None:return wait('WAIT_CURRENT_ENTRY_OR_REVERSE_DEPTH')
  required,legs=proxy;shock=1 if net10>0 else -1 if net10<0 else 0;depth=sum((F(px)*F(q)*F(unit) for px,q in (ref10['asks'] if shock==1 else ref10['bids'])[:5]),F(0));age=now-s['lasttrade_ns'] if s['lasttrade_ns'] is not None else None;rule,reason=pressure_choice(total10,net10,total1,net1,impulse,required,depth,age)
  if rule is None:return wait(reason)
  key=(asset,rule)
  if now-self.cool.get(key,-10**30)<35000000000:return wait('WAIT_RULE35_COOLDOWN')
  self.cool[key]=now;self.counters[asset+'|'+rule]+=1
  return {'asset':asset,'asof_ordinal':row['local_ordinal'],'source_asof_shared_ns':now,'source_receive_wall_ns':row['receive_wall_ns'],'run_id':row['run_id'],'connectionId':row['connectionId'],'clock_domain_id':row['clock_domain_id'],'qualified_rule':rule,'action':'FOLLOW' if rule==FOLLOW else 'FADE','shadow_actions':['FOLLOW','FADE'],'shadow_not_additional_strategy_configs':True,'shock_direction':shock,'trade_direction':shock if rule==FOLLOW else -shock,'impulse10_exact':str(impulse),'total10_exact':str(total10),'net10_exact':str(net10),'total1_exact':str(total1),'net1_exact':str(net1),'prior9_exact':str(total10-total1),'rate_ratio_exact':str(9*total1/(total10-total1)),'dominant10_exact':str((total10+shock*net10)/2),'reference_opposing_top5_exact':str(depth),'required_move_max_exact':str(required),'fixed_buffer_bps':5,'asof_cost_proxy_legs':legs,'current_book_ordinal':book['ordinal'],'reference10_ordinal':ref10['ordinal'],'reference1_ordinal':ref1['ordinal'],'latest_trade_age_ns':age,'rejectreason':None,'is_live':False,'provider_adapter':'NOT_IMPLEMENTED','past_received_proxy_not_future_profit':True}
