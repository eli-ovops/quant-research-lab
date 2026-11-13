# 后续采集v2提议（未启动）
复用唯一Owner，在PMO明确续接后顺序新建有限collector_v2；001已正常停止，不复制/并发collector。仍BTC/ETH/SOL keyless books5/trades，无认证、订单或付费调用。每作业明确45min/globaldeadline双限、once lock/PID/session、连接/失败预算、byte上限，源码/协议在新数据前冻结。

新增实际OS CLOCK_MONOTONIC、明确当前boot/domain/run identity，同时保留wall与旧process counter；绝不转换历史001。采用阶段004实核helper，live特征/未来模型计时须完整同域因果链。考虑直接gzip写新JSONL作为新数据格式，full raw与时间戳保留、无旧文件压缩/删除/覆盖，可降低12h/2GiB存储压力；具体预算由PMO登记，绝不据此无限采集。

先处理已发现size_capacity极小正budget残余的正确性问题并冻结修复版本/必要tests，再将同触发规则用于新窗口。原v1.1/本轮null证据保留，修复不是放宽trigger/fees/hold或挑收益。没有用户API权限预算则保持Jev transport禁用，公开数据和离线事件研究继续，不伪造AI成绩。

