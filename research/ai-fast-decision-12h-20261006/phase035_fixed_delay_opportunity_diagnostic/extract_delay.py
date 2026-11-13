from pathlib import Path
from collections import defaultdict,Counter
from decimal import Decimal as D
import json,hashlib,statistics
P=Path(__file__).resolve().parent
def stats(values):
 v=sorted(values);n=len(v)
 return {'n':n,'mean':statistics.mean(v) if n else None,'median':statistics.median(v) if n else None,'min':v[0] if n else None,'max':v[-1] if n else None,'p10':v[min(n-1,int(n*.1))] if n else None,'p90':v[min(n-1,int(n*.9))] if n else None,'positive':sum(x>0 for x in v),'positive_fraction':sum(x>0 for x in v)/n if n else None}
def key(r):return (r['segment_id'],r['event_id'],r['asset'],r['family'],r['action'],r['fee_each_side_bps'])
def main():
 p=json.loads((P/'protocol.json').read_text());freeze=json.loads((P/'execution_freeze.json').read_text())
 for n,h in freeze['hashes'].items():assert hashlib.sha256((P/n).read_bytes()).hexdigest()==h
 summaries=[];pairrows=[];pairgroups=[];sourcecounts=[]
 for source in p['sources']:
  f=Path(source['path']);assert hashlib.sha256(f.read_bytes()).hexdigest()==source['sha256'];allrows=json.loads(f.read_text());rows=[r for r in allrows if r['hold_seconds']==15];by=defaultdict(dict)
  for r in rows:
   assert r['capacity_USDT']==500 and r['delay_ms'] in p['delays_ms'] and r['fee_each_side_bps'] in p['fees_eachleg_bps'];k=key(r);assert r['delay_ms'] not in by[k];by[k][r['delay_ms']]=r
  spec=json.loads((f.parent/'instruments.json').read_text());assets=[s['instId'] for s in spec];groups=defaultdict(list)
  for r in rows:groups[(r['asset'],r['family'],r['action'],r['fee_each_side_bps'],r['delay_ms'])].append(r)
  for asset in assets:
   for family in ['FLOW_IMPULSE','BOOK_STATE','BTC_TRANSMISSION']:
    for action in ['FOLLOW','FADE']:
     for fee in p['fees_eachleg_bps']:
      for delay in p['delays_ms']:
       rs=groups[(asset,family,action,fee,delay)];observed=[r for r in rs if r['status']=='observed'];summaries.append({'source':source['phase'],'asset':asset,'family':family,'action':action,'fee_each_side_bps':fee,'delay_ms':delay,'hold_seconds':15,'capacity_USDT':500,'structurally_eligible':family!='BTC_TRANSMISSION' or asset in ['ETH-USDT-SWAP','SOL-USDT-SWAP'],'events':len(rs),'observed':len(observed),'censored_UNKNOWN':len(rs)-len(observed),'censor_reasons':dict(Counter(r['reason'] for r in rs if r['status']!='observed')),'net':stats([r['price_fee_delta_USDT'] for r in observed]),'gross_including_spread':stats([r['gross_price_delta_USDT'] for r in observed]),'fee':stats([r['fee_USDT'] for r in observed]),'actual_entry_delay_ms':stats([r['actual_entry_delay_ms'] for r in observed]),'quote_wait_after_nominal_delay_ms':stats([r['entry_wait_after_decision_ms'] for r in observed])})
  localpairs=[]
  for k,delays in by.items():
   assert set(delays)==set(p['delays_ms']);base=delays[0]
   for delay in p['delays_ms'][1:]:
    r=delays[delay];bo=base['status']=='observed';do=r['status']=='observed';same=D(base['contracts'])==D(r['contracts']) if bo and do else None
    status='COMMON_OBSERVED_SAMEQTY' if bo and do and same else 'COMMON_OBSERVED_QTY_MISMATCH' if bo and do else 'BASE_OBSERVED_DELAYED_UNKNOWN' if bo else 'BASE_UNKNOWN_DELAYED_OBSERVED' if do else 'BOTH_UNKNOWN'
    pr={'source':source['phase'],'segment_id':k[0],'event_id':k[1],'asset':k[2],'family':k[3],'action':k[4],'fee_each_side_bps':k[5],'delay_ms':delay,'status':status,'same_contract_qty':same,'base_status':base['status'],'delayed_status':r['status'],'base_reason':base['reason'],'delayed_reason':r['reason'],'base_contracts':base.get('contracts'),'delayed_contracts':r.get('contracts'),'base_net':base.get('price_fee_delta_USDT'),'delayed_net':r.get('price_fee_delta_USDT'),'net_change_delayed_minus0':r['price_fee_delta_USDT']-base['price_fee_delta_USDT'] if bo and do else None,'gross_change':r['gross_price_delta_USDT']-base['gross_price_delta_USDT'] if bo and do else None,'fee_change':r['fee_USDT']-base['fee_USDT'] if bo and do else None,'base_positive_delay_unknown':bo and base['price_fee_delta_USDT']>0 and not do,'base_actual_entry_delay_ms':base.get('actual_entry_delay_ms'),'delayed_actual_entry_delay_ms':r.get('actual_entry_delay_ms'),'not_AI_causal_effect':True};pairrows.append(pr);localpairs.append(pr)
  for asset in assets:
   for family in ['FLOW_IMPULSE','BOOK_STATE','BTC_TRANSMISSION']:
    for action in ['FOLLOW','FADE']:
     for fee in p['fees_eachleg_bps']:
      for delay in p['delays_ms'][1:]:
       ps=[r for r in localpairs if r['asset']==asset and r['family']==family and r['action']==action and r['fee_each_side_bps']==fee and r['delay_ms']==delay];common=[r for r in ps if r['same_contract_qty'] is not None];same=[r for r in common if r['same_contract_qty']];different=[r for r in common if not r['same_contract_qty']]
       pairgroups.append({'source':source['phase'],'asset':asset,'family':family,'action':action,'fee_each_side_bps':fee,'delay_ms':delay,'total_events':len(ps),'statuses':dict(Counter(r['status'] for r in ps)),'common_observed':len(common),'sameqty':len(same),'qty_mismatch':len(different),'sameqty_net_change':stats([r['net_change_delayed_minus0'] for r in same]),'sameqty_gross_change':stats([r['gross_change'] for r in same]),'sameqty_fee_change':stats([r['fee_change'] for r in same]),'mismatch_independent_capacity_net_change':stats([r['net_change_delayed_minus0'] for r in different]),'base_positive_delay_unknown_count':sum(r['base_positive_delay_unknown'] for r in ps)})
  sourcecounts.append({'source':source['phase'],'original_rows':len(allrows),'hold15_rows':len(rows),'unique_event_action_fee_keys':len(by),'pairrows':len(localpairs)})
 for name,x in [('delay_summary.json',summaries),('paired_event_rows.json',pairrows),('paired_delay_summary.json',pairgroups)]: (P/name).write_text(json.dumps(x,separators=(',',':'))+'\n')
 result={'status':'FIXED_DELAY_STORED_OUTCOME_DIAGNOSTIC_ONLY','sourcecounts':sourcecounts,'group_rows':len(summaries),'pair_group_rows':len(pairgroups),'pair_rows':len(pairrows),'manualdelays_not_AI':True,'held15from_each_entry_changes_exit':True,'no_strategy_runs':True,'no_source_asset_fee_action_return_sums':True,'job010':'PENDING_UNREAD','actualprovider':None,'API_calls':0,'globalgoal':'ACTIVE'};(P/'results.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
if __name__=='__main__':main()
