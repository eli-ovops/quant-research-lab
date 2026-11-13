# 固定十币资金费极值最小验证

结论：固定 10 个 OKX USDT 永续合约的近 30 天数据中，共 900 次实际结算，没有绝对费率达到 10bps 的事件。全局最大绝对实际费率为 ARB 的 2.96917186bps；890 个相邻实际结算间隔全部 8 小时，没有观察到间隔切换。因此基于“前一期已结算绝对费率 ≥10bps”的阶段 2 不触发。本轮没有价格事件、扣费收益或账户收益结果；零触发不否定机制在其他时期或合约可能存在。

## 本轮授权、规则与继承状态

唯一 Owner 复用 funding_liquidation；只写 `/Volumes/EXTERNAL/量化/research/funding-extremes-20261006`。本轮 20 分钟、最多 40 次显式公开请求，无账户/密钥/私有 API/下单/安装/生产/旧监控/后台轮询，没有派新 agent。所读规则为当前 AGENTS.details §§2/3、`HANDOFF-2026-10-06-v1`、`ROUTING-2026-09-30-v3`；保留目标 `gpt-6.1-sol / medium`，本次实际 model/effort/速度 UNKNOWN，followup 工具没有设置模型参数，未声称更换。

已实质补读旧 funding-flow 的 protocol/results/REPORT：旧样本仅 BTC/ETH 三天的 18 个事后结算事件，不可用未来 realizedRate 当入场前信号；未验证周期切换、真实强平或交易收益。本次扩大名单但重新冻结协议；旧材料只读封存，validation.json 已核旧交付清单七个文件 hash 未变。复用已读 okx-cex-market / backtesting-frameworks / agent-reach 技能；本轮只用专用公开 OKX 工具，无需再读网页或升级旧 CLI。

## 事先冻结和数据质量

protocol.json 在首次行情请求前于 2026-10-06 04:37:08 UTC 落盘：固定 BTC、ETH、SOL、DOGE、XRP、OP、ARB、UNI、AAVE、FIL 的 USDT-SWAP；不存在的合约不替换。当前 instruments 公共接口核实十个合约均 live。这是本次合约存在性证据，不把当前状态冒充历史期间状态。

每币只取一页最多 100 条历史结算费率，`after=1791244800000`，使用 realizedRate，过滤 [2026-09-06 00:00, 2026-10-06 00:00) UTC。实际原响应各 100 条；每币主窗恰有 90 条，首尾 9/6 00:00 与 10/5 16:00，全部构成完整 8h 网格。虽然协议保留“100 条上限可能截断 30 天”的边界，本轮十币实际数据均 `DATA_GRID_COMPLETE`，没有以未见截断代替网格验收。

validate.py 核查每币唯一时间点与网格、原始重复及冲突均为零、instId 正确、两费率字段有限。总 1,000 条原响应记录，900 条主窗记录、890 个主窗相邻间隔。原信封全部保留，权威请求时间为返回信封内的 server requestTime；资金费包装层名为 requested_at_utc 的字段实际记录完成/保存时间，requests.json 已明确其语义，避免冒充请求发起时刻。

## 实测结果

| 合约 | 主窗 n | abs ≥10bps 次数 | 最小实际费率 bps | 最大实际费率 bps | 最大绝对值 bps | 相邻间隔 |
|---|---:|---:|---:|---:|---:|---|
| BTC | 90 | 0 | -0.181444 | 1.000000 | 1.000000 | 89×8h |
| ETH | 90 | 0 | -0.604700 | 1.000000 | 1.000000 | 89×8h |
| SOL | 90 | 0 | -0.939000 | 1.000000 | 1.000000 | 89×8h |
| DOGE | 90 | 0 | -0.129634 | 1.000000 | 1.000000 | 89×8h |
| XRP | 90 | 0 | -1.011343 | 1.000000 | 1.011343 | 89×8h |
| OP | 90 | 0 | -1.996326 | 1.000000 | 1.996326 | 89×8h |
| ARB | 90 | 0 | -2.969172 | 1.000000 | 2.969172 | 89×8h |
| UNI | 90 | 0 | -0.878314 | 1.000000 | 1.000000 | 89×8h |
| AAVE | 90 | 0 | -1.920682 | 1.000000 | 1.920682 | 89×8h |
| FIL | 90 | 0 | -1.275926 | 1.000000 | 1.275926 | 89×8h |

全局极值原件：ARB-USDT-SWAP，2026-09-24 08:00 UTC，`fundingTime=1790236800000`，`realizedRate=-0.0002969171859936`，即 -2.969171859936bps（-0.02969171859936%）；formulaType=withRate、method=current_period。本轮没有新增当前 cap/floor 查询，也未推断历史 cap 触发。没有观察到相邻间隔切换不等于已经验过制度公告、自动调整或所有其他合约。

## 阶段 2 和结果边界

协议事先规定：只由前一次已结算 abs(realizedRate) ≥10bps 触发，按下一结算时间、固定名单顺序排序，最多最早六个；方向为前一次支付方的反向（正费率做空、负费率做多）。下一期实际费率只作诊断，不能按它筛事件。价格规则为下一实际结算前 30m 的 1m 开盘代理，要求前一根 1m 已闭合，结算后 30m 开盘退出；用 12/20/40bps 成本敏感性，取同币最近较早、同 UTC 时钟、前期非高费结算作为对照，并描述同期 BTC 价格。

本轮前期高费可触发对数=0，因此 selection.json 为空，阶段 2 状态 `NO_PRIOR_HIGH_TRIGGER_IN_OBSERVED_SAMPLE`。没有独立价格采样、同币对照或 BTC 对照，没有费用敏感性数字、统计显著性或账户 PnL。results.json 对收益均保留 null/NOT_COMPUTED，未用“0 盈利”替代未测。

即便将来发生触发，已结算费率的数值可在当时已知，不等于未来结算时间的当时可见性已经验证。本协议的 next actual timestamp 为事后时间索引，历史当时已公布/可见的周期档案仍 UNKNOWN；精确资金费现金归属和订单填充 UNKNOWN，因此只能做价格事件描述，不能声称执行可行或收益验证。当前固定名单未覆盖全市场、退市合约或其他月份，不调整本轮阈值来追逐赢家。

## 复算、校验和收口

仅离线复算：

```sh
python3 /Volumes/EXTERNAL/量化/research/funding-extremes-20261006/analyze.py
python3 /Volumes/EXTERNAL/量化/research/funding-extremes-20261006/validate.py
```

脚本不联网、不写旧目录。analyze.py 从原响应重算极值、间隔、选样及条件价格描述；validate.py 校验网格、费率、原响应 hash、请求数、旧封存 hash。验证结果位于 validation.json，数据结果位于 results.json，原件位于 raw/，请求时间/参数见 requests.json，完整源 URL/hash 见 sources.json，交付 hash 见 artifact-hashes.json。

本轮显式公共请求 11 次：一次 instruments，十次 historical funding；内部 HTTP 重试数量 UNKNOWN。未发生工具错误、未追加采样或轮询；运行时间未超过 20 分钟。所有本轮新建文件为协议、证据、脚本或交付，没有可清理的无用途临时文件。阶段 1 数据与复算已验，阶段 2 因预定条件未触发；策略与账户收益未验。本轮停止。
