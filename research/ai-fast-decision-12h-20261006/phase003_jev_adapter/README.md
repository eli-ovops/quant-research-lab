# Phase003：Jev离线适配器准备
本阶段本地准备完成，**未连接API、未获得真实响应或实际模型时延/盈利证据**。12小时总任务继续。8项离线测试PASS，真实已收到事件4111构造的请求1489B；synthetic响应只验证本地schema，不冒充模型调用。

固定请求model=jev-1.13.0，question_version=impulse_action_v1，questions.action为choice，criteria WAIT/FOLLOW/FADE。英文紧凑问题关注流延续/冲击衰竭或恢复/信息与费后空间不足；不含未来标签、entry/exit或价差损益。state采用严格allowlist与future-field拒绝，asof/输入hash/feature完成计数、action slot/问题hash和payload字节数留example_request_record。示例保留真实ETH盘口/成交特征与公开合约单位，未使用后续价格标签。

响应契约依据PMO本轮[官方HTTP文档](https://docs.typesafe.ai/api)缓存回执：model、answers keyed question、usage；action需type choice、允许choice、完整三概率对象、confidence，usage input_tokens/output_tokens。parser严格模型版本/enum/完整字段、有限[0,1]概率且sum在1e-6内、confidence范围与非负整数tokens；unknown/malformed/NaN、版本偏离均拒绝。confidence只保留原值，不验证未提供的公式、不是交易胜率、不提高risk。真实服务额外字段/错误shape兼容尚UNKNOWN，未来不适配时失败关闭，而非默默接收。

freshness_gate复核请求/sourcehash、connection/asof/statechanged、feature→send→complete时间顺序、1000ms响应timeout、decision之后新book/新ordinal、报价等待与当前年龄≤250ms、合法book/risk/cap。任一失败回WAIT并留原因。1000ms只是本轮未调参的离线保护策略，未由实际AI/机会寿命验证。parsed必须由parser成功产生，runtime风险与行情标志由确定性引擎提供，不能由模型填入。

重要限制：原collector来源asof monotonic约42.367s，本次新进程builder实测counter约43.9ms；跨进程时钟域未证可比，原因UNKNOWN。示例metadata明确clock_domain_verified=false，缺live completion/newbook/risk且state已变，故WAIT。没有将旧capture counter与新进程计数相减填造时延。phase002同collector域内人工延迟与quote差分不受此样例比较影响；未来真实链路需同一已验证计时域或可核桥接。

HTTP transport只有明确抛错的disabled占位，不导入网络、读取key/env/.env或构造认证header，不发送请求。Decisions adapter NOT_IMPLEMENTED、真实契约UNKNOWN，无Responses替代。Jev公开basic schema已知，但本账户权限、收费、真实端到端调用/异常仍待具体授权与实测；用户未答预算，调用/费用/凭据读取全部0。

8 tests覆盖固定无future请求、SYNTHETIC_NOT_MODEL_RUN合法fixture、概率NaN/缺失/范围/总和、action/type/model/usage拒绝、旧source/conn/asof、timeout/旧或过期book、风险不受confidence提升，以及transport禁用。local audit核payload/source哈希、无网络/环境import及source只读未改；不重跑旧阶段tests，不能由格式通过称接入通过。

文件：jev_offline.py、test_jev_offline、build_example、example_request_payload/record、synthetic_response_fixture、tests/dryrun原回执、audit/results/protocol/freeze/manifest。source request hash304d340350e61d19dfe76a5efc669906ab319074710df95ababc9b311ea25c60，问题hash4a458769c35c1ecbca13769803dae352d4a6518792ab9dc2638137714884f52f。

主任务15min/0网络模型收费keys安装/≤5MB，只新阶段；既有collector26221/83334、phase002及根control/contract未改。实际model/effort/speed UNKNOWN，目标Sol medium，已读规则版本未变。下一步由PMO在明确API权限/次数费用预算后决定真实transport；未答前只能继续公开数据/离线路线，不假造provider成绩，总目标仍RUNNING。

