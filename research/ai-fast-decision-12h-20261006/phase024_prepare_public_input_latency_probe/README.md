# 阶段024：公共输入本地处理计时probe准备（未启动）

有限准备通过，8必要边界测试PASS；0新WS/REST/model/key/paid/private/install。当前没有实际live计时、没有收益/订单，原008及旧代码不改。未来正式入口probe_collector.py，默认PREPARE_ONLY在任何连接/once锁前硬拒；复制模板首行也硬raise，不以文件名或缺路径冒充安全门。

未来需root具体新授权文件 `PMO_PHASE024_PUBLIC_PROBE_AUTHORIZATION.json`（approved=true/scope=phase024_public_local_processing_probe/WS_once=1/model_API_calls=0），并指向020实际闭合评价的root PMO验收（accepted=true/scope=closed_job008_fixed_rule_evaluation/source_run匹配），不是准备层验收。020状态必须CLOSED_JOB008，008及全部旧PID真终态；ps执行错误为UNKNOWN，不能当不存在。授权结构约定在protocol，当前没有该权限，不会自动启动。

启动前核assets/fixed_assets/9真实registry一致、books5/trades18频道，缺键或错配不留到连接后才报错。九规格原字节来自018/008注册，新本地schema file允许probe校验nine；这只是本地数学范围，V3.1真实provider新三币仍UNKNOWN/NOT_VALIDATED，不称九币API接入。

未来所有消息按received序ingest；每币首条market data建立anchor，每个anchored 1s bucket第一条实际message采snapshot。相邻sample可小于1s，不是距前sample至少1s；跨缺口不补造sample。cold/stale/depth/invalid/error/qualified与slot缺失分母保留，不按PnL/状态优劣挑样本。实际CLOCK_MONOTONIC received→ingest→snapshot→validate→canonical准备完成分别计时，source/currentbook的实际ready age另列；不是NIC/模型/发送/撮合时间。

状态有效与年龄分开：ages_within250ms是源/最新book实际age（缺book为null UNKNOWN）；ready_state_and_ages是state_valid且ages=true。cold但fresh可以ages=true而ready=false，不能叫TTL过期。所有snapshot is_live=false，transport DISABLED/send timestamp null，输入诊断标签PUBLIC_LIVE_LOCAL_PROCESSING_NO_MODEL_SEND。newbook实际执行hash/容量与订单未验，qualified只过去代理，不当预期收益。

未来一个≤30m job，绝对stop=min(start+1800,03:16:33UTC)，同官方public地址/TLS hostname/原request proxy/noauth/noautoreconnect。raw＋计时JSONL共240M logical硬cap，phase物理240M/global2GiB写前预测同时含gzip实际trailer/未flush字节、明文sample及telemetry，保留1M结束metadata余量；gzip≤230M或更小动态余量。不能靠计时另文件绕cap，达到界可提前停。raw成功保存立即记source channelledger，processing失败/telemetry截断也不失配；计时丢弃因cap单列，不静默填成功。高频物理cap检查/I/O会计入实际receive-to-ready，不能把此pipeline假装纯hot snapshot。

Incremental/state/rule副本仅本目录使用，旧collector/规则/fees/hold不变；probe没有未来价费计算。8tests包含真实receipt拒绝truthy、020准备未完成、pid UNKNOWN、九规格/缺assets、网络硬拒、cold/fresh分离、1Hz接口和逻辑/物理cap。fixture明确SYNTHETIC_INTERFACE_TEST，不报告模拟模型时延。有限静态/接口audit、code/protocol hash见execution_freeze；真实输入与终态验收待下一scope。

先完成原008闭合＋020固定评价及PMO验收，再由root派实际probe，不自动开source。12h总目标ACTIVE，actualroute UNKNOWN，不把准备通过或等待算盈利/实际agent执行时长。
