# 047：真实Jev前向试验的离线编排准备

**只完成可运行离线骨架与契约测试，不是已经可真实运行的Jev试验。** 真实HTTP transport、真实development receipt认证/选定冻结、可信实时source/feature adapter、实际费用/币种转换与融资验证仍未实现或未授权。拿到权限本身也不足以完整实跑。实际Jev/网络/费用/钥匙/私有/采集/订单/安装均0。

本作业独立授权03:13:38—03:33:38UTC；旧12小时窗口03:16:33已由root关闭/暂停ai-12，本作业不延长或恢复它。

## 已实现、可运行的范围

- 固定三开发候选FLOW/BOOK/LEAD（LEAD只ETH/SOL），各自严格数值/asof/合约/当前book结构；未来或额外字段拒绝。即时两方向500容量cost proxy与5/10bps输入草稿，API实际USD成本与USDT转换仍UNKNOWN，不冒充成本完整。
- 四对照臂：Jev选择、与Jev完成时刻同步的RULE_MATCHED_NO_AI、特征完成后立即可估执行的RULE_IMMEDIATE_NO_AI、WAIT_NO_AI。匹配规则对照用来隔离动作选择；即时对照另显示完成等待影响，不能合并称纯Jev因果。
- 模型必须完成后第一真实新book才能估入场，严格first-after/250ms；source/asof在completion也须≤250ms，不能用新book洗掉过期输入。timeout1s、所有error/reject/WAIT、不完整response及尾部记账。
- 每候选×臂独立500纸面账户、所有资产共用单仓锁、1x全notional collateral代理、资金不借用；fixture API成本在completion扣现金，WAIT/error/timeout同记。未知API成本标账不完整，不称真实净值；fee5/10构造时固定独立情景，不混账。
- 仅fixture可注入synthetic Choice，严格model/actions/probability/confidence/usage；默认真实入口硬拒网络、fixture不能当REAL。开发客观选择函数要求全部候选、固定样本/成本条件、确定性净值排序，但真实开发认证与freeze入口仍FAIL_CLOSED。fixture冻结仅测试selected/cut/unseen边界，非真实选定。

## 运行与有限验证

在本目录运行：

```
python3 orchestrator.py
python3 -m unittest test_orchestrator
python3 dry_run.py
```

第一个仅打印transport disabled/API0，不触网；dry_run明确SYNTHETIC_NOT_MODEL_RUN，模拟三候选/四臂/两个费用情景的时序与纸面账，用于契约检查，不输出真实模型时延/盈利/前向验证结论。

原8test日志首次IndentationError保留；同目录修正后8tests PASS，最终12tests PASS，覆盖即时/匹配完成、旧quote不能用、费用/单仓/未知API、completionTTL、超时/错误、schema/原始book绑定、validation cut/selected、尾部与真实入口硬拒。独立Fixture账务检查18个退出，API debit/fee/保留cash+collateral恒等式通过，真实funding/fill未验。

## 剩余接入与裁决

下一有限授权需先有实际预算/权限与真实source契约，再实现：可信原始feature与source/clock内容校验；provider凭据最小读取和可停网络transport；实际请求/响应/usage/错误完整journal；真实开发metric认证、选优/不可变freeze；未使用前向数据与同源对照；API实际费USD→记账币转换、真实fee/funding/margin/partial/queue风险。Decisions平台契约UNKNOWN，不猜endpoint或替代调用。

当前Source/feature传入数值与合法身份文本不自动真实，schema限制不认证所有自然语言/数据真实性。纸面capital仅1x代理、非交易所margin/强平模拟。盈利与Jev增量必须分别判，开发正值不自动验证通过、不能用验证反调或只留model接受正事件，不承诺一定盈利。

本范围未调用实际Jev，用户核心“真实Jev盈利验证”仍未完成。所有旧目录/PMO/原数据保护，只写047；本作业截止03:33:38后停止，不用旧automation续跑。

费用完整性修正：未知API成本使对应候选Jev账的完整性永久为false，后续已知成本不恢复完整性。新增unknown→known回归测试；原修正前代码留档。实际transport与真实开发证据认证仍未实现。
