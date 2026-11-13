import json,hashlib,math
from pathlib import Path
from decimal import Decimal
from collections import Counter
P=Path(__file__).resolve().parent
def main():
 protocol=json.loads((P/'protocol.json').read_text());pairs=json.loads((P/'paired_event_rows.json').read_text());groups=json.loads((P/'delay_summary.json').read_text());pairedgroups=json.loads((P/'paired_delay_summary.json').read_text());original={};sealed=0
 for s in protocol['sources']:
  path=Path(s['path']);assert hashlib.sha256(path.read_bytes()).hexdigest()==s['sha256'];m=json.loads((path.parent/'manifest.json').read_text())['files'];assert m[path.name]['sha256']==s['sha256'];sealed+=1
  records=json.loads(path.read_text())
  for r in records:
   if r['hold_seconds']==15:original[(s['phase'],r['segment_id'],r['event_id'],r['asset'],r['family'],r['action'],r['fee_each_side_bps'],r['delay_ms'])]=r
 for p in pairs:
  prefix=(p['source'],p['segment_id'],p['event_id'],p['asset'],p['family'],p['action'],p['fee_each_side_bps']);zero=original[prefix+(0,)];late=original[prefix+(p['delay_ms'],)]
  both=zero['status']=='observed' and late['status']=='observed'
  if both:
   equal=Decimal(zero['contracts'])==Decimal(late['contracts']);assert equal is p['same_contract_qty']
   for output,column in [('net_change_delayed_minus0','price_fee_delta_USDT'),('gross_change','gross_price_delta_USDT'),('fee_change','fee_USDT')]:
    expected=Decimal(str(late[column]))-Decimal(str(zero[column]));assert math.isclose(p[output],float(expected),rel_tol=1e-10,abs_tol=1e-10)
   assert math.isclose(p['net_change_delayed_minus0'],p['gross_change']-p['fee_change'],abs_tol=1e-10)
  else:assert p['same_contract_qty'] is None and p['net_change_delayed_minus0'] is None
  assert p['base_positive_delay_unknown']==(zero['status']=='observed' and zero['price_fee_delta_USDT']>0 and late['status']!='observed')
 for g in groups:
  subset=[r for k,r in original.items() if k[0]==g['source'] and r['asset']==g['asset'] and r['family']==g['family'] and r['action']==g['action'] and r['fee_each_side_bps']==g['fee_each_side_bps'] and r['delay_ms']==g['delay_ms']];observed=[r for r in subset if r['status']=='observed']
  assert len(subset)==g['events'] and len(observed)==g['observed'] and len(subset)-len(observed)==g['censored_UNKNOWN'] and sum(r['price_fee_delta_USDT']>0 for r in observed)==g['net']['positive']
  assert g['net']['n']==len(observed);assert (g['net']['mean'] is None)==(not observed)
 for g in pairedgroups:
  assert g['sameqty']+g['qty_mismatch']==g['common_observed'] and sum(g['statuses'].values())==g['total_events']
 (P/'audit.json').write_text(json.dumps({'status':'PASS_FINITE_STORED_COLUMN_AND_DENOMINATOR_AUDIT','source_manifest_hashes':sealed,'all_pair_rows_checked':len(pairs),'delay_groups_checked':len(groups),'pair_groups_count_checked':len(pairedgroups),'no_strategy_or_raw_quote_rerun':True,'source_quote_audits':'prior accepted stage finite audits only, not repeated here','sameOwner_distinct_arithmetic_not_thirdparty_fullreplay':True,'actualAI':None},indent=2)+'\n')
 print(len(pairs),len(groups),len(pairedgroups))
if __name__=='__main__':main()
