from pathlib import Path
import json,csv,hashlib,datetime,itertools
P=Path(__file__).resolve().parent;ROOT=P.parent;now=datetime.datetime.now(datetime.timezone.utc).isoformat()
def save(n,x):(P/n).write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def table(n,rows):
 with (P/n).open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
proto=json.loads((P/'protocol.json').read_text());gate=json.loads((P/'data_gate.json').read_text());assert not gate['pass']
s=json.loads((P/'sources.json').read_text());index={x['path']:x for x in s};fund=json.loads((ROOT.parent/'funding'/'sources.json').read_text());idx={x['path']:x for x in fund}
for x in s:
 if x['path'] in idx:
  orig=idx[x['path']];assert orig['sha256']==x['sha256'];x['original_request']=orig
for f in list((ROOT/'raw').glob('*_daily_*.txt'))+list((ROOT/'resume_20260926'/'raw').glob('*_daily_*.txt'))+[ROOT/'sources.json',ROOT/'resume_20260926'/'sources.json',ROOT.parent/'funding'/'sources.json']:
 if str(f) not in index:s.append({'path':str(f),'sha256':hashlib.sha256(f.read_bytes()).hexdigest(),'role':'read-only prior daily comparator or original provenance registry','new_request':False})
save('sources.json',s)
metrics=['final_equity','net_pnl','return_full_2000','price_pnl','fees','slippage','tick_rounding','dust','fills','closed_trades','rejections','holding_hours','turnover','win_rate','average_win','average_loss','max_drawdown','drawdown_recovery_hours','loss_streak','worst_day','tail_trades','top5_profit_concentration','coin_contributions','exposure_clusters','break_even_cost','overhead_capacity','difference_vs_cash','difference_vs_hold','simultaneous_ci95']
rows=[]
for period,(start,end) in proto['periods_UTC_half_open'].items():
 for en,ex,condition in itertools.product(proto['entry_hours'],proto['exit_hours'],proto['conditions']):
  rows.append(dict(period=period,start_inclusive=start,end_exclusive=end,entry_hours=en,exit_hours=ex,condition=condition,status='NOT_COMPUTED_DATA_BLOCKED',reason='Full historical hourly coverage and daily gate unavailable',**{k:None for k in metrics}))
assert len(rows)==108
save('results_all.json',{'status':'NOT_COMPUTED_DATA_BLOCKED','principal_scenarios':rows,'auxiliary_hold':[{'period':k,'condition':c,'net_pnl':None,'status':'NOT_COMPUTED_DATA_BLOCKED'} for k in proto['periods_UTC_half_open'] for c in proto['conditions']]});table('scenario_status.csv',rows)
save('unavailable_outputs.json',{'ledger':'NOT_GENERATED: no valid complete period; do not mistake missing ledgers for zero trades','statistics':'NOT_COMPUTED: no daily strategy return series; no multiple-testing-adjusted evidence','heatmaps':'NOT_GENERATED: all108 outcomes UNKNOWN; colored ranking would imply unobserved performance','independent_replay':'NOT_IMPLEMENTED_NOT_RUN: source data gate failed; only independent coverage verification performed','boundary_tests':'NOT_IMPLEMENTED_NOT_RUN: no V2 strategy engine delivered; signal/delay/fees/retained-position tests required before any future outcome publication','rolling_and_yearly':'NOT_COMPUTED;23 rolling windows frozen before outcomes;7 calendar-year slices each candidate planned','candidate_decision':'All9 NOT_EVALUATED, not9 failed and not0 profitable'})
fields=['applicability','formula_assumption','source_checked_utc','raw_evidence','implementation','validation','result','amount_or_sensitivity','remaining_unknown','blocks_true_feasibility']
items=[
 ('1_product_identity','OKX BTC/ETH SPOT USDT; no derivatives','Current spot specification and earlier identity corroboration only','sources.json; ../resume_20260926/identity_check.json','protocol.json cash/data','Current specifications retained by hash; old2020 sample identity evidence scope retained','PARTIAL','UNKNOWN','All-hour historical instrument/rule changes, region and account eligibility UNKNOWN',True),
 ('2_data','Both assets2019-12-28T16Z to2026-07-01T00Z','57032 required hours per coin; completed bars only','attempts.json; raw/BTC_pilot_app.headers.txt; reuse_hourly_sources.json','collect.py; data_gate.py','UTC grid/OHLC/confirmation/volume; aggregate4 complete days each','BLOCKED','110 present,56922 absent per coin;2 new requests failed','Original revision history, real-time receipt quality and56922 hours per coin UNKNOWN',True),
 ('3_execution','Conditional market buys/sells only','Next open adverse5bps;20bps and extra1h stresses; no capacity inference from candle volume','protocol.json','Frozen plan only; engine not implemented','No fill/depth/replay evidence','UNKNOWN','All108 outcomes null','Historical bid/ask/multilevel depth/impact/queue/latency/rejects/partial fills/outages/price caps/emergency exit UNKNOWN',True),
 ('4_costs','Buy base deduction, sell quote deduction','10bps per side baseline;20bps fee stress; ceilfee1e-8; floor legal lot','protocol.json; prior current specs hashes','Frozen plan only','Not run','UNKNOWN','Fee/slip/tick/dust attribution null','Actual fee tier/discount/fee precision historical version UNKNOWN; borrowing/funding/settlement/transfers N/A under spot-only no-transfer rule',True),
 ('5_cash_inventory','Shared2000U,400reserve,800percoin buy','Pro-rata simultaneous demand; rejected sells retain inventory; dust separate','protocol.json','Frozen plan only','Not run','UNKNOWN','Cash identities and exposure null','Execution inventory unverified; no leverage/short/margin/liquidation/ADL under model; stablecoin/venue risk remains',True),
 ('6_pnl','Tax-before conditional USDT','Initial capital+cashflows+PnL=final equity; separate price/fees/slip/tick/dust','results_all.json','All108 explicit null placeholders','No invented return or summed-period result','NOT_COMPUTED','Break-even and overhead allowance null','Tax/currency conversion/infrastructure/labor/opportunity cost UNKNOWN; cannot call take-home return',True),
 ('7_risk','Active holdings and full account capital','DD/recovery/loss streak/worstday/tail/concentration/lockup/coin exposure required','protocol.json; unavailable_outputs.json','Frozen risk screen only','Not run','NOT_COMPUTED','Risk thresholds not assessed','User risk budget/outages/delisting/emergency spreads/USDT depeg/venue loss UNKNOWN',True),
 ('8_statistics','All9 baseline candidates same latest period','Synchronized30day circular2000bootstrap seed2026092602;95%max-absolute centered interval;>=365days/30clusters','protocol.json; trial_ledger.json','Frozen plan only','No multiple-testing claim; no return series','NOT_COMPUTED','All9 NOT_EVALUATED','Broader search count UNKNOWN; all history reused; cash opportunity UNKNOWN;hold unequal risk',True),
 ('9_reproducibility','Freeze input/code/source/result separately','Hashes plus independent raw data coverage check; no same-function strategy verification','protocol_freeze.json; sources.json; independent_data_check.json; manifest.json','collect.py/data_gate.py/independent_data_check.py/package_blocked.py','Independent coverage only; strategy replay/boundaries absent explicitly','PARTIAL','No PnL engine,108null;new requests2of600','Data blocked before engine/ledger/statistical/risk verification; independent reviewer A pending',True)]
coverage=[]
for name,*values in items:
 applicability,formula,raw,implementation,validation,result,amount,unknown,blocks=values
 coverage.append(dict(item=name,applicability=applicability,formula_assumption=formula,source_checked_utc=now,raw_evidence=raw,implementation=implementation,validation=validation,result=result,amount_or_sensitivity=amount,remaining_unknown=unknown,blocks_true_feasibility=blocks))
table('coverage.csv',coverage)
ledger=json.loads((P/'trial_ledger.json').read_text());ledger['runs']=[{'utc':now,'type':'data_collection','attempts':2,'success':0,'reused_hours_each':110,'PnL_runs':0,'status':'BOUNDED_DATA_BLOCKED'}];save('trial_ledger.json',ledger)
save('status.json',{'state':'BOUNDED_DATA_BLOCKED_READY_FOR_REVIEW','research_complete':False,'reason':'Official main TLS EOF; official alternate connect timeout; insufficient cached hourly coverage','request_attempts':2,'request_cap':600,'new_successful_requests':0,'reused_hours_each':110,'expected_hours_each':57032,'missing_hours_each':56922,'principal_scenarios_planned':108,'principal_scenarios_computed':0,'candidate_status':'ALL9_NOT_EVALUATED','true_feasibility':'INSUFFICIENT_EVIDENCE','actual_orders':0,'background_jobs':0,'unseen_execution_samples':0,'calculations_and_downloads_stopped':True,'independent_review':'PENDING_A','routing':'ROUTING-2026-09-23-v2','weekly_used_percent':83,'five_hour':'UNKNOWN','ordinaryUsageAllowed':True,'actual_model_effort':'UNKNOWN','utc':now})
(P/'report.md').write_text('''# 趋势小时窗口 V2：数据阻断交付

**当前证据不足，尚不能判断24/4或其余8组窗口的盈利性。108个主要场景均未计算。** 这不是策略失败判定，也不是研究完成或审查通过。数据与协议包已封存，等待既有A独立复核。

## 已冻结的范围

24/4为主候选；24/48/72小时入场 × 4/8/12小时退出，共9组；各测基线、双手续费、20bps滑点、额外1小时延迟；2020—2022、2023—2024、2025—2026H1三段独立2000U共享现金，108场景，另12定额持有条件基准。400U储备、每币800U买入上限，升值敞口不强行压回40%。每个完整小时收盘比较**之前**N/M小时的高/低，次小时开盘条件成交。延迟、并发、拒卖保留、残币和末期退出均写入协议。

冻结时间2026-09-26T05:37:38Z；protocol SHA256 `d4a2fef3fc115291e0a9dd62c632c407c1e5bc99a5d59c81df60b83aefb43be4`。冻结早于本轮请求和任何损益计算，策略损益计算次数为0。

## 数据证据与停止原因

1. `www.okx.com`官方history-candles的12小时暖机小样本在Python TLS握手报`EOF occurred in violation of protocol (_ssl.c:1129)`，没有原始行情响应。
2. 查LOCAL_BLOCKERS无相关命中后，以已安装curl和官方备用`app.okx.com`域名做一次不同路径的有界诊断，10秒连接超时（curl28）。保存请求时间、URL、错误和空响应头文件；再次检索阻断记录仍无命中。没有降低TLS验证、改代理、认证、安装或重复同一失败URL。
3. 新增公开请求2/600，成功0。600是上限而非必须耗尽的次数；两条官方连接路径失败，且无新的已验证方案，停止网络工作。
4. 为检查已授权替代资料，只读核对既有funding现货小时原始文件。它们总范围为2026-06-26T10Z—2026-09-26T01Z；只纳入本协议截止之前的**每币110小时**，较晚记录不进入分析。4份相关原始响应保留原路径、SHA256、原请求和接收记录，无新增下载。
5. 每币应有57,032小时（含80小时暖机），各缺56,922小时。已有110小时均完成、正价、OHLC有序、正成交量；其中4个完整UTC日与C1日线OHLC和三项成交量精确一致。这仅验证小段来源一致性，不能代替完整历史。两币数据门槛均未通过。

没有缩短期间、单币替代、跨所补洞或从日线猜测小时路径。图表、108收益表、交易账本、压力、滚动年段和置信区间均无法形成；`results_all.json`保留108个明确null状态，不把缺数据写成零收益/零风险。12持有基准也未计算。

## 选择偏差和候选门槛

C1已见三段市场历史，本轮统一`EXPLORATORY_REUSED_HISTORY`。旧C1共27条件结果已登记，人工及更广研究选择总数UNKNOWN；小时新采集不会产生真正未见市场样本。C1最新段daily20/10费后亏损只作旧研究背景，不能否决本轮24/4。

预设23个180日窗口、90日步长，保持原持仓不按子窗口重置。统计家族固定为最新段9个基线候选对名义现金0的同步配对30日区块bootstrap，2000次、seed2026092602，max-absolute centered统计构造95%家族同时区间；不少于365天及30合并敞口事件簇才进入预设可靠性筛选。尚无收益序列，因此**不具备多重检验后的证据**。这种修正即使执行也不能消除事前研究家族选择偏差。

后续探索候选需最新段四条件均正、早两段基线均正、规定邻域支持、回撤/收益集中度/年段一致性门槛全过、同时区间下界>0。门槛为研究筛选，非用户风险容忍度。9组现在全部NOT_EVALUATED，不能说已有候选，也不能说9组均失败；候选为空不放宽门槛。

## 实现与验证状态

复用方向选择已更正的C1标准库Decimal逐事件账务，便于检查基础币扣费、卖出lot取整和拒绝卖出后保留持仓；Backtrader/VectorBT不会补足历史成交证据，不安装框架。当前交付小时采集器与数据核验器，以及不导入它们的独立原始数据核验器。**未实现/运行V2损益引擎、独立交易回放或策略边界测试**；不能将数据核验通过写成策略实现通过。今后完整数据到位后仍须完成全部因果、共享现金、扣费、拒卖、末期退出、恒等式和风险验证。

`coverage.csv`逐项列出九类真实性覆盖、来源、实现/验证状态、影响与残余UNKNOWN。当前规格和旧历史身份核验不证明每小时历史规则；真实费用、历史盘口与容量、延迟/部分成交/平台故障、税费/运维/人工/机会成本、稳定币/平台尾部风险、用户风险预算仍未核。现货无杠杆无借贷条件下资金费、保证金清算和ADL不适用，不据此推断其它成本为零。

## 复现及下一步

在本目录执行`python3 data_gate.py`、`python3 independent_data_check.py`可只读原始来源并重建数据缺口证据。`collect.py`不会自动重复失败URL；恢复前需新的网络可用性依据并记录采集修订，保留冻结协议和旧失败记录。不要直接将失败次数清空或绕过限制。

下载和计算已停止，不启动后台进程、定时任务、前向收集或实盘。交既有A一次`REVIEW_C_VARIANTS_ONLY`，只审本次阻断包及必要旧来源，审查结果未收到前保持PENDING。若将来具备受支持的官方采集路径，需补齐两币完整数据与日线对照，再继续原冻结108场景；本包不授权自动恢复或扩参。

方法来源：[OKX官方文档](https://app.okx.com/docs-v5/en)的history-candles接口支持1H、每页最多300、confirm标记；[Bailey等原作者论文](https://www.davidhbailey.com/dhbpapers/backtest-prob.pdf)说明多次回测选择可能造成过拟合，本文未计算PBO。公开文献不证明该策略盈利。
''')
print('Blocked evidence package written; no PnL computed')
