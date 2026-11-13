# 阶段027闭合终态：本地公共输入能力与经济规则分别验收

A层有限处理/账务通过，B层两固定规则零事件。前者不代表策略盈利、模型/API速度或订单确认。实际API/模型/私有/订单0，provider adapter仍NOT_IMPLEMENTED。

源025 session22265实际exit0、PID58613不存在、final error=null/正常deadline。raw123491行/140362609 logical，15483 telemetry行/20075283 bytes，capdropped0、18实际data频道、完整CRC/EOF与raw/tele两hash和ordinal/run/conn/boot/domain/NS账一致。rawhash0641cad87d448f4923d22ff6b77068259ffea14ca197e4586a557413e4bf8273，telehash6dadab2eb60b284dc1ca5bbbce8c0aa797524e30130a8d78edd0f0611979bed1。接收首末覆盖1799.434754秒，进程完整30分钟另见producer identity/final，不把close grace当接收数据。

## A：真实本地时钟与状态分母

15483固定anchored-bucket样本中：state valid12470、state＋source/latestbook年龄ready12457；年龄≤250ms15139、过期341、未知3。cold21、stale/missing reference2992，1s成本门qualified0；raw全部ingest123491，sample/invalid/dropped与真实文件bytes逐项核过。不可用或冷样本不删除，quiet/无book更新不自动称丢采；未满足预登记fresh/ref条件时就是不可准备该状态。

|币|sample|state valid|state&ages ready|age expired|
|---|---:|---:|---:|---:|
|BTC|1800|1645|1642|72|
|ETH|1800|1710|1709|35|
|SOL|1800|1698|1698|21|
|DOGE|1800|1687|1687|14|
|XRP|1800|1679|1676|27|
|SUI|1798|1606|1603|23|
|PEPE|1750|1213|1210|32|
|WIF|1570|724|724|59|
|BONK|1365|508|508|58|

state-valid与age各有不同分母，cold/fresh可age合格但state失败。源接收到ready实际ms：median8.669、经验p95 9.609、max57.378；latestbook在ready的age median8.704、p95 86.052、max4852.038（过老值保留）。sampled ingest median0.103/p95 0.131/max1.502ms；snapshot0.191/0.223/0.819ms；validate12470样本0.394/0.492/1.706ms；canonical12470样本0.053/0.070/0.276ms。完整逐asset/status/分母/尾部分布见actual_local_timing_summary。

计时从ws.recv返回后app实际OS clock开始，包含raw解析/保存/cap检查等前置耗时，不含NIC、网络、WS内部queue、实际API或订单。样本有跨币/相邻bucket相关性，经验p95不是可靠独立尾保证；不把单独stage和重复校验加成“端到端交易延迟”。is_live=false/send=null/transportdisabled，no model send。

固定每币首/中/末审计共27点：12有效状态从原raw causalprefix重建，用当时record.snapshot end作feature_completed，并设置当时PUBLIC诊断label，整stateSHA吻合；15不可用样本只核原source、clock与null，不称15个完整状态内容通过。source/bucket/clock/age账也不能替代真实盘口成交验收，new3 provider兼容性仍未验证。

## B：026 cut后新两规则

只由026原codecut22:20:17.734314UTC/OS29136966188000后实际asof发事件；57852行前缀仅causalwarmup/不emit不占冷却，65639行postcut为候选分母。两个规则九币全部0事件，actual与shadow真实均值/胜率/PnL均null，future报价/fees路径真实验证NOT_OBSERVED；不能把旧core核验或synthetic fixture替代本规则成交收益验证。

|postcut主要拒绝类别|消息次数|
|---|---:|
|shock方向/10s不平衡不足|32843|
|10s过去成本空间不足|15442|
|10s或1s参考时点不足|13360|
|current book过老|2900|
|WAIT_INVALID_FLOW|1060|
|当前容量或反向depth不足|34|

冻结helper的WAIT_INVALID_FLOW同时涵盖total10≤0（10秒内没有收到成交量）及不一致总/净量等条件；此标签不等于raw被破坏或观测负量。不能把零新量当decay，真实volume/rate互斥分支在本段没有qualified收益样本；没有降低阈值/费率、换币或选择退出。27个固定postcut原raw exactmath首/中/末检查与原common拒绝吻合，未宣称完整第三方策略复放。

完整actual540组rule×asset×fee×delay×hold、shadow1080组再分FOLLOW/FADE已输出：0分母/null都显式存在，15s/0delay主、5/30及其它delay只诊断不择优。数量不匹配shadow专门保留非strict sameqty，censored分母不丢，shadow完美best不是model结果。原费用5/10bps/500独立容量/core字节不变，不相加资产/窗口/动作成资金组合。wrapper/code后置历史边界和schema/provider未实现保留，不称全blindOOS。

证据protocol/execution_freeze、source_timing_receipt、summary_receipt、actual_local_timing_summary、local_timing_field_audit、pressure_math_audit、pressure所有原数组与full summary、原prep tests和snapshots及manifest。旧025/026数据与rule无改动，Owner只补025终态receipt/当前入口。所有producer均终态，当前不启动新WS；12h总目标仍ACTIVE。
