from pathlib import Path
from fractions import Fraction as F
from bisect import bisect_right
from collections import Counter
import json,gzip,hashlib,math
P=Path(__file__).resolve().parent
def main():
 p=json.loads((P/'protocol.json').read_text());freeze=json.loads((P/'execution_freeze.json').read_text())
 for name,h in freeze['hashes'].items():assert hashlib.sha256((P/name).read_bytes()).hexdigest()==h
 for r in p['references']:assert hashlib.sha256(Path(r['path']).read_bytes()).hexdigest()==r['sha']
 original=P.parent/'phase033_job010_replication_preparation';event=json.loads((original/'pressure_events.json').read_text())[0];assert event['asof_ordinal']==140916 and event['asset']=='SUI-USDT-SWAP';spec=next(s for s in json.loads((original/'instruments.json').read_text()) if s['instId']==event['asset']);unit=F(spec['ctVal'])*F(spec['ctMult']);books=[];trades=[];seen={};rawhash=hashlib.sha256();matchedraw=None
 with gzip.open(Path(p['source'])/'raw/ws_messages.jsonl.gz','rb') as stream:
  for line in stream:
   rawhash.update(line);r=json.loads(line)
   if r['local_ordinal']==p['event_ordinal']:matchedraw=r
   if r['instId']!=event['asset']:continue
   assert r['run_id']==event['run_id'] and r['connectionId']==event['connectionId'] and r['clock_domain_id']==event['clock_domain_id'];o=json.loads(r['raw'])
   for d in o.get('data',[]):
    if r['channel']=='books5':books.append({'ns':r['os_shared_ns'],'wall_ns':r['receive_wall_ns'],'ordinal':r['local_ordinal'],'bid':F(d['bids'][0][0]),'ask':F(d['asks'][0][0]),'bids':d['bids'],'asks':d['asks']})
    elif r['channel']=='trades':
     key=(d.get('tradeId'),d.get('source'));signature=tuple(d.get(k) for k in ['px','sz','side','ts','count'])
     if key in seen:assert seen[key]==signature;continue
     seen[key]=signature;amount=F(d['px'])*F(d['sz'])*unit;trades.append({'ns':r['os_shared_ns'],'ordinal':r['local_ordinal'],'amount':amount,'net':amount*(1 if d['side']=='buy' else -1)})
 assert rawhash.hexdigest()==p['raw_logical_SHA'] and matchedraw['os_shared_ns']==event['source_asof_shared_ns'];times=[b['ns'] for b in books];anchor=event['source_asof_shared_ns'];timeline=[]
 for offset in p['offsets_seconds']:
  target=anchor+offset*1000000000;idx=bisect_right(times,target)-1;b=books[idx] if idx>=0 else None;flows={}
  for secs in [1,10]:
   ts=[t for t in trades if target-secs*1000000000<t['ns']<=target];total=sum((t['amount'] for t in ts),F(0));net=sum((t['net'] for t in ts),F(0));flows[str(secs)]={'received_unique_records':len(ts),'total_exact':str(total),'net_exact':str(net),'imbalance':float(net/total) if total>0 else None}
  earlier=[t for t in trades if t['ns']<=target];last=earlier[-1] if earlier else None
  row={'offset_seconds':offset,'target_shared_ns':target,'label':'FUTURE_DIAGNOSTIC_NEVER_MODEL_INPUT' if offset>0 else 'PAST_OR_ASOF_RECEIVED_INFORMATION','last_book_ordinal':b['ordinal'] if b else None,'book_age_ms':(target-b['ns'])/1e6 if b else None,'book_fresh_250ms':0<=target-b['ns']<=250000000 if b else None,'bid':float(b['bid']) if b else None,'ask':float(b['ask']) if b else None,'mid':float((b['bid']+b['ask'])/2) if b else None,'spread':float(b['ask']-b['bid']) if b else None,'flow':flows,'latest_unique_trade_age_ms':(target-last['ns'])/1e6 if last else None,'not_new_hold_return':True};timeline.append(row)
 at=next(t for t in timeline if t['offset_seconds']==0)
 for sec in [1,10]:assert F(at['flow'][str(sec)]['total_exact'])==F(event['total'+str(sec)+'_exact']) and F(at['flow'][str(sec)]['net_exact'])==F(event['net'+str(sec)+'_exact'])
 assert math.isclose(at['latest_unique_trade_age_ms'],event['latest_trade_age_ns']/1e6,abs_tol=1e-9)
 lookup={b['ordinal']:b for b in books};outcomes=json.loads((original/'pressure_shadow_outcomes.json').read_text());decomposed=[]
 for r in outcomes:
  d={**r,'diagnosticlabel':'EXISTING033_OUTCOME_FUTURE_ONLY_NEVER_MODEL_INPUT'}
  if r['status']=='observed':
   entry=lookup[r['entry_ordinal']];exit=lookup[r['exit_ordinal']];q=F(r['contracts'])*unit;side=r['side'];mid0=(entry['bid']+entry['ask'])/2;mid1=(exit['bid']+exit['ask'])/2;directional_mid=side*(mid1-mid0)*q;spread_cost=(entry['ask']-entry['bid']+exit['ask']-exit['bid'])*q/2;gross_best=directional_mid-spread_cost;actualgross=F(str(r['gross_price_delta_USDT']));impact=actualgross-gross_best
   d.update({'entry_bestbid':float(entry['bid']),'entry_bestask':float(entry['ask']),'exit_bestbid':float(exit['bid']),'exit_bestask':float(exit['ask']),'directional_mid_component_USDT':float(directional_mid),'two_crossings_halfspread_cost_USDT':float(spread_cost),'depth_VWAP_difference_from_best_USDT':float(impact),'gross_identity_exact':str(directional_mid-spread_cost+impact),'fees_original_USDT':r['fee_USDT'],'net_original_USDT':r['price_fee_delta_USDT'],'delayed_entry_exit_both_move':True});assert math.isclose(float(directional_mid-spread_cost+impact)-r['fee_USDT'],r['price_fee_delta_USDT'],abs_tol=1e-10)
  else:d['decomposition']='UNKNOWN_CENSORED_NOT_ZERO'
  decomposed.append(d)
 (P/'timeline.json').write_text(json.dumps(timeline,indent=2)+'\n');(P/'existing_outcome_decomposition.json').write_text(json.dumps(decomposed,indent=2)+'\n');(P/'results.json').write_text(json.dumps({'status':'SINGLE_EVENT_RECEIVED_PATH_FORENSIC_NOT_NEW_STRATEGY','original_event':event,'source_logical_SHA':rawhash.hexdigest(),'fixed_timeline_rows':len(timeline),'original_economic_conditions':len(outcomes),'observed':sum(r['status']=='observed' for r in outcomes),'censored':sum(r['status']!='observed' for r in outcomes),'pairqty_original':json.loads((original/'pressure_shadow_pair_receipts.json').read_text()),'primary15_delay0_decomposition':[r for r in decomposed if r['hold_seconds']==15 and r['delay_ms']==0],'API_model_calls':0,'no_new_income_hold_rules':True,'not_forced_liquidation_proof':True,'globalgoal':'ACTIVE'},indent=2)+'\n');print(len(timeline),len(outcomes))
if __name__=='__main__':main()
