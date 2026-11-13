"""Reproduce unchanged matched-control estimand and explain support selection."""
import json,collections,statistics as st,hashlib,datetime,math
from pathlib import Path
import study as s,regime as g,warmup_diagnostic as w
P=Path(__file__).resolve().parent;OUT=P/'control-audit-20261005'
def mean(v):return st.mean(v) if v else None

def compare(rs,targets):
 controls=collections.defaultdict(list)
 for r in rs:
  if r['regime']=='down' and not r['signal']:controls[(r['month'],r['hour'])].append(r)
 supported=[];unsupported=[]
 for r in targets:
  cc=controls[(r['month'],r['hour'])]
  item=dict(r,control_n=len(cc),net_bps=s.net(r['gross'],.002,.001))
  if len(cc)>=5:
   cm=st.mean(s.net(x['gross'],.002,.001) for x in cc)
   item.update(control_mean_bps=cm,excess_bps=item['net_bps']-cm);supported.append(item)
  else:unsupported.append(item)
 return dict(n=len(targets),supported_n=len(supported),support=len(supported)/len(targets) if targets else 0,
  all_mean_bps=mean([s.net(r['gross'],.002,.001) for r in targets]),
  supported_mean_bps=mean([r['net_bps'] for r in supported]),
  matched_control_mean_bps=mean([r['control_mean_bps'] for r in supported]),
  excess_bps=mean([r['excess_bps'] for r in supported]),unsupported_mean_bps=mean([r['net_bps'] for r in unsupported])),supported,unsupported

def main():
 OUT.mkdir(exist_ok=False)
 proto=json.loads((P/'cross-asset-01/protocol.json').read_text())
 freeze={'date':'2026-10-05','scope':'8 assets fixed72h zero-delay; original >=5 controls same month/hour/down regime; full and greedy nonoverlap populations separately',
 'classification':'SUPPLEMENTARY_REUSED_HISTORY_NOT_PRIMARY_GATE_ACCEPTED','change_to_signal_or_matching_threshold':False,
 'cost':'stress each side20bps fee+10bps slippage','missing_support':'Excluded from comparison only; retained and reported separately',
 'code_hashes':{n:hashlib.sha256((P/n).read_bytes()).hexdigest() for n in ['control_audit.py','study.py','regime.py','warmup_diagnostic.py']}}
 s.system.engine.dump(OUT/'protocol.json',freeze)
 start=int(datetime.datetime.fromisoformat(proto['start_including_warmup']).timestamp()*1000);end=int(datetime.datetime.fromisoformat(proto['end_exclusive']).timestamp()*1000)
 raw,proof=s.system.source_gate.load();previous=json.loads((P/'cross-asset-diagnostic-01/results.json').read_text());manifest=json.loads((P/'cross-asset-01/manifest.json').read_text())
 hashes={r['path']:r['sha256'] for r in manifest['files']}
 allresults=[]
 for coin in proto['reference_assets']+proto['new_assets']:
  if coin in raw:rows=list(raw[coin].values())
  else:
   rows=[]
   for f in sorted((P/'cross-asset-01/raw').glob(coin+'_[0-9][0-9][0-9].json')):
    assert hashlib.sha256(f.read_bytes()).hexdigest()==hashes[str(f.resolve())]
    rows+=json.loads(f.read_text())['data']['data']
  d=w.diagnostic_gate(rows,start,end);bars=s.features([d[t] for t in sorted(d)]);rs=g.records(bars,72);events=[r for r in rs if r['signal'] and r['regime']=='down']
  original=g.evaluate(rs,'down')[0];old=next(r for r in previous['results'] if r['coin']==coin and r['delay_hours']==0)
  assert abs(original['matched_support']-old['zero_delay_matched_support'])<1e-12
  assert abs(original['matched_excess_bps']-old['zero_delay_matched_excess_bps'])<1e-8
  for label,targets in [('all',events),('nonoverlap',g.nonoverlap(events))]:
   result,sup,unsup=compare(rs,targets)
   # Separate direct scan verifies group selection and weighted excess, no shared lookup.
   deltas=[]
   for r in targets:
    cc=[x for x in rs if not x['signal'] and x['regime']=='down' and x['month']==r['month'] and x['hour']==r['hour']]
    if len(cc)>=5:
     # Difference between equal-cost long cash ratios.
     factor=(1-.001)/ (1+.001)*(.998**2)*10000
     deltas.append((r['gross']-sum(x['gross'] for x in cc)/len(cc))*factor)
   assert len(deltas)==result['supported_n']
   if deltas:assert abs(st.mean(deltas)-result['excess_bps'])<1e-8
   result.update(coin=coin,population=label,yearly={str(y):compare(rs,[r for r in targets if r['year']==y])[0] for y in [2023,2024,2025,2026]})
   allresults.append(result);s.system.engine.dump(OUT/f'{coin}_{label}_pairs.json',{'supported':sup,'unsupported':unsup})
 for n,h in freeze['code_hashes'].items():assert hashlib.sha256((P/n).read_bytes()).hexdigest()==h
 s.system.engine.dump(OUT/'results.json',{'rows':allresults,'independent_direct_scan':'PASS','original_support_and_excess_reproduced':True,'promotion':'NONE'})
 def f(v):return 'N/A' if v is None else f'{v/100:.3f}%'
 lines=['# 无信号对照复核','', '同月、同UTC小时、同下跌状态，至少5个无信号对照；不降低门槛。持有72小时，零额外延迟，压力成本。', '',
 '|币|样本组|总数|有对照数|全部均值|有对照信号均值|匹配对照均值|信号超额|无足够对照均值|', '|---|---|---:|---:|---:|---:|---:|---:|---:|']
 for r in allresults:lines.append(f"|{r['coin']}|{r['population']}|{r['n']}|{r['supported_n']}|{f(r['all_mean_bps'])}|{f(r['supported_mean_bps'])}|{f(r['matched_control_mean_bps'])}|{f(r['excess_bps'])}|{f(r['unsupported_mean_bps'])}|")
 lines+=['','## LTC 去重组分年','']
 ltc=next(r for r in allresults if r['coin']=='LTC' and r['population']=='nonoverlap')
 for y,r in ltc['yearly'].items():lines.append(f"- {y}：{r['n']}次，{r['supported_n']}次有足够对照；信号{f(r['supported_mean_bps'])}，对照{f(r['matched_control_mean_bps'])}，超额{f(r['excess_bps'])}。")
 lines+=['','## 核验与边界','',
 '8币原匹配支持率与原超额全部复现；用独立逐项扫描与直接现金比例差公式核对16组结果。没有改变任何信号或对照数量门槛。',
 '同一对照可被多个信号复用，未来持有窗口可重叠，不能将数量视为独立统计样本；不计算显著性或胜出概率。',
 '有对照子样本的负超额不证明全部信号无效；无足够对照部分保持UNKNOWN，不能假设它们的超额为零或沿用有对照结论。',
 '匹配未消除全部波动/跌幅混杂。对照未来收益只是事后研究基准，绝不输入交易决策。',
 '预热零量导致原数据门槛仍未通过，本文件继承补充诊断身份。数据是2023至2026上半年，2026仅半年；没有新增样本外信息、合约模型或账户收益。',
 '新建脚本、协议、逐项配对和报告均用于复现与验收，保留。未下单、未联网取行情、未重启轮询。']
 (OUT/'REPORT.md').write_text('\n'.join(lines)+'\n');print('\n'.join(lines[:24]))
if __name__=='__main__':main()
