from pathlib import Path
from collections import deque,Counter
from bisect import bisect_right
from fractions import Fraction as F
from decimal import Decimal as D
import json,gzip,hashlib
from frozen_pressure_rules import PressureRules
from pressure_rules_rolling import PressureRules as Rolling
B=Path(__file__).resolve().parent
def size(levels,unit,step,minq):
 remain=F(500)/(1+F(5,10000));q=F(0)
 for px,sz,*_ in levels:
  price,qty=F(D(px)),F(D(sz));take=min(qty,remain/(price*unit));q+=take;remain-=take*price*unit
  if remain==0:break
 if remain>0:return None
 q=(q/step).numerator//(q/step).denominator*step;return q if q>=minq else None
def fill(levels,q,unit):
 total=F(0)
 for px,sz,*_ in levels:
  take=min(q,F(D(sz)));total+=take*F(D(px))*unit;q-=take
  if q==0:return total
 return None
def main():
 p=json.loads((B/'protocol.json').read_text());
 from raw_replication import require_run
 require_run(p);registry=json.loads((B/'instruments.json').read_text());specs={x['instId']:x for x in registry};source=Path(p['source']);rows=[];sha=hashlib.sha256()
 with gzip.open(source/'raw/ws_messages.jsonl.gz','rb') as raw:
  for line in raw:sha.update(line);rows.append(json.loads(line))
 assert sha.hexdigest()==p['source_raw_sha256'];wanted=set()
 for asset in p['assets']:
  rr=[r for r in rows if r['instId']==asset and r['os_shared_ns']>=p['rule_cut_OS_shared_ns'] and json.loads(r['raw']).get('data')]
  if rr:wanted.update(r['local_ordinal'] for r in [rr[0],rr[len(rr)//2],rr[-1]])
 real_events=json.loads((B/'pressure_events.json').read_text());wanted.update(e['asof_ordinal'] for e in real_events)
 class SampledOnly(PressureRules):
  def candidate(self,a,row):
   if row['local_ordinal'] not in wanted:return None
   return super().candidate(a,row)
 class RollingSampled(Rolling):
  def candidate(self,a,row):
   if row['local_ordinal'] not in wanted:return None
   return super().candidate(a,row)
 rules=SampledOnly(registry,p['rule_domain'],forward_cut_ns=p['rule_cut_OS_shared_ns']);newrules=RollingSampled(registry,p['rule_domain'],forward_cut_ns=p['rule_cut_OS_shared_ns']);real_by_ordinal={e['asof_ordinal']:e for e in real_events};s={a:{'times':[],'books':[],'flow':deque(),'seen':{},'first':None,'last':None} for a in p['assets']};cases=[]
 for row in rows:
  actual=rules.ingest(row);newactual=newrules.ingest(row)
  if row['local_ordinal'] in wanted:assert newactual==actual,('OLD_NEW_CANDIDATE',row['local_ordinal'])
  if row['local_ordinal'] in real_by_ordinal:
   event=real_by_ordinal[row['local_ordinal']]
   for key,value in actual.items():assert event.get(key)==value,('REAL_EVENT_OLDALGO_FIELD',row['local_ordinal'],key)
  a=row['instId']
  if a not in s:continue
  state=s[a];now=row['os_shared_ns'];sp=specs[a];unit=F(D(sp['ctVal']))*F(D(sp['ctMult']))
  for data in json.loads(row['raw']).get('data',[]):
   if row['channel']=='books5':state['times'].append(now);state['books'].append(data)
   if row['channel']=='trades':
    key=(data['tradeId'],data.get('source'))
    if key in state['seen']:continue
    state['seen'][key]=True;amount=F(D(data['px']))*F(D(data['sz']))*unit;state['flow'].append((now,amount,amount*(1 if data['side']=='buy' else -1)));state['first']=now if state['first'] is None else state['first'];state['last']=now
  while state['flow'] and state['flow'][0][0]<=now-10000000000:state['flow'].popleft()
  if row['local_ordinal'] not in wanted:continue
  reason=None;chosen=None;details={}
  if state['first'] is None or now-state['first']<10000000000:reason='WAIT_TRADE_WARMUP10'
  elif not state['times'] or now-state['times'][-1]>250000000:reason='WAIT_CURRENT_BOOK_STALE'
  else:
   i10=bisect_right(state['times'],now-10000000000)-1;i1=bisect_right(state['times'],now-1000000000)-1
   if i10<0 or i1<0 or now-10000000000-state['times'][i10]>250000000 or now-1000000000-state['times'][i1]>250000000:reason='WAIT_REFERENCE10_OR1'
   else:
    book,ref=state['books'][-1],state['books'][i10];total10=sum((x[1] for x in state['flow']),F(0));net10=sum((x[2] for x in state['flow']),F(0));one=[x for x in state['flow'] if x[0]>now-1000000000];total1=sum((x[1] for x in one),F(0));net1=sum((x[2] for x in one),F(0));mid=lambda b:(F(D(b['asks'][0][0]))+F(D(b['bids'][0][0])))/2;imp=(mid(book)/mid(ref)-1)*10000;required=[];missing=False
    for side in [1,-1]:
     levels=book['asks'] if side==1 else book['bids'];reverse=book['bids'] if side==1 else book['asks'];q=size(levels,unit,F(D(sp['lotSz'])),F(D(sp['minSz'])))
     if q is None:missing=True;break
     E,X=fill(levels,q,unit),fill(reverse,q,unit)
     if X is None:missing=True;break
     f=F(5,10000);required.append((E*(1+f)/(X*(1-f))-1)*10000 if side==1 else (1-E*(1-f)/(X*(1+f)))*10000)
    shock=1 if net10>0 else -1;depth=sum((F(D(px))*F(D(q))*unit for px,q,*_ in (ref['asks'] if shock==1 else ref['bids'])[:5]),F(0));prior=total10-total1;age=now-state['last'] if state['last'] is not None else None
    if missing:reason='WAIT_CURRENT_ENTRY_OR_REVERSE_DEPTH'
    elif total10<=0 or abs(net10)>total10 or total1<0 or total1>total10 or abs(net1)>total1:reason='WAIT_INVALID_FLOW'
    elif abs(net10-net1)>prior:reason='WAIT_NESTED_WINDOW_INCONSISTENCY'
    elif abs(net10)/total10<F(4,5) or imp*net10<=0:reason='WAIT_SHOCK_DIRECTION'
    elif abs(imp)<max(required)+5:reason='WAIT_10S_COST_ROOM'
    elif depth<=0 or (total10+shock*net10)/2<depth:reason='WAIT_DOMINANT10_BELOW_REFERENCE_DEPTH'
    elif total1<=0 or age is None or age>250000000:reason='WAIT_NO_REAL_FRESH_1S_TRADE'
    elif prior<=0:reason='WAIT_NO_PRIOR9'
    elif 9*total1/prior>=1 and abs(net1)/total1>=F(4,5) and net1*shock>0:chosen='CONTINUATION_FOLLOW_V1'
    elif 9*total1/prior<=F(1,4) and abs(net1)/total1<=F(1,5):chosen='PRESSURE_DECAY_FADE_V1'
    else:reason='WAIT_PRESSURE_NEITHER_FIXED_REGIME'
    details={'total10':str(total10),'net10':str(net10),'total1':str(total1),'net1':str(net1),'latest_unique_trade_age_ns':age,'prior9':str(prior),'ratio':str(9*total1/prior) if prior>0 else None,'past_impulse10':str(imp)}
  assert actual is not None
  if chosen is None:assert actual['qualified_rule'] is None and actual['rejectreason']==reason
  else:assert actual['qualified_rule']==chosen or actual['rejectreason']=='WAIT_RULE35_COOLDOWN'
  cases.append({'asset':a,'ordinal':row['local_ordinal'],'independent_reason':reason,'independent_chosen':chosen,'actual':actual,'details':details})
 assert len(cases)==len(wanted);report={'status':'PASS_FINITE_FIXED_POSTCUT_FIRST_MIDDLE_LAST_RAW_PRESSURE_MATH','cases':cases,'sample_count':len(cases),'future_quote_fee_audit':'SEPARATE_GENERIC_QUOTE_AUDIT ifreal events; NOT_APPLICABLE ifzeroevents','old_new_sampled_candidate_and_all_eventfields_equal':True,'full_old_everytick_parity':'NOT_PERFORMED originaltimedout20min','sampling_scope':'first/middle/last + all recorded qualified asofs; nonselected sourceprefix ingested without candidate calculation; not full strategy replay','actual_event_asofs_included':len(real_events),'forwardcut_beforeingest':True,'precut_cooldown_not_consumed':True,'actual_AI':None,'not_thirdparty_fullstrategy_replay':True};(B/'old_algorithm_sample_equivalence.json').write_text(json.dumps(report,indent=2));print({'cases':len(cases)})
if __name__=='__main__':main()
