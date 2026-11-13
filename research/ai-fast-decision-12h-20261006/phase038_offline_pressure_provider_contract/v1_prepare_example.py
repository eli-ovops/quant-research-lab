from pathlib import Path
from fractions import Fraction as F
import gzip,json,hashlib,time
from capsule import SCHEMA,QUESTION,digest,validate,build_request
P=Path(__file__).resolve().parent
def main():
 old=P.parent/'phase033_job010_replication_preparation';pr=json.loads((old/'protocol.json').read_text());e=json.loads((old/'pressure_events.json').read_text())[0];reg=json.loads((P/'instruments.json').read_text());spec=next(x for x in reg if x['instId']==e['asset']);rows={};trades=[];seen={};first=None;now=e['source_asof_shared_ns']
 def provenance(r):return {**{k:r[k] for k in ['run_id','connectionId','clock_domain_id','boot_identity','local_ordinal','os_shared_ns','receive_wall_ns']},'asset':r['instId']}
 with gzip.open(Path(pr['source'])/'raw/ws_messages.jsonl.gz','rb') as stream:
  for line in stream:
   r=json.loads(line)
   if r['local_ordinal']>e['asof_ordinal']:break
   if r['local_ordinal'] in [e['current_book_ordinal'],e['reference10_ordinal'],e['reference1_ordinal'],e['asof_ordinal']]:rows[r['local_ordinal']]=r
   if r['instId']!=e['asset'] or r['channel']!='trades':continue
   for d in json.loads(r['raw']).get('data',[]):
    key=(d.get('tradeId'),d.get('source'));signature=tuple(d.get(k) for k in ['px','sz','side','ts','count'])
    if key in seen:assert seen[key]==signature;continue
    seen[key]=signature;first=r['os_shared_ns'] if first is None else first
    if now-10000000000<r['os_shared_ns']<=now:trades.append({'provenance':provenance(r),'trade':d})
 def book(ordinal):
  r=rows[ordinal];d=json.loads(r['raw'])['data'][0];content={'asks':d['asks'],'bids':d['bids']};return {**content,'provenance':provenance(r),'content_sha':digest(content)}
 state={'schemaVersion':SCHEMA,'questionVersion':QUESTION,'qualified_rule_sha':hashlib.sha256((P/'frozen_pressure_rules.py').read_bytes()).hexdigest(),'asset':e['asset'],'contract_spec':spec,'contract_spec_sha':digest(spec),'source':provenance(rows[e['asof_ordinal']]),'source_dataset_logical_sha':pr['source_raw_sha256'],'is_live':False,'flow_identity_conflict':False,'feature_completed_shared_ns':time.clock_gettime_ns(time.CLOCK_MONOTONIC),'first_unique_trade_shared_ns':first,'current_book':book(e['current_book_ordinal']),'ref10_book':book(e['reference10_ordinal']),'ref1_book':book(e['reference1_ordinal']),'received_trade_witnesses10s':trades,'flow_exact':{k:e[k+'_exact'] for k in ['total10','net10','total1','net1']},'asof_exact':{'impulse10_bps':e['impulse10_exact'],'required_move_max_bps':e['required_move_max_exact'],'dominant10':e['dominant10_exact'],'reference_opposing_top5':e['reference_opposing_top5_exact']},'fixed_buffer_bps':5,'capacity_USDT':500,'mainfee_eachleg_bps':5,'asof_cost_legs':e['asof_cost_proxy_legs'],'eligibility':True,'registered_rule':e['qualified_rule'],'registered_action':e['action'],'rejectreason':None}
 validate(state);request=build_request(state,time.clock_gettime_ns(time.CLOCK_MONOTONIC),state['source']);(P/'historical_asof_capsule.json').write_text(json.dumps(state,indent=2)+'\n');(P/'historical_offline_request.json').write_text(json.dumps(request,indent=2)+'\n');print(len(trades),len(json.dumps(request)),request['metadata']['gate'])
if __name__=='__main__':main()
