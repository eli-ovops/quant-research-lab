# 033：job010闭源压力规则复核

**固定延续规则出现1个真实合格事件，主条件价费为负；尚无合格盈利路线。** PRESSURE_DECAY_FADE仍0事件，收益null。规则和费用不调，也不把FADE影子改成实际选择。

|SUI事件，15秒持有/名义0延迟|5bps每腿|10bps每腿|
|---|---:|---:|
|预登记实际FOLLOW|−1.0946725 USDT|−1.594345 USDT|
|同事件FADE影子|+0.0103275 USDT|−0.489345 USDT|

这是一个事件的独立容量情景，不是账户或四笔可相加收益。单一影子微正既不证明方向选择优势，也不证明AI能识别；真实provider调用数0。不得凭本事件翻转实际动作、改门槛或选择最好持有期。

## 实际源终态

job010/run `phase006-65623-1791328168`，PID65623已不存在，原Owner session83585回执exit0；与collector_final STOPPED、实际reason `deadline`、error=null、完整源共同认终态，不单凭exit0。23:09:28.963429UTC开始，23:54:29.040740UTC finished，实际收到跨度2699.480233秒。

192444行、218311447逻辑字节，gzip CRC/EOF、run/conn/boot/domain、严格ordinal/共享时钟与18实际data频道通过；producer channel_counts含18订阅ACK，data与ACK分开核。logical SHA `820ccbbded55b4befaaba1a4f108d801acf589695046e6b8fed3e8d983ffef43`。正常本轮终止不证明远端丢失根因修复或今后45分钟稳定，旧job009短网络失败原件与结果仍保留。

## 不变规则与完整分母

原026 cut22:20:17.734314UTC / OS29136966188000，全部新源在其后；自身真实10秒成交warmup仍必须满足。两个固定pressure规则/原core/summary/spec字节保持，500独立容量、主15秒、诊断5/30秒、人工延迟0/250/500/1000/3000ms、费用5/10bps每腿不变。entry/exit是目标后第一本有效book，等待超250ms删失，不选后来有利报价。

实际CONTINUATION_FOLLOW仅SUI1事件，其他币和decay全0；完整540 actual /1080 shadow格子中无事件均值null。实际条件30条：26有效、4删失；影子60条：52有效、8删失。配对21个同qty、5个qty不同、4个未知删失；数量不同不称严格同成交量对照。全部其他延迟/持有期留档，不晋级正诊断为主收入。

## 有限核验

固定27个每币首/中/末postcut raw压力数学复核通过。额外针对唯一实事件从原raw正向核当前/ref10/ref1、10s/1s exact去重量、最新unique成交新鲜度、嵌套窗口、past位移/两方向500成本阈值、reference五档规模及实际continuation分支。

独立Fraction实现核全部60个event报价情景：52有效的第一后quote、完整depth/lot下取整、entry notional+fee≤500、退出同qty、双腿fee和净差；8个expired_exit_quote保持null。540/1080全组计数与无事件null一致。此为同Owner有限异实现/原价费核验，不称第三方完整全策略/撮合复现。

盘口/收到成交只是观察代理，不证明强平或真实交易压力因果。全部price_fee_delta是报价容量假设，实际订单/手续费/融资现金/保证金/市场完整性未知；未实现pressure provider适配，无真实AI动作或时延。三新增币provider schema资格仍未知。

## 冻结与收尾边界

准备README/protocol/freeze/results/manifest已保存prep_sealed快照；23:56:38.807475UTC在首次实际结果前绑定AUTHORIZED_CLOSED_REPLICATION、source logical SHA和本scope截止。源终态metadata来自当前final实际`stop_reason_planned_untilfinal`，没有照抄029网络失败标签或32013。先前ISOfixture失败和修正测试保留；本轮未重跑准备subprocess测试或采集进程。

源码/旧源只读，未新增网络/规则/模型调用。各来源结果独立，不与025/009收益合并；不是全局blind OOS，只有一个新事件不足判断机制是否可重复。总12小时任务仍ACTIVE至03:16:33UTC，本阶段不是最终报告。实际model/effort/speed UNKNOWN。
