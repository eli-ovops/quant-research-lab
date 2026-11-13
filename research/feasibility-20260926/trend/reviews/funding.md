# C 独立复核 B

结论：通过 B「证据不足、不认定可兑现正期望」的限定结论；不通过真实可执行账务/收益验收。PMO 最终验收待定。

本轮先冻结 C protocol.json，再只读 B；START 已披露 B 摘要，C 已登记且排除该日期。没有运行 B 的写入程序，没有改 B 文件。

check_funding.py 从 B 原始现货/永续/标记小时数据、费率、产品规格独立重建数量、扣币、备用现金、独立保证金和最终现金，不导入 B 策略函数、不采用其输出数量作计算起点。162 个来源 SHA-256 一致，封存分析代码哈希一致；108 情景全量数量及现金误差 0。资金费为币量乘当期标记开盘代理乘 realizedRate；严格位于端点之间计入，整点资格未知另列界限；现货基础币扣费、四腿费用、变动名义金额、基差和资金分母正确，情景没有相加或当独立事件。

发现 F1：B 用 net=gross*(1-fee) 全量卖出，未将净持仓按现货 lotSz 下取整。108 情景都有非整步长卖出，按相同代理卖价估算的残余最大 0.0019605601788U。该偏差不足以把报告主情景负值变正，不能因此推翻「证据不足」；但所有实盘可执行账务验收须拒绝，需 B 原 Owner 后续修正取整和残币估值并重验，不能宣称独立账务已覆盖可成交性。本次复核不越权代改。

其余重大限制均得到承认：历史精确结算标记价/真实盘口缺失；历史 fee/lot/mmr 及账户权限 UNKNOWN；现货盈利不能补独立空头保证金；100%涨价压力暴露清算风险；持有期单一、3个相关日历事件且均为上涨行情，不能推断可靠正期望或否决整个机制。OHLC 高低界限仅为条件估值界限，不是统计区间。费用示例与 5bps 假设不是核实费率或保守上界。封存仅未据收益选参，无独立访问隔离；不可升级为第三方未见验证。

Evidence: funding source directory is the sibling ../funding/ containing raw, sources.json, protocol.json, seal.json, scenarios_all.json, report.md. Review evidence: funding_checks.json and check_funding.py. Conditional arithmetic PASS; execution quantity FAIL; realized profitability UNKNOWN; limited verdict PASS; PMO PENDING.
