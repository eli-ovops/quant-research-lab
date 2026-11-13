# MT5公开EA候选与EURUSD复测门槛

结论：**三候选已完成证据筛查；原市场回放受阻，PnL=null。** 固定优先候选1的mq5原源未取得，EURUSD双边历史探针TLS失败；不能把公开说明改写成“已复现EA”，也不能自动换候选2跑收益。没有可验证的五日回放结果或盈利结论。

| 候选 | 公开来源/表现 | 本轮规则证据 | 复现状态 |
|---|---|---|---|
|1 [Session Opening Range Breakout](https://www.mql5.com/en/code/76153)|免费CodeBase；页面列mq5下载|说明：M1 OR30min、闭合bar突破、市价、broker08点、120min窗、20pointsbuffer、30pointsSLbuffer、2R、1%balance、session最多1|附件和原页本地传输失败；完整源码、持仓跨日、总仓、lot取整、隐藏依赖UNKNOWN。唯一回放候选，未运行|
|2 [Asian Breakout](https://www.mql5.com/en/articles/17239)|官方教学文章含inline源码与附件；文章回测图不是本轮结果|实际片段：23→03箱，MA50当前bar过滤、固定0.1lot、pending BuyStop/SellStop附SL/1.3R TP，13点关闭/撤单|片段已审，mq5附件未取得。发现pips/points与未闭合bar边界、magic作用范围风险。仅筛查，不替换1|
|3 [Precise Pair Trading Pro](https://www.mql5.com/en/signals/2329290) / [EA产品](https://www.mql5.com/en/market/product/148319)|信号有公开增长与风险统计；产品470USD、复制50USD/月|两资产偏离关系，公式与完整风控未知；“非grid/非martingale、每symbol1仓”仅发行者声明|无源码可复现；真实记录≠机制可审、可复制或未来收益。未购买、订阅、下载/运行商业二进制|

这三项均没有本轮原市场收益回放。“有下载链接”“文章展示回测”“发布信号历史”是三类证据，不能互相替代。详细SL/TP、订单类型、重复入场、lot、carry、最大仓和依赖见code_review.md，含官方页面行号；不是mq5源文件行号。

## 固定小样本与实际数据门

在任何收益前冻结2026-09-21 00:00至09-26 00:00UTC五交易日、500USD、唯一候选1。若原源和数据都通过，条件版本用M5确认、伦敦08:00 Europe/London映射UTC（该周夏令时对应07:00UTC），OR30min+120min窗、20/30points、2R、1%risk。标准合约100000EUR、最小/step0.01lot、100:1均仅代理假设；EURUSD point/digits还必须由真实broker规格确认，不能把points当pips。佣金0或7USD roundtrip/lot分别计算，真实spread来自双边，swap/stop-level未知独立列。此映射不是原EA broker时间认证。

实际只取得[Dukascopy官方历史格式文档](https://www.dukascopy.com/wiki/en/development/data-export/)原HTML/hash：LZMA bi5、big-endian20bytes tick、时间UTC、ask/bid、EURUSD scale100000有文档依据。**当前官方归档路线是AWS S3 requester-pays，需要凭据和费用，未调用。** 旧公开datafeed的EURUSD/2026/08/21/07h_ticks.bi5仅作无认证一小时先导探针，urllib TLS handshake timeout，无任何tick字节；一天门槛未完成，因此未扩到五日。

数据审计：记录数UNKNOWN/不可用；bidask/timegrid/spread/OHLC/周末交易时间/数据修订均未通过。未猜缩放、未生成价格、未填缺失。即使scale有官方依据，旧hour-bucket与当前day-bucket的时钟基准仍必须现场验证，不能混套格式。双边一分钟SL/TP冲突需先SL、跳空更差open、入场市价，只有实际数据和原EA退出逻辑齐全才可实施；本轮未实现该回放。

## 环境、失败与边界

精确只读检查/Applications与/Users/USER/Applications目录顶层，未见名称匹配MetaTrader/Wine/Crossover；其他位置安装状态UNKNOWN，未遍历用户配置/账号。当前没有已验证MT5 tester运行环境；本轮不安装。

urllib三个MQL5原页均TLS handshake15秒timeout；web公开页面内容可读，但两个mq5附件仅Internal Error。Jina候选1原页401，未重试/找凭据/绕过。IAB unavailable；Chrome本任务新标签navigate10秒timeout，标签仍about:blank，未触其他用户标签。停止新浏览器/代理/认证/配置和重复数据尝试。仅源码说明及官方文章inline得到静态阅读证据。

最多34个显式公共读取/导航操作（27 web查询/打开/查找/点击、6 urllib、1 Chrome导航；实际内部HTTP重试UNKNOWN），低于60预算；数据新增不足30MB。ROUTING-2026-09-30-v3，目标Sol medium、实际model/effort UNKNOWN。旧目录封存未重跑，唯一Owner/root/external_relative_value；无安装、EA运行、keys、账户、订单、付款、生产或后台。

## 真正做了与未做

做了：收益前protocol冻结；三个准确产品原入口及来源；候选2inline代码风险核查；官方格式原件保存；一个EURUSD真实数据URL探针；精确MT5环境检查；原错/hash保留；LOCAL_BLOCKERS只补本次适用条目。没有取得候选1mq5、完整双边数据、完整broker规格；没有EA编译/运行、历史交易、ledger、synthetic replay测试或Pnl。结果不是“0交易/0收益”，是未运行/UNKNOWN。

下一步最小必需输入是：**候选1原mq5文本 + 固定五日真实双边报价文件（或受支持MT5 Tester的broker tick data）+ broker point/digits/lot/tick-value/服务器TZ、commission/swap与stop-level说明**。这些齐全后，同一个冻结候选原规则核对再做条件回放。可从已支持的官方历史出口或broker tester数据取得，不需要购买商业EA、替换市场、问大问卷或为修某个网络工具扩大授权。本轮没有请求安装/账户权限。

交付protocol.json、results.json、dataaudit.json、code_review.md、requests.jsonl、rawsource与artifact_manifest.json。rawsource两份web JSON是工具解析回执，不冒充原mq5/原网页HTML；官方格式文档是实际下载HTML。失败原件也是证据，全部保留；无可清理项。业务层：筛查可审，数据/原源门未过，回放未完成。
