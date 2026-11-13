# 来源与采用范围

2026-10-06只读检查，未安装第三方程序、未执行仓库脚本、未连接交易账户。

|候选|本次核实|采用范围|
|---|---|---|
|[wshobson/agents](https://github.com/wshobson/agents/tree/main/plugins/quantitative-trading/skills/backtesting-frameworks)|MIT，40222 stars，未归档；SKILL与本地版本一致|保留预注册、样本外、成本、幸存者偏差规则；没有重复安装|
|[Freqtrade策略库](https://github.com/freqtrade/freqtrade-strategies)|GPL-3.0，5524 stars，未归档；README明确示例不是即用盈利策略|方法参考，不复制其交易实现，不执行示例|
|[Backtrader](https://github.com/mementum/backtrader)|GPL-3.0，23401 stars，未归档|比较对象；现有独立账本已可复核，本轮不迁移框架|
|[quantskills backtesting bias](https://github.com/quantskills/skill-backtesting-bias-avoidance)|0 stars，GitHub license=NOASSERTION|不安装不执行；不能把检索摘要或复杂统计名字当正确性证据|

Stars/updated_at只能说明检索时元数据，不能证明维护质量、安全、策略盈利。未把更新时间当代码最后提交日期。具体下载路径、blob SHA见references/receipt.json。

[Freqtrade lookahead analysis](https://github.com/freqtrade/freqtrade/blob/develop/docs/lookahead-analysis.md)说明完整历史数据框易引入未来信息；本轮用截断/扰动测试与独立信号重建检查。

[Freqtrade backtesting assumptions](https://github.com/freqtrade/freqtrade/blob/develop/docs/backtesting.md#assumptions-made-by-backtesting)列出OHLC内成交顺序和无滑点等假设。本轮自行实现下一开盘、显式滑点/费用、同根不抢先触发止盈；这些仍是代理，非真实成交。

技术指标与K线形态仅生成待检验假设；没有从网上收益排行榜选择结果，也没有安装“自动赚钱”Skill。15分钟短线反转不能证明秒级剥头皮可成交；有上限三档马丁不能借无限资金掩盖清零风险。
