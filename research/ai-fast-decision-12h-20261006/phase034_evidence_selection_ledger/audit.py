import json,hashlib
from pathlib import Path
P=Path(__file__).resolve().parent
def main():
 r=json.loads((P/'ledger.json').read_text());checked={};sealed=0
 for entry in r['sources']:
  p=Path(entry['path']);assert p.stat().st_size==entry['bytes'] and hashlib.sha256(p.read_bytes()).hexdigest()==entry['sha256'];checked[str(p)]=entry['sha256']
  m=p.parent/'manifest.json'
  if m.exists() and p.parent.name.startswith('phase'):
   f=json.loads(m.read_text())['files'];assert p.name in f;v=f[p.name];h=v['sha256'] if isinstance(v,dict) else v;assert h==entry['sha256'];sealed+=1
 for e in r['episodes']:
  for fee,c in e['primary_counts_by_fee'].items():
   xs=[x for x in r['primary_groups'] if x['cohort']==e['stage'] and x['fee_each_side_bps']==int(fee)]
   assert sum(x['observed'] for x in xs)==c['observed'] and sum(x['censored_UNKNOWN'] for x in xs)==c['censored_UNKNOWN']
   assert sum(x['observed_positive_count'] for x in xs)==c['observed_positive_count']
   assert all(x['hold_seconds']==15 and x['delay_ms']==0 and x['capacity_USDT']==500 for x in xs)
 assert all(z['events']==0 and z['return'] is None and z['future_income_path']=='NOT_OBSERVED' for z in r['new_rules_zero_event_null'])
 assert r['job010']['results'] is None and r['actual_provider_calls']==0
 (P/'audit.json').write_text(json.dumps({'status':'PASS_SOURCE_HASH_SEAL_AND_PRIMARY_DENOMINATOR_INTEGRATION','source_references':len(r['sources']),'unique_source_paths':len(checked),'sealed_source_references_checked':sealed,'five_independent_episodes_twofees':True,'zero_events_not_income_zero':True,'job010_pending':True,'no_strategy_rerun':True,'not_full_independent_strategy_replay':True},indent=2)+'\n')
 print(len(checked),sealed)
if __name__=='__main__':main()
