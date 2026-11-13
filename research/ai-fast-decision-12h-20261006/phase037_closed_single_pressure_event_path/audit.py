from pathlib import Path
from decimal import Decimal as D
from fractions import Fraction as F
import json,gzip,hashlib,math
P=Path(__file__).resolve().parent
def main():
 p=json.loads((P/'protocol.json').read_text());timeline=json.loads((P/'timeline.json').read_text());result=json.loads((P/'results.json').read_text());wanted={r['target_shared_ns']:r for r in timeline};last={k:None for k in wanted};flowpoints={k:[] for k in wanted};seen={};digest=hashlib.sha256()
 with gzip.open(Path(p['source'])/'raw/ws_messages.jsonl.gz','rb') as f:
  for line in f:
   digest.update(line);r=json.loads(line)
   if r['instId']!='SUI-USDT-SWAP':continue
   ns=r['os_shared_ns'];raw=json.loads(r['raw'])
   for d in raw.get('data',[]):
    if r['channel']=='books5':
     for target in wanted:
      if ns<=target:last[target]={'ordinal':r['local_ordinal'],'ns':ns,'bid':D(d['bids'][0][0]),'ask':D(d['asks'][0][0])}
    elif r['channel']=='trades':
     key=(d.get('tradeId'),d.get('source'))
     if key in seen:continue
     seen[key]=True;amount=F(d['px'])*F(d['sz'])
     for target in wanted:
      if target-10000000000<ns<=target:flowpoints[target].append((ns,amount,amount*(1 if d['side']=='buy' else -1)))
 assert digest.hexdigest()==p['raw_logical_SHA']
 for target,r in wanted.items():
  b=last[target];assert b['ordinal']==r['last_book_ordinal'] and math.isclose(float(b['bid']),r['bid'],abs_tol=1e-12) and math.isclose(float(b['ask']),r['ask'],abs_tol=1e-12);assert r['book_age_ms']==(target-b['ns'])/1e6 and r['book_fresh_250ms']==(0<=target-b['ns']<=250000000)
  for sec in [1,10]:
   ts=[x for x in flowpoints[target] if x[0]>target-sec*1000000000];total=sum((x[1] for x in ts),F(0));net=sum((x[2] for x in ts),F(0));assert total==F(r['flow'][str(sec)]['total_exact']) and net==F(r['flow'][str(sec)]['net_exact']) and len(ts)==r['flow'][str(sec)]['received_unique_records'];assert (r['flow'][str(sec)]['imbalance'] is None)==(total==0)
  assert r['label']==('FUTURE_DIAGNOSTIC_NEVER_MODEL_INPUT' if r['offset_seconds']>0 else 'PAST_OR_ASOF_RECEIVED_INFORMATION')
 rows=json.loads((P/'existing_outcome_decomposition.json').read_text());count=0
 for r in rows:
  if r['status']!='observed':assert r['price_fee_delta_USDT'] is None;continue
  expected=D(str(r['directional_mid_component_USDT']))-D(str(r['two_crossings_halfspread_cost_USDT']))+D(str(r['depth_VWAP_difference_from_best_USDT']))-D(str(r['fee_USDT']));assert math.isclose(float(expected),r['price_fee_delta_USDT'],abs_tol=1e-10);count+=1
 (P/'audit.json').write_text(json.dumps({'status':'PASS_FINITE_RECEIVED_TIMELINE_AND_STORED_COMPONENT_MATH','all_ten_last_received_quotes_and_age':True,'all_ten_1s10s_exact_dedup_totals':True,'future_labels_checked':True,'existing_observed_conditions_identity_checked':count,'censored_kept_unknown':len(rows)-count,'sourcehash':digest.hexdigest(),'prior033_full60quoteaudit_not_reclaimed_as_new_execution':True,'no_strategy_rerun_ornewholds':True,'sameOwner_finite_notthirdparty':True},indent=2)+'\n');print(10,count)
if __name__=='__main__':main()
