# 自主模式：MT5原源与EURUSD正常路由复核

结论：**本轮已完成两项获授权的新路由诊断，原源/数据门仍受阻，回放未运行，PnL=null。** 不把curl退出0当行情成功，也不因自主模式无依据重复请求。

AUTONOMOUS-2026-10-05-v1已完整读取。用户已有明确候选、市场、日期、资金、成本、预算和边界，没有新增问卷。当前唯一Owner/root/external_relative_value，ROUTING-2026-09-30-v3目标Sol medium，实际model/effort UNKNOWN。45分钟/150公共请求/100MB为上限；本轮实际2个公共curl请求，无安装/账号/keys/付款/订单/生产/后台/新agent，旧目录未修改。

## 本轮新依据与真实结果

父任务只读scutil已确认本机启用既有HTTP/HTTPS/SOCKS代理。上一轮urllib可能未继承它，因此本轮获准仅对两个正常TLS失败资源各作一次请求级curl代理继承，不改系统/应用设置、不换身份，原TLS校验保留。没有代理访问或重试Jina401，也没有遇到403后换通道。

| 资源 | 请求结果 | 实际取得 | 可支持结论 |
|---|---|---|---|
|MQL5候选1原页 code/76153|curl28，HTTP000，SSL connection timeout|0字节，无HTML|代理继承未解决这个资源的连接失败；原因UNKNOWN，不推断源码不存在|
|Dukascopy EURUSD/2026/08/21/07h_ticks.bi5|curl0，HTTP503，107字节|503错误正文保留，非LZMA行情|路由收到HTTP响应，但价格探针失败；不能解码、不能升级一天/五日成功|

`requests.jsonl`保留请求UTC、URL、HTTP状态、returncode、stderr、bytes/hash。Dukascopy错误正文存为原请求目标文件名.bi5，明确 **不是价格数据**；SHA256 `839488ebc08446a096a893996ed23eac321ac166724cd8c5d9092057834d2d79`。HTTP503的产生层/是否暂时性UNKNOWN，无新诊断依据不重复提交。

## 原源与回放边界

上一轮[官方web解析回执](/Volumes/EXTERNAL/量化/research/mt5-public-ea-pilot-20261006/rawsource/official_web_receipt.json)只保留mq5文件名与工具链接标识，没有附件真实href；不能猜URL。本轮原页未取得，仍不能解析附件地址、下载/核源码或建立源文件行号。候选1默认规则仅有官方说明证据；跨日退出、已持仓抑制、总仓、lot/minimum/余量等实际行为未核，不凭说明重新创作一个策略冒充原EA。

固定候选仍是Session Opening Range Breakout，未换候选2/3。固定五日09-21至09-26UTC、M5确认、伦敦08点→本周07UTC、500USD/1%risk、佣金0/7USD roundtrip lot保留在protocol.json；contract100000EUR、point1e-5、lotmin/step0.01、100:1都是代理假设。没有真实tick时不可计算成交spread、SL gap、margin、overnight、浮亏或Pnl。

实际完整覆盖0天，行情records为UNKNOWN而不是0事件。未实施120小时采集、未移植EA、未编译/运行MT5、未生成虚构ledger或收益。没有执行synthetic策略测试，因为原源移植尚未发生；本轮验证是两次原始请求状态/坏正文/hash核查，非交易验收。

## 收口与下一步

按自主模式§5，必要原源和数据缺失且授权内一次替代仍失败，停止受影响采集；不以预算剩余追加代理、身份、安装或账号动作。恢复下一步需要 **候选1原mq5文本/真实href可达 + 已支持入口的固定五日双边报价 + broker规格和服务器时区/费用**。取得后再按同一冻结候选准确移植、进行资金/lot/stop-gap/佣金测试及不同实现核账。无需购买商业EA或问大问卷。

本轮交付protocol/results/dataaudit、requests、503原件、fetch实现、manifest/hash、规则回执。全部证据保留，无清理项。源码取得、数据完整、条件回放、账务审计分别为NOT_COMPLETED；整体业务未完成，不能称自主跑通。
