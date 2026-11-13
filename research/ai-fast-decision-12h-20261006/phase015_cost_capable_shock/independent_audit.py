from pathlib import Path
from fractions import Fraction as F
from decimal import Decimal as D
from collections import deque
from bisect import bisect_right
import json,gzip,hashlib
B=Path(__file__).resolve().parent
def size(levels,unit,step):
 rem=F(500)/(1+F(5,10000));q=F(0)
 for px,amount,*_ in levels:
  px,amount=F(D(px)),F(D(amount));take=min(amount,rem/(px*unit));q+=take;rem-=take*px*unit
  if rem==0:break
 if rem>0:return None
 return (q/step).numerator//(q/step).denominator*step
def filled(levels,q,unit):
 value=F(0)
 for px,amount,*_ in levels:
  take=min(q,F(D(amount)));value+=take*F(D(px))*unit;q-=take
  if q==0:return value
 return None
def main():
 p=json.loads((B/'protocol.json').read_text());fr=json.loads((B/'execution_freeze.json').read_text())
 for n,h in fr['hashes'].items():assert hashlib.sha256((B/n).read_bytes()).hexdigest()==h
 receipts=json.loads((B/'development_counters_wait_receipts.json').read_text())[0];wanted={v[k] for v in receipts['WAIT_asset_first_last_receipts'].values() if v['reason'] in ['WAIT_INSUFFICIENT_PAST_COST_ROOM','WAIT_ASOF_ENTRY_OR_REVERSE_DEPTH'] for k in ['first_ordinal','last_ordinal']};specs={x['instId']:x for x in json.loads((B/'instruments.json').read_text())};states={a:{'books':[],'times':[],'flow':deque()} for a in specs};checked=[];sha=hashlib.sha256()
 with gzip.open(Path(p['development_source'])/'raw/ws_messages.jsonl.gz','rb') as raw:
  for line in raw:
   sha.update(line);r=json.loads(line);a=r['instId']
   if a not in states:continue
   s=states[a];now=r['os_shared_ns']/1e6;spec=specs[a];unit=F(D(spec['ctVal']))*F(D(spec['ctMult']));o=json.loads(r['raw'])
   for data in o.get('data',[]):
    if r['channel']=='books5':s['books'].append((now,r['local_ordinal'],data));s['times'].append(now)
    if r['channel']=='trades':value=F(D(data['px']))*F(D(data['sz']))*unit;s['flow'].append((now,value,value*(1 if data['side']=='buy' else -1)))
   while s['flow'] and s['flow'][0][0]<=now-1000:s['flow'].popleft()
   if r['local_ordinal'] not in wanted:continue
   i=bisect_right(s['times'],now-1000)-1;assert i>=0;ref=s['books'][i];current=s['books'][-1];assert now-current[0]<=250 and now-1000-ref[0]<=250;book=current[2];reference=ref[2];total=sum((x[1] for x in s['flow']),F(0));net=sum((x[2] for x in s['flow']),F(0));assert total>0 and abs(net)/total>=F(4,5)
   mid=(F(D(book['asks'][0][0]))+F(D(book['bids'][0][0])))/2;refmid=(F(D(reference['asks'][0][0]))+F(D(reference['bids'][0][0])))/2;impulse=(mid/refmid-1)*10000;required=[];nod=False
   for side in [1,-1]:
    entrylevels=book['asks'] if side==1 else book['bids'];reverse=book['bids'] if side==1 else book['asks'];q=size(entrylevels,unit,F(D(spec['lotSz'])))
    if q is None or q<F(D(spec['minSz'])):nod=True;break
    E=filled(entrylevels,q,unit);X=filled(reverse,q,unit)
    if X is None:nod=True;break
    f=F(5,10000);move=(E*(1+f)/(X*(1-f))-1)*10000 if side==1 else (1-E*(1-f)/(X*(1+f)))*10000;required.append(move)
   expected=next(v['reason'] for v in receipts['WAIT_asset_first_last_receipts'].values() if r['local_ordinal'] in [v['first_ordinal'],v['last_ordinal']] and v['reason'] in ['WAIT_INSUFFICIENT_PAST_COST_ROOM','WAIT_ASOF_ENTRY_OR_REVERSE_DEPTH'])
   if expected=='WAIT_ASOF_ENTRY_OR_REVERSE_DEPTH':assert nod
   else:assert not nod and abs(impulse)<max(required)+5
   checked.append({'asset':a,'ordinal':r['local_ordinal'],'reason':expected,'observed_past_impulse_bps':float(impulse),'asof_required_max_bps':float(max(required)) if not nod else None,'past_proxy_not_futureprofit':True})
 assert sha.hexdigest()==p['development_raw_sha256'];assert not json.loads((B/'development_events.json').read_text());assert len(checked)==len(wanted);result={'status':'PASS_FINITE_REAL_SOURCE_COST_GATE_FORMULAS','cases':checked,'sample_count':len(checked),'aggregate_wait_receipts_sum':sum(receipts['WAIT_reasons'].values()),'qualified_events':0,'sourcehash_match':True,'realvolume_threshold_acceptance':'NOT_OBSERVED costgate alreadyrejects; synthetic exactboundary tested','AI':None,'sameOwner_notthirdparty_fullreplay':True};(B/'audit.json').write_text(json.dumps(result,indent=2));print({'sample_count':len(checked),'events':0,'status':result['status']})
if __name__=='__main__':main()
