from pathlib import Path
from decimal import Decimal as D
from collections import defaultdict
import json,hashlib
B=Path(__file__).resolve().parent
def near(a,b):assert abs(D(str(a))-D(str(b)))<=D('1e-9')
def main():
 p=json.loads((B/'protocol.json').read_text());f=json.loads((B/'execution_freeze.json').read_text())
 for n,h in f['hashes'].items():assert hashlib.sha256((B/n).read_bytes()).hexdigest()==h
 assert hashlib.sha256(Path(p['source']).read_bytes()).hexdigest()==p['source_sha256'];source=[x for x in json.loads(Path(p['source']).read_text()) if x['hold_seconds']==15 and x['delay_ms']==0];groups=defaultdict(list);n=null=0
 for x in source:
  groups[(x['family'],x['asset'],x['action'],x['fee_each_side_bps'])].append(x)
  if x['status']!='observed':assert x['price_fee_delta_USDT'] is None;null+=1;continue
  E,X=D(str(x['entry_notional_USDT'])),D(str(x['exit_notional_USDT']));gross=D(x['side'])*(X-E);fee=(E+X)*D(x['fee_each_side_bps'])/10000;near(gross,x['gross_price_delta_USDT']);near(fee,x['fee_USDT']);near(gross-fee,x['price_fee_delta_USDT']);n+=1
 summary=json.loads((B/'future_only_cost_attribution.json').read_text())
 for g in summary:
  rows=groups[(g['family'],g['asset'],g['action'],g['fee_each_side_bps'])];valid=[x for x in rows if x['status']=='observed'];assert g['observed']==len(valid) and g['null_censored']==len(rows)-len(valid)
  if valid:
   for key,col in [('future_only_gross_price_delta_USDT','gross_price_delta_USDT'),('future_only_explicit_fee_USDT','fee_USDT'),('future_only_net_price_fee_delta_USDT','price_fee_delta_USDT')]:near(sum((D(str(x[col])) for x in valid),D(0))/len(valid),g[key]['mean'])
   near(max(D(str(x['gross_price_delta_USDT']))/(D(str(x['entry_notional_USDT']))+D(str(x['exit_notional_USDT'])))*10000 for x in valid),g['future_only_break_even_eachleg_fee_bps']['max'])
  else:assert g['future_only_net_price_fee_delta_USDT']['mean'] is None
 index={(x['event_id'],x['fee_each_side_bps'],x['action']):x for x in source};best=json.loads((B/'future_only_best_action_rows.json').read_text());same=cens=mismatch=0
 for x in best:
  a=index[(x['event_id'],x['fee_each_side_bps'],'FOLLOW')];b=index[(x['event_id'],x['fee_each_side_bps'],'FADE')]
  if x['status']=='BOTH_OBSERVED_SAMEQTY_HINDSIGHT':assert D(a['contracts'])==D(b['contracts']);near(max(a['price_fee_delta_USDT'],b['price_fee_delta_USDT']),x['future_only_best_net_USDT']);same+=1
  elif x['status']=='UNKNOWN_CENSORED_KEEP_DENOMINATOR':assert a['status']!='observed' or b['status']!='observed';assert x['future_only_best_net_USDT'] is None;cens+=1
  else:assert a['status']==b['status']=='observed' and D(a['contracts'])!=D(b['contracts']);assert x['future_only_best_net_USDT'] is None;mismatch+=1
 audit={'status':'PASS_FINITE_STORED_COLUMN_ARITHMETIC','valid_rows_checked':n,'null_rows_checked':null,'group_summary_counts_means_roommax_checked':len(summary),'sameqty_hindsight_pairs_checked':same,'censored_pairs_unknown':cens,'qty_mismatch_pairs_unknown':mismatch,'source_hash_unchanged':True,'no_strategy_rerun':True,'source_quote_boundary':'reuses017 limited originalquote audit124valid+28null; no new quote or fullstrategy replay','actual_AI':None};(B/'audit.json').write_text(json.dumps(audit,indent=2));print(audit)
if __name__=='__main__':main()
