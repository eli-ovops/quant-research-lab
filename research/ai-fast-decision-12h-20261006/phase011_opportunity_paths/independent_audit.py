from pathlib import Path
from decimal import Decimal
from bisect import bisect_right
from collections import defaultdict
import json,gzip,hashlib
B=Path(__file__).resolve().parent
def filled(levels,quantity,unit):
 left=quantity;value=Decimal(0)
 for level in levels:
  take=min(left,Decimal(level[1]));value+=take*Decimal(level[0])*unit;left-=take
  if left==0:return value
 return None
def near(a,b):assert abs(float(a)-float(b))<1e-8
def main():
 p=json.loads((B/'protocol.json').read_text());freeze=json.loads((B/'execution_freeze.json').read_text())
 for n,h in freeze['hashes'].items():assert hashlib.sha256((B/n).read_bytes()).hexdigest()==h
 paths=json.loads((B/'future_path_diagnostics.json').read_text());specs={x['instId']:x for x in json.loads((B/'instruments.json').read_text())};events={e['event_id']:e for e in json.loads(Path(p['events_readonly']).read_text())};groups=defaultdict(list)
 for x in paths:
  if x['window_seconds'] in [15,180] and x['action']=='FOLLOW':groups[(x['family'],x['asset'],x['fee_each_side_bps'],x['window_seconds'])].append(x)
 chosen=[x for g in groups.values() for x in [g[0],g[-1]]]+[x for x in paths if x['future_path_entry_rejection']][:4];books=defaultdict(list);times=defaultdict(list);sha=hashlib.sha256()
 with gzip.open(Path(p['source_directory'])/'raw/ws_messages.jsonl.gz','rb') as f:
  for line in f:
   sha.update(line);r=json.loads(line)
   if r['channel']=='books5' and json.loads(r['raw']).get('data'):
    books[r['instId']].append((r,json.loads(r['raw'])['data'][0]));times[r['instId']].append(r['os_shared_ns']/1e6)
 assert sha.hexdigest()==p['raw_logical_sha256'];valid=noentry=0
 for x in chosen:
  e=events[x['event_id']];asset=x['asset'];t=times[asset];bb=books[asset];i=bisect_right(t,e['asof_ms'])
  if x['future_path_entry_rejection']:
   noentry+=1;assert not x['future_path_window_complete']
   if x['future_path_entry_rejection']=='EXPIRED_ENTRY':assert t[i]-e['asof_ms']>250
   if x['future_path_entry_rejection']=='NO_ENTRY':assert i>=len(t)
   continue
  entryrow,entry=bb[i];assert entryrow['local_ordinal']==x['future_path_entry_ordinal'];assert 0<t[i]-e['asof_ms']<=250
  qty=Decimal(x['future_path_contracts']);unit=Decimal(specs[asset]['ctVal'])*Decimal(specs[asset]['ctMult']);fee=Decimal(x['fee_each_side_bps'])/10000;entryn=filled(entry['asks'] if x['side']==1 else entry['bids'],qty,unit);assert entryn*(1+fee)<=500;near(entryn,x['future_path_entry_notional_USDT']);end=t[i]+x['window_seconds']*1000;stop=bisect_right(t,end);observed=[];missing=0;first=None
  for j in range(i+1,stop):
   rr,data=bb[j];assert rr['run_id']==entryrow['run_id'] and rr['connectionId']==entryrow['connectionId'] and rr['clock_domain_id']==entryrow['clock_domain_id'];ex=filled(data['bids'] if x['side']==1 else data['asks'],qty,unit)
   if ex is None:missing+=1;continue
   v=Decimal(x['side'])*(ex-entryn)-(ex+entryn)*fee;observed.append((rr['local_ordinal'],v))
   if first is None and v>=0:first=rr['local_ordinal']
  assert x['future_path_observed_quote_count']==len(observed) and x['future_path_no_exit_depth_quotes']==missing;assert x['future_path_window_complete']==(stop<len(t) and t[stop]-end<=250);assert x['future_path_first_nonnegative_ordinal']==first
  if observed:
   near(max(v for _,v in observed),x['future_path_observable_max_USDT']);near(min(v for _,v in observed),x['future_path_observable_min_USDT'])
  for sens in x['future_path_crossing_delay_quotes']:
   if sens['status']!='OBSERVED_QUOTE':continue
   target=x['future_path_first_nonnegative_received_ms']+sens['delay_ms'];j=bisect_right(t,target);assert bb[j][0]['local_ordinal']==sens['ordinal'] and t[j]<=end and t[j]-target<=250
   ex=filled(bb[j][1]['bids'] if x['side']==1 else bb[j][1]['asks'],qty,unit);v=Decimal(x['side'])*(ex-entryn)-(ex+entryn)*fee;near(v,sens['price_fee_delta_USDT']);assert (v>=0)==sens['still_nonnegative']
  valid+=1
 receipt={'status':'PASS_FINITE_HINDSIGHT_PRICE_FEE_TIMING_AUDIT','path_sample_checked':valid,'noentry_sample_checked':noentry,'original_raw_hash_match':True,'same_quantity_all_quotes':True,'first_after_entry_and_crossing_delay':True,'max_min_firstcross_completewindow_checked':True,'real_AI':None,'not_thirdparty_or_full_strategy_replay':True};(B/'audit.json').write_text(json.dumps(receipt,indent=2));print(receipt)
if __name__=='__main__':main()
