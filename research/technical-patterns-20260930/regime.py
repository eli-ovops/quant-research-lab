"""Predefined regime test of Bollinger re-entry; no optimization or network."""
import study as s
from pathlib import Path
import statistics as st,json,hashlib,datetime,collections
P=Path(__file__).resolve().parent

def regime(bars,i):
 if i<21:return None
 # Ends BEFORE signal bar, so the trigger rebound cannot change the regime.
 c=[b['c'] for b in bars[i-21:i]]
 move=c[-1]-c[0];path=sum(abs(b-a) for a,b in zip(c,c[1:]))
 er=abs(move)/path if path else 0
 return ('range' if er<.30 else 'up' if move>0 else 'down'),er

def summarize(rs):
 v=[s.net(r['gross']) for r in rs]
 return {'n':len(rs),'mean_bps':st.mean(v) if v else None,'median_bps':st.median(v) if v else None,
 'stress_mean_bps':st.mean(s.net(r['gross'],.002,.001) for r in rs) if rs else None,
 'loss_fraction':sum(x<0 for x in v)/len(v) if v else None,
 'p05_bps':sorted(v)[int((len(v)-1)*.05)] if v else None}

def records(bars,h):
 result=[];n=h//4
 for i in range(130,len(bars)-n-1):
  enter=bars[i+1];exit=bars[i+1+n]
  if exit['t']-enter['t']!=h*s.H:raise ValueError('gap')
  dt=datetime.datetime.fromtimestamp(enter['t']/1000,datetime.timezone.utc)
  if dt.year<2023:continue
  r,er=regime(bars,i)
  result.append(dict(t=enter['t'],exit_t=exit['t'],year=dt.year,month=dt.strftime('%Y-%m'),hour=dt.hour,
   regime=r,er=er,signal=bars[i]['signals']['bollinger'],gross=exit['o']/enter['o']-1))
 return result

def nonoverlap(rs):
 keep=[];due=-1
 for r in rs:
  if r['t']>=due:keep.append(r);due=r['exit_t']
 return keep

def evaluate(rs,state):
 events=[r for r in rs if r['signal'] and r['regime']==state]
 controls=collections.defaultdict(list)
 for r in rs:
  if not r['signal'] and r['regime']==state:controls[(r['month'],r['hour'])].append(s.net(r['gross']))
 matched=[]
 for r in events:
  cc=controls[(r['month'],r['hour'])]
  if len(cc)>=5:matched.append(s.net(r['gross'])-st.mean(cc))
 yearly={str(y):summarize([r for r in events if r['year']==y]) for y in [2023,2024,2025,2026]}
 de=nonoverlap(events);out=dict(regime=state,**summarize(events),nonoverlap=summarize(de),yearly=yearly,
  matched_n=len(matched),matched_support=len(matched)/len(events) if events else 0,
  matched_excess_bps=st.mean(matched) if matched else None)
 failures=[]
 if len(events)<30:failures.append('fewer_than30_events')
 if len(de)<20:failures.append('fewer_than20_nonoverlapping_events')
 if out['stress_mean_bps'] is None or out['stress_mean_bps']<=0:failures.append('stress_mean_not_positive')
 if out['nonoverlap']['stress_mean_bps'] is None or out['nonoverlap']['stress_mean_bps']<=0:failures.append('nonoverlap_stress_not_positive')
 if sum(v['n']>=10 and v['mean_bps']>0 for v in yearly.values())<3:failures.append('fewer_than3_positive_years_with10_events')
 if out['matched_support']<.8:failures.append('matched_support_below80pct')
 if not matched or st.mean(matched)<=0:failures.append('no_positive_matched_excess')
 out['screen_failures']=failures;out['screen_pass']=not failures
 return out,events

def main():
 out=P/'regime-01';out.mkdir(exist_ok=False)
 proto={'status':'EXPLORATORY_REUSED_HISTORY','rule':'Bollinger20 populationSD2 reentry long; 4h',
 'state':'ER20 close differences ending before signal bar; <0.30 range; otherwise sign up/down',
 'horizons':[24,72],'assets':['BTC','ETH'],'parameters_searched':False,
 'fees_slippage':'baseline each side10+5bps; stress20+10bps',
 'screen':'Both coins per horizon: n>=30, nonoverlap>=20, stress mean>0 and nonoverlap stress>0, >=3 years n>=10 and base mean>0, same month/hour/regime control support>=80% and excess>0',
 'scope':'Descriptive screen only, no statistical significance or causal/portfolio profitability claim; no new holdout',
 'code_sha256':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(__file__),P/'study.py']},
 'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
 s.system.engine.dump(out/'protocol.json',proto)
 raw,proof=s.system.source_gate.load();merged={c:{} for c in ['BTC','ETH']}
 for period in ['middle','latest']:
  selected,a,z,checks=s.system.source_gate.for_period(raw,period)
  for c in merged:merged[c].update({int(r[0]):r for r in selected[c]})
 results=[]
 for c,d in merged.items():
  bars=s.features([d[t] for t in sorted(d)])
  for h in [24,72]:
   rs=records(bars,h)
   for state in ['range','up','down']:
    r,ev=evaluate(rs,state);r.update(coin=c,horizon=h);results.append(r)
    s.system.engine.dump(out/f'{c}_{h}_{state}_events.json',ev)
 passes=[h for h in [24,72] if all(r['screen_pass'] for r in results if r['regime']=='range' and r['horizon']==h)]
 s.system.engine.dump(out/'results.json',{'source':proof,'results':results,'range_cross_asset_screen_pass_horizons':passes,'validated_profitability':None})
 def fmt(v):return 'N/A' if v is None else f'{v:.2f}'
 lines=['# 布林回归与市场状态','', '结论：震荡状态跨币筛选通过的持有时长：'+str(passes)+'。筛选通过也不等于独立验证通过。','',
 '|币|小时|状态|样本|费后均值bps|压力均值bps|不重叠样本|不重叠压力bps|匹配支持率|匹配超额bps|', '|---|---:|---|---:|---:|---:|---:|---:|---:|---:|']
 for r in results:
  lines.append(f"|{r['coin']}|{r['horizon']}|{r['regime']}|{r['n']}|{fmt(r['mean_bps'])}|{fmt(r['stress_mean_bps'])}|{r['nonoverlap']['n']}|{fmt(r['nonoverlap']['stress_mean_bps'])}|{r['matched_support']:.1%}|{fmt(r['matched_excess_bps'])}|")
 lines+=['','range=震荡；up=上涨趋势；down=下跌趋势。均为信号之前的状态。','', '## 分年与筛选失败原因','']
 for r in results:
  ys='；'.join(f"{y}: n={v['n']}, {fmt(v['mean_bps'])}bps" for y,v in r['yearly'].items())
  lines.append(f"- {r['coin']} {r['horizon']}h {r['regime']}：{ys}。失败项：{r['screen_failures']}")
 lines+=['','## 边界','',
 '数据截至2026年6月底，2026只是半年；最初130根4h作为指标预热，首段不是完整2023年。状态阈值未搜索，策略来自此前结果，故整体仍有研究选择偏差。',
 '这只是单一ER20状态定义，失败不能证明任何震荡过滤都无效。无信号对照按同月/小时/状态匹配，仅保留至少5个对照的事件；支持不足即拒绝筛选。',
 '去重检查按时间贪心保留、不叠加同币事件；不是完整组合，不同状态各自独立。费用为假设，真实成交、合约资金费/强平未模拟。',
 '没有做显著性检验、状态交互因果推断或全量第二实现回放，不给盈利概率。不重启轮询，不自动优化下一轮。']
 (out/'REPORT.md').write_text('\n'.join(lines)+'\n')
 print('\n'.join(lines[:19]))
if __name__=='__main__':main()
