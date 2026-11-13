# 049 Jev真实HTTP传输准备（默认关闭）

此模块包含未来可授权调用的标准库HTTPS实现，但本轮没有任何真实网络、模型调用或凭据读取。默认CLI只输出DISABLED。不要用测试中的内存合成token作为凭据。

本地检查：

```sh
python3 -m unittest -v test_transport
python3 transport.py
```

真实接口固定 `POST https://api.typesafe.ai/v1/systemone`，model `jev-1.13.0`。不接受caller URL，不follow redirect，不retry；TLS使用系统信任链、CERT_REQUIRED及hostname校验。真实HTTP响应上限1MB是本地保护，不是已知provider限制。完整错误契约和计价UNKNOWN。

未来调用前必须全部提供：enabled明确为True；未过期具体授权receipt；固定model；内存token；美元/调用次数预算；已验证每次最大美元价格证据（绑定同一canonical request SHA和model）；同域source/book/feature/deadline真实时钟。缺失即WAIT/拒绝，无HTTP。价格证据与授权真实性须由未来可信Owner核验，本模块检查字段和绑定，不认证外部文档或账号权限。

预算先占用一次调用及最坏美元上限，再将BEFORE_HTTP journal落盘，随后最多一次HTTP。WAIT/error/timeout/redirect/未知billing保留全部预留，不从usage猜收费；仅外部已验证billing receipt可以settle释放差额，不能重复settle。Budget目前为单进程内存状态；跨进程/崩溃恢复的预算账重建、计价证据认证和审计器仍未实现，真实试验前必须补齐，禁止重启为新预算洗掉旧预留。

journal保存canonical请求/响应哈希、模型/usage、安全错误码、开始/完成OS及wall clocks、预留和状态。token、Authorization头、响应原文、任意exception文本均不写；选择概率不是收益概率。BEFORE_HTTP时间是本地调用入口附近，并非已证明最后字节发送或服务器接收时间。

send和实际completion分别检查输入250msTTL及绝对deadline。socket timeout取本次剩余deadline和配置timeout的较小值；completion迟到仍拒绝，不让新book洗白过期state。标准库socket timeout不是DNS/多个阻塞步骤的严格总耗时杀进程保证，本轮未实测真实连接；硬限总调用时间/取消和实际网络行为仍待真实极小预算验收。真实response完成后盘口绑定和任何下单不在本模块范围。

已运行13项Fake HTTP/mock TLS契约测试及合成WAIT/error/timeout预留核对。Fake HTTP两次离线receipt运行均留档（最终journal共12行，含旧6行和新6行）；不代表12真实调用或真实时延。实际网络/API费用/Jev收益均0。

仍需权限与预算答案、真实定价/计价换算、可信授权/预算恢复、真实feed因果adapter、response后盘口和开发真实性verifier/freeze、真实HTTP验收；旧047/048与交易规则只读，原12小时和automation未恢复。Decisions endpoint/schema仍UNKNOWN，没有替代或猜测。

## PMO审查补充边界

Budget不支持重启恢复、跨进程并发或原子持久预算事务；BEFORE_HTTP journal不是已证明的崩溃恢复方案。Authorization/Pricing证据目前仅caller的SHA与verified声明，不能认证真实人类授权、官方计价或production预算安全；可信证据认证必须在真实接入前完成。

真实响应目前只保留body SHA和严格提取的model/choice/probabilities/confidence/usage，不保存完整原body或headers。故可核请求/响应hash及允许字段，但无法从本journal独立复原完整provider响应原件。未来若需原件留存，须预登记安全脱敏/访问范围；本次不扩大存储秘密或真实响应。

socket timeout是各I/O约束，completion超时是完成后拒绝；未经真实网络测试，不是端到端硬实时认证。当前最终测试13项（早版12项后补请求价格证据绑定回归），版本日志分开保留。
