from pathlib import Path
import json,gzip,datetime,calendar
B=Path(__file__).resolve().parent
p=json.loads((B/'protocol.json').read_text());cut=json.loads((B/'cohort_cut.json').read_text());d=datetime.datetime.fromisoformat(cut['phase013_control_cut_utc']);old=calendar.timegm(d.utctimetuple())*1000000000+d.microsecond*1000
events=json.loads((B/'events.json').read_text())+json.loads((B/'baseline_B_events.json').read_text());wanted={e['asof_ordinal'] for e in events};raw={}
with gzip.open(Path(p['source'])/'raw/ws_messages.jsonl.gz','rb') as f:
 for line in f:
  r=json.loads(line)
  if r['local_ordinal'] in wanted:raw[r['local_ordinal']]=r
for e in events:
 r=raw[e['asof_ordinal']];assert e['source_receive_wall_ns']==r['receive_wall_ns'] and e['source_asof_shared_ns']==r['os_shared_ns'];assert e['control13_cohort']==('POST_CONTROL13_WALL_FREEZE' if r['receive_wall_ns']>=old else 'PRE_CONTROL13_WALL_FREEZE_DEVELOPMENT');assert e['phase014_cohort']==('POST_PHASE014_CODE_SHARED_CUT' if r['os_shared_ns']>=cut['phase014_cut_OS_shared_ns'] else 'PRE_PHASE014_CODE_CUT')
assert cut['phase013_control_cut_OS_shared_ns'] is None
receipt={'status':'PASS_FINITE_ACTUAL_RAW_COHORT_BINDING','signal_and_grid_asof_checks':len(events),'exact_calendar_wall13_cut':old,'phase14_actual_shared_cut':cut['phase014_cut_OS_shared_ns'],'no_backfilled13_OS':True,'raw_source_clock_namespaces_unchanged':True,'not_independent_strategy_replay':True};(B/'cohort_audit.json').write_text(json.dumps(receipt,indent=2));print(receipt)
