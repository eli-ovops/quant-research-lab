# Phase002：离线事件研究引擎（开发样本）
本阶段完成固定前缀引擎与有限审计，12小时总任务继续。4个事件、约5分钟开发数据不足作整体策略裁决；15秒主诊断在两费用假设、所有人工延迟下均为负，不称AI失败或账户盈利。

冻结首20000完整消息，13,391,314B，SHA256 5a70d5e0e938a6c23be16a17c7354a2df684dca26bbebee40c6d4d84265e91cc，最后ordinal20000/15:31:08.567UTC。原append-only未改，不对正在增长全文件伪造冻结hash。事件BTC1/ETH1/SOL2；BTC与首个SOL接收仅约24ms之差，不能视为4个统计独立事件或真实领先关系。

唯一触发：收到时间(asof−1s,asof]成交notional净/总绝对失衡≥.8，同方向可见mid变化≥3bps；book接收新鲜度≤250ms，完整warmup/双边无cross/同conn、每资产35秒冷却。trades为聚合、seq/全来源完整UNKNOWN，未解释接收顺序为真实成交先后。固定FOLLOW/FADE及WAIT；15s主、5/30s仅诊断，人工延迟0/250/500/1000/3000ms，费每侧5/10bps为未验证假设，不按结果挑参数。

**v1→v1.1正确性修复透明记录：** v1首次结果后，PMO发现参考book可过老、首后quote可等任意久。原v1 code/freeze/events/240价差保留。v11目录在15:41:45UTC重新冻结：ref距(asof−1000)≤250ms；entry/exit各取严格在目标时间后的首有效book，须同conn且等待≤250ms，否则删失、不择后报价。连接改变即不搜索后connection。触发阈值/费用/动作/人工延迟不变；不是独立新样本。
v1.1事件仍4、接受224条、16条expired_exit_quote删失；5s/30s诊断受影响，15s主结果不变。新增4边界测试PASS、原6因果/数量测试PASS。首次v11冻结辅助脚本相对路径错误在任何v11结果前修为绝对resolve，失败回执留档，非收益后改规则。

|人工延迟ms|实际entry接收到达总延迟ms范围|目标后等首quote ms范围|
|---:|---:|---:|
|0|23.662–143.645|23.662–143.645|
|250|272.789–335.121|22.789–85.121|
|500|530.988–673.793|30.988–173.793|
|1000|1059.951–1174.009|59.951–174.009|
|3000|3015.992–3224.026|15.992–224.026|

这些是固定人为决策延迟加实际quote等待，**不是API/AI时延**。freshness按receive时钟，exchange clock offset及源发布年龄仍UNKNOWN；合法接收book不证明实时撮合或无漏采。

15秒、0人工延迟、每侧5bps，每资产平均事件price_fee_delta（USDT）：
|资产|事件数|FOLLOW|FADE|
|---|---:|---:|---:|
|BTC|1|-0.605424|-0.378564|
|ETH|1|-0.407321|-0.595001|
|SOL|2|-0.601860|-0.478760|

完整每资产×动作×延迟×持有×fee结果在v11/asset_summary.json，逐事件在event_price_fee_deltas.json；不将不同币种/配置相加或拼成账户收益。results里的pool mean仅描述性事件均值，不是账户统计。WAIT表示观察且无event价差。无有效出口/深度/新鲜度就price_fee_delta=null，不填零损益；16条删失不能当避免亏损。

500USDT是每事件独立容量约束（entry名义+entry fee≤500），不是持仓组合或保证金账户。qtycontracts Decimal按ctVal*ctMult转币量、lotSz下取整；entry买asks/卖bids深度VWAP，exit反侧同qty，不重按500 sizing。若5档不足容量或出口深度不足则删失，未假设partial/queue/深层撮合。spread在VWAP内不重复扣；两腿手续费按各自notional计。真实费层、融资、short margin和订单执行未知，不报告500U账户收益/强平或实盘可成交。

v11异实现有限audit从原prefix重算4个已接受特征、224观察价差的首quote/单位/最大可覆盖lot/深度/两腿费，以及16过期null，PASS。同Owner不同实现，不是第三方/全触发策略独立复放。每事件state只取asof及之前的received输入，v11/compact_states保存book深度/spec/flow/成本与WAIT/FOLLOW/FADE接口；provider_adapter NOT_IMPLEMENTED，decision_completed_timestamp null。离线构造不是实测live特征延迟，未模拟模型返回成功。

Jev基本HTTP契约已由PMO公开复核，引用根PMO_PROVIDER_CONTRACT.md，不能再把baseURL/basic schema全说UNKNOWN；权限/收费/实际响应时延仍未知，Decisions真实契约UNKNOWN，不用Responses冒充。0公开请求/付费/key读取/安装，实际model/effort/speed UNKNOWN，目标Sol medium。

所有源码、协议、前缀、freeze、tests、v1/v1.1结果/有限audit/manifest保留。phase001 collector26221/session83334继续原45min截止，未改其源码/重启或control。下一步在PMO续接后先做Jev离线request/response adapter，再将固定规则用于后续新接收数据；当前开发小前缀不裁决整条机制、总目标至2026-10-07T03:16:33UTC前不标完成。

