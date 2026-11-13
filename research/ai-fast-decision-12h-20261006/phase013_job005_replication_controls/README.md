# 阶段013：第二新接收episode复核与已用样本基准

主结论：job005固定信号15s/0名义延迟/5或10bps每腿的有效价费差额全部为负，未复现可付成本的主场景机会。它是独立新接收episode，但不是完全盲OOS，也不能把job004+005结果相加成账户盈利。AI/provider实际结果仍null。

旧007/008/v12算法原字节复制，原17:14cut不变、绑定job005真实run。源全gzip CRC/EOF、125765条/134494295logical、原hash通过，0guard invalid，单run/conn；FLOW19/BOOK119/LEAD0，共138事件、8280网格行（7964有效/316删失）。所有5/15/30秒、五延迟、两费网格保留all_signal_summary.json，不挑最佳配置。

以下主表15s/0delay/500容量，各资产/动作独立，均值USDT只含真实报价与假设双腿费，不是资金账户/真实撮合/融资净收益。N是fee5有效/删失，fee10的完整分母也保留文件。

|机制/币|N有效/删失|FOLLOW均值5 / 10bps|FADE均值5 / 10bps|
|---|---:|---:|---:|
|FLOW_IMPULSE/BTC|1/0|-0.4095 / -0.9055|-0.5835 / -1.0795|
|FLOW_IMPULSE/ETH|3/0|-0.4127 / -0.9108|-0.5871 / -1.0851|
|FLOW_IMPULSE/SOL|15/0|-0.5901 / -1.0888|-0.4934 / -0.9921|
|BOOK_STATE/BTC|49/2|-0.4726 / -0.9684|-0.5204 / -1.0163|
|BOOK_STATE/ETH|59/2|-0.4726 / -0.9703|-0.5277 / -1.0254|
|BOOK_STATE/SOL|7/0|-0.5052 / -1.0038|-0.5762 / -1.0748|
|BTC_TRANSMISSION/BTC|0/0|null / null|null / null|
|BTC_TRANSMISSION/ETH|0/0|null / null|null / null|
|BTC_TRANSMISSION/SOL|0/0|null / null|null / null|

A基准严格按信号asof之前的1s received mid方向，current/ref均≤250ms、同conn/domain、ordinal不跨未来。不能将BOOK原500ms impulse当1s。138个asof中106真零WAIT、31非零方向、1过老ref UNKNOWN。WAIT的价费0是明确不交易；UNKNOWN为null。BOOK BTC/ETH/SOL的fee5平均A价费分别−0.05824/−0.04883/0，主要来自44/55/7次等待，非策略alpha或更高盈利。A每币family/fee原统计、median/尾部/删失和选择方向保存primary_vs_A_summary.json与baseline_A_features/outcomes.json。

B基准冻结seed FAST_AI_CONTROL_V1，以run+asset+grid_index SHA256首byte parity定方向，无利润/未来报价/目标标签参与。每资产35s格子，起点原run首OSclock+1s；格子之后首有效book≤250ms作为asof，其后另一本作为entry，不用同一本盘口偷成交。228个有效grid asof、6个grid本身拒绝，随机方向不等于matched随机试验；频率/分母与signal不同。

|B固定格子币|fee5有效/删失|mean5 / mean10 USDT|
|---|---:|---:|
|BTC-USDT-SWAP|67/7|-0.4920 / -0.9878|
|ETH-USDT-SWAP|75/2|-0.4874 / -0.9849|
|SOL-USDT-SWAP|69/8|-0.5386 / -1.0374|

B两费每币有效结果全负，零positive；全部grid事件/拒绝/费用/中位数和尾部保留，不选seed/格子。A/B是本阶段在已闭合源之后预登记的开发诊断，不称新OOS。信号选时与时间基准不同，100ms时间簇及重叠持有存在相关性；less negative不等于利润或因果优越。控制统计没有与原事件收益叠加。

4项必要边界测试PASS；同Owner有限独立核原gzip74有效价格数量/双腿费/首after报价≤250ms及8个null、137个原1s符号和228个grid首book/seed方向。不是第三方完整策略复放。原suite计数 invalidclock/book/tradeidentityconflict/repeats/missing 均0、cooldown4203。真实fee/funding/queue/partial/完整市场源未知，人工delay不是真实AI时延。

证据：protocol/execution_freeze、source_guard_receipt、events/event_deltas、baseline_A/B文件、全部summaries、tests日志、independent_audit/audit及manifest。旧phase7/8/10/12 seal未改，job006保持唯一有限source；总12h目标ACTIVE，不自动续开采集。
