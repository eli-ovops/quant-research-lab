# 048 现金完整性回归修复

本目录只修复047测试fixture，业务orchestrator.py逐字节保持047当前累积AND版本。第二请求采用ordinal100及20秒后独立asof，满足非重叠输入；DUPLICATE_STATE保护未关闭。全部示例都是SYNTHETIC_NOT_MODEL_RUN。

可本地运行（不联网、不读取凭据）：

```sh
python3 -m unittest -v test_orchestrator
python3 orchestrator.py
python3 dry_run.py
python3 audit.py
```

17项测试通过。CLI返回transport disabled；dry-run的18笔平仓只是合成契约，不是行情收益。audit以不同算术核三种费用次序和18笔fixture净额；同Owner有限检查，不是第三方全策略复现。

## 获得用户API权限与预算后仍需完成的最小接入工作

1. 先登记具体provider、model、调用上限、美元预算、单次timeout、失败停止条件和授权凭据读取位置；当前没有这些授权，本阶段不读env或密钥。
2. 实现真实Jev HTTP transport：按已核POST /v1/systemone、state/model/questions Choice契约，严格TLS、无隐式retry；保存实际send/completion、request/response hash、model/usage/error/timeout和调用计数。现函数仍硬禁用，不能拿权限后直接跑。
3. 接入真实公开feed及因果feature adapter，绑定原raw/run/conn/boot/OS clock/ordinal/contract hash与current book，核source→feature→actualsend→completion链和250msTTL。namespace字符串或caller提供的hash不证明输入真实；新盘口必须由实际完成后收到的原件证明，不能回填时钟。
4. 补真实费用账：所有accept、WAIT、error、timeout都保存API usage与实际计价证据；未知价格或USD/USDT换算保持账完整性false。只有已证费用才能扣成本并裁决完整净值，不能用synthetic价格代替；当前资金、保证金、funding和真实fill模型也未认证。
5. 实现开发ledger真实性验证器及真实freeze_selection：保留全部三个预登记候选，客观开发选优后绑定不可变代码/参数/模型/数据cut和未使用前向来源。当前pure selector只是公式草稿，real verifier/freeze硬失败，不能以kind字符串充当真实调用证据。
6. 做一次明确授权、极小预算的真实接口验收后，再开启预登记试验。JEV、RULE_IMMEDIATE_NO_AI、RULE_MATCHED_NO_AI（同步到真实Jev完成时刻）和WAIT同源、同成本/风险；全部响应/拒绝/费用/尾部保留。盈利与Jev相对matched规则增量分别裁决，不能承诺正收益。

上述仅具体待办，本阶段未实现或执行；Decisions endpoint/schema仍UNKNOWN。原12小时窗口和automation保持关闭。
