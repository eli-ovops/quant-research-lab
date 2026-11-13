"""Render all frozen outcomes without ranking or changing candidate rules."""
from pathlib import Path
import os,json,gzip,csv,datetime,math
P=Path(__file__).resolve().parent
os.environ['MPLCONFIGDIR']=str(P/'plot_runtime');import matplotlib
matplotlib.use('Agg');import matplotlib.pyplot as plt
x=json.loads((P/'results_all.json').read_text());rr=x['scenarios'];fam=json.loads((P/'family_intervals.json').read_text());dec=json.loads((P/'candidate_decisions.json').read_text());index={(r['period'],r['entry'],r['exit'],r['condition'],r['mode']):r for r in rr}
f=lambda v:float(v)
periods=['early','middle','latest'];conds=['baseline','fee2','slip20','delay1'];names={'early':'2020-2022','middle':'2023-2024','latest':'2025-2026H1'}
limit=max(abs(f(r['metrics']['net_pnl'])) for r in rr if r['mode']=='trend')
fig,axes=plt.subplots(3,4,figsize=(13,9),layout='constrained')
for i,p in enumerate(periods):
 for j,c in enumerate(conds):
  ax=axes[i,j];mat=[[f(index[(p,en,ex,c,'trend')]['metrics']['net_pnl']) for ex in [4,8,12]] for en in [24,48,72]];im=ax.imshow(mat,cmap='RdYlGn',vmin=-limit,vmax=limit)
  for y in range(3):
   for z in range(3):ax.text(z,y,f'{mat[y][z]:+.1f}',ha='center',va='center',fontsize=9,color='black')
  ax.set_xticks([0,1,2],[4,8,12]);ax.set_yticks([0,1,2],[24,48,72]);ax.set_title(names[p]+' / '+c);ax.set_xlabel('Exit lookback hours');ax.set_ylabel('Entry lookback hours')
fig.colorbar(im,ax=axes.ravel().tolist(),label='Conditional net PnL (USDT, separate 2000 starts)',shrink=.75);fig.suptitle('All 108 scenarios - EXPLORATORY REUSED HISTORY\nPrimary stays24/4; candle-open fills are conditional proxies',fontsize=12);fig.savefig(P/'heatmaps.png',dpi=160);fig.savefig(P/'heatmaps.pdf');plt.close(fig)
fig,axes=plt.subplots(1,3,figsize=(16,4),layout='constrained')
for ax,p in zip(axes,periods):
 for cond,mode in [(c,'trend') for c in conds]+[('baseline','hold')]:
  r=index[(p,24,4,cond,mode)];daily={}
  with gzip.open(P/'runs'/r['id']/'equity.csv.gz','rt') as fh:
   for v in csv.DictReader(fh):daily[int(v['t'])//86400000]=float(v['valuation_equity'])
  ax.plot([datetime.datetime.fromtimestamp(d*86400,datetime.timezone.utc) for d in daily],list(daily.values()),label=cond if mode=='trend' else 'fixed hold',linewidth=1)
 ax.axhline(2000,color='gray',linewidth=.7);ax.set_title(names[p]+' independent2000 start');ax.tick_params(axis='x',rotation=25);ax.set_ylabel('Conditional liquidation-value proxy / USDT');ax.legend(fontsize=7)
fig.suptitle('Primary24/4 vs fixed hold: unequal exposure and risk');fig.savefig(P/'primary_equity.png',dpi=160);plt.close(fig)
lines=['# 小时趋势V2：完整历史条件研究','', '**108个主要场景和12个持有基准均已计算并完成独立重算。真正可行性仍为INSUFFICIENT_EVIDENCE；全部属于复用历史探索，未验证真实成交或真正未见样本。**','', '## 24/4主候选','', '|期间|基线净额U|手续费压力U|滑点压力U|额外1h延迟U|基线最大回撤|固定持有基线U|','|---|---:|---:|---:|---:|---:|---:|']
for p in periods:
 rows=[index[(p,24,4,c,'trend')]['metrics'] for c in conds];hold=index[(p,24,4,'baseline','hold')]['metrics'];lines.append('|'+names[p]+'|'+'|'.join(f"{f(m['net_pnl']):+.2f}" for m in rows)+f"|{f(rows[0]['max_drawdown']):.2%}|{f(hold['net_pnl']):+.2f}|")
lines+=['','每段各从共享2000U开始，以上净额不可相加为连续账户收益。收益分母包括400U储备；单币买入最多800U，升值敞口可超过初始比例。次小时开盘只是条件成交代理，费用/滑点均为假设。末期按固定收盘强制退出影响最后日和年度切片，年度/滚动窗口内不重置持仓。','', '## 九窗口与固定门槛','', '|窗口|最新基线净额U|最新四条件均正|此前两段基线均正|最新年化算术超额家族95%区间|通过后续探索候选门槛|','|---|---:|---|---|---|---|']
for d in dec:
 en,ex=d['entry'],d['exit'];k=str(en)+'/'+str(ex);ci=fam['candidates'][k];m=index[('latest',en,ex,'baseline','trend')]['metrics'];latestpositive=all(f(index[('latest',en,ex,c,'trend')]['metrics']['net_pnl'])>0 for c in conds);earlier=all(f(index[(p,en,ex,'baseline','trend')]['metrics']['net_pnl'])>0 for p in periods[:2]);lines.append(f"|{k}{' 主候选' if d['primary'] else ''}|{f(m['net_pnl']):+.2f}|{latestpositive}|{earlier}|[{ci['simultaneous95_lower']:.2%}, {ci['simultaneous95_upper']:.2%}]|{d['exploratory_followup_candidate']}|")
lines+=['','探索候选数：**'+str(sum(d['exploratory_followup_candidate'] for d in dec))+' /9**。24/4不以赢家替换。全部门槛逐项见candidate_decisions.json，未放宽邻域、DD、前两段及最新四条件、top5集中度、去top5净额、7个年度切片至少5正、事件簇和同时区间条件。2026只有上半年，半年度并非完整年度。','', '区间主比较固定为2025—2026H1九基线对名义现金0：同步循环30日区块、2000次、seed2026092602；取九候选年化算术均值的最大绝对中心偏差95%分位，构造家族同时区间。'+f"共同半宽{fam['common_half_width']:.2%}；全部样本/簇可靠性筛查通过={fam['family_all_reliability_screens_pass']}。区间不是未来复合年收益承诺、不是PBO，也不消除既往家族选择偏差。",'', '## 主候选最新段成本和风险','']
m=index[('latest',24,4,'baseline','trend')]['metrics'];lines+=['|项目|数值|','|---|---:|']
for label,key in [('价格损益U','price_pnl'),('手续费U','fees'),('不利滑点U','slippage'),('tick取整U','tick_rounding'),('残币零可兑现写减U','dust_writeoff'),('周转U','turnover_usdt'),('持仓小时（两币相加）','holding_hours'),('已平交易','closed_trades'),('拒单','rejections'),('最长水下小时','longest_underwater_hours'),('期末未恢复小时','unrecovered_hours_at_end'),('最大已完成恢复小时','max_completed_recovery_hours'),('最长连亏','max_consecutive_losses'),('最差单笔U','worst_trade'),('正收益top5占比','top5_share_gross_gains'),('去top5赢家净额U','pnl_without_top5_winners'),('合并敞口簇','exposure_clusters'),('BTC净贡献U','by_coin'),('额外成本容纳空间U','extra_cost_capacity_usdt'),('静态盈亏平衡额外bps','break_even_extra_cost_bps_static')]:
 v=m[key];lines.append('|'+label+'|'+(json.dumps(v,ensure_ascii=False) if isinstance(v,dict) else ('UNKNOWN' if v is None else f'{f(v):.6f}'))+'|')
lines+=['',f"胜率{f(m['win_rate']):.2%}；最差日{f(m['worst_day']):.2%}；平均/峰值敞口{f(m['mean_exposure']):.2%}/{f(m['max_exposure']):.2%}。只列胜率不构成盈利证据。",'', '静态成本空间按观察到的名义周转计算，不是改变费率后再执行的精确求根；正的额外成本空间也未扣运维、人工、税费和机会成本，负静态bps说明连零额外开销也不能转正。固定持有风险和敞口不同，不把收益差称为纯超额能力。三个期间的全部指标、全年/半年度切片和23滚动窗口见results_all.json；所有交易、信号、现金/库存/残币/压缩小时权益和独立原始重算在runs/。','', '## 数据、实现和审查边界','']
g=json.loads((P/'data_gate.json').read_text());a=json.loads((P/'attempts.json').read_text());fail=[x['id'] for x in a if not x.get('success')]
lines += [f"两币各57,032根唯一小时（80小时暖机+56,952研究小时），合计114,064根。当前数据门槛={g['pass']}；每币2,373个整日与旧C1 OHLC及成交量核对，边界重复及旧缓存重叠均精确一致。所有确认标记/价量/零量检查见data_gate.json。显式新工具调用{len(a)}次，加此前6次共{len(a)+6}/600；服务内部HTTP重试UNKNOWN。失败原始页保留：{', '.join(fail) or '无'}；补洞按另冻一次分段计划执行，未重发同一失败参数。",'', '原协议hash d4a2fef3fc115291e0a9dd62c632c407c1e5bc99a5d59c81df60b83aefb43be4不变。data/engine/independent/statistics/config分项封存，首次真实结果计算时间见first_real_PnL_run.json。25项合成与统计测试通过，真实120场景的信号、期末待执行取消、成交/拒单、现金/库存/可兑现权益和补充风险/归因指标均与从raw出发的独立实现核对。它们共享协议与当前规格代理，可能共享模型假设盲点，不能代替第三方审查或真实成交。A独立审查尚待。','', '工具响应不回显instrument/bar：归属依据是请求参数、SPOT规格、旧缓存与全日线交叉核对；当前listTime/规格不证明整个历史规则版本。严格限定BTC-USDT/ETH-USDT现货，无杠杆、借贷、资金费、合约清算/ADL及转账路径；这些项目仅在该模型中不适用。实际费率、扣费精度、历史盘口/价差/多档深度/冲击/队列/时延/部分成交/故障、点时修订/历史身份规则、账户地区可用性、税务、运维人工机会成本、USDT/平台尾部风险、用户风险预算与真正未见样本均UNKNOWN并阻断真实盈利结论。没有实际下单或持续采集。','', '旧C1与当前V2全部已见历史，所有试验及人工更广选择UNKNOWN在trial_ledger.json披露。不能称新小时数据为新市场样本，不能把120场景或小时数当作独立经济事件。拒绝为得到候选而改参数、删年份、换币或放松门槛。','', '## 可分享图表与原始结果','', '![108场景热图](heatmaps.png)','', '![主候选权益](primary_equity.png)','', '静态图同时提供heatmaps.pdf；完整数表summary.csv，不仅列最优结果。复现入口analyze.py（必须先通过数据和封存门槛），render入口present.py。独立审查接力后停止计算下载，不自动启动前向样本或实盘。']
(P/'report.md').write_text('\n'.join(lines)+'\n')
print('Rendered full fixed results and report')
