# 阶段010：规则冻结后新报价的条件事件评价

本段主场景没有发现费后正事件：15秒持有、名义0ms延迟、单边5bps假设下，各有效 FOLLOW/FADE 的 price_fee_delta 全负。数据是17:14规则冻结后新接收的45分钟 job004；保留此前开发及后置源质量/数值修复历史，不称完整盲 OOS，不代表所有市场机制无效。真实 AI/provider 尚未调用，时延和增益为 null。

job004 正常截止18:31:41.192194 UTC，122419条、131745890 logical bytes，gzip CRC/EOF通过、PID终止、raw哈希与冻结一致。guard 0无效行，单run/connection段；FLOW 23、BOOK 115、LEAD 2。整个固定网格8400条件行中8078有效、322删失，删失保留null而非亏盈0。每一币、动作、费用、延迟、持有期独立，不相加为账户收益。

主表为15秒/名义0ms延迟/500USDT容量，数量为每动作有效事件。均值单位USDT，仅报价和假设双腿费，非资金账户、真实成交或含融资净收益。

|机制/资产|有效/删失|FOLLOW均值 5bps / 10bps|FADE均值 5bps / 10bps|
|---|---:|---:|---:|
|FLOW BTC|3 / 0|-0.5626 / -1.0597|-0.4327 / -0.9298|
|FLOW ETH|0 / 0|null|null|
|FLOW SOL|20 / 0|-0.5342 / -1.0328|-0.5488 / -1.0475|
|BOOK BTC|47 / 5|-0.4565 / -0.9535|-0.5386 / -1.0356|
|BOOK ETH|58 / 0|-0.4663 / -0.9641|-0.5355 / -1.0334|
|BOOK SOL|5 / 0|-0.4993 / -0.9984|-0.5817 / -1.0808|
|LEAD ETH|2 / 0|-0.6439 / -1.1402|-0.3590 / -0.8563|
|LEAD BTC/SOL|0 / 0|null|null|

5bps主场景最佳单事件可承担单边费为4.1346bps，仍低于假设5bps。spread已含盘口VWAP，不再扣一次。primary_summary.json保留两费用、五延迟的全部主统计（均值/中位数/尾部/正值比例/分母），diagnostic_summary.json保留预登记5/30秒；不得从中挑最大正项。paired_delay_diagnostic.json明确只对两边有效的同事件作差，另列删失；延后入场也延后退出，因此不是纯网络/AI时延因果。

关联2个事件中确定性时间近邻控制1匹配、1未匹配；未匹配不填0。唯一匹配的持有窗约15秒全部重叠，控制实际入场晚于leader asof，不能称独立无冲击反事实。控制共享次数及同asof动量基线保留 matched_controls.json。FLOW/BOOK随机控制未预登记、未实现。receive_time_clusters.json描述100ms事件簇，不将跨资产事件当独立N。

有限异实现审计从原gzip核128个有效样本的首个后报价/≤250ms、同run/conn、合约grid、500入口含费容量、退出同数量、双腿费用与价差，另核8个删失null。3项新adapter测试通过，冻结suite/core/原cut字节不变。该Owner审计不是第三方完整策略复放。segment_counters.json保留 invalid_clock/book/tradeID conflict/repeats/missing 均0与cooldown4101，source_guard_receipt.json提供原件层验收。

资金费时间超出此前公开history取得范围，UNKNOWN，未填0；真实费率/滑点/队列/partial/mark/全市场完整性均未验证。价格窗口不能当真实到账盈利或杠杆方案。总12小时任务仍ACTIVE；唯一job005有截止采集继续，不能把其等待时间当主动研究工时。
