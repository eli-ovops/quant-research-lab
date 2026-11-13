# 阶段025：真实公共输入的本地处理probe（已启动，未终态）

唯一WS已启动，有限启动层通过。PID58613/session22265/run phase006-58613-1791324377，22:06:17.556972UTC开始，22:36:17.556972UTC数据截止或cap更早，close grace3秒另计。18ACK及后续频道帧、首100actualOS/run/ordinal核过；真实timing已落盘，完整源和完整统计仍待终态，当前不称全部30分钟完成。

scope绑定root一次性授权原件和020实际CLOSED_JOB008验收，全部旧PID不存在。024代码副本位于新025，旧seal/source不改；仅强化activation receipt当前job/30m绑定，规则不改。activated目录没有重跑PREPARE_ONLY subprocess测试：原测试存text参考，test_probe.py硬raise，避免它意外启动第二连接。正式只调用一次probe_collector入口，mode/code/hash在网络前freeze。

固定九币18频道，同public官方地址/verifiedTLS/hostname/原requestproxy/noauth/noautoreconnect。logical raw＋telemetry240M、phase物理240M/global2GiB写前预测，实际gzip229904751B更严；gzip trailer/未flush字节、timing和sample均计cap，不能绕cap另存计时。root auth/model API0，private/key/order/install0。

实际profile从ws.recv返回后app的OS clock起计：包含解析、保存raw、物理cap检查、ingest、snapshot、validate/canonical/statehash准备；不包含NIC/网络/WS内部排队/模型API/交易确认，不能叫端到端交易时延。固定first per anchored1s bucket采样，相邻sample可<1s，gap不补；所有source消息ingest、cold/stale/invalid/depth/slow/error/qualified/age unknown分别保留。

状态有效、是否qualified、实际source/latestbook年龄及ready_state_and_ages是不同轴，cold fresh不当age过期。snapshot始终is_live=false/send_timestamp=null/transportdisabled，PUBLIC_LIVE_LOCAL_PROCESSING_NO_MODEL_SEND只是输入与本地处理诊断。没有未来价费、订单或真实模型成绩；localnine registry只数学probe范围，V3.1实际provider新增三币仍UNKNOWN/NOT_VALIDATED。

startup_receipt/activation_preflight/execution_freeze/first100是启动证据，raw gzip和local_processing_timing/status仍增长，不把它们全文件hash当已冻结完整输入。首20timing仅核域/run/is_livefalse/model0，不挑最快统计；终态后再做完整CRC/ledger/时钟与所有分母统计。总12h ACTIVE，等待不算主动研究时长，不启动副本/自动新source。
