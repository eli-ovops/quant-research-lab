from pathlib import Path
from decimal import Decimal,ROUND_FLOOR
import json
B=Path(__file__).resolve().parent
p=json.loads((B/'protocol.json').read_text());specs={x['instId']:x for x in json.loads((B/'instruments.json').read_text())};ev={e['event_id']:e for e in json.loads((B/'events.json').read_text())};affected=[r for r in json.loads((B/'event_price_fee_deltas.json').read_text()) if r['reason']=='minlot_or_entrydepth'];keys={}
for r in affected:keys[(r['event_id'],r['action'],r['delay_ms'],r['fee_each_side_bps'])]={'outcome':r,'entry':None}
with Path(p['source_live_until_stop']).open() as inp:
 for line in inp:
  row=json.loads(line)
  if row['channel']!='books5':continue
  o=json.loads(row['raw']);t=row['monotonic_ns']/1e6
  for k,obj in keys.items():
   if obj['entry'] is not None:continue
   r=obj['outcome'];e=ev[r['event_id']]
   if row['instId']==r['asset'] and row['connectionId']==e['connectionId'] and t>e['asof_ms']+r['delay_ms']:
    d=o['data'][0]
    if d['bids'] and d['asks'] and Decimal(d['bids'][0][0])<Decimal(d['asks'][0][0]):obj['entry']=d;obj['entry_ordinal']=row['local_ordinal']
trace=[]
for key,obj in keys.items():
 r=obj['outcome'];d=obj['entry'];levels=[(Decimal(x[0]),Decimal(x[1])) for x in (d['asks'] if r['side']==1 else d['bids']) if Decimal(x[1])>0];unit=Decimal(specs[r['asset']]['ctVal'])*Decimal(specs[r['asset']]['ctMult']);step=Decimal(specs[r['asset']]['lotSz']);fee=Decimal(r['fee_each_side_bps'])/10000;initial=Decimal(500)/(1+fee);budget=initial;q=Decimal(0);steps=[]
 for price,amt in levels:
  take=min(amt,budget/(price*unit));q+=take;budget-=take*price*unit;steps.append({'price':str(price),'available':str(amt),'take':str(take),'remaining_budget':str(budget)})
  if budget<=0:break
 rounded=(q/step).to_integral_value(rounding=ROUND_FLOOR)*step;available=sum(price*amt*unit for price,amt in levels);assert available>=initial and rounded>=Decimal(specs[r['asset']]['minSz']) and 0<budget<Decimal('1e-18')
 trace.append({'event_id':r['event_id'],'asset':r['asset'],'action':r['action'],'delay_ms':r['delay_ms'],'fee_bps':r['fee_each_side_bps'],'entry_ordinal':obj['entry_ordinal'],'available_notional':str(available),'initial_budget':str(initial),'positive_rounding_residual':str(budget),'quantity_floor_would_meet_min':str(rounded),'numeric_false_censor_confirmed':True,'steps':steps,'no_exit_or_PnL_imputation':True})
(B/'numeric_censor_diagnosis.json').write_text(json.dumps({'affected_outcome_rows':len(affected),'distinct_entry_sizing_cases':len(trace),'trace':trace,'core_preserved_unchanged':True,'result_stays_null':True},indent=2));print({'affected':len(affected),'distinct':len(trace),'residuals':[x['positive_rounding_residual'] for x in trace]})

