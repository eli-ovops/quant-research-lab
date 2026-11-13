from pathlib import Path
import json,hashlib,datetime,csv
P=Path(__file__).resolve().parent;OLD=P.parent
sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
def save(n,v):(P/n).write_text(json.dumps(v,indent=2))
x=json.loads((P/'results_all.json').read_text());rr=x['scenarios'];dec=json.loads((P/'candidate_decisions.json').read_text());audit=json.loads((P/'independent_validation.json').read_text());freeze=json.loads((P/'analysis_freeze.json').read_text())
assert len(rr)==120 and len({r['id'] for r in rr})==120
assert sum(r['mode']=='trend' for r in rr)==108 and sum(r['status']=='COMPUTED_VALIDATED' for r in rr)==80
assert len(audit['scenarios'])==80 and all(r['pass'] for r in audit['scenarios'])
for r in rr:
 p=r['period'];assert len(r['slices']['yearly'])=={'early':3,'middle':2,'latest':2}[p] and len(r['slices']['rolling'])=={'early':11,'middle':7,'latest':5}[p]
 if p=='early':assert all(v is None for v in r['metrics'].values())
assert len(dec)==9 and all(d['full_candidate_pass'] is None and d['checks']['at_least5of7_positive_calendar_slices']=='UNKNOWN' for d in dec)
assert all(float(r['metrics']['net_pnl'])<0 for r in rr if r['period']=='latest' and r['mode']=='trend')
for n,h in freeze['files'].items():assert sha(P/n)==h,n
for n,h in freeze['reused_inputs'].items():assert sha(Path(n))==h,n
oldproof=[]
for folder in [OLD,OLD/'resume_implementation_20260926',OLD/'full_history_20260926']:
 seal=json.loads((folder/'seal.json').read_text());assert sha(folder/'manifest.json')==seal['manifest_sha256'];manifest=json.loads((folder/'manifest.json').read_text())
 for r in manifest['files']:assert sha(folder/r['path'])==r['sha256'],r['path']
 oldproof.append({'directory':str(folder),'manifest_sha256':seal['manifest_sha256'],'files_verified':len(manifest['files']),'unchanged':True})
save('integrity_check.json',{'UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'new_frozen_files_verified':len(freeze['files']),'reused_inputs_verified':len(freeze['reused_inputs']),'old_sealed_artifacts':oldproof,'authority_note':'Current PMO task has authorized supplement: current hash recorded in authority.json; prior source snapshots may record prior task hash. No claim all historical external-source hashes unchanged.','scenario_and_slice_counts_pass':True,'visual_check':'heatmaps and primary equity inspected: readable, early grayN/A, all9 unchanged, primary24/4 retained'})
prior=json.loads((OLD/'full_history_20260926'/'trial_ledger.json').read_text());save('trial_ledger.json',{'prior_ledger_path':str(OLD/'full_history_20260926'/'trial_ledger.json'),'prior_ledger_sha256':sha(OLD/'full_history_20260926'/'trial_ledger.json'),'known_prior_market_scenarios':27,'V2_historical_trend_scenarios':72,'V2_historical_hold_scenarios':8,'V2_not_evaluated':40,'all_fixed_candidates':9,'planned_trend':108,'planned_hold':12,'historical_analysis_attempts_this_stage':1,'all80_independent_replays':True,'targeted_gate_tests':'pre_pnl_tests.json; no repeated unchanged synthetic suite','new_network_calls':0,'previous_visible_market_calls':prior['visible_total'],'previous_announcement_queries':9,'conservative_visible_budget_total':403,'internal_HTTP_and_human_search_total':'UNKNOWN','classification':'EXPLORATORY_REUSED_HISTORY','rule_changed':False,'missing_policy_frozen_before_outcomes':True})
items=[
('1_product_identity','PARTIAL','Saved request endpoint/parameters, overlap and daily reconciliation support BTC/ETH spot attribution; raw response does not echo instrument/bar','source_gate.py; input_gate.json','Historical rule/listTime/migration and regional eligibility UNKNOWN'),
('2_data','PARTIAL','Middle/latest complete with80warmup each; early full grid but zero/price/volume gate FAILED','input_gate.json; ../full_history_20260926/period_quality.json','Early36+4 remain null; anomaly cause UNKNOWN'),
('3_execution','CONDITIONAL_ONLY','All80 independent nextopen/adverse price model; four cost/delay conditions','runs/; independent_validation.json','Historical spread/depth/impact/queue/partial fill/latency/outages UNKNOWN; real fills0'),
('4_costs','MODEL_VALIDATED','Base-fee buys and quote-fee sells; fee rounding/slippage/tick/dust independent41 metric fields','independent_validation.json; runs/*/independent_metrics.json','Actual fee tier/precision/spec history UNKNOWN; no actual infrastructure/labor/tax/opportunity costs'),
('5_cash_inventory','MODEL_VALIDATED','2000shared/400reserve/800buycap; rejected sells held; pending and terminal inventory independently reconciled','runs/*/independent_events.json; independent_curve.json.gz','Real inventory0; venue/stablecoin tail risks UNKNOWN; leverage/funding/liquidation/ADL N/A in spot model'),
('6_pnl','72_PLUS8_VALIDATED','Separate period paths; net attribution and cash/hold excess; all120 retained','results_all.json; summary.csv','Conditional USDT after assumed transaction costs, before tax/overheads; not take-home profit'),
('7_risk','KNOWN_FAILURES','DD/recovery/tails/holding/exposure/clusters/winners measured; primary latest DD46.26pct','candidate_decisions.json; results_all.json','Early risk null; user budget and real emergency execution UNKNOWN'),
('8_statistics','EXPLORATORY','Original9 synchronized30day2000rep family interval; annual4observed+3null; rolling12observed+11null','family_intervals.json; results_all.json; trial_ledger.json','No candidate PASS; reused history; broader selection UNKNOWN; not forward/unseen'),
('9_reproducibility','OWNER_VALIDATED_A_PENDING','PrePnL code/config/display freeze; raw-second implementation all80; frozen sources and old artifacts hashchecked','analysis_freeze.json; first_real_PnL_run.json; integrity_check.json','Independent reviewer A pending; shared protocol assumptions remain')]
with (P/'coverage.csv').open('w',newline='') as f:
 w=csv.writer(f);w.writerow(['item','status','method_scope','evidence','remaining_unknown']);w.writerows(items)
save('status.json',{'UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'owner':'C','stage':'COMPUTATION_COMPLETE_STOPPED_FOR_A','principal':'72/108','hold':'8/12','early':'36+4 NOT_EVALUATED null','independent_replay':'80/80 PASS','all9_latest_all4_pnl_negative':True,'known_visible_requirements':'All9 FAIL','full_candidate_and_true_feasibility':'INSUFFICIENT_EVIDENCE','reviewer_A':'PENDING','network_calls':0,'real_orders':0,'analysis_freeze_sha256':sha(P/'analysis_freeze.json')})
print('Package validation complete',len(rr),'scenarios',sum(r['hourly_states'] for r in audit['scenarios']),'hourly states',sorted(set(r['independent_metric_fields'] for r in audit['scenarios'])),'metric fields')
