"""Supplementary only: quantify irrelevant pre-signal warmup anomalies. Not primary gate approval."""
from pathlib import Path
import json,datetime,copy
import cross_asset as a
P=Path(__file__).resolve().parent
original_gate=a.gate
proofs=[]
def diagnostic_gate(rows,start,end):
 selected=[r for r in rows if start<=int(r[0])<end]
 cut=int(datetime.datetime(2023,1,1,tzinfo=datetime.timezone.utc).timestamp()*1000)-84*a.s.H
 zero=[r for r in selected if float(r[5])==0]
 if not zero: return original_gate(rows,start,end)
 # Still reject zero volume within any admitted Bollinger/ER lookback or execution period.
 if any(int(r[0])>=cut for r in zero):raise ValueError('zero_inside_relevant_history')
 check=copy.deepcopy(rows)
 for r in check:
  if start<=int(r[0])<end and float(r[5])==0:r[5]='1'
 # Synthetic volume is ONLY for testing the other gate predicates, never passed to the strategy.
 original_gate(check,start,end)
 d={int(r[0]):r for r in selected};ordered=[d[t] for t in sorted(d)]
 events=a.b.independent_events(ordered)
 altered=copy.deepcopy(ordered)
 for r in altered:
  if int(r[0])<cut:
   for j in range(1,5):r[j]=str(float(r[j])*2)
 assert a.b.independent_events(altered)==events
 proofs.append({'zero_hours':len(zero),'latest_zero_ms':max(int(r[0]) for r in zero),'relevant_history_start_ms':cut,'earlier_prices_doubled_events_unchanged':True,'strategy_input_volume_unchanged':True})
 return d
if __name__=='__main__':
 out=P/'cross-asset-diagnostic-01';out.mkdir(exist_ok=False)
 (out/'raw').symlink_to('../cross-asset-01/raw',target_is_directory=True)
 proto=json.loads((P/'cross-asset-01/protocol.json').read_text());proto['status']='SUPPLEMENTARY_NOT_PRIMARY_GATE_APPROVED';proto['diagnostic']='Only zero volumes before all relevant signal lookbacks; no input bars changed; primary rejection remains'
 (out/'protocol.json').write_text(json.dumps(proto,ensure_ascii=False,indent=2))
 a.O=out;a.gate=diagnostic_gate;a.main()
 (out/'warmup_impact_proof.json').write_text(json.dumps(proofs,indent=2))
 report=out/'REPORT.md';report.write_text('# 补充诊断，非原门槛合格结果\n\n原始严格门槛仍拒绝含零量数据。本文件只检验：异常早于全部有效信号依赖时，保留真实原始数据所得的探索结果。禁止引用为已通过原验收。\n\n'+report.read_text())
