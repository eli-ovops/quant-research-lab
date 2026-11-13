from pathlib import Path
import json,gzip,hashlib
from capsule import canonical,digest,validate
P=Path(__file__).resolve().parent
def main():
 s=json.loads((P/'historical_asof_capsule.json').read_text());pr=json.loads((P/'protocol.json').read_text());old=P.parent/'phase033_job010_replication_preparation';op=json.loads((old/'protocol.json').read_text());wanted={x['provenance']['local_ordinal'] for x in s['received_trade_witnesses10s']};wanted.update(s[n]['provenance']['local_ordinal'] for n in ['current_book','ref10_book','ref1_book']);wanted.add(s['source']['local_ordinal']);wanted.add(s['first_unique_trade_witness']['provenance']['local_ordinal']);rows={}
 with gzip.open(Path(op['source'])/'raw/ws_messages.jsonl.gz','rb') as f:
  for line in f:
   r=json.loads(line)
   if r['local_ordinal']>s['source']['local_ordinal']:break
   if r['local_ordinal'] in wanted:rows[r['local_ordinal']]=r
 def check_provenance(v):
  r=rows[v['local_ordinal']]
  for k in ['os_shared_ns','receive_wall_ns','run_id','connectionId','clock_domain_id','boot_identity']:assert r[k]==v[k]
  assert r['instId']==v['asset'];return json.loads(r['raw'])
 check_provenance(s['source'])
 for name in ['current_book','ref10_book','ref1_book']:
  b=s[name];raw=check_provenance(b['provenance']);assert any(d['asks']==b['asks'] and d['bids']==b['bids'] for d in raw['data']) and b['content_sha']==digest({'asks':b['asks'],'bids':b['bids']})
 for witness in s['received_trade_witnesses10s']+[s['first_unique_trade_witness']]:
  raw=check_provenance(witness['provenance']);assert any(canonical(d)==canonical(witness['trade']) for d in raw['data'])
 assert validate(s);reg=json.loads((P/'instruments.json').read_text());assert canonical(s['contract_spec'])==canonical(next(x for x in reg if x['instId']==s['asset']))
 envelope=json.loads((P/'historical_offline_request.json').read_text());payload=envelope['offline_draft_payload'];assert payload['state']['received_trade_witnesses10s_sha']==digest(s['received_trade_witnesses10s']) and payload['state']['received_trade_witnesses10s_count']==len(s['received_trade_witnesses10s']);assert envelope['payload'] is None and envelope['sendable_payload'] is None
 for ref in pr['references']:assert hashlib.sha256(Path(ref['path']).read_bytes()).hexdigest()==ref['sha']
 (P/'audit.json').write_text(json.dumps({'status':'PASS_FINITE_HISTORICAL_ASOF_FIELD_AND_DRAFT_BINDING','raw_provenance_ordinals':len(rows),'received_trade_witnesses':len(s['received_trade_witnesses10s']),'three_book_raw_contents':True,'firstunique_raw_trade_proof':True,'spec_bound':True,'compact_payload_witness_sha_count_bound':True,'reference_hashes':len(pr['references']),'source_fullSHA_boundary':'prior033 accepted fullraw SHA, this audit onlyconsumes asofprefix','provider_calls':0,'future_income_model_labels_in_payload':False,'no_real_new_book_or_fill_verification':True,'sameOwner_finite_notthirdparty':True},indent=2)+'\n');print(len(rows),len(s['received_trade_witnesses10s']))
if __name__=='__main__':main()
