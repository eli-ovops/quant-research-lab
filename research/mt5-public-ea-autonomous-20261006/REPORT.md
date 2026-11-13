# EURUSD真实双边报价：研究版条件回放终态

**已完成本地研究版、真实报价条件回放和不同实现账务校核；未证明原EA可复制或盈利，不晋级。** 候选1源码取得仍受阻；按新增授权转到候选2官方inline片段重建。原周只覆盖四天及周五不足一小时，前两新授权日历周在零佣金下亦为负。结果独立呈现，不相加、不换规则救参数。

| 固定UTC期间（每期500USD） | 往返佣金USD/lot | 条件净PnL USD | 期末USD | 可得报价DD | 平仓笔数 | 佣金USD |
|---|---:|---:|---:|---:|---:|---:|
|09-07至09-12|0|-12.11|487.89|3.3101%|3|0|
|同上|7|-14.21|485.79|3.4521%|3|2.10|
|09-14至09-19|0|-15.73|484.27|8.4850%|5|0|
|同上|7|-19.23|480.77|8.9658%|5|3.50|
|09-21至09-26，实际到09-25 00:59:37|0|+16.81|516.81|3.4379%|4|0|
|同上，周五主策略窗缺失|7|+14.01|514.01|3.5936%|4|2.80|

现金对照每期500USD，无息、净收益0、DD0。三期间最差观察浮亏分别-12.80、-17.60、-17.90USD；期末持仓均0，无额外强制平仓，模型保证金不足/拒单事件均0。09-07周两日pending未触发，首个>=13点报价到达后取消；不是漏删亏损交易。spread来自真实bidask，已在买ask/卖bid现金流内；mid半spread诊断合计0.95/1.70/1.10USD，不重复扣。表为条件数学执行结果，不是真实撮合或连续盘中风险上界。

## 数据与完整性

从[HistData官方入口](https://www.histdata.com/download-free-forex-data/)沿实际href获取EURUSD2026年9月原公开表单，POST下载5,203,731字节ZIP；表单临时值只在RAM使用，日志无值，月页脱敏并保留原hash。原ZIP SHA256 `9d5ab8f56a36a9a458326a15e7673b0baeeeba3a89e406864528ade0ddca36e0`，内件 `DAT_ASCII_EURUSD_T_202609.csv`，永久保留未改。

[官方规格](https://www.histdata.com/f-a-q/data-files-detailed-specification/)是DateTime,Bid,Ask,Volume，固定EST UTC-5、不调DST。本轮严格照此映射UTC；实际timestamp全部整秒，不能称完整毫秒级市场逐tick。volume均0，作为供方未知，不当真实成交量。

全月流式扫描1,315,871行、72个相邻1秒倒序；原周11个、0跨M5。event-time稳定排序保留所有行及同timestamp原序，不补价；原周有130,703个相邻同秒不同报价，原序只是条件假设，订单到达时序UNKNOWN。只提取授权周及最多前5小时warmup，未整月解压复制。

| 区间 | 双边报价 | 预热 | 覆盖 |
|---|---:|---:|---|
|09-07周|275,034|685|至09-11 21:59:59；每日M15箱/MA49网格齐，09-09/10各1分钟无报价|
|09-14周|308,427|2500|至09-18 21:59:59；每日M15箱/MA49网格齐，09-15有1分钟无报价|
|原09-21周|258,548|954|至09-25 00:59:37；周五03至13点策略窗不可评估|

前两周为**PASS_WITH_GAPS：可得quote下的条件覆盖**；OTC一分钟无报价不自动证明缺采，全部来源完整性仍UNKNOWN。原周Friday明确缺主要时段，保持INCOMPLETE。覆盖解释澄清在本执行者已读取跨周PnL后到达，未写成收益前门槛修正；旧严格分钟gate=false留档，解释没有改动策略、价格、账本或PnL，本轮始终不晋级。各run的certified-full-week PnL保守null，但真实条件结果已计算，如表。

>60秒报价间隔分别118/32/59个，最长240/241/185秒；其中2/3/3个持仓、2/1/2个待单。gap_context_audit逐个记录M5跨界和状态；间隔内SL/TP路径不可观测，不能用观察DD当最大损失。

## 原版与研究版边界

候选1 [Session ORB](https://www.mql5.com/en/code/76153)原mq5未取得，**本报告不是它的结果**。候选2 [Asian Breakout文章](https://www.mql5.com/en/articles/17239)inline片段可审，但原附件EA/原生MT5未运行或验收。

研究版：固定0.1lot（不是1%risk）；UTC server23→03箱、13点退出、MA50/M5时框代理、10*_Point offset、1.3R。contract100000EUR、point1e-5、lotmin/step0.01、100:1均为broker代理。源码对应原文L127–142、165、190–191、267、370–404、422–468，索引保留。当前MA按已到达tick及前49闭合M5计算，不用未来close；shift0本身不定性为前视。

明确研究改动：箱体半开23–03，排除forming03点bar（不称修原策略bug）；重建散列inline控制；不启用可选trailing；单symbol隔离magic作用；资本不足拒绝。未取得全附件，不能验证其全部依赖或无grid/martingale。实际计划SL风险与balance比例/margin逐笔在ledger，原部分窗约2.20%–3.42%，不能宣传1%。本次无跨日持仓；未来swap仍UNKNOWN。数学TP可能不落5位broker价格，未仿真native价格规范化/stop-level/实际拒单，故不构成可下真实单证明。

## 验证、版本与自主模式

完整读取AUTONOMOUS-2026-10-05-v1；目标明确，未重复问卷。Owner/root/external_relative_value，ROUTING-2026-09-30-v3目标Sol medium，实际model/effort UNKNOWN。初次两资源请求级继承现有proxy、TLS校验保留：MQL5仍SSL timeout、Dukascopy503；未重试Jina401或改配置。HistData是独立公开提供方，不是绕拒绝。

v1失败留档；v2按可用性切换候选2，在任何forex收益前冻结；v2.1纯warmup无订单；v2.2event-time归一化；v2.3修同秒warmup原序。旧sorted(set)账本保留但不作最终验收。全月重扫确认早停假设所选范围漏行0；修正audit另冻结，不冒充第一次盲核。父曾肉眼读反宽CSV的entry/latest_price，DictReader确认sell entry1.13696<bid1.13762合法，误判撤回留档，不据此改策略。

v3前两日历周为新增明确授权的独立500USD复测，日期/数据/代码hash在该阶段收益前冻结；不是把原周中途换日期。最终六输出各有运行前后相同代码hash、输入hash和命令。8个必要合成测试通过（决策、双边执行、stop-gap、fee、lotmargin、warmup、同秒原序、日期参数）；模拟价不当历史收益。三期间不同实现核账PASS，父已读原件/源码/数据/账本并接受本地管线与条件账务。审计由同一Owner不同账务实现完成，不是第三方或完整独立策略复放。

## 交付和使用

results.json六情景；protocol_v*/freeze_v*；原ZIP与脱敏raw；dataaudit/fullscan/跨周输入；每个replay目录ledger/equity/runtime/results；三份independent_audit、gap_context与测试回执；manifest逐件hash。旧pilot/低换手/机制报告未改，无安装/账号/keys/付款/私有API/订单/生产/后台/新agent。12次执行者显式公开操作，父代读/内层请求另列UNKNOWN，ZIP后0联网，文件约63MB内，证据均保留。

在本目录可运行CSV适配器（输出目录须不存在）：

```sh
python3 asian_research.py --csv week0907_ticks.csv --warmup-csv week0907_warmup.csv --format utc --start 2026-09-07T00:00:00Z --end 2026-09-12T00:00:00Z --commission 7 --data-audit week0907_dataaudit.json --output new_run
```

也支持原GenericASCII tick的--format histdata，拒绝单边M1/非法数据，不填缺失。已停止新增阶段。本地研究链路完成；原EA/native/fill、全部来源完整性和盈利晋级均未完成。
