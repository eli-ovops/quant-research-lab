# 只读套利观察器

## 持续观察（2026-09-23）

`monitor.py` 复用公开行情连接，每秒计算 OKX / Gate 的 ZEC、UNI，金额100、500、1000 USDT。仅在扣费及缓冲后净额大于0时记录候选；行情无效立即结束候选。重复正值每分钟至多保留一次，不是独立交易。用进程锁防止重复运行。

本机后台进程已经启动；不设置开机自启，不阻止电脑休眠。电脑需保持唤醒、联网，本机已有代理7890需可用。断线后行情连接重试；进程退出不会自动重启。`monitor/status.json` 每秒更新状态、有效性、最新估算和本轮最优值，`monitor/时间/opportunities.jsonl` 保留候选及结束事件，`monitor/时间/config.json` 记录参数，`monitor/console.log` 为进程日志。为控制存储，不保留持续监控的全量盘口；需要逐笔原始证据时仍用有限时长的 detector.py。

Codex 自动跟进 `zec-uni` 每15分钟检查结果，只有新候选或异常才提醒，因此不是即时交易信号。监控不会下单。停止时先核对 status.json 中 PID 对应本目录 monitor.py，再向该进程发送 SIGTERM，并暂停对应自动跟进；不要误停旧生产服务。

新增文件 `monitor.py`、`test_monitor.py` 与 `monitor/` 中上述运行证据用于持续观察与验收，需保留。

仅连接公共现货 WebSocket，默认观察 OKX / Gate 的 ZEC、UNI 双向价差，可选 Bybit。没有凭证读取、私人接口、下单、撤单或转账功能。与原生产项目隔离。

使用已有 Python 3 与 websocket-client（本机检测到 1.9.0，未安装新依赖）：

```sh
python3 detector.py --seconds 60
python3 detector.py --seconds 60 --venues okx,gate --symbols ZECUSDT,UNIUSDT --proxy-port 7890
python3 -m unittest -v
```

若已有本机 HTTP 代理，可显式传 `--proxy-port 7890`；不得用于规避地区或账户限制。检测器本身不修改代理。

输出在 `runs/时间/`：配置、两所原始推送、每秒估算、JSON 汇总、中文报告。Ctrl-C 可停止；默认运行一分钟，不创建后台服务。

默认每边手续费 10 bps（0.1%），额外双腿合计缓冲 5 bps。可通过 `--fee-bps`、`--buffer-bps` 修改，并用 `--fee-source` 记录本次依据；未提供来源时标为假设。2026-09-23 的 OKX 账户查询与 Gate 用户截图均显示吃单0.1%，但未验证实际成交扣费。金额默认 100、500、1000 USDT，指买入名义金额，不含手续费。

Gate 使用 spot.order_book 的100档、100ms完整快照，每次替换全部盘口，以 result.t 检查行情年龄；不混用增量协议。

盘口按数量逐档计算。已包括的深度冲击不重复扣除；额外缓冲只是延迟/误差假设，不是滑点实测。数据过时2秒、两所时间差超过500ms、盘口不完整或深度不足时不估算。重连须新快照；OKX 检查 prevSeqId，Bybit 使用更新ID并接受服务重置快照。未实现旧版 checksum 校验；保存原始消息以便审查。

跨所卖出假定预先持有币，不是无资金的空卖。估算不含真实再平衡费用、失败补对冲、交易精度/最小单验证及实际手续费扣币方式。现货观察不涉及永续资金费；若扩展合约必须另行实现。重复正值采样不是独立交易次数；最大收益不是平均收益。没有排队成交模拟、没有订单发送，不能把结果当盈利回测。

后续验收：实际费率与规格、前向数据质量、连续机会分段、延迟压力测试、库存再平衡、故障损失，之后才能讨论独立模拟盘。

资料：
- https://www.okx.com/docs-v5/en/
- https://bybit-exchange.github.io/docs/v5/websocket/public/orderbook
- https://www.gate.com/docs/developers/apiv4/ws/en/

本任务生成物：detector.py、test_detector.py、README.md，以及 runs/ 下每次观察证据；均需保留。测试使用 PYTHONDONTWRITEBYTECODE=1 避免缓存。

## 50币种动态观察（2026-09-24）

当前运行 `python3 monitor.py --universe`。`universe.py` 从 OKX 与 Gate 官方公开REST接口取共同USDT现货，排除BTC/ETH、停牌、Gate ST标签、杠杆代币、Gate充提关闭或状态缺失的币；超过5%的跨所报价差异先隔离。币名匹配不等于身份核验，OKX充提及各币种专属账户费率仍为UNKNOWN。初筛不是可交易白名单。

每轮取5次最优买卖报价，按扣保守费用后正值次数、净价差中位数、峰值排序，最多选50个；不按市值排名。第一轮282个符合基础条件，选50个。全量排名、排除原因、币种元数据及来源保存在 `monitor/universe.json` 和每轮 `monitor/universe-时间戳.json`。进程每15分钟重新筛选，更新名单时关闭旧订阅后再连接，若刷新失败保留原名单并在status中报告错误。

每个币种仍以100、500、1000 USDT检查完整盘口深度和时效，50个币不代表同时有50个有效信号。当前初筛未使用全部币种的完整深度，深度检验在入选后进行；不承诺这50个是全市场最优。新币种OKX按10bps假设，Gate按账户显示10bps与公共币对费率中较高者；本轮Gate通常20bps，另加5bps缓冲，因此不能直接沿用此前两币0.25%的总成本。配置symbol_metadata与每条记录保存实际使用的费率。

候选发生约1秒后按原始币数量重新计算两边成本，写入 `delay_check`，记录实际延迟；行情失效就标无效，不认定盈利。仅同时重新计价，不模拟真实订单、部分成交、两腿先后、资金再平衡或故障补单。按每10个币一组订阅，保持每秒计算。无交易/凭证功能。

自动跟进已改名“50币种套利观察”，仍使用id `zec-uni`，每15分钟检查新候选、延迟记录和覆盖率。新产物：`universe.py`、`test_universe.py`、上述轮次扫描JSON、`monitor/pre-expansion-1480.json`及新运行目录。旧数据保留。
