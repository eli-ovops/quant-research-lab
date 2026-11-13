# LSK / G 价差取证（audit_v2）

当前工作是公开行情研究。没有账户、下单、转账或真实模拟成交功能；旧生产系统不在本目录修改。2026-09-24 起停用 50 币轮换，固定 LSKUSDT、GUSDT，最多运行 24 小时，到时停止，不自动续期。旧源码已保存在 review_packages/before-audit-fixes-20260924T020609Z；旧行情和报告保留，不追溯改写。

## 计算与限制

- 100 USDT 为主观察金额；500、1000 只是容量对比，不是额外独立机会或资金分配。
- base 场景两边各 10 bps；higher_gate 场景 OKX 10、Gate 20 bps；均额外留 5 bps。这些是费率假设，不是 LSK/G 的真实账户费率或费率上限。Gate 公共币对 fee 字段已弃用，不再读取它参与计算。
- 按多档盘口计算，共同数量步长向下取整，检查公开的最小数量、最小金额和市场单上限，剩余预算不当作已花掉。规则及抓取时间冻结在本轮配置中；不构成真实订单合法性验证，也不验证限价价格步长。
- 基础质量要求：报价年龄不超过 2000 ms，两所时间差不超过 500 ms，收到消息的本机单调时间年龄也有效。同时记录更严格的 500/100 ms 质量结果；基础通过不能代替严格通过或同时成交。
- 深度价格已经包含吃多档带来的价差，不重复扣同一成本。额外 5 bps 是假设余量，不是实测滑点。
- 尚未计入扣费币种影响、库存净值变化、再平衡、单腿失败或成交概率。qualification.json 所有路线仍为 BLOCKED_UNKNOWN，模拟执行和实盘始终关闭。

## 修复后的数据规则

OKX 增量必须携带匹配的 prevSeqId；允许官方规定的空更新同序号、连续 prevSeqId 下的序号重置，拒绝同序号却改变档位。Gate full snapshot 在同一连接中拒绝序号或时间倒退。重连清空旧盘口，须新快照；畸形、空、交叉或断序行情无效。

同币同方向只建立一个异常事件。短暂数据缺失标 data_unavailable，恢复为 anomaly_resumed，沿用原事件 ID；3 次连续有效非正值才结束。持续正值不每分钟重开。样本与容量金额不能相加成收益。

一秒复核保持原始币数量，重新走盘口，要求两边均收到后续消息且连接未切换。记录实际延迟、现金假设是否够用及订单限制。NO_NEW_BOOK / INVALID / UNKNOWN 不属于盈利或亏损；复核也不是成交验证。

## 运行与证据

```sh
python3 -m unittest -v test_detector test_monitor test_universe test_evidence
python3 qualification.py
python3 monitor.py --seconds 86400 --proxy-port 7890
python3 replay.py --run-dir /绝对路径/monitor/本轮目录
```

不要在已有监控运行时重复启动；process.lock 会拒绝同一状态目录的第二个进程。用于测试的 --state-root 必须是明确隔离的短时目录。电脑需保持唤醒、联网；代理 7890 沿用本机既有设置，不修改网络配置。进程没有开机自启、自动重启或自动延长。

monitor/status.json 是当前状态。run_dir 中包含：

- source/ 与 config.json：本轮实际源码副本、哈希、时限、参数和冻结规则。
- journal-*.jsonl.gz：每分钟关闭一片的全量原始 WebSocket 文本、连接 ID、交易所消息内容、本机接收/处理时间、正负和无效计算样本及事件。
- journal_manifest.json：已关闭分片的 SHA-256、大小和序号。写入中的分片到关闭后才可完整回放。
- opportunities.jsonl：供提醒使用的事件投影；真实复核以原始 journal 为准。
- qualification.json：本轮路线核验状态副本，未核实项不默认通过。
- final_status.json：结束原因、覆盖统计、失败状态。

总证据压缩量上限 4 GiB，剩余磁盘下限 20 GiB；碰到限额或写入失败即停止，不删除证据。不保证进程或电脑异常退出时最后一个未关闭分片完整。

replay.py 有独立的盘口重建与 Decimal 计算，不调用 detector 的 Book/evaluate。检查源文件、分片哈希、序号完整性、全部金额及费率场景、数量/差额、事件分段和延迟结果。通过只说明记录与重算一致，不说明资产可转、两腿成交或套利赚钱。

自动跟进 zec-uni 已改为“LSK G 只读取证复核”，每 15 分钟检查。仅新异常、持续故障或本轮完成时提醒；不会把旧 candidate 或恢复事件重报为新机会。

## 外部事实与尚缺证据

独立公开 REST 快照和规则见 monitor/public-check-*.json；其请求/响应时间和交易所时间均保留。2026-09-24 的一次采样中，两所时间差：LSK 约 688 ms，G 约 2848 ms，均不能当同步成交证据。Gate 返回两个币均为 Ethereum，充提标志 false（未禁用）；这不是用户账户路线可用的证明。

还需核实 OKX 两个币的网络/合约、具体方向可用性、双方该币账户费率及扣费币种、提现费用/最小额/到账条件。无需把密钥发到聊天里。未确认前继续只观察异常，不做资金分配和成交模拟。

官方依据（2026-09-24核对）：

- [OKX 序号规则](https://tr.okx.com/docs-v5/)，允许空更新相同序号及维护重置；[checksum 弃用公告](https://www.okx.com/en-eu/help/okx-order-book-channels-checksum-field-deprecation)，2026-06-23起不能继续依赖该字段校验。
- [Gate 公共现货规则](https://www.gate.com/docs/developers/apiv4/en/spot/)与[变更记录](https://www.gate.com/docs/developers/apiv4/en/)，币对 fee 字段弃用；[账户费率接口](https://www.gate.com/docs/developers/apiv4/en/wallet/)须按相应权限查询，本轮没有调用私有接口。
- [Lisk 官方公告](https://lisk.com/blog/posts/introducing-the-new-lisk/)：Lisk Chain 计划于2026-10-31关闭，Ethereum 和交易所上的 LSK 与链上退出要求有别，不能据此解释价差原因。
- [Gravity 官方网络说明](https://docs.gravity.xyz/the-g-token/g-token)：不同网络的 G 即使地址相同也不能默认可等量桥接；本轮只得到 Gate Ethereum 的公开信息。

早期 detector.py CLI 和 universe.py 留作历史研究入口；当前 monitor 不调用动态初筛。旧数据缺少原始深度，无法补成可回放的历史盈利证明。
