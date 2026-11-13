from pathlib import Path
from collections import Counter,defaultdict
import json,gzip,datetime
import run_adapter as replication
B=Path(__file__).resolve().parent
def classify(wall_ns,shared_ns,cut):
 old=int(datetime.datetime.fromisoformat(cut['phase013_control_cut_utc']).timestamp()*1e9)
 return {'control13_cohort':'POST_CONTROL13_WALL_FREEZE' if wall_ns>=old else 'PRE_CONTROL13_WALL_FREEZE_DEVELOPMENT','phase014_cohort':'POST_PHASE014_CODE_SHARED_CUT' if shared_ns>=cut['phase014_cut_OS_shared_ns'] else 'PRE_PHASE014_CODE_CUT','source_receive_wall_ns':wall_ns,'source_asof_shared_ns':shared_ns}
def main():
 replication.main();p=json.loads((B/'protocol.json').read_text());cut=json.loads((B/'cohort_cut.json').read_text());events=json.loads((B/'events.json').read_text());be=json.loads((B/'baseline_B_events.json').read_text());wanted={e['asof_ordinal'] for e in events+be};meta={}
 with gzip.open(Path(p['source'])/'raw/ws_messages.jsonl.gz','rb') as raw:
  for line in raw:
   r=json.loads(line)
   if r['local_ordinal'] in wanted:meta[r['local_ordinal']]=classify(r['receive_wall_ns'],r['os_shared_ns'],cut)
 emap={e['event_id']:meta[e['asof_ordinal']] for e in events};bmap={e['event_id']:meta[e['asof_ordinal']] for e in be}
 files=[('events.json',events,emap),('event_deltas.json',None,emap),('baseline_A_features.json',None,emap),('baseline_A_outcomes.json',None,emap),('baseline_B_events.json',be,bmap),('baseline_B_outcomes.json',None,bmap)]
 results={}
 for name,data,mapping in files:
  if data is None:data=json.loads((B/name).read_text())
  for x in data:x.update(mapping[x['event_id']])
  (B/name).write_text(json.dumps(data,separators=(',',':')));results[name]=data
 group=defaultdict(list)
 for kind,name in [('SIGNAL','event_deltas.json'),('A_OWN1S','baseline_A_outcomes.json'),('B_TIMEGRID','baseline_B_outcomes.json')]:
  for x in results[name]:
   if x.get('hold_seconds')!=15 or x.get('delay_ms')!=0:continue
   key=(kind,x.get('family','NO_SIGNAL_SELECTION'),x['asset'],x.get('action','WAIT'),x['fee_each_side_bps'],x['control13_cohort'],x['phase014_cohort']);group[key].append(x)
 summary=[]
 for k,data in group.items():summary.append({**dict(zip(['kind','family','asset','action','fee_each_side_bps','control13_cohort','phase014_cohort'],k)),'stats':replication.stats(data)})
 (B/'cohort_primary_summary.json').write_text(json.dumps(summary,separators=(',',':')));r=json.loads((B/'results.json').read_text());r.update(status='CLOSED_FIXED_SIX_ASSET_EPISODE_WITH_FROZEN_RULES_AND_VERSIONED_CONTROLS',assets=p['assets'],cohorts={'signal_events':dict(Counter((x['control13_cohort']+'|'+x['phase014_cohort']) for x in events)),'B_grid_events':dict(Counter((x['control13_cohort']+'|'+x['phase014_cohort']) for x in be))},control13_OS_cut=None,no_backfilled_OS_cut=True,LEAD_only=['ETH-USDT-SWAP','SOL-USDT-SWAP'],not_full_blind_OOS=True);(B/'results.json').write_text(json.dumps(r,indent=2));print({'cohorts':r['cohorts']})
if __name__=='__main__':main()
