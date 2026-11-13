# 阶段017：固定成本门槛的新episode复核

COST_CAPABLE_SHOCK_V1六币全部零事件；FOLLOW/FADE的均值、胜率和持有价费结果为null，不是收益0或盈利成功。新45分钟接收episode仍未找到适格信号，不降阈值、手续费或换退出规则。实际AI结果仍null。

原六规则上下文194事件=FLOW65/BOOK129/LEAD0，11640全网格条件行10564有效/1076删失。15s/0名义delay的每腿5或10bps，各350有效动作全部负，另38删失UNKNOWN。BTC FLOW及全部LEAD无事件在summary为0分母/null；未把旧4/5/6/7episode、金额、币种、方向或持有窗相加成账户收益。全部mean/median/tails/正比/分母见primary_vs_A_summary和all_signal_summary，5/30秒只作预登记诊断。

新门槛按015原字节与Fraction：原1s因果/current/ref fresh≤250ms、absflowimb≥.8且同方向，双方向asof500入口含费容量＋同qty反向VWAP估必要位移；abs过去位移≥max required＋固定5bps，然后dominant received notional≥参考对手top5规模。新35s冷却仅在全部qualified后开始。主触发固定fee5，fee10压力共用事件集合，出口和五delay不变。它们是过去量与成本代理，不是预测收入、撤单或强平证据。

|WAIT原因|消息决策次数|
|---|---:|
|冷启动/过老参考/来源未知|7629|
|无流/不平衡或方向不足|140896|
|过去成本空间不足|19799|
|当前入口/同qty反向深度不足|75|

没有volume不足、qualified或新cooldown记录：所有候选先被成本/深度条件拒绝。因此真实volume合格条件与新family持有执行尚未触发，不能称已通过真实数据验收。每币WAIT计数与首末ordinal/wall全部保留costshock_WAIT_counters_receipts，原Feature source异常/repeat/conflict/missingtrade均0。六币newfamily全窗口/费用/延迟summary明确0事件/null，不制造成交或成功率。

A同signal asof严格1s received动量：107真零WAIT、82方向可用、5ref过老UNKNOWN。BOOK500ms不当1s，WAIT明确不交易/费0，UNKNOWN=null；更少亏往往来自等待，不当alpha。B固定seed/35s timegrid共458 asof、10 grid拒绝，六币各费用有效结果均负；其频率和分母不同，非matched随机试验或无冲击反事实。A/B原特征、事件、分母、median/tails与删失全留档，不据它们择参数；时间簇和重叠持有不当独立N。

源007正常deadline21:05:47.186912/errornull，session62552 exit0、PID51279不存在。168411rows/189320046logical/20735211gzip；全gzip CRC/EOF、hash56d480a06816bd902b282294481c603f8064dc5c46302dce295929ad3b647033、ordinal/run/domain/OS序、12实际data频道和初100核验通过，ACK计数另列。所有collector终态，无自动续采。

015真实cut20:20:25.499116 / OS21944730989000早于00720:20:47起采，整段是固定门槛后新接收数据。V3.1 schema freeze20:42:39.496789晚于起采，OScut无原件保留null；没有schema实际调用，不冒称全段模型前向实测。wrapper先pre_terminal_code_freeze，terminal后只补原hash，再execution_freeze后全体运行。旧核心/controls/rule字节不改，但旧开发、后置guard、本host episode及完整市场限制保留，不称全盲OOS。

2适配测试PASS；有限异实现核原gzip124有效价量/双腿费/首after时序及28null、189原1s符号、458grid首book/seed；新gate独立Fraction16个各币首末真实成本/深度拒绝案例PASS。不是第三方完整策略复放。新family0真实事件，旧上下文价费核不能代替新family持有验证。实际fees/funding/queue/partial/mark/全市场完整性UNKNOWN；spread含VWAP不重复扣，人工delay不是真实AI时延。

证据：protocol/pre_terminal_code_freeze/execution_freeze、capture_terminal_receipt/source_guard、costshock原事件/全summary/WAIT、旧上下文/A/B、tests/audit/shock_audit和manifest。报告生成首次stdin中文编码失败，改用patch写入；保留此前未含报告的manifest/seal快照，最终manifest才是当前证据入口，原计算未变化。总12h ACTIVE，尚未执行018或开新source。
