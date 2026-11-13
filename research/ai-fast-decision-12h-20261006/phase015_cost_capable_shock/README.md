# 阶段015：固定成本与主导成交规模门槛

实现与有限检查层通过，旧job006开发样本为零事件；不是盈利成功，也不据此否定全部机制或放宽门槛。唯一job007已在规则冻结之后启动，未来结果仍null，实际AI/provider尚未调用。

新增仅 COST_CAPABLE_SHOCK_V1 的FOLLOW/FADE，旧六规则封存不动，总八配置。固定六币、原1s因果Features/同run连接OS域/当前及参考fresh≤250ms，absflowimb≥0.8、midmove与收到净成交方向一致。用asof盘口原Fraction500含入口fee容量，分别估long/short数量与同数量立即reverse VWAP。fee5每腿下成本必要位移：long `(E*(1+f)/(X0*(1-f))-1)*10000`；short `(1-E*(1-f)/(X0*(1+f)))*10000`。两方向都可估且足够深度才取max，过去abs1s位移必须≥max＋固定5bps缓冲。

同时要求 dominant_received_notional=(total+direction*net)/2 ≥ 原1s参考盘口对应方向对手top5 `sum(price*contracts*ctVal*ctMult)`。参考ask用于buy冲击，bid用于sell。ExactFlow使用真实已收到trade px/sz、原tradeID/source/signature去重，所有notional/净流/ratio与bidask mid比较用Fraction精确计算；聚合count只是身份metadata，不能再乘volume。没有任意epsilon吞边界。它是过去报价/成交代理，不是预期收入、强平、撤单或实际成交确认。

新35s冷却只在完整成本＋规模门槛全部通过后启动，旧3bps门槛或其它family冷却不拦后续强冲击。退出仍15s主/5,30s诊断、五人工delay、fee5/10压力与原500sameqty，fee10不重选触发集合。不择最佳持有期/方向/币种。新family未接入009 provider schema，不借旧family别名伪称兼容或实际AI成功。

6项必要测试PASS，包含两方向费用公式、缺深度、精确阈值±1E-30、聚合count不乘量、1s因果过期、早期小冲击不启动新冷却。原gate首次prepare freeze后仅补充perasset WAIT计数/首末ordinal日志，所有旧prepare源码/hash保留；发生于任何数据运行与新采集前。最终规则cut20:20:25.499116UTC、实际OS21944730989000，两clock采样原件见execution_freeze。

闭合已用job006开发检查：六币全部0事件/0条件行，均值和成功率均null，不填收益0。WAIT分层如下（这些是接收消息决策次数，非独立交易样本）：

|原因|次数|
|---|---:|
|冷启动/过老参考/来源未知|4411|
|流不平衡不足/方向不符/无流|100724|
|过去成本空间不足|21058|
|当前入口或反向同数量深度不足|139|

原Feature source异常/repeats/conflicts/missingtrade计数均0，全部WAIT按币与reason首末ordinal/wall保存 development_counters_wait_receipts。成本门槛已经拒绝所有剩余候选，所以真实volume合格/冷却/持有结果没有被触发，不能把volume因子称已通过实数据验证；边界与冷却仅必要合成测试通过。有限异实现从原raw独立Fraction重算16个各币首末成本/深度案例，rawhash相同，数学与拒绝原因吻合；不是第三方或完整独立策略复放。源已接触/使用，开发检查不是OOS。

job007启动层：PID51279/session62552/run phase006-51279-1791318047，20:20:47.126782→21:05:47.126782UTC，原六币12ACK及data、首100 actualOS/run/ordinal核通过。TLS/hostname与原request proxy、noauth/noautoreconnect，logical240M、gzip实际183797554B更严、phasephysical240M/global2GiB。全部旧PID终态后才启动，once锁保护；新capture不读取livegzip收益、不自动续开。完整终态和未来评价另待有限派单，rootcontrol由PMO维护。

真实费用/融资/queue/partial/mark与完整市场源未知。未来模型调用/权限/预算/时延null；总代码12小时目标ACTIVE，等待采集不能记主动研究工时。证据：protocol/execution_freeze/tests、development_adapter_freeze、原source_guard、开发事件/全summary/WAIT receipts、audit及manifest；当前source入口在phase006_shared_capture/CURRENT_CAPTURE.json。
