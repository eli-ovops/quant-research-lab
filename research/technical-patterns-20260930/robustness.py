"""Audit existing downtrend rebound hypothesis; no parameter search."""
import study as s
from pathlib import Path
import json,hashlib,math,statistics as st,datetime
P=Path(__file__).resolve().parent

def independent_events(rows):
 d={int(r[0]):r for r in rows};bars=[]
 for t in sorted(d):
  if t%(4*s.H)==0 and all(t+j*s.H in d for j in range(4)):
   bars.append((t,float(d[t][1]),float(d[t+3*s.H][4])))
 def band(i):
  v=[b[2] for b in bars[i-19:i+1]];m=sum(v)/20
  return m-2*math.sqrt(sum((x-m)**2 for x in v)/20)
 ev=[]
 for i in range(130,len(bars)-19):
  past=[b[2] for b in bars[i-21:i]];change=past[-1]-past[0];path=sum(abs(past[j]-past[j-1]) for j in range(1,21))
  if change>=0 or not path or abs(change)/path<.30:continue
  if not (bars[i-1][2]<band(i-1) and bars[i][2]>=band(i)):continue
  t=bars[i+1][0]
  if datetime.datetime.fromtimestamp(t/1000,datetime.timezone.utc).year<2023:continue
  ev.append({'t':t,'exit_t':bars[i+19][0],'gross':bars[i+19][1]/bars[i+1][1]-1})
 return ev

def summary(events):
 v=[e['stress_bps'] for e in events];n=len(v)
 def mean(a):return st.mean(a) if a else None
 ordered=sorted(v)
 return {'n':n,'stress_mean_bps':mean(v),'base_mean_bps':mean([e['base_bps'] for e in events]),
 'stress_median_bps':st.median(v) if v else None,'worst_bps':min(v) if v else None,
 'p05_bps':ordered[int(.05*(n-1))] if v else None,
 'without_top5_stress_mean_bps':mean(ordered[:-5]),
 'without_bottom5_stress_mean_bps':mean(ordered[5:]),
 'loss_fraction':sum(x<0 for x in v)/n if n else None}

def main():
 out=P/'robustness-01';out.mkdir(exist_ok=False)
 proto={'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'evidence':'EXPLORATORY_REUSED_HISTORY',
 'hypothesis':'Existing downtrend ER20>=.30 Bollinger20/2 reentry, long72h',
 'delays_hours':[0,1,4],'delay_policy':'Both entry and exit shift; fixed72h holding; no future retrigger',
 'assets':['BTC','ETH'],'controls':'Original failed matching gates remain failed; not changed',
 'stress':'each side fee20bps+slippage10bps','base':'each side fee10bps+slippage5bps',
 'diagnostics':'greedy nonoverlap by actual execution time; symmetric delete5largest/delete5smallest stress returns; never executable strategies',
 'code_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
 'input_event_sha256':{c:hashlib.sha256((P/'regime-01'/f'{c}_72_down_events.json').read_bytes()).hexdigest() for c in ['BTC','ETH']}}
 s.system.engine.dump(out/'protocol.json',proto)
 raw,proof=s.system.source_gate.load();merged={c:{} for c in ['BTC','ETH']}
 for period in ['middle','latest']:
  selected,a,z,checks=s.system.source_gate.for_period(raw,period)
  for c in merged:merged[c].update({int(r[0]):r for r in selected[c]})
 results=[];audits=[]
 for c,d in merged.items():
  existing=json.loads((P/'regime-01'/f'{c}_72_down_events.json').read_text());rebuilt=independent_events(list(d.values()))
  assert [(r['t'],r['exit_t']) for r in existing]==[(r['t'],r['exit_t']) for r in rebuilt]
  assert all(abs(a['gross']-b['gross'])<1e-12 for a,b in zip(existing,rebuilt))
  audits.append({'coin':c,'events':len(existing),'timestamps_and_labels_match':True})
  for lag in [0,1,4]:
   ev=[];censored=0
   for e in existing:
    t=e['t']+lag*s.H;end=e['exit_t']+lag*s.H
    if t not in d or end not in d:censored+=1;continue
    buy=float(d[t][1]);sell=float(d[end][1])
    # Independently compute cash ratio, no study.net call.
    base=(sell*(1-.0005)*(.999**2)/(buy*(1+.0005))-1)*10000
    stress=(sell*(1-.001)*(.998**2)/(buy*(1+.001))-1)*10000
    ev.append(dict(t=t,exit_t=end,base_bps=base,stress_bps=stress))
   kept=[];due=-1
   for e in ev:
    if e['t']>=due:kept.append(e);due=e['exit_t']
   yearly={}
   for y in [2023,2024,2025,2026]:
    yearly[str(y)]=summary([e for e in kept if datetime.datetime.fromtimestamp(e['t']/1000,datetime.timezone.utc).year==y])
   r={'coin':c,'delay_hours':lag,'censored':censored,'all':summary(ev),'nonoverlap':summary(kept),'nonoverlap_yearly':yearly}
   results.append(r);s.system.engine.dump(out/f'{c}_delay{lag}_events.json',{'all':ev,'nonoverlap':kept})
 assert proto['code_sha256']==hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
 s.system.engine.dump(out/'results.json',{'audit':audits,'source':proof,'results':results,'promotion':'BLOCKED_ORIGINAL_GATES_UNCHANGED'})
 lines=['# 下跌后布林反弹：稳健性诊断','', '信号不变，固定持有72小时；仅检查延迟、事件重叠和极端收益影响。全部为现货历史探索。','',
 '|币|延迟h|不重叠事件|基础均值bps|压力均值bps|压力中位数bps|去掉最大5次后均值bps|去掉最小5次后均值bps|最差一次bps|', '|---|---:|---:|---:|---:|---:|---:|---:|---:|']
 for r in results:
  v=r['nonoverlap'];lines.append(f"|{r['coin']}|{r['delay_hours']}|{v['n']}|{v['base_mean_bps']:.2f}|{v['stress_mean_bps']:.2f}|{v['stress_median_bps']:.2f}|{v['without_top5_stress_mean_bps']:.2f}|{v['without_bottom5_stress_mean_bps']:.2f}|{v['worst_bps']:.2f}|")
 lines+=['','## 不重叠事件的年度压力成本均值','']
 for r in results:
  text='；'.join(f"{y}: {v['n']}次，{v['stress_mean_bps']:.2f}bps" if v['n'] else f'{y}: 无样本' for y,v in r['nonoverlap_yearly'].items())
  lines.append(f"- {r['coin']} 延迟{r['delay_hours']}小时：{text}")
 lines+=['','## 核验与解释','',
 '用另一套布林带、过去趋势状态及标签计算重建两币全部72h下跌状态事件，时间戳和收益标签一致。不是合约、组合账本或真实成交独立回放。',
 '去掉最好/最差5次是对称敏感性诊断，不是可执行过滤器，也不是策略否决的充分统计证据；趋势/反弹收益本来就可能偏斜。',
 '延迟成交使用之后1h/4h的小时开盘代理；退出同时顺延以保持72h。仍未包含订单失败、深度和真实延迟分布。',
 '原先对照样本支持不足、跨年份不稳定与缺少未见留出集等缺口全部保留。诊断不自动提升候选，不优化规则，不重启轮询。']
 (out/'REPORT.md').write_text('\n'.join(lines)+'\n');print('\n'.join(lines[:14]))
if __name__=='__main__':main()
