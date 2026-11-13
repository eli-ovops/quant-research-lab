# 官方周期调整公告：来源可用性筛查

结论：在固定生效日期范围 [2026-09-06, 2026-10-06) UTC 内，本轮未检索到可入选的 OKX 个币资金费结算周期调整公告。实际调整事件数量 UNKNOWN，不能将检索命中数 0 解释成全月没有实际调整。阶段 B/C 均 NOT_STARTED；没有历史费率采样、价格窗、成本收益或账户收益。此次完成的是来源可用性筛查，未检验盈利。

## 冻结与继承边界

protocol.json 于 2026-10-06 04:44:57 UTC 在首次网页查询前冻结。只限 OKX 官方真实个币周期调整公告，按取得公告的生效时刻升序取最早三份，每份按币种顺序最多三币、全局最多六币；泛制度公告、上币初始周期、下线清算及其他交易所均不计事件。搜索索引不是公告全集，所谓最早仅能针对取得的合格语料，不能宣称全平台最早。

Owner 仍为 funding_liquidation，目标 gpt-6.1-sol / medium，实际 model/effort/速度 UNKNOWN；ROUTING-2026-09-30-v3 不变，无模型变更声明。已补读当前 HANDOFF 条款与上一轮 REPORT/validation：上一轮固定十币 900 个主窗费率点完整、0 达 10bps，盈利未测。本轮只写新目录，旧两轮共 18 个封存交付文件 hash 未变。

采用 agent-reach 的官方网页研究路线。LOCAL_BLOCKERS B009 记录既有 Exa Unknown MCP server 与 Jina 匿名 401 的受支持替代入口，因此本轮直接使用现有 web 工具限制官方源；未重试故障中介、认证、安装或改配置。没有读取价格来选事件。

## 检索覆盖与排除

实际进行 14 个定向中英检索，返回 48 个去重官方页面 URL；其中对 13 个重点入口/候选记录排除原因。另对三个唯一官方页面做九次打开操作，包括定位阅读同页不同段落，并非九个独立公告。原响应完整保存在 raw/，确切参数、请求/保存时间和逐文件 hash 见 requests.json、sources.json。

已打开的具体来源：

- [中文交易规则更新第一页](https://www.okx.com/zh-hans/help/section/announcements-trading-updates)：取得 15 个标题，最晚显示 2026-08-24；没有在此页看到本窗口的资金费周期调整。该列表可能受语种/类别/索引时效影响，不作为九月公告全集。
- [欧洲英文交易更新第一页](https://www.okx.com/en-eu/help/section/announcements-trading-updates)：取得 15 个标题，9/25 和 9/11 项分别涉及 VIP 档位及现货手续费，其余更早。它没有提供合格的个币资金费周期事件；区域列表完整性 UNKNOWN。
- [参数调整通知入口公告](https://www.okx.com/en-gb/help/okx-launches-parameter-adjustment-notification-page)：页面列仓位档位、抵押折扣、tick size、最小订单量四类。不能据此推断资金费周期被集中在该入口，更不能把参数页迁移当作本窗口资金费变更证据。

重点候选的排除记录：

| 候选 | 公告日期／相关生效时间 | 排除依据 |
|---|---|---|
| 资金费自动周期升级机制 | 2026-04-14 | 泛制度、日期窗外，不能计作个币事件 |
| FET 合约上币 | 9/5，03:30 UTC 开盘 | 日期窗外、初始 4h 周期，非旧新周期切换 |
| CT 合约上币 | 9/30，11:00 UTC 开盘 | 初始 4h 周期，非既有合约变更 |
| ICXUSDT 下线 | 9/10 公告，9/17 08:00 UTC 下线 | 下线结算不是周期调整 |
| HUT/OKLO/TEM/TEAM 上币 | 9/21 公告 | 股票合约初始 8h，非周期变更 |
| US500/US100/XOM 上币 | 9/10 公告 | 同上 |
| JP225/ZHONGJI 上币 | 9/9 公告 | 同上 |
| LGELECTRONICS/NAVER/HANMI 上币 | 9/16 公告 | 同上 |
| 参数通知入口 | 4/24 | 泛入口、日期窗外、四类中没有 funding interval |
| 通用资金费规则文档 | 2020 发布、2026-08 更新 | 通用说明，非历史个币公告 |
| 旧交割／资金费时间调整 | 2019-08 | 日期窗外，不扩样本 |
| 中英文交易更新索引 | 本轮读取 | 导航列表不是实际个币变更事件 |

candidates-reviewed.json 包含每项来源 URL、页面展示的日期、相关时间、币种、旧新间隔缺失与排除原因。排除的上币项目所列 instId 是从公告 ticker 规范化的标识，未查询其 instrument 身份，不冒充已验合约。多币上币条目 effective_utc 仅记录第一项开盘时间，不伪称所有币同时生效。所有被排除页的发布时间精确时刻均未用于事前交易判断。

检索覆盖限制：未证明全量历史公告索引、语言/地区一致性、未被搜索收录条目或自动调整通知全集；部分搜索返回时间窗外页面，仅用于排除，不据此扩展日期。未登录、未查询私有通知、未绕过拒绝。零合格结果是来源门槛未满足，不是机制不存在的证据。

## 阶段 B/C 未执行

合格公告=0、冻结币种事件=0，故没有开始每币最多 100 条事件附近资金费历史请求。跨变更点覆盖、真实旧新间隔、10bps 次数均 NOT_TESTED/null，不记为观察到零变更或零高费。

没有满足“历史记录覆盖变更点且公告当时可见”的前置条件，故未读取 1m 价格、同币非切换对照或 BTC 市场窗。事先规定的前一期已结算率反支付方方向、公告生效后首个结算前后各 30m 窗口及 12/20/40bps 成本只保留为冻结规则，没有对应数字。现金归属 UNKNOWN，account_pnl=NOT_COMPUTED，毛价格收益与成本敏感性均 null；没有显著性、因果性或收益可行性声明。

## 请求、复算与终态

共 23 次显式公开操作：14 个 search_query 和 9 个 open；web.run 函数调用六次，按嵌套公开操作累计而非仅按函数批次数。内部 HTTP 请求/重试数量 UNKNOWN；没有 funding/candles/account/orders 请求。预算 30 次、20 分钟，本轮没有用完预算继续扩大查找，完成后停止。

离线复算 `python3 /Volumes/EXTERNAL/量化/research/funding-announced-events-20261006/reproduce.py`，不联网、不写旧目录。脚本核重点候选来源在原响应、按冻结规则选样、统计请求数量、生成 results/selection/requests/sources/validation，并核旧两轮封存 hash。它复算的是这次保留语料及人工排除表，不声称能离线复现搜索引擎的全球排名或证明未收录公告不存在。

validation.json：原响应完整性 PASS、23 操作预算 PASS、旧 18 个交付文件 hash 未变。artifact-hashes.json 保留本轮交付 hash。业务状态：来源筛查完成，公告门槛未满足；B/C 未开始，盈利未检验。所有新文件为证据/协议/脚本/交付，没有无用途一次性临时文件。无安装、keys、账户、订单、生产、旧监控、后台轮询、新 agent 或他人修改回滚。本轮停止。

## 完整查询记录

下列检索均限制官方 okx.com 来源，首组以 site:okx.com/help 限定，其后使用 domains=[okx.com]；原参数见 requests.json。

1. `site:okx.com/help "funding" "September" "2026" "frequency"`
2. `site:okx.com/help "funding" "Sep" "2026" "settlement"`
3. `site:okx.com/help "资金费" "2026" "9月" "周期"`
4. `site:okx.com/help "funding" "October" "2026" "adjust"`
5. `"OKX" "adjust" "funding fee settlement" "2026"`
6. `"funding" "interval" "September" "2026" "adjustment"`
7. `"资金费" "结算" "调整" "2026年9月"`
8. `"funding" "frequency" "2026-09"`
9. `"funding fee settlement" "adjust" "2026" -mechanism -faq -list -listing`
10. `"资金费" "周期调整" "9" "2026"`
11. `"OKX" "funding" "settlement" "September 2026" "adjust"`
12. `"OKX" "funding" "period" "2026" "September"`
13. `"OKX" "funding" "settlement frequency" "adjust" -mechanism -list -faq -equities`
14. `"OKX launches parameter adjustment notification page"`
