# 038：压力规则provider离线契约准备

**仅离线格式与失败关闭层通过，真实provider尚未接入。** 状态为`PRESSURE_PROVIDER_DRAFT_V1`，问题为`PRESSURE_ACT_REGISTERED_WAIT_V1`；动作仅`ACT_REGISTERED`/`WAIT`，前者只能支持原已注册FOLLOW或FADE，不能反转、改风险或形成新经济配置。十规则不变，没有重跑收益或接触job011 live收益。

Jev公开基本HTTP的model/state/questions Choice结构已知，使用文档模型`jev-1.13.0`；本阶段没有HTTP transport、headers、凭据或账号读取。`payload=null`、`sendable_payload=null`始终成立；合格或历史例子只保留`offline_draft_payload`，不会发送。transport函数硬抛错。Decisions endpoint/schema仍`UNKNOWN / NOT_IMPLEMENTED`，不拿其他API替代。

## 输入证据与隔离

历史唯一SUI capsule来自033原raw的asof prefix，不读其未来路径或outcomes作为输入：当前/ref10/ref1原价量、run/conn/boot/domain/ordinal/OS/wall、第一unique成交证明、271条10秒去重成交见证、exact10s/1s total/net、过去impulse/cost/depth、实际源hash及本地合约spec均绑定。数学内容按原026公式复核，原规则字节不改。

模型草稿约5476字节；完整原始10秒trade见证留在本地审计状态，草稿只传其canonical SHA及数量，并保留确切过去汇总、报价/spec/来源证据。canonical采用sort_keys JSON、禁止NaN。顶层字段白名单与递归future/outcome/price_fee_delta/pnl/profit/label禁字段检查拒绝未来或收益夹带，037任何未来路径和033经济列不入payload。

九币仅为本地行情/合约registry资格，**没有真实Jev schema兼容性或权限认证**。qualified_rule_sha与spec内容/hash必须一致；缺字段、未完成10秒warmup、旧参考/当前过期、tradeId缺失/冲突、嵌套窗口或内容不一致均失败关闭，不假补量或时钟。

## 历史、时钟与响应门

历史SUI例子`is_live=false`，asof规则合格但send gate明确拒绝`HISTORY_NOT_SENDABLE`与`ACTUAL_SEND_TTL`。feature_completed是本轮离线构建实际OS读数，不能回填成历史live时间；没有真实request/send/response延迟。

send检查source≤feature≤实际send，source/current book年龄≤250ms、runtime run/conn/boot/domain与输入一致。planned与actual分开；response重新核actualsend TTL、完整时序、1000ms timeout、post-response book及ordinal、严格bool、state/draft hash。即使synthetic格式链合格，最终仍WAIT：**真实新book内容/容量执行证据和transport未实现**，不能将caller book_valid/time声明当真实新盘口或成交验收。

严格Choice parser检model版本、choice type、完整两枚概率、finite[0,1]/sum≈1、confidence范围与非负整数usage；不把概率或confidence当盈利率/提高仓位。synthetic响应和新鲜continuation/decay/cold示例均硬标`SYNTHETIC_NOT_MODEL_RUN`，不是实际调用。

## 有限验证与停止位置

11个新增离线测试通过，覆盖新两规则synthetic资格/真实一致cold、历史与actual晚发TTL、缺参考/错域/形成未来参考、冲突/缺ID/伪造嵌套汇总、合约/feature错位、未来与额外收益字段、parser未知动作/模型/NaN、响应hash/clock/bool绑定、transport硬拒。

有限原始字段审核核271条见证+第一unique原trade、三book内容/provenance和spec、compact见证hash/count及历史拒send。完整raw SHA沿用033已验终态，本阶段审计只消耗asof prefix，不冒称重新全源/第三方全策略或provider验证。

v1草稿/冻结/例子保留；新增firstunique证明与strict额外字段guard均属于输入正确性加严，当前代码/协议已重新冻结并验，不改026阈值/费用/经济规则。后续必须另获具体权限/预算才能开发真实transport并测模型；现阶段model/API/收费/私有/密钥/安装/订单均0。目标至03:16:33UTC仍ACTIVE，实际model/effort/speed UNKNOWN。
