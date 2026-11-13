from fractions import Fraction as F
from decimal import Decimal
from collections import deque,Counter
import json
import frozen_suite as suite
import frozen_execution_v12 as core
FEE=F(5,10000);BUFFER=F(5)
def asof_required_move(book,unit,step,minqty):
 proxy=[]
 for side in [1,-1]:
  levels=book['asks'] if side==1 else book['bids'];qty=core.size_capacity(levels,unit,step,minqty,Decimal('0.0005'))
  if qty is None:return None
  entry=core.depthfill(levels,qty,unit);reverse=core.depthfill(book['bids'] if side==1 else book['asks'],qty,unit)
  if entry is None or reverse is None:return None
  E,X=F(entry[0]),F(reverse[0])
  required=(E*(1+FEE)/(X*(1-FEE))-1)*10000 if side==1 else (1-E*(1-FEE)/(X*(1+FEE)))*10000
  proxy.append({'side':side,'contracts':str(qty),'entry_notional_USDT':str(entry[0]),'asof_reverse_notional_USDT':str(reverse[0]),'required_move_bps':float(required),'required_exact_fraction':str(required)})
 return max(F(x['required_exact_fraction']) for x in proxy),proxy
def qualifies(impulse,total,net,required,reference_opposing):
 if total<=0:return 'WAIT_NO_FLOW'
 if abs(net)/total<F(4,5) or impulse*net<=0:return 'WAIT_FLOW_DIRECTION'
 if abs(impulse)<required+BUFFER:return 'WAIT_INSUFFICIENT_PAST_COST_ROOM'
 direction=1 if net>0 else -1;dominant=(total+direction*net)/2
 if reference_opposing<=0:return 'WAIT_NO_REFERENCE_DEPTH'
 if dominant/reference_opposing<1:return 'WAIT_RECEIVED_VOLUME_BELOW_REFERENCE_DEPTH'
 return 'QUALIFIED'
class ExactFlow:
 def __init__(self):self.states={}
 def ingest(self,row,now,conn,domain,spec):
  asset=row['instId'];s=self.states.get(asset)
  if s is None or s['scope']!=(conn,domain):s={'scope':(conn,domain),'items':deque(),'seen':{},'total':F(0),'net':F(0),'unknown':False};self.states[asset]=s
  if row['channel']=='trades':
   for d in json.loads(row['raw']).get('data',[]):
    identity=(d.get('tradeId'),d.get('source'));signature=(d.get('px'),d.get('sz'),d.get('side'),d.get('ts'),d.get('count'))
    if identity[0] is None:s['unknown']=True;continue
    if identity in s['seen']:
     if s['seen'][identity]!=signature:s['unknown']=True
     continue
    s['seen'][identity]=signature;amount=F(Decimal(d['px']))*F(Decimal(d['sz']))*F(Decimal(spec['ctVal']))*F(Decimal(spec['ctMult']));signed=amount*(1 if d['side']=='buy' else -1);s['items'].append((now,amount,signed));s['total']+=amount;s['net']+=signed
  while s['items'] and s['items'][0][0]<=now-1000:
   _,a,n=s['items'].popleft();s['total']-=a;s['net']-=n
  return s
def run(rows,specs,domain):
 features=suite.Features(specs,domain);exact=ExactFlow();events=[];wait=Counter();details={};logs=[];cool={};scope=None
 def count(reason,asset,row):
  wait[reason]+=1;key=asset+'|'+reason
  if key not in details:details[key]={'asset':asset,'reason':reason,'count':0,'first_ordinal':row['local_ordinal'],'first_receive_wall_ns':row['receive_wall_ns']}
  details[key].update(count=details[key]['count']+1,last_ordinal=row['local_ordinal'],last_receive_wall_ns=row['receive_wall_ns'])
 for row in rows:
  value=features.ingest(row)
  if value is None:continue
  asset,now,mode,d,conn=value
  if scope!=(d,conn):cool={};scope=(d,conn)
  flow=exact.ingest(row,now,conn,d,specs[asset]);feature=features.feature(asset,now,1000,conn,d)
  if feature is None or flow['unknown']:count('WAIT_COLD_STALE_OR_SOURCE_UNKNOWN',asset,row);continue
  book,ref=feature['book'],feature['reference'];mid=(F(book['asks'][0][0])+F(book['bids'][0][0]))/2;refmid=(F(ref['asks'][0][0])+F(ref['bids'][0][0]))/2;impulse=(mid/refmid-1)*10000;total,net=flow['total'],flow['net']
  if total<=0 or abs(net)/total<F(4,5) or impulse*net<=0:count('WAIT_FLOW_DIRECTION',asset,row);continue
  spec=specs[asset];unit=Decimal(spec['ctVal'])*Decimal(spec['ctMult']);proxy=asof_required_move(book,unit,Decimal(spec['lotSz']),Decimal(spec['minSz']))
  if proxy is None:count('WAIT_ASOF_ENTRY_OR_REVERSE_DEPTH',asset,row);continue
  required,legs=proxy;direction=1 if net>0 else -1;opposing=sum((F(p)*F(q)*F(unit) for p,q in (ref['asks'] if direction==1 else ref['bids'])[:5]),F(0));dominant=(total+direction*net)/2;status=qualifies(impulse,total,net,required,opposing)
  if status!='QUALIFIED':count(status,asset,row);continue
  meta={'asset':asset,'asof_ordinal':row['local_ordinal'],'asof_ms':now,'source_receive_wall_ns':row['receive_wall_ns'],'source_asof_shared_ns':row['os_shared_ns'],'connectionId':conn,'clock_domain_id':d,'impulse_bps':float(impulse),'impulse_exact_fraction':str(impulse),'flow_total_USDT':float(total),'flow_net_USDT':float(net),'flow_total_exact_fraction':str(total),'flow_net_exact_fraction':str(net),'imbalance':float(net/total),'direction':direction,'dominant_received_notional_USDT':float(dominant),'dominant_exact_fraction':str(dominant),'reference_opposing_top5_notional_USDT':float(opposing),'reference_opposing_exact_fraction':str(opposing),'dominant_reference_ratio':float(dominant/opposing),'required_move_max_bps':float(required),'required_move_exact_fraction':str(required),'fixed_buffer_bps':5,'asof_cost_proxy_legs':legs,'quote_age_ms':feature['quote_age_ms'],'latest_book_ordinal':book['ordinal'],'reference_book_ordinal':ref['ordinal'],'cost_volume_proxy_not_future_income':True}
  if now-cool.get(asset,-1e99)<35000:count('QUALIFIED_BUT_NEWFAMILY_COOLDOWN',asset,row);logs.append({**meta,'status':'COOLDOWN'});continue
  cool[asset]=now;event={**meta,'event_id':len(events)+1,'family':'COST_CAPABLE_SHOCK_V1'};events.append(event);logs.append({**meta,'status':'EVENT'})
 return events,features.states,{'original_feature_source_counters':features.counters,'WAIT_reasons':dict(wait),'WAIT_asset_first_last_receipts':details,'qualified_candidate_log':logs}
