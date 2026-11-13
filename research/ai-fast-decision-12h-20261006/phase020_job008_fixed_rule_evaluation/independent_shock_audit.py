from pathlib import Path
from collections import deque
from bisect import bisect_right
from fractions import Fraction as F
from decimal import Decimal as D
import json,gzip,hashlib
B=Path(__file__).resolve().parent
def size(levels,unit,step):
 budget=F(500)/(1+F(5,10000));q=F(0)
 for px,sz,*_ in levels:
  price,qty=F(D(px)),F(D(sz));take=min(qty,budget/(price*unit));q+=take;budget-=take*price*unit
  if budget==0:break
 if budget>0:return None
 return (q/step).numerator//(q/step).denominator*step
def fill(levels,q,unit):
 n=F(0)
 for px,sz,*_ in levels:
  take=min(q,F(D(sz)));n+=take*F(D(px))*unit;q-=take
  if q==0:return n
 return None
def main():
 p=json.loads((B/'protocol.json').read_text());f=json.loads((B/'execution_freeze.json').read_text())
 for n,h in f['hashes'].items():assert hashlib.sha256((B/n).read_bytes()).hexdigest()==h
 events=json.loads((B/'costshock_events.json').read_text());receipts=json.loads((B/'costshock_WAIT_counters_receipts.json').read_text());wanted={e['asof_ordinal'] for e in events};why={}
 for segment in receipts:
  for v in segment['WAIT_asset_first_last_receipts'].values():
   if v['reason'] in ['WAIT_INSUFFICIENT_PAST_COST_ROOM','WAIT_ASOF_ENTRY_OR_REVERSE_DEPTH','WAIT_RECEIVED_VOLUME_BELOW_REFERENCE_DEPTH']:
    for key in ['first_ordinal','last_ordinal']:wanted.add(v[key]);why[v[key]]=v['reason']
 specs={x['instId']:x for x in json.loads((B/'instruments.json').read_text())};states={a:{'times':[],'books':[],'flow':deque(),'seen':{}} for a in specs};checked=[];sha=hashlib.sha256()
 with gzip.open(Path(p['source'])/'raw/ws_messages.jsonl.gz','rb') as raw:
  for line in raw:
   sha.update(line);row=json.loads(line);a=row['instId']
   if a not in states:continue
   st=states[a];now=row['os_shared_ns']/1e6;sp=specs[a];unit=F(D(sp['ctVal']))*F(D(sp['ctMult']))
   for d in json.loads(row['raw']).get('data',[]):
    if row['channel']=='books5':st['books'].append((row,d));st['times'].append(now)
    if row['channel']=='trades':
     ident=(d.get('tradeId'),d.get('source'));signature=tuple(d.get(k) for k in ['px','sz','side','ts','count'])
     if ident in st['seen']:assert signature==st['seen'][ident];continue
     st['seen'][ident]=signature;value=F(D(d['px']))*F(D(d['sz']))*unit;st['flow'].append((now,value,value*(1 if d['side']=='buy' else -1)))
   while st['flow'] and st['flow'][0][0]<=now-1000:st['flow'].popleft()
   if row['local_ordinal'] not in wanted:continue
   i=bisect_right(st['times'],now-1000)-1;assert i>=0;reference=st['books'][i];current=st['books'][-1];assert 0<=now-st['times'][-1]<=250 and 0<=now-1000-st['times'][i]<=250;book=current[1];ref=reference[1];total=sum((x[1] for x in st['flow']),F(0));net=sum((x[2] for x in st['flow']),F(0));assert total>0 and abs(net)/total>=F(4,5);mid=lambda b:(F(D(b['asks'][0][0]))+F(D(b['bids'][0][0])))/2;imp=(mid(book)/mid(ref)-1)*10000;required=[];missing=False
   for side in [1,-1]:
    entry=book['asks'] if side==1 else book['bids'];reverse=book['bids'] if side==1 else book['asks'];q=size(entry,unit,F(D(sp['lotSz'])))
    if q is None or q<F(D(sp['minSz'])):missing=True;break
    E,X=fill(entry,q,unit),fill(reverse,q,unit)
    if X is None:missing=True;break
    fee=F(5,10000);required.append((E*(1+fee)/(X*(1-fee))-1)*10000 if side==1 else (1-E*(1-fee)/(X*(1+fee)))*10000)
   direction=1 if net>0 else -1;dominant=(total+direction*net)/2;depth=sum((F(D(px))*F(D(q))*unit for px,q,*_ in (ref['asks'] if direction==1 else ref['bids'])[:5]),F(0));reason=why.get(row['local_ordinal'])
   if reason=='WAIT_ASOF_ENTRY_OR_REVERSE_DEPTH':assert missing
   elif reason=='WAIT_INSUFFICIENT_PAST_COST_ROOM':assert not missing and abs(imp)<max(required)+5
   elif reason=='WAIT_RECEIVED_VOLUME_BELOW_REFERENCE_DEPTH':assert not missing and abs(imp)>=max(required)+5 and dominant<depth
   else:
    e=next(e for e in events if e['asof_ordinal']==row['local_ordinal']);assert not missing and abs(imp)>=max(required)+5 and dominant>=depth;assert F(e['flow_total_exact_fraction'])==total and F(e['flow_net_exact_fraction'])==net and F(e['required_move_exact_fraction'])==max(required) and F(e['reference_opposing_exact_fraction'])==depth
   checked.append({'asset':a,'ordinal':row['local_ordinal'],'type':reason or 'QUALIFIED_EVENT'})
 assert sha.hexdigest()==p['raw_logical_sha256'] and len(checked)==len(wanted);(B/'shock_audit.json').write_text(json.dumps({'status':'PASS_FINITE_ORIGINAL_RAW_EXACT_GATE_CHECK','checks':checked,'qualified_events_checked':len(events),'rejected_samples_checked':len(checked)-len(events),'sourcehash_match':True,'actual_AI':None,'not_thirdparty_fullreplay':True},indent=2));print({'gate_checks':len(checked),'events':len(events)})
if __name__=='__main__':main()
