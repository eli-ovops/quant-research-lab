# 阶段021：封存主场景的报价与费用归因

当前负值不是全部来自费用：每费用场景350有效动作中，108个gross正但不足付费，242个gross已非正；fee后全部负。gross已经包含买卖盘口、方向路径、固定15s退出和该费用口径对应数量，不能称纯mid预测、选对方向比例或真正零费策略收益。未降低手续费或改变hold/币种以救结果。

只读封存017 event_deltas 的15s/0名义delay，776行=两费各350有效＋38删失。原hash/core/报价不变，没有策略rerun或新配置。每family×asset×FOLLOW/FADE×fee5/10独立报告，不相加为组合/账户收益；无事件group为0分母/null。future_only_cost_attribution.json提供72组gross/显式fee/net mean、median、p10/p90、min/max、gross及net正数、单腿break-even分布和实际entrydelay分布，含删失reason与available延迟数量。

举例（15s/0delay/每腿5bps，单位USDT）：BOOK BTC FOLLOW平均gross+0.04952、显式fee0.49644、net−0.44691；FLOW DOGE FOLLOW gross−0.07442、fee0.49925、net−0.57367。前者可观察价差很小而费用超过它，后者报价/方向路径本身已负、费用进一步恶化。多数非空组的平均gross绝对值远小于约0.5的双腿费；这只解释当前假设的算术，不识别具体市场机制，也不证明真实费率或改善方向即可盈利。

单腿break-even `gross/(entry+exit)*10000` 逐事件计算，fee5主最大约4.2776bps，低于固定5bps假设；分布全部保留，不把它作新费率候选或将负break-even称可付正费用。spread已含在gross的两端VWAP，不再次扣。人工0delay后的首book实际等待不等于AI/网络/订单确认时延；观察与删失的available延迟分别报告，不把失配或不可执行报价当成交。

同event/同fee/两方向都有效/合约数量相等才计算事后bestaction上界。fee5为174个同qty双有效、19个删失UNKNOWN、1个qty不匹配UNKNOWN；fee10为168/19/7。有效上界仍全部负，max分别−0.0721434和−0.5714868USDT。不将WAIT0当收益，不丢删失分母、不重新调整qty；两方向原结果仍可各自审阅。该未来完美选择不可实现，不能当模型成绩或策略收入。

所有派生文件为future_only诊断，不进入V3/模型输入或策略选择。2项必要算术边界测试PASS；独立Decimal核700有效行的gross价量列/双腿fee/net、76null、72组分母/均值/room max，以及342同qty配对、38删失配对、8qty不匹配配对，源hash不变。原quote验收沿017有限124有效＋28null边界，本阶段没有新增原quote或完整策略复放。

真实fees/funding/queue/partial/mark及完整市场源仍UNKNOWN；此处只有已观察报价与假设费用。实际AI/provider结果null，source008保持唯一原PID54627/session57237，当前不读live收益/不改producer。总12h ACTIVE，接着只作已授权020发布元数据wrapper修正，不新增采集/参数。
