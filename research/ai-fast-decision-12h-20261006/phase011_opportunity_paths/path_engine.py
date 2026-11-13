from pathlib import Path
from bisect import bisect_right
from collections import defaultdict,Counter
from decimal import Decimal
import gzip,json,hashlib,statistics
import frozen_execution_v12 as core
B=Path(__file__).resolve().parent
def quote_delta(book,qty,unit,side,entryn,fee):
 fill=core.depthfill(book['bids'] if side==1 else book['asks'],qty,unit)
 if fill is None:return None
 n,_=fill;return Decimal(side)*(n-entryn)-(entryn+n)*fee
def diagnostic(books,times,entry,qty,unit,side,entryn,fee,hold):
 end=entry['time']+hold*1000;i=bisect_right(times,entry['time']);stop=bisect_right(times,end);after=stop
 complete=after<len(books) and books[after]['time']-end<=250
 points=[];missing=0;spans=[];start=last=None;first=None;previous=entry['time'];gaps=[]
 for book in books[i:stop]:
  gap=book['time']-previous
  if gap>250:gaps.append({'from_received_ms':previous,'to_received_ms':book['time'],'gap_ms':gap})
  delta=quote_delta(book,qty,unit,side,entryn,fee)
  if delta is None:missing+=1
  else:
   points.append((book,delta))
   if first is None and delta>=0:first=(book,delta)
  if delta is not None and delta>0:
   if start is None or gap>250:
    if start is not None:spans.append((start,last))
    start=book['time']
   last=book['time']
  else:
   if start is not None:spans.append((start,last))
   start=last=None
  previous=book['time']
 if start is not None:spans.append((start,last))
 sensitivity=[]
 for delay in [0,250,1000]:
  item={'delay_ms':delay,'status':'NO_NONNEGATIVE_CROSSING','still_nonnegative':None}
  if first:
   target=first[0]['time']+delay;j=bisect_right(times,target)
   if j>=len(books) or books[j]['time']>end:item['status']='CENSORED_OUTSIDE_WINDOW'
   elif books[j]['time']-target>250:item['status']='EXPIRED_FIRST_QUOTE'
   else:
    value=quote_delta(books[j],qty,unit,side,entryn,fee)
    if value is None:item['status']='EXIT_DEPTH_UNKNOWN'
    else:item.update(status='OBSERVED_QUOTE',still_nonnegative=value>=0,price_fee_delta_USDT=float(value),ordinal=books[j]['ordinal'],received_ms=books[j]['time'])
  sensitivity.append(item)
 mx=max(points,key=lambda x:x[1]) if points else None;mn=min(points,key=lambda x:x[1]) if points else None
 return {'future_path_window_complete':complete,'future_path_status':'COMPLETE_OBSERVED_WINDOW' if complete else 'INCOMPLETE_TAIL_OR_GAP','future_path_observed_quote_count':len(points),'future_path_no_exit_depth_quotes':missing,'future_path_positive_quote_count':sum(d>0 for _,d in points),'future_path_nonnegative_quote_count':sum(d>=0 for _,d in points),'future_path_observable_max_USDT':float(mx[1]) if mx else None,'future_path_observable_min_USDT':float(mn[1]) if mn else None,'future_path_max_ordinal':mx[0]['ordinal'] if mx else None,'future_path_min_ordinal':mn[0]['ordinal'] if mn else None,'future_path_first_nonnegative_ordinal':first[0]['ordinal'] if first else None,'future_path_first_nonnegative_received_ms':first[0]['time'] if first else None,'future_path_positive_observed_spans_ms':[[a,b] for a,b in spans],'future_path_longest_positive_observed_span_ms':max((b-a for a,b in spans),default=0),'future_path_gaps_over250ms':gaps,'future_path_crossing_delay_quotes':sensitivity,'future_path_not_strategy_exit_or_revenue':True}
def main():
 p=json.loads((B/'protocol.json').read_text());freeze=json.loads((B/'execution_freeze.json').read_text())
 for n,h in freeze['hashes'].items():assert hashlib.sha256((B/n).read_bytes()).hexdigest()==h
 for key,hkey in [('events_readonly','events_sha256'),('reference_outcomes_readonly','reference_sha256')]:assert hashlib.sha256(Path(p[key]).read_bytes()).hexdigest()==p[hkey]
 events=json.loads(Path(p['events_readonly']).read_text());ref=json.loads(Path(p['reference_outcomes_readonly']).read_text());specs={x['instId']:x for x in json.loads((B/'instruments.json').read_text())};books=defaultdict(list);times=defaultdict(list);sha=hashlib.sha256();invalid=0;scopes=set()
 with gzip.open(Path(p['source_directory'])/'raw/ws_messages.jsonl.gz','rb') as raw:
  for line in raw:
   sha.update(line);r=json.loads(line);scopes.add((r['run_id'],r['connectionId'],r['clock_domain_id']))
   if r['channel']!='books5':continue
   for d in json.loads(r['raw']).get('data',[]):
    valid=core.valid_book(d)
    if valid is None:invalid+=1;continue
    asks,bids=valid;book={'time':r['os_shared_ns']/1e6,'ordinal':r['local_ordinal'],'conn':r['connectionId'],'run':r['run_id'],'domain':r['clock_domain_id'],'asks':asks,'bids':bids};books[r['instId']].append(book);times[r['instId']].append(book['time'])
 assert sha.hexdigest()==p['raw_logical_sha256'] and invalid==0
 fillscope={(b['run'],b['conn'],b['domain']) for bs in books.values() for b in bs};assert len(fillscope)==1
 # ACK/control rows may have no connection yet; only book scope matters forfills.
 results=[];same=0;refindex={(x['event_id'],x['action'],x['fee_each_side_bps']):x for x in ref if x['delay_ms']==0 and x['hold_seconds']==15}
 for e in events:
  asset=e['asset'];bb=books[asset];tt=times[asset];spec=specs[asset];unit=Decimal(spec['ctVal'])*Decimal(spec['ctMult'])
  for action in ['FOLLOW','FADE']:
   side=e['direction']*(1 if action=='FOLLOW' else -1)
   for fee_bps in [5,10]:
    entry=core.first_after(bb,tt,e['asof_ms'],e['connectionId']);reason=None;qty=None;entryn=None;fee=Decimal(fee_bps)/10000
    if entry is None:reason='NO_ENTRY'
    elif entry['time']-e['asof_ms']>250:reason='EXPIRED_ENTRY'
    else:
     qty=core.size_capacity(entry['asks'] if side==1 else entry['bids'],unit,Decimal(spec['lotSz']),Decimal(spec['minSz']),fee)
     if qty is None:reason='NO_ENTRY_DEPTH_OR_MINLOT'
     else:entryn,_=core.depthfill(entry['asks'] if side==1 else entry['bids'],qty,unit)
    original=refindex[(e['event_id'],action,fee_bps)]
    if original['status']=='observed':assert str(qty)==original['contracts'] and entry['ordinal']==original['entry_ordinal'] and abs(float(entryn)-original['entry_notional_USDT'])<1e-7;same+=1
    for hold in [15,30,60,180]:
     item={'event_id':e['event_id'],'family':e['family'],'asset':asset,'action':action,'side':side,'fee_each_side_bps':fee_bps,'window_seconds':hold,'future_path_entry_rejection':reason,'future_path_entry_ordinal':entry['ordinal'] if entry else None,'future_path_entry_received_ms':entry['time'] if entry else None,'future_path_contracts':str(qty) if qty is not None else None,'future_path_entry_notional_USDT':float(entryn) if entryn is not None else None}
     if reason:item.update(future_path_status='NO_VALID_ENTRY',future_path_window_complete=False,future_path_observable_max_USDT=None,future_path_observable_min_USDT=None)
     else:item.update(diagnostic(bb,tt,entry,qty,unit,side,entryn,fee,hold))
     results.append(item)
 (B/'future_path_diagnostics.json').write_text(json.dumps(results,separators=(',',':')))
 groups=defaultdict(list)
 for x in results:groups[(x['family'],x['asset'],x['action'],x['fee_each_side_bps'],x['window_seconds'])].append(x)
 summary=[]
 for key,rows in groups.items():
  complete=[x for x in rows if x['future_path_window_complete']];v=[x['future_path_observable_max_USDT'] for x in complete if x['future_path_observable_max_USDT'] is not None];summary.append(dict(zip(['family','asset','action','fee_each_side_bps','window_seconds'],key),events=len(rows),complete_windows=len(complete),incomplete_or_noentry=len(rows)-len(complete),future_path_complete_has_nonnegative=sum(x.get('future_path_first_nonnegative_ordinal') is not None for x in complete),future_path_max_median_USDT=statistics.median(v) if v else None,future_path_maximum_USDT=max(v) if v else None,future_path_noentry_reasons=dict(Counter(x['future_path_entry_rejection'] for x in rows if x['future_path_entry_rejection']))))
 (B/'future_path_summary.json').write_text(json.dumps(summary,separators=(',',':')));(B/'results.json').write_text(json.dumps({'status':'HINDSIGHT_QUOTE_PATH_DIAGNOSTIC_NOT_STRATEGY','events':len(events),'diagnostic_rows':len(results),'original_observed_entry_qty_exact_matches':same,'raw_sha256':sha.hexdigest(),'invalid_books':invalid,'all_future_labels_separate':True,'actual_AI':None,'global_goal':'ACTIVE'},indent=2));print({'events':len(events),'rows':len(results),'same_entry_qty':same})
if __name__=='__main__':main()
