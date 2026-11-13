import json,hashlib,datetime,time
from pathlib import Path
P=Path(__file__).resolve().parent;B=P.parent
SOURCES=[]
def read(path):
 p=B/path;data=p.read_bytes();SOURCES.append({'path':str(p),'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data)});return json.loads(data)
def txt(path):
 p=B/path;data=p.read_bytes();SOURCES.append({'path':str(p),'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data)});return data.decode()
def main():
 f=json.loads((P/'execution_freeze.json').read_text())
 for n,h in f['hashes'].items():assert hashlib.sha256((P/n).read_bytes()).hexdigest()==h
 selection=txt('PMO_SELECTION_ORDER.md');requirements=read('PMO_REQUIREMENT_GATES.json');episodes=[];primary=[]
 configs=[('010_job004_evaluation','PMO_PHASE010_ACCEPTANCE.json','primary_summary.json'),('013_job005_replication_controls','PMO_PHASE013_ACCEPTANCE.json','all_signal_summary.json'),('014_closed_job006_universe_comparison','PMO_PHASE014_ACCEPTANCE.json','all_signal_summary.json'),('017_job007_costshock_evaluation','PMO_PHASE017_ACCEPTANCE.json','all_signal_summary.json'),('020_job008_fixed_rule_evaluation','PMO_PHASE020_CLOSED_EVALUATION_ACCEPTANCE.json','all_signal_summary.json')]
 for name,accept,summary in configs:
  phase='phase'+name;r=read(phase+'/results.json');a=read(accept);rows=read(phase+'/'+summary);entry={'stage':phase,'PMO_acceptance':str(B/accept),'status':r['status'],'event_counts':r['event_counts'],'actual_AI':r.get('actual_AI',r.get('actual_AI_results')),'full_result':r,'primary_groups':[]}
  for row in rows:
   if row.get('hold_seconds')!=15 or row.get('delay_ms')!=0:continue
   assert row['fee_each_side_bps'] in [5,10]
   key={k:row[k] for k in ['family','asset','action','fee_each_side_bps']};key.update(cohort=phase,hold_seconds=15,delay_ms=0,capacity_USDT=500)
   if 'stats' in row:
    stats=row['stats'];obs=stats.get('statuses',{}).get('observed',0);unknown=stats['unknown_or_censored'];pos=round((stats.get('positive_fraction') or 0)*obs)
   else:
    obs=row['observed'];unknown=row['censored'];stats=row['price_fee_delta_USDT'];pos=round((stats.get('positive_fraction') or 0)*obs)
   out={**key,'observed':obs,'censored_UNKNOWN':unknown,'observed_positive_count':pos,'statistics_original':stats,'original_summary_path':str(B/phase/summary)};primary.append(out);entry['primary_groups'].append(out)
  entry['primary_counts_by_fee']={fee:{'observed':sum(x['observed'] for x in entry['primary_groups'] if x['fee_each_side_bps']==fee),'censored_UNKNOWN':sum(x['censored_UNKNOWN'] for x in entry['primary_groups'] if x['fee_each_side_bps']==fee),'observed_positive_count':sum(x['observed_positive_count'] for x in entry['primary_groups'] if x['fee_each_side_bps']==fee)} for fee in [5,10]}
  entry['counts_only_not_sum_of_returns']=True;episodes.append(entry)
 zero=[]
 for phase in ['phase017_job007_costshock_evaluation','phase020_job008_fixed_rule_evaluation']:
  rows=read(phase+'/costshock_all_summary.json');chosen=[r for r in rows if r.get('hold_seconds')==15 and r.get('delay_ms')==0];zero.append({'stage':phase,'family':'COST_CAPABLE_SHOCK_V1_FOLLOW_FADE','primary_original_groups':chosen,'events':0,'return':None,'future_income_path':'NOT_OBSERVED'})
 for phase,accept in [('phase027_closed_probe_analysis_preparation','PMO_PHASE027_ACCEPTANCE.json'),('phase029_fresh_pressure_replication_preparation','PMO_PHASE029_ACCEPTANCE.json')]:
  r=read(phase+'/results.json');a=read(accept);ss=read(phase+'/pressure_actual_full_summary.json');zero.append({'stage':phase,'family':'CONTINUATION_FOLLOW_V1_PRESSURE_DECAY_FADE_V1','source_status':r['status'],'result_original':r,'primary_original_groups':[x for x in ss if x['hold_seconds']==15 and x['delay_ms']==0],'events':0,'return':None,'future_income_path':'NOT_OBSERVED'})
 context={}
 for phase,accept in [('phase021_primary_cost_attribution','PMO_PHASE021_ACCEPTANCE.json'),('phase023_incremental_state_preparation','PMO_PHASE023_ACCEPTANCE.json'),('phase027_closed_probe_analysis_preparation','PMO_PHASE027_ACCEPTANCE.json'),('phase032_closed_asof_gate_coverage','PMO_PHASE032_ACCEPTANCE.json')]:
  context[phase]={'result':read(phase+'/results.json'),'acceptance':read(accept)}
 provider=txt('PMO_PROVIDER_CONTRACT.md');compatible=read('PMO_PROVIDER_STATE_COMPATIBILITY.json')
 controls=[]
 for name,accept,summary in configs[1:]:
  phase='phase'+name;controls.append({'stage':phase,'A_same_signal_own1s':read(phase+'/primary_vs_A_summary.json'),'B_fixed35s_seed':read(phase+'/B_timegrid_summary.json'),'interpretation':'A own momentum reference WAITtruezero vsUNKNOWN; B unconditionaltimebenchmark notmatchedrandomized trial; overlappingclusters/nonindependentN'})
 result={'status':'RESEARCH_EVIDENCE_LEDGER_NOT_FINAL_DEADLINE','at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'selection_rule_original':selection,'requirements_current_snapshot':requirements,'episodes':episodes,'primary_groups':primary,'new_rules_zero_event_null':zero,'context':context,'controls':controls,'provider_contract_snapshot':provider,'legacy_provider_compatibility_snapshot':compatible,'actual_provider_calls':0,'AI_latency_gain':None,'job010':{'status':'PENDING_RUNNING_NO_RESULT_READ','source_run':'phase006-65623-1791328168','PID':65623,'session':83585,'scheduled_stop_UTC':'2026-10-06T23:54:28.963429+00:00','results':None},'qualification':'NO_QUALIFIED_FAST_AI_PROFIT_ROUTE','next_economic_route':'Frozen pressure/cost-space hypothesis observation only; newcohort pending, no positive edge yet; do not relaxgate orrankzeroevents asreturns','comparable':'samecohort/asset/family/hold15/delay0/fee distinct FOLLOWvsFADE descriptive; A sameasof ownmomentum; B separatefrequency benchmark; fee sensitivity notwinnerselection','not_comparable':'no跨source资产actionfeehold收益相加; qty-mismatch notsameqty; funding/privatefees/margin未验; noeventnull notWAITincome; manualdelaynotAI; localprocessingnotmodel/API/NIC/order latency; newthreeproviderregistryNOTVALIDATED','globalgoal':'ACTIVE','sources':SOURCES}
 (P/'ledger.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps({'episodes':len(episodes),'primary_groups':len(primary),'zero_event_groupsets':len(zero),'sources':len(SOURCES)}))
if __name__=='__main__':main()
