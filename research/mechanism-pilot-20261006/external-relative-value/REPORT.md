# 四机制公开数据初查（2026-10-06）

结论：取得真实期限盘口、期权链/Greeks/保证金参数和592点历史赔率，完成500U纸面规模检查；四项均没有盈利回测通过证据。优先后续验证跨期限报价回放。指数先补真实持仓；预测传导先补可用时点与代币报价；期权先解决500U资金缓冲和准入，再谈收益。

唯一Owner为 `/root/external_relative_value`，只写本目录。已读全局 §§0/2/3/4、agent-reach、backtesting-frameworks、okx-cex-market 和用户指数原件。ROUTING-2026-09-30-v3，目标gpt-6.1-sol/medium，实际model/effort/速度均UNKNOWN。纯公开只读、无订单、无账户接口、无秘密、无安装、无生产、无后台。Skill要求升级/查认证配置与本次边界冲突，因此未执行。37次显式公共请求（10个OKX MCP、1个失败Exa、8条web搜索、10个web打开/点击、8个直接公开GET）；内部HTTP重试UNKNOWN。CLI版本命令另有一次自动更新提示，其内部请求UNKNOWN，保守计38次外部操作。

## 1. 跨期限基差：有真实净报价成本，收益未检验

BTC-USD-261030近月与BTC-USD-261225远月各1张，面值各100USD，最小0.1张；BTC结算。两本盘口时间差50ms：买近月85900.8、卖远月86546.1；立即反向退出近月85880.2、远月按深度86558.64（首档仅0.2张，不能把86557.2用于整张）。真实盘口即刻往返损失0.038224USD；假设每腿taker0.05%，四腿费用0.198522USD，净 **-0.236746USD**。真实个人费率UNKNOWN，不把假设当官方已核账户费率。

BTC逆向合约现金流按 `100*(1/near_entry-1/near_exit+1/far_exit-1/far_entry)` 计BTC，再用退出时BTCUSD统一记账。200USD BTC抵押预算为本地保守无净额假设，gross票面不是保证金；公共tier已保存，账户实际模式/抵押折扣/可用保证金/资格UNKNOWN。BTC抵押自身有方向敞口，不能因两腿抵消就忽略。

期限曲线斜率隐含的0.742855USD只有在两腿未来按同价退出这一额外假设下成立。两期限各自到期结算价不同；近月先结算后，远月继续裸露。若持至远月，必须显式近月到期对冲/roll及成本，本轮未做。假想退出85000/85500，扣假设费只得-0.045290USD；85000/86500为-1.194024USD；90000/90000为+0.576814USD。这些是压力计算，不是历史收益。

合约与[结算规则](https://www.okx.com/help/expiry-futures)已核：BTC结算、到期最后一小时逐秒指数平均；cross daily settlement会重置成本基础。尚未取得多日逐笔盘口/roll/真实资金可用性，没有锁定套利结论。

## 2. delta对冲期权：真实链已取得，500U资金约束接近边缘

BTC-USD-261009-85500-C，最小1张，multiplier0.01BTC。真实bid0.012、ask0.0125（按1BTC underlying报BTC），1张卖出权利金约10.269948USD；实时mark0.01213594；public mark IV30.5821%，deltaBS0.5272003，inverse delta0.5150792。IV为mark参考，不是可成交卖价。标准USD经济delta spot hedge约0.005272003BTC/451.193299USD。index、book、Greek、mark分别在04:13:03、04:13:56、04:14:20、04:15:06UTC采集，异步，不能称整套可执行净报价。

按[非PM官方公式](https://www.okx.com/help/ii-option-margin)和公共tier factor1，position IMR138.760636USD，sell-to-open IMR128.490688USD，MMR36.061156USD。若保证金与spot hedge分开备资，占用 **579.683986USD，超过500U**。若所持spot BTC部分直接作为币本位保证金，则不能双算；451.193299USD总BTC持仓中锁定128.490688USD，剩余总预算48.806701USD（费用前）。这只是资金恒等式检查，未验证实际账户隔离模式、可锁币数量或资格。抵押BTC全部计入USD delta；权利金到账亦需纳入后续重平衡。

假设option费率0.03%、spot0.1%，期权即时往返spread0.427915USD+两次fee0.513497USD，spot入场fee0.451193USD；缺spot真实bidask，因此完整净报价UNKNOWN。1张在5%跳变的局部gamma二次项损失约14.97USD，非尾部损失上界。delta对冲仍有gamma、jump、vega、离散再平衡、流动性和margin风险，BTC抵押也有价值变化。

[公开准入说明](https://www.okx.com/en-gb/help/get-started-with-okx-options)列大陆KYC非simple期权启用资金10000USD；海外KYC该项无最低资金。用户实际资格UNKNOWN，未碰账户。没有用IV与过去RV差推断收益，没有完整卖方回测；500U可行性只能列条件成立，不能称可交易通过。

## 3. 预测市场赔率→代币传导：取得真赔率，缺关键时间证据

固定历史事件为“SEC首个spot Bitcoin ETF是否在2024-01-10获批”，映射BTC、对照ETH，在下载赔率和任何代币收益测试前固定；事件本身事后选取，只用于可行性。Gamma原始metadata保存四个Jan8/9/10/未批结果。CLOB历史接口返回592点，UTC2024-01-08 22:15:02至01-10 23:55:02，最大相邻间隔1462秒；API请求5分钟fidelity，但返回并非严格5分钟网格。

赔率数据能获得，然而现在重建的历史时间不等原始首次接收时间，缺历史token bidask/交易深度、延迟、共同信息发布控制。即便赔率与BTC曲线相关，也不能证明赔率领先或可赚钱。本轮未计算方向收益、500U成交或因果传导。事件由[SEC issuer filing](https://www.sec.gov/Archives/edgar/data/1588489/000095017024003719/gbtc_uplist_pr.htm)交叉确认。赔率token ID和URL在raw原件/请求回执，不以终值拟合信号。

## 4. 指数调仓：公告与实物载体真实，实际买盘UNKNOWN

识别两次历史具体调整：

| 公告 | 生效 | 新增/剔除 | 当时指示权重 | 因子确定 |
|---|---|---|---|---|
|[2026-01-02](https://downloads.coindesk.com/cd3/CDI/IA/CD20-Final-2026Q1-Reconstitution-Results.pdf)|01-30 16:00ET|BNB/POL|15.56%/0.19%|01-23|
|[2026-04-02](https://downloads.coindesk.com/cd3/CDI/IA/CD20-Final-Apr-2026-Reconstitution-Results.pdf)|04-30 16:00ET|TAO/APT|0.60%/0.12%|04-23|

[2026-10-02公告](https://downloads.coindesk.com/cd3/CDI/IA/CD20-Final-Oct-2026-Reconstitution-Results.pdf)拟10-30 16:00ET加入GRAM(previously Toncoin)、剔除CRO；0.61%为指示权重，10-23因子与10-30最终权重尚未产生，不能当历史样本。GRAM现货contract/ticker身份尚未映射，未查其收益。

WisdomTree [官方factsheet](https://dataspanapi.wisdomtree.com/pdr/documents/FACTSHEET/WIXL/EU/EN-GB/GB00BN474G19/)真实下载并提取文本，当前原件文档日期2026-08-31，与搜索缓存出现03-31不同；以下载原件为准。ISIN GB00BN474G19、Physical replication、staking、custody可核。但该原件没有逐币持币数量、历史份额、申赎流和前后调仓记录。官网产品页401未绕过。

已找2历史事件，要求4个机制样本尚未满足；已检验资金流事件数 **0**。实际净买入=目标持仓-漂移后的现有持仓，必须同时扣申赎与staking变化。未知持仓时既不拿AUM代替买入，也不把新增币涨幅当机械买盘。500U价格策略尚未运行。

## 计价核查与证据边界

`P_BTC_USDT=P_BTC_USD/S_USDT_USD`。若BTCUSD不变而USDTUSD由1降至0.98，BTCUSDT报价机械上涨2.040816%，不是BTC USD收益。直接做空BTC增加方向敞口；隔离计价效应需统一USD账本，计入稳定币资产/负债、BTC抵押和hedge全部数量。

合约选择在首次现场chain看到后进行，属于报价可行性，不是预注册盈利检验。没有历史收益样本。raw API原件、失败请求和官方web摘录在 `raw/`；后者明确标“web excerpt”，没有冒充原PDF。`manifest.json`逐件路径、大小、SHA256。`protocol.json`记录规则、选择时点、预算和假设；`results.json`四项状态和数值。离线复算：`python3 compute.py`，不再联网；`fetch_public.py`/`fetch_extra.py`是公开GET采集复现脚本，再次运行会新增调用并覆盖同名raw，当前任务未重跑。

验收：本地计算与原件匹配待父任务审核；交易/账户/盈利门均未通过。原始传输错误、Exa未配置、OKX初始BTC-USDT family无数据/51000均保留；只查受支持BTC-USD公开产品，未修环境、降TLS或重发同失败参数。无一次性清理项，所有新建文件均为交付证据/脚本，保留；总量低于100MB。
