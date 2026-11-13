# Phase006当前采集入口
当前是job002_corrected_cap **RUNNING，不是采集完成**：PID32689、exec session25952、jobphase006-32689-1791305087、WS conn e57cd14c。16:44:47.429717UTC启动，数据绝对截止17:29:47.429717UTC（与global截止取小），wall+OS共享clock双限，close grace最多3s。6公共订阅均ACK/有data，TLS主机名验证、已有proxy仅请求级继承、无auth/重连/REST/model/key/install。

初job001 PID32079/session24730已因新的logical240MB硬要求正常SIGTERM停止，不是45min完成。原冻结guard500MB不hotpatch、不删除数据；实际9831msg/logical9,988,193B/gzip847,574B远低240。gzip trailer/CRC、完整ordinal与初100prefix相同均核实，原件和logicalcap变化回执保留。PMO明确授权追加一次修正版WS，非auto reconnect；全局WS总4。

job002在新子目录、新source/protocol/once lock重新冻结。每行先检查logical计数≤240,000,000，事务性zlib.copy预计算当前row压缩chunk与完整finish trailer，只有compressed合计≤230,000,000才commit，否则不写该row；关闭footer预算已预留，不以压后小体积允许无限解压。stage实际物理≤240MB、global任务物理≤2GiB另有headroom/有限检查。3 readiness tests PASS：gzip硬cap与有效trailer、逻辑cap/单连接代码、既有real sharedproof namespace；不重跑原时钟实测或旧策略。

所有receive是在WS.recv返回后，本地应用层，不是假NIC/交易所时间。先OSbefore，后wall/processmono，再OSafter；保存sampling_OS_bracket_ns以记录串行采样偏差，保留旧monotonic_ns/process字段以及真正os_shared_ns/clock_domain_id/boot/run identity。启动只读kern.boottime与阶段004当前boot proof一致；不升级Python或改系统clock，不倒填旧001计数。初100采样OS bracket最大6µs，OS非递减；较长流skew/status另列，不作为AI时延。

初100消息是同一writer已commit流的固定明文样本，不是第二条事件流；ordinal1–100，SHA cfc7efcc864e88bb362ff768dea42984591033e0dec0bd4b3664fe0f6a76f90c。源码确保相同enc写gzip及sample；当前通过JSON/ordinal/domain/time检查。新gzip尚未正常关闭，CRC/trailer及样本对压缩流prefix的独立等价核待final，不能用live EOF当数据损坏或完整。活检用PID/status/sample，不启动副本、读取全live gzip或重新连接。

CURRENT_CAPTURE.json指向job002，旧status STOPPED保持历史，heartbeat不能据job001计划截止认定仍live。新数据仅用于已在16:31冻结的v1.2数学修复+原FOLLOW/FADE基线；尚未冻结的盘口/关联机制不能拿它称前向验证。v12必要审计已通过，旧005 PARTIAL证据保留；真实模型/费用/账户执行仍未知，0付费、12h总目标仍ACTIVE。

下一步按同PID有限截止核final/session/ps、正常gzip关闭/解压logical hash/ordinals、首100等价、数据字段和clock漂移；再按预登记baseline评价。没有权限预算不接收费transport；当前只报启动/初数据层，不报最终数据或账户/AI盈利。

