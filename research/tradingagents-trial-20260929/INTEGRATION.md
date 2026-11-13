# TradingAgents 量化研究接入 v1

状态：数据和原生评级适配已完成本地验收；完整多代理模型运行、纸面执行映射、收益验证待完成。唯一实现Owner为当前主会话。不修改20260929已冻结的24小时条件观察。

## 已实现

- integration.py prepare：官方公开ETH-USDT-SWAP日线响应→严格时间/连续性/OHLCV检查→安装包实际指标计算→不可覆盖的研究输入。仅使用确认收盘的K线，保留交易所日界，不把日线当作15分钟信号。
- integration.py accept：原始输入字节、原生final_state及带时间/哈希的回执→保留原生Buy/Overweight/Hold/Underweight/Sell/REVIEW→研究观点。Sell不自动转成开空，REVIEW不静默转成Hold。
- 原生评级与文本冲突、旧输入/未来时间/哈希不符拒绝；测试fixture始终标注，不冒充模型输出。provider/model/request_id只算声称的元数据，尚需独立提供商回执验证。
- 无网络指标运行，无交易接口，无API密钥读取。paper_execution_allowed固定false，trade_action固定null；这些是研究适配器，不是合约执行许可。

## 本轮验证

已安装运行时：/Volumes/EXTERNAL/.codex-global-tools/uv-tools/tradingagents/bin/python，TradingAgents 0.5.2。11项测试通过，覆盖时间泄漏、断档、非法数据、评级语义、冲突、哈希、回执、禁止覆盖。单元测试使用明确fixture，不是模型能力测试。

公开响应 public-1790694435763.json 已实际生成 packet-1790694435763.json。未来使用时必须重新采集，不能用该包冒充新鲜输入。此前try_indicators.py与component-result.json保留为第一轮组件试用证据。

## 调用接口

使用上述已安装Python执行，不安装新依赖：

```text
integration.py prepare --source <新鲜公开日线响应.json> --out <新的packet.json>
integration.py accept --packet <packet.json> --receipt <模型回执.json> --out <新的opinion.json>
```

模型回执需要input_sha256、instrument、started_ms、completed_ms、source_kind、final_state，及provider_receipt中的provider/model/request_id。原生TradingAgents propagate返回(final_state, signal)，但它默认自行抓数据；当前尚未实现全图数据路由冻结与提供商调用，不得只把原生报告附上packet哈希便声称使用了该packet。后续需要记录所有模型输入/工具返回、工具数据时间和调用成本，并独立核验回执。

## 下一阶段边界

1. 用户指定/确认可用模型服务（服务名称/是否已配置即可，不在聊天传密钥）。目前UNKNOWN，无付费模型调用。
2. 接通真实模型运行适配与工具数据审计，固定模型、提示、成本上限；完成一次独立运行。
3. 在新的预注册纸面实验中冻结评级→方向/仓位的映射，不回写当前实验。不把减仓建议直接当开空。
4. 费用/资金费/强平路径、无信号对照与样本外验证分开验收；策略不因指标正常或多个代理一致就通过。

交付物均在本目录，用于后续接入和审计，保留。没有声称量化系统整体完成或已证明盈利。官方项目：https://github.com/TauricResearch/TradingAgents 。
