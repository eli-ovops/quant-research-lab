# 每日实际开仓上限1/5/15：终态比较

**提高上限没有制造15笔机会，5与15完全相同；重入后的条件表现更差，不晋级。** 同一8月四周、EURUSD原市场，一个500USD持续账户，每个配置独立。所有六个结果保留，不选赢家、不相加，也不与旧固定0.1lot或9月独立账户叠加盈利。

| 日OPEN上限 | 成本 | 净USD | 期末USD | 收益 | 观察quote DD | PF净逐笔 | 交易数 | 日均/20weekday | 最高日笔数 | 达15日数 |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
|1|基础|+5.03|505.03|+1.006%|3.5854%|1.2523|15|0.75|1|0|
|5|基础|-3.78|496.22|-0.756%|4.3962%|0.8699|20|1.00|3|0|
|15|基础|-3.78|496.22|-0.756%|4.3962%|0.8699|20|1.00|3|0|
|1|压力|-8.54|491.46|-1.708%|3.3276%|0.5772|15|0.75|1|0|
|5|压力|-20.12|479.88|-4.024%|4.8814%|0.3669|20|1.00|3|0|
|15|压力|-20.12|479.88|-4.024%|4.8814%|0.3669|20|1.00|3|0|

全部有5个weekday无交易、期末无持仓；650USD权益/已实现余额目标均未到，没有新增目标退出。cap5/15没有cap阻断，实际最高3，因此在这份行情与冻结规则下，上限不是瓶颈；不能据此说其他策略永远只能3笔。

## 公平规则与风险

UTC23–03半开箱、13退出、M5当前MA50、offset10points、RR1.3不变。cap计实际OPEN，pending未成交、minlot/margin拒绝不计，UTC实际日期重置。首个正常PENDING保持原逐tick节奏；完成后至少到下一M5边界，空仓无pending，再用同一天区间与当前合法MA方向在原edge挂virtual breakout stop。已经穿过非法stop就等下一M5，不任意现价重入、不多pending/同时多仓、不强凑15。未触发pending持续到13取消。

三个上限统一计划损失预算：触发时当前可见quote加预设slip，roundedSL加预计出口slip与7USD/lot全佣金，按入场前净值1%，lot向下0.01/min0.01/max100，最低手超预算拒绝；contract100000EUR、100:1均代理。研究是因果virtual stop→当前quote估值risklot→假设市价fill，不是已经发送native挂单后改lot，也不用未来quote重算。风险拒绝撤销pending并等下一M5，不计cap；本轮未发生minlot/margin拒绝。

压力对市价/SL/13退出加逆向1pip；TP候选不满足limit则等待，合法时保守按limit；Decimal5位舍入沿上一轮。1%是含假定费用/slip的计划风险，不保证真实gap亏损。最高计划风险：
- cap1基础0.9991%，5/15基础0.9428%；
- cap1压力0.8953%，5/15压力0.9089%。
每配置有2笔亏损略超计划值，单笔最大实际净亏分别4.92/4.76/4.41USD，逐笔loss_over_plan留档。

统一日内净值保护：首个实际UTC日quote权益为基准，触及-5%后sticky锁到下一UTCday，取消/抑制pending、触发时再核；已有仓仍按SL/TP/13正常退出，无恢复资金。本轮全部日锁0次；必需合成检查与代码审过，不声称5%是实际损失硬上限。基础/压力按各自全风险保守sizing，所以frequency只在同成本内部比较，不与旧fixed0.1结果直接比。

## 净差匹配：不是把总差都叫额外交易亏损

以(day,dayordinal)匹配cap1与cap5，共有交易资本变化可改变lot：
| 同成本cap5减cap1 | 总净差USD | 额外5笔净USD | 共有交易sizing差USD | 额外费用USD | 共有费用差USD |
|---|---:|---:|---:|---:|---:|
|基础|-8.81|-10.04|+1.23|1.19|-0.07|
|压力|-11.58|-11.58|0|1.05|0|

基础1笔共有交易lot不同；压力共有lots相同。详细逐对表在independent_audit.json。cap5与cap15全部事件（忽略cap/cost标签）等价、权益文件hash完全相同，不只是期末巧合相等。

## 执行计数与成本

| 配置 | 佣金USD | 直接slip USD | 非法stop候选次数 | cooldown quote计数 | cap阻断quote计数 | 日锁quote/日数 |
|---|---:|---:|---:|---:|---:|---|
|1基础|3.43|0|0|0|53113|0/0|
|5/15基础|4.55|0|96|1404|0|0/0|
|1压力|2.59|6.80|0|0|44257|0/0|
|5/15压力|3.64|9.80|76|1245|0|0/0|

这些quote计数不是订单或交易笔数。cap1平仓后已因cap阻断，cooldown计数0不表示允许立即重入。压力TP等待377个quote；spread已在bidask执行内，未重复扣，mid诊断单列。所有资金、qty、fee、risklot、margin、cap、冷却、窗口与daily权益逐件留账。

## 数据、验证与交付

只读复用8月995146双边报价及预热，原CSV/hash从旧目录索引，没有复制44.96MB大数据。该历史已接触，不是新留出或未来成功。固定EST UTC-5/noDST映射、整秒/同秒原序条件等旧数据限制继续：全市场完整/真正到达顺序、native broker规格、latency/partial/margin-tier/stopLevel UNKNOWN，非原版EA或原生MT5认证。

收益前protocol和code/input freeze齐全。六个新增必要测试PASS；在不计算新收益的信号探针中，20个首正常PENDING的时点、MA与价格edge与原8月参考匹配，不要求新风险拒绝后的全部fills一致。共享只读Market的49闭合M5缓存只在bar边界更新、加入当前quote，六账户的资金/order/cap状态隔离；没有为了速度改判定。

不同实现账务audit PASS，核真实quote、fee/lotfloor/全计划风险/margin、实际OPEN cap、下一M5重入、日锁、窗口、daily净值与手续费、频率配对。是同一Owner不同账务实现，不是第三方或完整独立策略复放。父审接受实现与条件账务层，未接受盈利晋级。

results.json全部六配置；cap*_base/stress各ledger/equity/daily/results；independent_audit含共有/额外交易分解与5/15等价hash；signal_equivalence、protocol/execution_freeze、tests/source、manifest。运行程序在输出已存在时拒绝覆盖。0联网/安装/private/key/真实交易/生产/后台/新agent，旧目录封存未写，新文件约18MB内。AUTONOMOUS-2026-10-05-v1、ROUTING-2026-09-30-v3未变，目标Sol medium，实际model/effort UNKNOWN。已停止新增实验，阶段条件回放完成，真实盈利不晋级。

