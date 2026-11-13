# EURUSD 8月固定四周：同一账户条件回放

**基础有盈利，压力为负，不满足继续线索门，不晋级。** 2026-08-03 00:00至08-29 00:00UTC，一个500USD持续账户；两个执行情景各自独立，未每周reset、未调阈值。此前未计算该月收益，但仍是回顾历史研究，不能叫未来前向/盲样本。

| 情景 | 月份PnL USD | 收益 | 期末USD | 观察报价DD | PF（逐笔扣费后） | 平仓/胜/负 | 佣金USD |
|---|---:|---:|---:|---:|---:|---:|---:|
|真实bidask+7USD/lot往返佣金|+35.40|+7.08%|535.40|10.4214%|1.62655|15 / 7 / 8|10.50|
|同费，每次市价/stop逆向1pip压力|-12.80|-2.56%|487.20|12.7926%|0.82345|15 / 7 / 8|10.50|

现金对照500→500、收益0/DD0。两情景15笔均低于20笔门槛；压力净不正且PF<1，因此NEGATIVE_UNDER_FIXED_STRESS，样本不足另列，不是把数据或实现通过当盈利。压力1pip是冻结假设，不声称现实每次都是1pip，也不据此否定全部MT5/原版EA。

+30%（650USD）未观察到权益触及，也未实际退出实现。所有输入quote都检查目标，只观察不添加目标平仓；保留分钟曲线最高基础557.35、压力516.15USD，已实现余额最高547.10/504.90。期末未平仓0、无额外强制卖出；本次实际无跨日持仓，模型未发生swap，未来/真实broker swap仍UNKNOWN。最差观察浮亏-13.60/-14.60USD。

## 每周贡献：同一账户，不重置

| UTC周开始 | 基础贡献USD | 压力贡献USD | 平仓笔数 |
|---|---:|---:|---:|
|08-03|-1.60|-7.60|3|
|08-10|-19.50|-26.50|4|
|08-17|+68.20|+39.00|5|
|08-24|-11.70|-17.70|3|
|该连续账户合计|+35.40|-12.80|15|

收益集中第三周；前三个负贡献不能删掉。这里只对同一账户贡献相加，不与9月旧独立账户、两情景或其他研究收益相加。

## 执行差额、舍入和风险

两情景净差48.20USD=直接滑点27.00+TP等待改变退出路径21.20USD，不能全写现金滑点。8月17日基础按TP于09:28:20退出；压力133次观察quote逆向1pip后不满足limit，等到13:00按原时间退出。该笔净差23.20，其中2USD直接滑点、21.20退出路径。匹配逐笔表在independent_audit.json；月全体TP等待计377次。

基础TP到达合法quote保守按limit成交；压力需bid-1pip>=longlimit或ask+1pip<=shortlimit才能按limit成交，不合法就等待，不借overshoot改善利润。市价/SL/时间退出使用quote加逆向滑点。真实spread已在ask入/bid出（空头反向）价格内，未重复扣，mid半spread仅诊断。

Decimal及1e-10网格噪声容差避免已在5digit的值误偏1point。entry最近5位；longTP向下、shortTP向上，SL朝更远risk方向（long向下/short向上）；raw/舍入差逐笔保留，最大TP舍入价格差约0.000009。固定0.1lot，不是1%risk；基础名义单笔SL风险1.5194%–6.16%，压力1.8690%–6.36%，包含预估出口滑点/双边佣金风险另在ledger。最小lot/step0.01、contract100000EUR、100:1、point1e-5是代理规格，不是broker已验证；stopLevel、latency、partial/margin-tier UNKNOWN。没有保证金不足事件。

incomplete_session_box=3对应08-09/16/23三个Sunday重开时非交易时段诊断；20个weekday箱/MA网格齐，不能称缺3个交易日。五个weekday pending未触发，未为凑20笔换规则。

## 数据、规则和验证

[HistData官方入口](https://www.histdata.com/download-free-forex-data/)的实际2026年8月href与原公开表单POST，原ZIP4,325,257字节，SHA256 09f1c164d36433e4a73958d0dcf153f9654488122ac397e2350f6c48b9df7b7a。公开表单临时值只RAM使用，原月页脱敏，未认证/付款。仅2公共请求，继承现有proxy、TLS验证开启，未改系统。

按已核[供方格式](https://www.histdata.com/f-a-q/data-files-detailed-specification/)固定EST UTC-5、不DST映射UTC。全ZIP流式扫描，严禁遇范围右端earlybreak；稳定event-time/rawordinal排序，同timestamp保留所有原quote次序，不补。筛选995,146双边报价+3856纯预热，一份CSV44,955,109字节。20个weekday箱/MA网格齐，覆盖四周；原月原件永久保留。实际整秒、volume未知/0、350个>60秒间隔含正常周末；gap_context标当时持仓/待单与M5跨界，间隔内价格路径UNKNOWN，无quote分钟不自动当缺采。全部来源完整性、真正到达序列、完整市场tick及native撮合仍UNKNOWN。

同一候选2[官方inline研究版](https://www.mql5.com/en/articles/17239)：UTC23–03箱、13退出、M5 MA50、offset10points、RR1.3、固定0.1lot。半开箱、单symbol隔离、无可选trailing等旧研究改动未变。原候选1及原附件/原生MT5没有因此被复现；没有运行下载EA。

协议、旧source df9525...、新执行代码669896...、输入/dataaudit完整hash在任何新8月PnL前冻结，见execution_freeze.json。没有deque/速度优化，复用核心。8个必要测试PASS（bidask、压力stopgap、TP不越限/精确网格、舍入、费用/lotmargin、warmup/no-future、目标观察不退出）。不同实现核账PASS：真实quote匹配、规范化/limit/fees/margin、逐笔计划风险、PF/胜败、周贡献与账户净值可重建；同一Owner不同账务实现，不是第三方或完整独立策略复放。父已读原件并接受数据/条件账务层，未接受盈利晋级。

## 交付与边界

results.json汇总、base/stress各ledger/equity/runtime/results、independent_audit与逐笔差额、gap_context、协议/首次freeze/源码、数据audit/原ZIP及manifest。运行入口：

```sh
python3 august_engine.py --scenario base
python3 august_engine.py --scenario stress
```

输出目录已存在时拒绝覆盖；复跑须显式用新目录/版本，不改当前证据。自主模式AUTONOMOUS-2026-10-05-v1，ROUTING-2026-09-30-v3目标Sol medium，实际model/effort UNKNOWN。30分钟/40调用/100MB内，无安装、账号、keys/privateAPI、订单、购买、生产、后台、新agent。旧目录封存未写；约55MB新证据均保留，无清理项。已停止新增实验；一个基础盈利四周不足以证明稳定正期望，压力负和15笔不足均明确保留。

