# 阶段012：固定扩展标的公开可得性

DOGE、XRP、SUI 均通过公开 live/linear/USDT SWAP 规格和单次盘口首5档500USDT入口含费容量检查。共9个 dedicated public MCP 调用，无重试、无费用/模型/key/private/安装。每候选原信封、endpoint、provider requestTime、调用开始UTC均保留；完成字段为回执收集的上界，不作为精确网络RTT。CLI升级及凭据扫描与明确授权冲突，未执行。

|固定标的|ctVal / ctMult|lot / min|tick|单盘口spread bps|180根闭合1m range中位数 / p90 bps|
|---|---:|---:|---:|---:|---:|
|DOGE-USDT-SWAP|1000 DOGE / 1|0.01 / 0.01|0.00001|1.0673|7.3890 / 14.7493|
|XRP-USDT-SWAP|100 XRP / 1|0.01 / 0.01|0.0001|0.6674|6.6346 / 10.6909|
|SUI-USDT-SWAP|1 SUI / 1|1 / 1|0.0001|0.8471|10.1682 / 17.7530|

三个候选均保留，未按高range挑赢家或替换失败币。分钟 high-low/close 只是事后单边价格空间代理，非15秒双边可执行路径、信号优势或盈利；单次盘口容量不保证后续退出深度。各币两方向×5/10bps费用合计12容量案例的独立Fraction价量核查通过，180根 confirm=1时间网格齐，各排除1根forming；不证明全市场源完整。

旧job005已按session31407核终态exit0、PID42092不存在，正常截止19:20:26.250780UTC/errornull。完整gzip CRC/EOF、125765条、134494295 logical、14104710 gzip、ordinal/run/domain/OS顺序均通过；terminal receipt在原job目录，仅源验收，未计算该段新策略结果。

唯一新job006已启动：PID48225/session49659/run phase006-48225-1791315176，19:32:56.921785→20:02:56.921785UTC，30分钟或容量界先到即停。原3＋固定新3共12频道ACK和data，首100行来源/时钟核通过。TLS/hostname验证、原request代理、无auth/noautoreconnect；实际 logical 240M、gzip199744735B（比230M更严以满足phase物理240M/global2GiB）。源码/规格/注册/protocol hash在连接前冻结，once锁保护。运行中gzip完整数据验收及未来评价仍null，不读livegzip收益、不提前重开。

FLOW/BOOK仍原冻结规则，LEAD仍只ETH/SOL，无新beta/阈值/持有/费用配置。7/8/9/10/11原seal未改，来源扩展本身不证明alpha或盲OOS。实际AI、费用、资金费、撮合与性能未验证。capture当前入口见phase006_shared_capture/CURRENT_CAPTURE.json，12小时总目标ACTIVE。
