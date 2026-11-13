# 阶段009：离线 stateV2.1 请求封装

有限离线准备层通过：7项必要测试通过，真实历史接收状态可构造版本化 Jev 请求，且历史状态返回 WAIT、禁止发送。没有真实 provider 调用，权限、费用、兼容性及实际模型时延仍 UNKNOWN；transport 明确禁用，Decisions 未实现。

新 schema 使用显式 shared-clock 字段；旧过程内 monotonic 仅保留为历史字段，没有别名成 OS shared clock。源、事件、状态和盘口核对 run/domain/ordinal/内容及时间顺序。输入禁止未来结果、entry/exit 价格和收益标签。示例来自封存的20000行开发前缀，仅增加由原 row 核出的 run provenance；没有用当前行情补历史状态。

计划发送时间与实际发送回执分开：响应 gate 使用未来真实 runtime 的发送时间重新核 source≤feature≤actual send≤response<new book≤now，以及 source/latest book 各250ms TTL。实际发送不能早于计划；布尔开关必须真实 bool。所有时序测试都是 SYNTHETIC_NOT_MODEL_RUN，不提供模拟 API 时延。概率和 confidence 不代表盈利率，不改变风险。

证据：protocol.json、execution_freeze.json、tests_stderr.log、historical_request_example.json、historical_source_receipt.json、audit.json、results.json。运行 `python3 -m unittest test_v2_bridge.py` 仅离线测试，不打开 HTTP transport。003/007/008 封存产物未修改。总12小时任务仍 ACTIVE；下一步是已授权的010闭合新源评价，实际 provider 仍待具体权限/预算。
