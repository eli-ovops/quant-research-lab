# Phase007三机制预登记与开发核查
三机制/六个FOLLOW或FADE配置已冻结，WAIT保留；本阶段仅准备与旧001开发回归，未评价006新段或调用模型，12h总目标仍ACTIVE。

正式未来切分17:14:35.763208UTC，OS共享cut10794995081000ns，限定当前006 run phase006-32689-1791305087及同已验domain。只有实际os_shared_ns≥cut的收到消息可用于这些新规则的后续冻结后评价；006早段是开发，001旧processmono不能冒充共享或前向。clock_domain/代码/protocol/hash与7tests回执在新suite开发结果前冻结，collector32689/25952未改/重启，原17:29:47UTC截止继续。

|机制|固定事件语义|限制|
|---|---|---|
|FLOW_IMPULSE|原v12 received1s/absimb≥.8/同向mid≥3bps|聚合成交、receive序非真正先后|
|BOOK_STATE|当前/ref500ms误差≤250；双边top3价格完全同；abs notionalimb≥.8；对手top3≤ref50%；1s flow同向abs≥.5；mid500≤1bp|只是可见减少，不能定性撤单/吃单/意图|
|BTC_TRANSMISSION|BTC1s≥3bps+flow≥.8同向；ETH/SOL fresh/ref1s；固定beta1gap≥2bps同向BTC；follower自身absimp≤1bp|beta未估计，receive差非真实领先或套利|

共用同conn/domain、warmup/ref/current age≤250ms、35s perasset/perfamily cooldown。samebook档价变化不比较成撤单量。首ref严格asof以前，任何未来cache/缺字段/冷启动/旧ref/domain不对都WAIT；trade身份同asset/conn/domain内tradeId/source精确repeat移除，冲突/missingID使flow未知，count不乘volume。旧开发repeat/conflict均0。

执行金额模块逐字节v1.2 Fraction，500独立容量VWAP、15s主/5,30s诊断、delay0/250/500/1000/3000、fee每侧5/10bps、entry/exit首后book等待≤250ms。未挑hold、参数或方向。全部事件price_fee_delta是条件诊断，不是资金账户/AI成绩，真实fee/融资/mark/margin/partial与全市场序仍UNKNOWN。

旧001首20000完整行（已用开发）产生FLOW4/BOOK17/LEAD0、1260条件rows；有限异实现audit核21特征、984有效价量/两腿费/首quote以及276 null，PASS，FLOW asof/方向/特征精确原v12回归。BOOK 0delay/15s/5bps：BTC观察7/删失1 FOLLOW均-0.474642、FADE-0.509494；ETH5/3 -0.478722/-0.523618；SOL1/0各-0.540729。仅开发，不将这些值裁决整机制/择hold。LEAD没有真实dev事件，只有必要synthetic/因果测试，不凑N。

stateV2保留family、top3 imbalance/可见opposing ratio、flow、leader gap及own momentum符号、单资产深度/合约/成本，并明确source_asof_shared_ns/source_latest_book_shared_ns。历史默认is_live=false；live_input_gate除source≤feature≤send外，要求send-sourceasof及send-latestbook均≤250ms。正确OS域也不能把结束gzip的历史state拿当前book作live决策。旧003/004封存不改，新问题版本名impulse_suite_action_v2，provider transport NOT_IMPLEMENTED，未填mock延迟或confidence。

关联对照只是预登记计划：同asof follower自有动量sign（0=WAIT）；无leader候选需同asset/received1s bin/ownsign、所有输入可见且fresh，取目标前首个符合候选，不按结果选；不匹配标UNMATCHED，不伪造无leader样本。计划未实现匹配收益、不增加注册策略配置；时间簇/共同冲击必须描述，不能当跨币独立N。

产物protocol/suite/core/stateV2/tests/freeze/dev事件与条件delta/summary/有限audit/manifest。7 tests含价格档变动、三资产未来引用、beta非套利、cold/ref/stale/conn、v12数学、真实共享cut与live输入TTL。0网络/model/key/fee/install，实际model/effort/speed UNKNOWN；后续由PMO派单完整006冻结后评价，本阶段不等collector、不中断总任务。

