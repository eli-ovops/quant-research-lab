from pathlib import Path
from collections import defaultdict,Counter
from decimal import Decimal
import json,hashlib,statistics
B=Path(__file__).resolve().parent
def distribution(v):
 if not v:return {'n':0,'mean':None,'median':None,'min':None,'max':None,'p10':None,'p90':None}
 v=sorted(v);return {'n':len(v),'mean':statistics.mean(v),'median':statistics.median(v),'min':v[0],'max':v[-1],'p10':v[int((len(v)-1)*.1)],'p90':v[int((len(v)-1)*.9)]}
def summarize(rows):
 obs=[x for x in rows if x['status']=='observed'];gross=[x['gross_price_delta_USDT'] for x in obs];fees=[x['fee_USDT'] for x in obs];net=[x['price_fee_delta_USDT'] for x in obs];room=[x['gross_price_delta_USDT']/(x['entry_notional_USDT']+x['exit_notional_USDT'])*10000 for x in obs]
 for x in obs:assert abs(Decimal(str(x['gross_price_delta_USDT']))-Decimal(str(x['fee_USDT']))-Decimal(str(x['price_fee_delta_USDT'])))<=Decimal('1e-9')
 return {'total':len(rows),'observed':len(obs),'null_censored':len(rows)-len(obs),'censor_reasons':dict(Counter(x.get('reason') for x in rows if x['status']!='observed')),'future_only_gross_price_delta_USDT':distribution(gross),'future_only_explicit_fee_USDT':distribution(fees),'future_only_net_price_fee_delta_USDT':distribution(net),'future_only_break_even_eachleg_fee_bps':distribution(room),'future_only_gross_positive_count':sum(g>0 for g in gross),'future_only_net_positive_count':sum(n>0 for n in net),'future_only_positive_gross_below_fee_count':sum(x['gross_price_delta_USDT']>0 and x['gross_price_delta_USDT']<x['fee_USDT'] for x in obs),'future_only_nonpositive_gross_count':sum(g<=0 for g in gross),'future_only_actual_entry_delay_observed_ms':distribution([x['actual_entry_delay_ms'] for x in obs]),'future_only_actual_entry_delay_all_available_ms':distribution([x['actual_entry_delay_ms'] for x in rows if 'actual_entry_delay_ms' in x]),'not_pure_mid_prediction':True}
def best_pair(follow,fade):
 result={'event_id':follow['event_id'],'family':follow['family'],'asset':follow['asset'],'fee_each_side_bps':follow['fee_each_side_bps'],'future_only_not_executable_or_AI':True,'FOLLOW_status':follow['status'],'FADE_status':fade['status'],'future_only_best_net_USDT':None}
 if follow['status']!='observed' or fade['status']!='observed':result['status']='UNKNOWN_CENSORED_KEEP_DENOMINATOR';return result
 result['contracts_FOLLOW']=follow['contracts'];result['contracts_FADE']=fade['contracts']
 if Decimal(follow['contracts'])!=Decimal(fade['contracts']):result['status']='UNKNOWN_QTY_NOT_MATCHED_KEEP_BOTH';return result
 result.update(status='BOTH_OBSERVED_SAMEQTY_HINDSIGHT',future_only_best_net_USDT=max(follow['price_fee_delta_USDT'],fade['price_fee_delta_USDT']),future_only_best_gross_USDT=max(follow['gross_price_delta_USDT'],fade['gross_price_delta_USDT']))
 return result
def main():
 p=json.loads((B/'protocol.json').read_text());f=json.loads((B/'execution_freeze.json').read_text())
 for n,h in f['hashes'].items():assert hashlib.sha256((B/n).read_bytes()).hexdigest()==h
 assert hashlib.sha256(Path(p['source']).read_bytes()).hexdigest()==p['source_sha256'];allrows=json.loads(Path(p['source']).read_text());rows=[x for x in allrows if x['hold_seconds']==15 and x['delay_ms']==0];groups=defaultdict(list);pairs=defaultdict(dict)
 for x in rows:groups[(x['family'],x['asset'],x['action'],x['fee_each_side_bps'])].append(x);pairs[(x['event_id'],x['fee_each_side_bps'])][x['action']]=x
 summary=[]
 for family in ['FLOW_IMPULSE','BOOK_STATE','BTC_TRANSMISSION']:
  for asset in ['BTC-USDT-SWAP','ETH-USDT-SWAP','SOL-USDT-SWAP','DOGE-USDT-SWAP','XRP-USDT-SWAP','SUI-USDT-SWAP']:
   for action in ['FOLLOW','FADE']:
    for fee in [5,10]:summary.append({'family':family,'asset':asset,'action':action,'fee_each_side_bps':fee,'hold_seconds':15,'delay_ms':0,'future_only_diagnostic':True,**summarize(groups[(family,asset,action,fee)])})
 best=[best_pair(v['FOLLOW'],v['FADE']) for v in pairs.values()];bestsummary=[]
 for asset in ['BTC-USDT-SWAP','ETH-USDT-SWAP','SOL-USDT-SWAP','DOGE-USDT-SWAP','XRP-USDT-SWAP','SUI-USDT-SWAP']:
  for family in ['FLOW_IMPULSE','BOOK_STATE','BTC_TRANSMISSION']:
   for fee in [5,10]:
    xs=[x for x in best if x['asset']==asset and x['family']==family and x['fee_each_side_bps']==fee];valid=[x for x in xs if x['status']=='BOTH_OBSERVED_SAMEQTY_HINDSIGHT'];bestsummary.append({'asset':asset,'family':family,'fee_each_side_bps':fee,'total_events':len(xs),'both_observed_sameqty':len(valid),'unknown_censored':sum(x['status']=='UNKNOWN_CENSORED_KEEP_DENOMINATOR' for x in xs),'unknown_qty_mismatch':sum(x['status']=='UNKNOWN_QTY_NOT_MATCHED_KEEP_BOTH' for x in xs),'future_only_best_net':distribution([x['future_only_best_net_USDT'] for x in valid]),'future_only_best_net_positive_count':sum(x['future_only_best_net_USDT']>0 for x in valid),'not_implementable_perfect_future_choice':True})
 for name,data in [('future_only_cost_attribution.json',summary),('future_only_best_action_rows.json',best),('future_only_best_action_summary.json',bestsummary)]: (B/name).write_text(json.dumps(data,separators=(',',':')))
 (B/'results.json').write_text(json.dumps({'status':'FUTURE_ONLY_STORED_COLUMN_ARITHMETIC_NOT_NEW_STRATEGY','selected_condition_rows':len(rows),'fees':{str(fee):{'observed':sum(x['fee_each_side_bps']==fee and x['status']=='observed' for x in rows),'censored':sum(x['fee_each_side_bps']==fee and x['status']!='observed' for x in rows),'gross_positive_actions':sum(x['fee_each_side_bps']==fee and x['status']=='observed' and x['gross_price_delta_USDT']>0 for x in rows),'net_positive_actions':sum(x['fee_each_side_bps']==fee and x['status']=='observed' and x['price_fee_delta_USDT']>0 for x in rows)} for fee in [5,10]},'source_core_reruns':0,'actual_AI':None,'not_account_PnL':True,'global_goal':'ACTIVE'},indent=2));print({'selected_rows':len(rows),'best_pairs':len(best)})
if __name__=='__main__':main()
