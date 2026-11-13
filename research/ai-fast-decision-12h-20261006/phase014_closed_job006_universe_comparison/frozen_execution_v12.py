from pathlib import Path
from collections import deque
from bisect import bisect_right
from decimal import Decimal,ROUND_FLOOR
import json,hashlib,datetime as dt
B=Path(__file__).resolve().parent
def valid_book(d):
 try:
  asks=[(Decimal(p),Decimal(q)) for p,q,*_ in d['asks'] if Decimal(q)>0];bids=[(Decimal(p),Decimal(q)) for p,q,*_ in d['bids'] if Decimal(q)>0]
  if not asks or not bids or bids[0][0]>=asks[0][0]:return None
  if asks!=sorted(asks) or bids!=sorted(bids,reverse=True):return None
  return asks,bids
 except Exception:return None
def floorlot(q,step):return (q/step).to_integral_value(rounding=ROUND_FLOOR)*step
def depthfill(levels,qty,unit):
 remaining=qty;notional=Decimal(0)
 for price,available in levels:
  take=min(remaining,available);notional+=take*unit*price;remaining-=take
  if remaining==0:return notional,notional/(qty*unit)
 return None
def size_capacity(levels,unit,step,minqty,fee):
 from fractions import Fraction as F
 unitF,stepF,minF,feeF=F(unit),F(step),F(minqty),F(fee)
 if unitF<=0 or stepF<=0 or minF<=0 or feeF<0:return None
 remaining=F(500)/(1+feeF);qty=F(0)
 for price,available in levels:
  p,a=F(price),F(available)
  if p<=0 or a<0:return None
  cost=p*unitF*a
  if cost>=remaining:
   qty+=remaining/(p*unitF);remaining=F(0);break
  qty+=a;remaining-=cost
 if remaining>0:return None
 steps=(qty/stepF).numerator//(qty/stepF).denominator
 q=Decimal(steps)*step
 if F(q)<minF:return None
 left=F(q);notional=F(0)
 for price,available in levels:
  take=min(left,F(available));notional+=take*F(price)*unitF;left-=take
  if left==0:break
 if left!=0 or notional*(1+feeF)>F(500):raise ArithmeticError('EXACT_CAPACITY_INVARIANT')
 return q
def first_after(books,times,when,conn):
 i=bisect_right(times,when)
 if i>=len(books) or books[i]['conn']!=conn:return None
 return books[i]
def triggers(rows,specs):
 states={a:{'flow':deque(),'books':[],'times':[],'firsttrade':None,'last_event':-1e99,'conn':None,'latest':None} for a in specs};events=[];counters={'warmup':0,'stale_book':0,'cooldown':0,'invalid_book':0,'stale_reference':0}
 for r in rows:
  a=r['instId']
  if a not in states:continue
  o=json.loads(r['raw']);s=states[a];now=r['monotonic_ns']/1e6;conn=r['connectionId']
  if s['conn']!=conn:
   s.update(flow=deque(),books=[],times=[],firsttrade=None,last_event=-1e99,conn=conn,latest=None)
  records=o.get('data',[])
  if not records:continue
  unit=Decimal(specs[a]['ctVal'])*Decimal(specs[a]['ctMult'])
  if r['channel']=='books5':
   for d in records:
    b=valid_book(d)
    if b is None:s['latest']=None;counters['invalid_book']+=1;continue
    asks,bids=b;book={'time':now,'ordinal':r['local_ordinal'],'wall_ms':r['receive_wall_ms'],'conn':conn,'asks':asks,'bids':bids,'mid':float((asks[0][0]+bids[0][0])/2)}
    s['books'].append(book);s['times'].append(now);s['latest']=book
  elif r['channel']=='trades':
   if s['firsttrade'] is None:s['firsttrade']=now
   for d in records:
    amount=Decimal(d['px'])*Decimal(d['sz'])*unit;s['flow'].append((now,float(amount)*(1 if d['side']=='buy' else -1),float(amount),r['local_ordinal']))
  else:continue
  while s['flow'] and s['flow'][0][0]<=now-1000:s['flow'].popleft()
  i=bisect_right(s['times'],now-1000)-1
  if s['firsttrade'] is None or s['firsttrade']>now-1000 or i<0:counters['warmup']+=1;continue
  if now-1000-s['books'][i]['time']>250:counters['stale_reference']+=1;continue
  book=s['latest']
  if book is None or now-book['time']>250:counters['stale_book']+=1;continue
  total=sum(x[2] for x in s['flow']);net=sum(x[1] for x in s['flow']);imb=net/total if total else 0;impulse=(book['mid']/s['books'][i]['mid']-1)*10000
  if abs(imb)<.8 or abs(impulse)<3 or imb*impulse<=0:continue
  if now-s['last_event']<35000:counters['cooldown']+=1;continue
  s['last_event']=now;events.append({'event_id':len(events)+1,'asset':a,'asof_ms':now,'asof_wall_ms':r['receive_wall_ms'],'asof_ordinal':r['local_ordinal'],'connectionId':conn,'direction':1 if net>0 else -1,'imbalance':imb,'flow_total_USDT':total,'flow_net_USDT':net,'impulse_bps':impulse,'quote_age_ms':now-book['time'],'latest_book_ordinal':book['ordinal'],'reference_book_ordinal':s['books'][i]['ordinal'],'reference_book_time':s['books'][i]['time'],'latest_book_time':book['time'],'WAIT_price_fee_delta':0,'feature_available_only_received':True})
 return events,states,counters
def outcomes(events,states,specs):
 result=[]
 for e in events:
  s=states[e['asset']];spec=specs[e['asset']];unit=Decimal(spec['ctVal'])*Decimal(spec['ctMult']);step=Decimal(spec['lotSz']);minq=Decimal(spec['minSz'])
  for action in ['FOLLOW','FADE']:
   side=e['direction']*(1 if action=='FOLLOW' else -1)
   for delay in [0,250,500,1000,3000]:
    for hold in [15,5,30]:
     for feebps in [5,10]:
      r={'event_id':e['event_id'],'asset':e['asset'],'action':action,'side':side,'delay_ms':delay,'hold_seconds':hold,'primary':hold==15,'fee_each_side_bps':feebps,'capacity_USDT':500,'status':'censored','price_fee_delta_USDT':None}
      entry=first_after(s['books'],s['times'],e['asof_ms']+delay,e['connectionId'])
      if entry is None:r['reason']='no_postdecision_book';result.append(r);continue
      r.update(actual_entry_delay_ms=entry['time']-e['asof_ms'],entry_wait_after_decision_ms=entry['time']-e['asof_ms']-delay)
      if r['entry_wait_after_decision_ms']>250:r['reason']='expired_entry_quote';result.append(r);continue
      fee=Decimal(feebps)/10000;levels=entry['asks'] if side==1 else entry['bids'];qty=size_capacity(levels,unit,step,minq,fee)
      if qty is None:r['reason']='minlot_or_entrydepth';result.append(r);continue
      fill=depthfill(levels,qty,unit)
      if fill is None:r['reason']='entry_depth';result.append(r);continue
      entryn,entrypx=fill;exit=first_after(s['books'],s['times'],entry['time']+hold*1000,e['connectionId'])
      if exit is None:r['reason']='no_posthold_book';result.append(r);continue
      r['exit_wait_after_deadline_ms']=exit['time']-entry['time']-hold*1000
      if r['exit_wait_after_deadline_ms']>250:r['reason']='expired_exit_quote';result.append(r);continue
      ef=depthfill(exit['bids'] if side==1 else exit['asks'],qty,unit)
      if ef is None:r['reason']='exit_depth';result.append(r);continue
      exitn,exitpx=ef;fees=(entryn+exitn)*fee;gross=Decimal(side)*(exitn-entryn)
      r.update(status='observed',reason=None,contracts=str(qty),underlying_quantity=str(qty*unit),entry_ordinal=entry['ordinal'],exit_ordinal=exit['ordinal'],entry_received_ms=entry['time'],exit_received_ms=exit['time'],entry_notional_USDT=float(entryn),exit_notional_USDT=float(exitn),entry_VWAP=float(entrypx),exit_VWAP=float(exitpx),fee_USDT=float(fees),gross_price_delta_USDT=float(gross),price_fee_delta_USDT=float(gross-fees),not_account_PnL=True)
      result.append(r)
 return result
def main():
 proto=json.loads((B/'protocol.json').read_text());f=json.loads((B/'execution_freeze.json').read_text())
 for n,h in f['hashes'].items():assert hashlib.sha256((B/n).read_bytes()).hexdigest()==h
 blob=(B.parent/'prefix.jsonl').read_bytes();assert hashlib.sha256(blob).hexdigest()==proto['prefix']['sha256'];rows=[json.loads(x) for x in blob.splitlines()];specs={x['instId']:x for x in json.loads((B/'instruments.json').read_text())};events,states,counters=triggers(rows,specs);res=outcomes(events,states,specs)
 (B/'events.json').write_text(json.dumps(events,indent=2));(B/'event_price_fee_deltas.json').write_text(json.dumps(res,indent=2));summary=[]
 for action in ['FOLLOW','FADE']:
  for delay in [0,250,500,1000,3000]:
   for hold in [15,5,30]:
    for fee in [5,10]:
     subset=[r for r in res if (r['action'],r['delay_ms'],r['hold_seconds'],r['fee_each_side_bps'])==(action,delay,hold,fee)];good=[x['price_fee_delta_USDT'] for x in subset if x['status']=='observed'];summary.append({'action':action,'delay_ms':delay,'hold_seconds':hold,'fee_each_side_bps':fee,'observed':len(good),'censored':len(subset)-len(good),'mean_price_fee_delta_USDT':sum(good)/len(good) if good else None,'positive_events':sum(x>0 for x in good),'not_account_PnL':True})
 (B/'results.json').write_text(json.dumps({'status':'DEVELOPMENT_EVENT_STUDY','events':len(events),'counters':counters,'summary':summary,'model_results':None,'network':0,'not_account_PnL':True},indent=2));print({'events':len(events),'outcome_rows':len(res),'counters':counters})
if __name__=='__main__':main()
