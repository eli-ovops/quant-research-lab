# Phase004：共享时钟与有限public transport探针
本阶段完成当前host/boot共享OS时钟实核与一次公开ping-only探针，12小时总目标仍RUNNING。不能由此称真实模型/订单延迟、完整freshness、HFT或盈利通过。

当前Python3.9.6，legacy time.monotonic实现mach_absolute_time，进程起点不同。显式time.clock_gettime_ns(CLOCK_MONOTONIC)可用；getres约1微秒。两个真实新Python child的OS值：
|样本|parent before ns|child ns|parent after ns|
|---|---:|---:|---:|
|1|6270442017000|6270458704000|6270460420000|
|2|6270460426000|6270477858000|6270479347000|

两child严格在parent区间内，非synthetic fixture。clock_proof记录runtime、clock_info、legacy/process与OS/wall计数、只读kern.boottime及run identity；仅证明本机当前boot/运行环境可比，不保证跨host/重启或其他clock namespace。shared_clock helper不可用时抛错，不降级成legacy进程计数。

新causal_shared_gate基于真实proof域ID，要求source_asof_shared_ns≤feature_completed_shared_ns≤request_sent≤response_completed<new_book≤now，拒缺shared字段/domain错配/feature早于source/超时/过期book；不是靠两个caller bool证明相同域。4项必要tests PASS，包括真实parent-child原回执核。phase003原gate缺feature≥source检查保留为受限离线准备，未改封存文件；新helper只是补时钟层，sourcehash/connection/statechanged/risk/模型与权限仍须独立验证。

[OKX官方WS条款](https://www.okx.com/docs-v5/en/)由既有raw docs核literal ping→pong，无新增文档请求。唯一public WS、PID29757/session92996，TLS/主机名验证、已有127.0.0.1:7890系统proxy仅请求级继承，无auth、subscribe或重连；15秒OS硬deadline+最多3秒close grace、5pings/间隔0.25s参数在实测前冻结。正常close返回，2.339463秒内结束，5个样本均在deadline前：

|测量|实测ms|
|---|---:|
|冷连接|355.906|
|ping1|67.979|
|ping2|602.480|
|ping3|51.165|
|ping4|51.123|
|ping5|64.794|

raw保留literal send/receive、OSshared/legacyprocess/wall计数、域与runID，summary保存cold、全样本、截止与close。只5次、含一次波动，不能给可靠p95/单向网延迟或全链路模型认证。冷连接包括本机proxy/TLS/WS升级等，未拆单环节，不把不同p95相加。1个附加WS、0REST/AI/收费/keys读取，未换route或重试凑满。

父PMO public/time探针的条件server−local共同offset约[-38,460]ms，依赖服务器TS在请求内生成及缓存/时钟一致假设；header no-store不完成全假设验证。共享OS同host不解决exchange timestamp同步，原raw未回写或“校正”，该offset不作为精确单向延迟或模型时延。

future_clock_contract仅定义以后collector_v2保留exchange_ts/receive_wall/process_monotonic并新增真实os_shared_ns/clock_domain_id/boot/run identity。旧001相对processmono绝不伪装共享计数；历史002同collector内部差分仍有效。新实际采集版本尚未启动，旧PID26221/session83334/sourcehash不变，继续原16:11UTC数据截止。未来source-asof必须取实际shared记录，无历史倒填或clock relabel。

代码/参数在15:59:11UTC真探针前冻结；helper/probes/tests/clock raw proof/ping raw+summary/audit/results/future contract/manifest全部保留。有限本地与public transport层audit PASS；无安装、模型API、私有/key/系统clock改动或旧stage写入。实际model/effort/speed UNKNOWN，目标Sol medium。下一步PMO验本阶段后安排原collector正常收口与新共享域数据，预算/权限未答不实现付费transport；本小阶段不结束总12h窗口。

