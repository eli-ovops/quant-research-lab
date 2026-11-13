# Phase001 readiness：采集进行中
状态：COLLECTOR_RUNNING，阶段未完成，12小时总目标未完成。已接受的是公开可得性、启动与初始数据层；完整45分钟数据、实际AI接口/延迟、费后策略、账务和收益仍未验。

唯一采集PID26221，exec session83334，job phase001-26221-1791300360，WS connId37c6a9a1。15:26:00.665657UTC启动；数据接收保存硬截止16:11:00.665657UTC，另有monotonic45min与raw240MB上限。正常close/final summary为截止后必要清理，最多recv timeout3s及close timeout3s的grace，不代表继续采样或延长实验；超过边界的消息不保存。RUNNING中的stop_reason=deadline只是预设原因，不是已经停止。collector_final.json与PID结束尚待核验，once lock禁止重复启动，本阶段无自动重连，不改运行源码。

BTC/ETH/SOL三SWAP公共spec/book/recenttrades均真实成功，state live、linear、USDT结算，ctMult=1。数量单位为contract，不当成USDT或币数量：BTC ctVal .01BTC、ETH .1ETH、SOL 1SOL；三者lot/min均.01contract，最小币量分别.0001BTC/.001ETH/.01SOL。tickSz分别.1/.01/.01。raw和instrument索引留档，账户资金、费率层、撮合权限无查询。

[OKX官方契约](https://www.okx.com/docs-v5/en/)：public WS books5为100ms变化推送的5档snapshot，不是全量queue；trades按taker订单/成交价/source聚合，count为匹配数，tradeId为聚合最后ID。实测seqId存在、prevSeqId缺失；同序号或跳序不能自动作为全市场缺采证明，snapshot也不能重建深层撤单/队列。未订阅VIP频道、无auth消息或密钥，TLS证书与主机名验证保留。已有系统proxy只请求级继承，没有修改配置/身份或绕拒绝。

15:26:55UTC初始前缀5151条、3,254,337字节；local ordinal连续、monotonic非递减，三book均未cross或空。book p50接收减exchange_ts约96/110/115ms、p95约426/451/472ms；trades约168/192/141ms、p95约538/526/515ms。只是一段短样本，包含clock offset、上游发布与传输/排队，**不是AI延迟，更不是全链路订单时间**。时钟同步UNKNOWN。六频道都有data，BTC/ETH/SOL聚合count>1样本509/706/98，不能将每条当单笔maker fill。可按quality_snapshot中prefix字节与SHA复算，raw仍持续增长。

公开操作12/12：9次MCP REST、1次官方OKX web读取因>4MB工具上限失败、1次同官方原URL curl成功、1次Jev概念页。官方raw HTML5.25MB/headers、选取普通books/trades章节留档。此普通读取大小失败不是权限拒绝；未用历史已拒绝Jina入口。阶段不再新增公开请求。4项本地deadline/bytecap/raw元数据/重复start测试PASS；采集源码hash与真实identity一致。

[Jev官方System One概念页](https://docs.typesafe.ai/concepts/system-one)确认text/JSON状态、typed决策及概率、POST /v1/systemone和jev-latest alias。完整baseURL/auth/request-response schema、本账户权限/预算及版本pin未核，未构造调用或测毫秒成绩。Decisions实际契约/权限仍UNKNOWN；普通Responses/结构化输出不冒充它。付费预算待用户，收费调用0、密钥读取0。概率不能直接当金融收益概率。decision_interface.json只是本地paper-interface草案，不是两个供应商API schema。

已实质补读当前STRATEGY_DESIGN纠偏：单次仅一提供方；共同特性为紧凑状态的快速有限动作，不串联两个模型、不开三条完整路线，不继续EURUSD。下一层必须先用receive顺序增量状态，模型响应之后新可执行book才可纸面入场，超时/断序/过期删失。行情本地ordinal不同于全市场完整序号；跨资产接收先后不证明真实领先。

当前交付READINESS.json、instrument/model-contract/paper-interface、quality_snapshot与可复算analyze_quality、collector.py/test回执、source_manifest（provisional，live raw非终态hash）。Owner只写phase001；control.json由PMO维护。已读AUTONOMOUS/ROUTING-v3/HANDOFF-v1/BLOCKERS未变；目标Sol medium，实际model/effort/speed UNKNOWN。未安装、私有查询、交易、旧monitor或追加collector。等待数据增长不算agent工作时长。

下一步：复用同PID至正常截止，核final/PID/raw完整hash与最终质量；在随后授权阶段做成本/机会寿命及人工延迟退化曲线。没有调用与资金证据，不填写AI表现、账户盈利或实盘可成交。

