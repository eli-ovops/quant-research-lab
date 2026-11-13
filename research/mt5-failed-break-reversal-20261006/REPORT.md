# 价格突破失败后的区间回归：固定F实验

本版本机会不足，唯一成交亏损，不晋级。8月基础-5.00USD、压力-4.90USD，9月零交易。反向并未自动修复突破；每成本19个候选全成本RR不足、仅1笔成交，不能据此否定整个机制。本假设由已用历史观察提出，非holdout，收益前冻结不消除开发偏差。

|时段/成本|净USD|期末|return|quote DD|PF|次数|胜率|实际净赢输比|平均netR|费/slipUSD|
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
|Aug base|-5.00|495.00|-1.00%|1.659%|0|1|0%|NA|-1.00|0.70/0|
|Aug stress|-4.90|495.10|-0.98%|1.305%|0|1|0%|NA|-1.00|0.49/1.40|
|Sep base|0|500|0%|0%|NA|0|NA|NA|NA|0/0|
|Sep stress|0|500|0%|0%|NA|0|NA|NA|NA|0/0|

各账户独立500USD持续，无周重置或跨段合并。实现netR≥3/5全部0。Aug最长连亏1，19个weekday无交易；Sep连亏0、10weekday无交易。全部无期末持仓或未完watch，未达到650观察/已实现目标。PF/实际盈亏比缺分母为NA，零交易不等于已证空仓alpha。

固定F沿旧UTC23–03亚洲箱、当前tick MA50、10point偏移产生首合法virtual stop。首次突破只WATCH，side/原rawhigh-low固定、无资金/费用/OPEN；排除trigger forming M5。从下一根开始取连续完整闭合M5，原向上用bidclose、向下用askclose，第一次严格落回rawlow<close<rawhigh后只取bar结束后的首真实quote，同报价侧还在箱内才反向。缺bar、首quote已出箱、13到期或拒绝则当天不重试，不能等未来有利quote。

从trigger直到decision quote（含当前已见quote）累计最高ask/最低bid：反short SL=maxask+10point，反long SL=minbid−10point，Decimal远侧规范化；TP反short固定rawlow、反long固定rawhigh，不覆盖为5R。实际市价entry含情景slip；方向正确且每lot净TP收益扣7USD佣金÷含SL出口slip的计划损失≥3才准入。1%全成本计划风险、lot .01向下/min.01/max100、100kEUR/100:1代理、cap1/5%sticky、21首quote退出不变；TP逆向candidate须合法、保守按limit。未调3、未加参数或无gate变体。

每成本观察分解：
- Aug15 watch：1 RR通过、12 RR<3、2首quote已出箱。
- Sep8 watch：7 RR<3、1到13仍未形成回区间决定。
- 无真实missing_bar取消；必要合成测试覆盖缺bar与13取消，不造bar填齐。

唯一08-03原向下突破后反long，03:25:00入场、04:11:55 SL。可见minbid1.15283，SL1.15273，TP原high1.15587。基础entry1.15316/lot0.10/计划风险5.00USD/计划净RR5.28；压力entry1.15326/lot0.07/计划风险4.90/净RR3.629，SL退出压力价1.15263。压力少亏0.10来自风险lot缩小，不能称压力更优或把差异全叫滑点。准入交易日期本样本相同，但两个成本独立RR/size，可改变未来交易集合。

同日已封存C基础+1.77、压力+1.57USD，只作描述性比较。F是正向原quote扫描产生，未倒放C、未直接翻转其亏损或事后从C亏损贴F事件。数据只有双边报价，不声称观察到强平、扫止损或做市订单流。

6项新因果测试PASS；有限异实现原quote核第一回区间闭合bar/首quote、WATCH极值、40个两成本decision的RR、entrySLTP、现金费用/风险lot/margin/21与连续账本，四账户PASS。同Owner不同实现，不是第三方全策略复放。父PMO已审原账本独立现金复算、引擎与audit，接受有限因果/条件账务，不接受盈利晋级。四旧交易源码byte-for-byte未改，C/E仅索引，不重跑旧tests/策略。

首次新PnL前冻结2026-10-06T14:26:26.906351Z。输入只读：Aug08-03–29，hash 51578137ffc63dac408443c50ce4b602c276e85a9f9b44ddc1a494317dae43ce；Sep09-07–19，hash 9839f59972eb772ce0d736ca9348c13a66eb314a939224fe1ec0c2acab52efb4。event-time/同秒原顺序条件及预热沿旧审计，不复制raw/no造bar；一分钟无报价不自动缺采，规则需要的完整M5缺失则取消。原来源完整性、到达序/真实撮合、原生EA/broker规格与swap/rollover UNKNOWN；无UTC跨日不证明无融资。未知项不抹掉已知成本负值。

产物：protocol/execution_freeze、四ledger/equity/daily/results、run_results、independent_audit源码/原件、测试回执及manifest。主任务20min/4账户/≤25MB、0联网/安装/private/key/订单/生产/后台/新agent，实际model/effort/speed UNKNOWN、请求Sol medium，已读规则版本未变。旧入口及冻结哈希复核，有限实验已封存并停止新增动作。

