# 041：job012固定十规则闭源复验

**本源固定主条件仍无合格盈利路线。** 原六规则15秒/名义0延迟，每费用488有效动作、108删失UNKNOWN，5/10bps正动作均0；costshock唯一BONK事件两方向主价费均负；pressure两规则0事件、收益null。

## 来源边界与冻结

job012/run phase006-80392-1791334671因逻辑bytecap提前停止，Owner28459 exit0、PID80392不存在、final error=null；完整root终态证据共同成立，不凭exit0认采集成功。217038行/239999262logical/27842666gzip，收到2478.743272秒（约41.31分钟），**不是完整45分钟**。实际finished01:39:10.536959UTC，计划01:42:51.298643UTC。

root完整CRC/EOF/typedclock/run/conn/boot/ordinal/rawarg、18data与18ACK分账、producercounts通过；logical SHA f16222abcbd3c58cd57112844e969d775d02a92c0e65e1a46fc6611b71df536c。尾部未收到报价不补造，必须UNKNOWN/删失。

完整prepare快照保留，Owner exit/root run receipt/mode/sourcehash绑定后，实际V2输入freeze01:42:53.655644UTC先于经济计算。两个前引擎准备错误（phasecwd路径重复、mutable stderr误入immutable freeze）都由guard/assert在计算前阻断，错误/旧freeze留档；仅路径/日志输入元数据修正。原21核心、24模块、规则/cuts/参数不改。

## 固定15秒、0延迟、500独立容量主结果

原六事件：FLOW169、BOOK127、LEAD2，共298；动作/fee行不是独立样本或可合账户收益。

|层|事件|主5bps有效/UNKNOWN|5bps正动作|10bps正动作|
|---|---:|---:|---:|---:|
|原六规则|298|488/108|0|0|
|costshock FOLLOW/FADE|1 BONK|2/0|0|0|
|pressure延续/衰减实际|0|0/0，均值null|null|null|

|同一BONK事件主情景|contracts|净price_fee_delta USDT|
|---|---:|---:|
|FOLLOW fee5|1374|−0.7745918|
|FADE fee5|1373|−0.7508165|
|FOLLOW fee10|1373|−1.2733561|
|FADE fee10|1372|−1.2492055|

主entry125156/exit127230，ctVal100000、ctMult1。不同动作/费用有不同lot向下数量，属于各自500容量，不是严格sameqty差额对照。双腿收费已扣、spread已包含VWAP，不再重复扣。只有一个事件不足否定cost机制，不能翻转动作或放宽门槛来救结果。

本源pressure没有事件，所以与cost不存在同asof重叠；若未来同asof/run/conn/asset则只能是一条市场事件证据，延迟/fee/action多行不算多次成功。旧job011同asof重叠证据保留，但不合来源收益。

## 完整网格与有限核验

3780格子全数从原outcomes重建：原六1620、cost540、pressure actual540/shadow1080；无事件均值null、所有non-observed净值null。主15秒、诊断5/30、五人工延迟、双费率、500容量全部留档，不选择最好点。A自身1秒动量同asof真零WAIT/缺参考UNKNOWN、B固定35秒seed grid保持，均非随机因果试验；LEAD2亦不能当独立BTC冲击样本。

有限原件审核：原六174有效+48删失、294自身1秒方向、528grid首book/seed；cost原数学1qualified+20reject，实际60quote条件32有效+28UNKNOWN，严格目标后第一quote/250ms、完整深度、fee-inclusive500与nextlot不够、退出同qty、双腿fee/净值核通过。

pressure27固定原asof拒绝数学通过；**pressure收益路径NOT_APPLICABLE**。其event_quote_audit原文件PASS标题是空集检查（0events/0conditions），未覆盖任何真实事件价费，不当收益层通过；空集产物不覆盖，新增audit_scope_receipt明确边界。

这些是同Owner有限异实现，不是第三方完整策略、真实撮合/到账或AI认证。经济结果仍事件price_fee_delta，不是500U账户；实际手续费、融资/mark、保证金、partial/queue与全市场完整性未知。人工延迟会改变entry和exit，非实际provider耗时。

当前source没有新增rule、币、API、收费、密钥、安装或实盘；provider实际接口/质量/时延仍未知、调用0。准备README作为冻结历史输入保留，当前状态以本REPORT/results为准。总12小时目标仍ACTIVE至03:16:33UTC，非最终截止报告。actualmodel/effort/speed UNKNOWN。
