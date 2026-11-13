from pathlib import Path
from fractions import Fraction as F
from bisect import bisect_right
import json,gzip,hashlib,math
P=Path(__file__).resolve().parent
def size(levels,unit,step,minimum,fee):
 remaining=F(500)/(1+fee);q=F(0)
 for px,qty in levels:
  take=min(qty,remaining/(px*unit));q+=take;remaining-=take*px*unit
  if remaining==0:break
 if remaining>0:return None
 q=(q//step)*step
 return q if q>=minimum else None
def notional(levels,q,unit):
 left=q;cost=F(0)
 for px,available in levels:
  take=min(left,available);cost+=take*px*unit;left-=take
  if left==0:return cost
 return None
def main():
 p=json.loads((P/'protocol.json').read_text());events=json.loads((P/'pressure_events.json').read_text());out=json.loads((P/'pressure_shadow_outcomes.json').read_text());spec={r['instId']:r for r in json.loads((P/'instruments.json').read_text())};books={a:[] for a in spec};seen={a:{} for a in spec};trades={a:[] for a in spec};witness={};digest=hashlib.sha256();target={e['asof_ordinal']:e for e in events}
 with gzip.open(Path(p['source'])/'raw/ws_messages.jsonl.gz','rb') as stream:
  for line in stream:
   digest.update(line);r=json.loads(line);a=r['instId']
   if a not in spec:continue
   unit=F(spec[a]['ctVal'])*F(spec[a]['ctMult']);raw=json.loads(r['raw']);ns=r['os_shared_ns']
   for d in raw.get('data',[]):
    if r['channel']=='books5':books[a].append({'ns':ns,'ordinal':r['local_ordinal'],'conn':r['connectionId'],'asks':[(F(z[0]),F(z[1])) for z in d['asks']],'bids':[(F(z[0]),F(z[1])) for z in d['bids']]})
    elif r['channel']=='trades':
     k=(d.get('tradeId'),d.get('source'));sig=tuple(d.get(x) for x in ['px','sz','side','ts','count'])
     if k in seen[a]:assert seen[a][k]==sig;continue
     seen[a][k]=sig;amount=F(d['px'])*F(d['sz'])*unit;trades[a].append((ns,amount,amount*(1 if d['side']=='buy' else -1),r['local_ordinal']))
   if r['local_ordinal'] in target:
    e=target[r['local_ordinal']];assert e['run_id']==r['run_id'] and e['connectionId']==r['connectionId'] and e['clock_domain_id']==r['clock_domain_id'] and ns==e['source_asof_shared_ns'];bs=books[a];ts=[b['ns'] for b in bs];cur=bs[-1];ref10=bs[bisect_right(ts,ns-10000000000)-1];ref1=bs[bisect_right(ts,ns-1000000000)-1]
    assert 0<=ns-cur['ns']<=250000000 and 0<=ns-10000000000-ref10['ns']<=250000000 and 0<=ns-1000000000-ref1['ns']<=250000000
    ten=[t for t in trades[a] if ns-10000000000<t[0]<=ns];one=[t for t in ten if t[0]>ns-1000000000];total=sum((x[1] for x in ten),F(0));net=sum((x[2] for x in ten),F(0));t1=sum((x[1] for x in one),F(0));n1=sum((x[2] for x in one),F(0));prior=total-t1;direction=1 if net>0 else -1;mid=lambda b:(b['asks'][0][0]+b['bids'][0][0])/2;imp=(mid(cur)/mid(ref10)-1)*10000
    expected={'total10_exact':total,'net10_exact':net,'total1_exact':t1,'net1_exact':n1,'prior9_exact':prior,'rate_ratio_exact':9*t1/prior,'impulse10_exact':imp,'dominant10_exact':(total+direction*net)/2}
    for k,v in expected.items():assert F(e[k])==v,(k,e[k],v)
    assert abs(net-n1)<=prior and abs(net)/total>=F(4,5) and imp*net>0 and total>t1>0 and 0<=ns-trades[a][-1][0]<=250000000 and ns-trades[a][0][0]>=10000000000
    depth=sum((px*q*unit for px,q in (ref10['asks'] if direction==1 else ref10['bids'])[:5]),F(0));assert F(e['reference_opposing_top5_exact'])==depth and (total+direction*net)/2>=depth
    costs=[]
    for side in [1,-1]:
     levels=cur['asks'] if side==1 else cur['bids'];reverse=cur['bids'] if side==1 else cur['asks'];qty=size(levels,unit,F(spec[a]['lotSz']),F(spec[a]['minSz']),F(5,10000));E=notional(levels,qty,unit)/(qty*unit);X=notional(reverse,qty,unit)/(qty*unit);fee=F(5,10000);costs.append((E*(1+fee)/(X*(1-fee))-1)*10000 if side==1 else (1-E*(1-fee)/(X*(1+fee)))*10000)
    assert max(costs)==F(e['required_move_max_exact']) and abs(imp)>=max(costs)+5
    if e['qualified_rule']=='CONTINUATION_FOLLOW_V1':assert 9*t1/prior>=1 and abs(n1)/t1>=F(4,5) and n1*direction>0
    else:assert 9*t1/prior<=F(1,4) and abs(n1)/t1<=F(1,5)
    witness[e['event_id']]={'event_id':e['event_id'],'asset':a,'ordinal':r['local_ordinal'],'current_ref10_ref1': [cur['ordinal'],ref10['ordinal'],ref1['ordinal']],'exact_flow_cost_depth_branch':True}
 assert digest.hexdigest()==p['source_raw_sha256'];receipts=[]
 for o in out:
  e=next(e for e in events if e['event_id']==o['event_id']);a=e['asset'];bs=books[a];times=[b['ns'] for b in bs];target_ns=e['source_asof_shared_ns']+o['delay_ms']*1000000;idx=bisect_right(times,target_ns);assert idx<len(bs);entry=bs[idx];exit_target=entry['ns']+o['hold_seconds']*1000000000;exidx=bisect_right(times,exit_target);assert exidx<len(bs);ex=bs[exidx]
  assert entry['conn']==ex['conn']==e['connectionId'];entrywait=entry['ns']-target_ns;exitwait=ex['ns']-exit_target;reason='expired_entry_quote' if entrywait>250000000 else 'expired_exit_quote' if exitwait>250000000 else None
  if reason:
   assert o['status']=='censored' and o['reason']==reason and o['price_fee_delta_USDT'] is None;receipts.append({'action':o['action'],'fee':o['fee_each_side_bps'],'delay':o['delay_ms'],'hold':o['hold_seconds'],'censored_reason':reason,'first_entry_ordinal':entry['ordinal'],'first_exit_ordinal':ex['ordinal'],'entrywait_ns':entrywait,'exitwait_ns':exitwait});continue
  unit=F(spec[a]['ctVal'])*F(spec[a]['ctMult']);side=e['shock_direction']*(1 if o['action']=='FOLLOW' else -1);fee=F(o['fee_each_side_bps'],10000);entrylevels=entry['asks'] if side==1 else entry['bids'];exitlevels=ex['bids'] if side==1 else ex['asks'];qty=size(entrylevels,unit,F(spec[a]['lotSz']),F(spec[a]['minSz']),fee);E=notional(entrylevels,qty,unit);X=notional(exitlevels,qty,unit)
  assert qty is not None and X is not None and E*(1+fee)<=500 and F(o['contracts'])==qty and o['entry_ordinal']==entry['ordinal'] and o['exit_ordinal']==ex['ordinal']
  gross=side*(X-E);fees=(X+E)*fee;net=gross-fees
  for k,v in [('entry_notional_USDT',E),('exit_notional_USDT',X),('gross_price_delta_USDT',gross),('fee_USDT',fees),('price_fee_delta_USDT',net)]:assert math.isclose(o[k],float(v),rel_tol=1e-12,abs_tol=1e-10),(k,o[k],v)
  receipts.append({'action':o['action'],'fee':o['fee_each_side_bps'],'delay':o['delay_ms'],'hold':o['hold_seconds'],'status':'observed','qty_exact':str(qty),'net_exact':str(net),'entry_ordinal':entry['ordinal'],'exit_ordinal':ex['ordinal']})
 report={'status':'PASS_FINITE_ALL_OBSERVED_EVENT_CAUSAL_RAW_AND_OUTCOME_MATH','events_checked':list(witness.values()),'condition_rows_checked':len(receipts),'observed':sum(x.get('status')=='observed' for x in receipts),'censored':sum('censored_reason' in x for x in receipts),'receipts':receipts,'sameOwner_not_thirdparty_fullstrategy':True,'actual_order_orprovider':False};(P/'event_quote_audit.json').write_text(json.dumps(report,indent=2)+'\n');print(report['status'],len(receipts))
if __name__=='__main__':main()
