# Capture001当前终态验收入口
原phase001 READINESS是历史启动snapshot；本文件结合collector_final/真实session/PID与最终raw作为当前数据层入口。数据层有限验收通过；事件引擎的6条数值删失原因另有未解决限制，不能把该问题写成整体策略/全部实现PASS。

collector PID26221/session83334，job phase001-26221-1791300360。15:26:00.665657UTC启动、16:11:00.665657数据硬截止，finished16:11:00.945195UTC（约279.5ms清理grace）。collector_final=STOPPED/error null，真实session exit0，ps无26221。stop_reason组合deadline_or_bytecap，raw141,714,246B<240,000,000，结合截止证明因时间停止；不因文案合并猜bytecap。未重启、截断或修改原collector源码。

最终raw只读，不复制，SHA256 ed09711a3a95d3c049d7a252fb4892ceee7c4cbeba78ed021c3437f2ad7d6bff。217912完整JSON消息；first receive15:26:02.048080UTC、last16:11:00.617183UTC。ordinal连续、旧process monotonic非递减，六频道消息数：
|频道|BTC|ETH|SOL|
|---|---:|---:|---:|
|books5|26053|26142|25773|
|trades|72781|55499|11664|

公开订阅ACK计入上述messages，每频道首ACK无data。实测exchange_ts backstep0，但全部data缺prevSeqId，不证明全市场无漏采。books5变化snapshot是5档，不是完整queue/逐笔maker数据；trades聚合size已包含matched量，count不再乘。trade身份按instId/tradeId/source及完整px/sz/side/ts/count；相同重复0、冲突0、tradeId缺失0，adapter去重本次无输入/触发行为影响。

book最大接收gap约BTC3.680s/ETH3.425s/SOL3.426s；trade最大约4.842/5.301/5.555s。变化推送无消息不自动等于漏采，但固定250ms新鲜度因此拒绝若干状态/报价。相邻wall−processmono变化范围约[-.102,.101]ms，>50ms跳变0；完整45min累计小漂移仍不证明exchange时钟同步。旧raw没有OSshared字段，绝不倒填phase004共享时钟；002内部差分只在该collector域使用。

三个公开funding history均ok，带requestTime/原件、16:00UTC fundingTime与realizedRate：BTC .0000316622259844、ETH .0000168911603294、SOL .0000173435437754。SOL事件49部分窗口跨该时点（40个不同诊断rows），仅flag；未用mid代理mark填融资现金，全部economic financing net UNKNOWN。600ms近边界flag只是local/server时间不确定性诊断，不是改执行时点或盈利规则。

证据：input_freeze、capture_quality、audit/原失败回执、funding三raw及funding_times/window_summary、source最终collector_final路径、dev_regression。有限独立审计核22特征/234观察价差与其前后quote/费用，数据层及已观察价差层通过；追加删失原因核发现6条+1E-137 Decimal数值残余导致假深度拒绝，见numeric_censor_diagnosis，整体删失实现验收为PARTIAL_FAIL。原初版PASS保留为历史，不作为当前全部实现状态。

