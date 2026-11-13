# 039：job011固定十规则闭源复验

**本次仍无合格盈利路线。** 原六规则固定主条件有三个5bps小正动作，但所有非空币/family/action/fee主分组均值为负，10bps正动作数为0。costshock与pressure各触发一个SUI事件，实际为同一asof，不能当两个独立样本；实际和影子主价费均负。

## 来源与冻结

job011/run phase006-70339-1791331388正常deadline终止，00:48:08.857092UTC finished/error=null、PID70339不存在；Owner session62844回执exit0与final/完整源联合认终态，不仅凭handler exit0。195547行、221218835逻辑字节、25375030gzip，收到跨度2699.463868秒，18实际data与18订阅ACK分开计数。CRC/EOF、typed clocks、run/conn/boot/ordinal/rawarg和logical SHA df8b392b96f4e25cc60faf664bb867806f7ca3fe4cc76ebe0014de8bac51c2a7通过。

039准备快照完整保留；00:49:22.895774UTC source/hash/mode实际冻结后执行。原21核心/规则/spec/辅助字节未改；只有prepare guard与当前source发布metadata的wrapper适配，原wrapper文本留存。原六/015cost/026pressure cut不动，source全段晚于规则，但后置wrapper准备和此前开发选择仍使其不是全局blind OOS。

## 固定主结果：15秒、名义0延迟、独立500容量

|规则层|实际事件|5bps有效/删失动作|5bps正动作|10bps正动作|
|---|---:|---:|---:|---:|
|原六规则总观察（计数，不合收益）|250：FLOW134/BOOK116/LEAD0|422/78|3|0|
|costshock FOLLOW/FADE|1 SUI|2/0|0|0|
|pressure延续实际FOLLOW|1 SUI|1/0|0|0|
|pressure衰减实际FADE|0|0/0，均值null|null|null|

原六规则的三个5bps正动作分别SUI/FLOW event55 FOLLOW +0.2225364、event119 FOLLOW +0.27904515、event159 FADE +0.0131943USDT；完整负样本/尾部与删失均保留，不把正例选为策略或视为真实成交。动作、费用、币和来源不相加为账户收益，时间簇相关性仍在。

## costshock与pressure重叠

两者同SUI/asofordinal93220、OS36529587858000，conn181b9b80；10秒与1秒规则的参考/量门不同，但实际命中同一收到市场状态。主入场93305、退出94510、427contracts；全60个action×fee×delay×hold情景的状态、qty、quote/fee/净差逐项相同。不是两笔独立机会，也不叠加两机制收益。

|同一SUI主事件|5bps每腿|10bps每腿|
|---|---:|---:|
|FOLLOW（cost与pressure实际延续共享）|−0.96871355|−1.4677271|
|FADE（cost另一动作/pressure影子）|−0.1574349|−0.6564698|

pressure衰减规则仍无事件，不能把FADE影子当其真实触发或把无交易当零亏成功。单事件的两方向负值也不足否定整个压力机制。

## 完整网格与对照

3780 summary组已从原条件行逐组重建：原六1620、cost540、pressure actual540、pressure shadow1080；无事件均值null，所有失败/过期/冷/缺深度/尾部UNKNOWN保留。主15秒、诊断5/30秒、五人工延迟、费用5/10bps和500容量均固定，不挑最好点。pressure实际30条件和两方向影子60条件均有有效quote，本源30配对全部同qty；这不推及旧来源，任何数量不匹配仍不能称严格同qty。

A自身1秒动量同信号时点、真零WAIT/缺参考UNKNOWN及B固定35秒seed grid保留原预登记口径；它们是描述性/无条件频率对照，不是随机匹配因果试验。LEAD只ETH/SOL且本源0事件，不补造控制性能。人工延迟会同时改变entry和15秒exit，不是实测AI延迟。

## 有限审计

原六/对照有限原件核168有效+46删失、246自身1秒方向与567固定grid首quote/seed；cost数学核1个qualified与23个拒绝原asof；pressure数学核27固定首中末，加实际qualified事件的原flow/current/ref/cost/depth。

唯一重叠实事件全部60报价情景独立Fraction核通过：目标后首quote与250ms边界、完整可见深度、lot向下取整、entry notional+entryfee≤500、退出同qty、双腿fee与净差。cost全60列与该审计对象精确匹配。3780组全分母与null通过，旧21核心hash保持。有限同Owner异实现，不是第三方完整策略、实盘撮合或经济到账认证。

全部结果仍price_fee_delta事件研究，不是500账户/杠杆/保证金模拟；真实手续费、融资/mark、排队/部分成交、市场完整性未知。新三币本地registry不等于provider注册，Jev/Decisions实际权限/时延/质量仍未知，provider调用0。

本次没有新网络、配置、参数、安装、钥匙、订单或producer。旧job009失败不洗掉，job010与job011结果独立不合收益。整体12小时目标仍ACTIVE到03:16:33UTC，此为阶段复核而非最终截止报告；actualmodel/effort/speed UNKNOWN。
