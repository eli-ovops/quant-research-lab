"""Fixed technical indicator event study; standard library, offline, no portfolio/order API."""
from pathlib import Path
import sys,json,math,statistics as st,random,hashlib,datetime,collections
P=Path(__file__).resolve().parent;ROOT=P.parents[1]
sys.path.insert(0,str(ROOT/'strategy_system'))
import system
H=3600000
RULES={'macd':'4h MACD EMA12-EMA26 crosses above EMA9 signal, MACD>0',
'bollinger':'4h close re-enters above lower SMA20-2 population SD band after previous close below previous band',
'stochastic':'4h K14 crosses above SMA3(K), previous K<20'}
def features(rows):
 bars=[]
 d={int(r[0]):r for r in rows}
 for t in sorted(d):
  if t%(4*H) or not all(t+j*H in d for j in range(4)):continue
  rr=[d[t+j*H] for j in range(4)]
  bars.append(dict(t=t,o=float(rr[0][1]),h=max(float(r[2]) for r in rr),l=min(float(r[3]) for r in rr),c=float(rr[-1][4])))
 closes=[];ks=[];hist=[];bands=[];ema12=ema26=ema9=None
 for i,b in enumerate(bars):
  c=b['c'];closes.append(c)
  ema12=c if ema12 is None else ema12+2/13*(c-ema12)
  ema26=c if ema26 is None else ema26+2/27*(c-ema26)
  macd=ema12-ema26;ema9=macd if ema9 is None else ema9+2/10*(macd-ema9);hist.append(macd-ema9)
  bands.append(st.mean(closes[-20:])-2*st.pstdev(closes[-20:]) if i>=19 else None)
  last=bars[max(0,i-13):i+1];hi=max(x['h'] for x in last);lo=min(x['l'] for x in last)
  ks.append(50 if hi==lo else 100*(c-lo)/(hi-lo))
  b['signals']={name:False for name in RULES}
  if i>=130: # fixed long EMA warmup, no cross-period initialization
   b['signals']={'macd':hist[-2]<=0<hist[-1] and macd>0,
    'bollinger':closes[-2]<bands[-2] and c>=bands[-1],
    'stochastic':ks[-2]<=st.mean(ks[-4:-1]) and ks[-1]>st.mean(ks[-3:]) and ks[-2]<20}
 return bars

def net(g,fee=.001,slip=.0005):return ((1+g)*(1-slip)/(1+slip)*(1-fee)**2-1)*10000

def analyze(bars,name,horizon,coin):
 n=horizon//4; records=[]
 for i in range(130,len(bars)-n-1):
  b=bars[i];enter=bars[i+1];leave=bars[i+1+n]
  if leave['t']-enter['t']!=horizon*H:raise ValueError('gap')
  dt=datetime.datetime.fromtimestamp(enter['t']/1000,datetime.timezone.utc)
  if dt.year<2023:continue
  records.append(dict(t=enter['t'],month=dt.strftime('%Y-%m'),year=dt.year,hour=dt.hour,
   signal=b['signals'][name],gross=leave['o']/enter['o']-1))
 controls=collections.defaultdict(list)
 for r in records:
  if not r['signal']:controls[(r['month'],r['hour'])].append(net(r['gross']))
 events=[r for r in records if r['signal']];supported=[]
 for r in events:
  cc=controls[(r['month'],r['hour'])]
  if len(cc)>=5:supported.append(dict(r,delta=net(r['gross'])-st.mean(cc)))
 def summary(rs):
  vals=[net(r['gross']) for r in rs]
  return dict(n=len(rs),net_mean_bps=st.mean(vals) if vals else None,net_median_bps=st.median(vals) if vals else None,
    loss_fraction=sum(v<0 for v in vals)/len(vals) if vals else None,p05_bps=sorted(vals)[int(.05*(len(vals)-1))] if vals else None,
    gross_mean_bps=st.mean(r['gross']*10000 for r in rs) if rs else None,
    stress_mean_bps=st.mean(net(r['gross'],.002,.001) for r in rs) if rs else None)
 # Month cluster resampling keeps overlapping horizons together within month.
 months=sorted({r['month'] for r in records}); clusters={m:[r for r in supported if r['month']==m] for m in months}
 rng=random.Random(930);boot=[]
 for _ in range(5000):
  selected=[clusters[rng.choice(months)] for j in months];count=sum(len(v) for v in selected)
  if count:boot.append(sum(sum(r['delta'] for r in v) for v in selected)/count)
 boot.sort();alpha=.05/12
 ci=[boot[int((alpha/2)*(len(boot)-1))],boot[int((1-alpha/2)*(len(boot)-1))]] if len(boot)>=4900 else None
 return dict(coin=coin,indicator=name,horizon_hours=horizon,**summary(events),
  supported_n=len(supported),support_fraction=len(supported)/len(events) if events else 0,
  matched_excess_bps=st.mean(r['delta'] for r in supported) if supported else None,
  approximate_bonferroni_month_bootstrap_ci_bps=ci,bootstrap_draws=len(boot),
  yearly={str(y):summary([r for r in events if r['year']==y]) for y in sorted({r['year'] for r in records})}),events

def main():
 out=P/'run-01';out.mkdir(exist_ok=False)
 protocol=dict(rules=RULES,horizons_hours=[24,72],coins=['BTC','ETH'],parameter_search=False,
  evidence='EXPLORATORY_REUSED_HISTORY',entry='next 4h open',exit='fixed horizon open',
  fees_each_side_bps=10,slippage_each_side_bps=5,stress_fee_each_side_bps=20,stress_slippage_each_side_bps=10,
  total_tests=12,controls='same month and UTC entry hour, no same-indicator signal; minimum5',
  uncertainty='5000 month-cluster bootstrap, approximate Bonferroni12; conditional on fixed control means; not independent validation',
  interpretation='Overlapping events, not a portfolio; no short/funding/liquidation simulation',
  code_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
 system.engine.dump(out/'protocol.json',protocol)
 raw,proof=system.source_gate.load();result=[]
 for coin in ['BTC','ETH']:
  merged={}
  for period in ['middle','latest']:
   rr,a,z,checks=system.source_gate.for_period(raw,period)
   merged.update({int(r[0]):r for r in rr[coin]})
  bars=features([merged[t] for t in sorted(merged)])
  for name in RULES:
   for horizon in [24,72]:
    row,events=analyze(bars,name,horizon,coin);result.append(row)
    system.engine.dump(out/(coin+'_'+name+'_'+str(horizon)+'_events.json'),events)
    print(coin,name,horizon,row['n'],round(row['net_mean_bps'],2),flush=True)
 system.engine.dump(out/'results.json',{'source_proof':proof,'results':result})
 lines=['# 技术指标规律筛选','', '固定3种指标×2持有时长×2资产，共12项，不搜索参数。现货4h K线，仅探索已使用历史。',
 '每边10bps费+5bps滑点；压力为每边20bps费+10bps滑点。收益是单次信号条件均值，不是组合收益。', '',
 '|资产|指标|时长h|样本|费后均值bps|中位数bps|亏损比例|压力均值bps|对无信号超额bps|', '|---|---|---:|---:|---:|---:|---:|---:|---:|']
 for r in result:
  lines.append(f"|{r['coin']}|{r['indicator']}|{r['horizon_hours']}|{r['n']}|{r['net_mean_bps']:.2f}|{r['net_median_bps']:.2f}|{r['loss_fraction']:.1%}|{r['stress_mean_bps']:.2f}|{r['matched_excess_bps']:.2f}|")
 lines+=['','## 按年份检查','']
 for r in result:
  years='；'.join(f"{y}: n={v['n']}, {v['net_mean_bps']:.2f}bps" if v['n'] else f'{y}: 无样本' for y,v in r['yearly'].items())
  lines.append(f"- {r['coin']} {r['indicator']} {r['horizon_hours']}h：{years}。")
 lines+=['','## 不确定性和边界','',
 'results.json保留全部分年统计、5%尾部、匹配支持率及多重比较调整的近似区间。月聚类自助法保留部分重叠依赖，但边界跨月依赖和控制组均值不确定性未完整重采样；区间仅辅助描述，不能当显著性验收。',
 '同月同时段匹配不消除波动、趋势等状态混杂；正均值可能只是市场上涨。尚未做独立实现的指标/标签全量回放。',
 '事件可重叠；未建资金共享、库存、真实深度与失败模型，不能将事件收益累加。BTC/ETH选择存在资产选择偏差；历史已使用，无真正样本外。',
 '本轮不交易，不重启轮询。没有一个结果可仅凭本报告标为可盈利策略。']
 (out/'REPORT.md').write_text('\n'.join(lines)+'\n')
if __name__=='__main__':main()
