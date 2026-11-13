# 044：精确窗口累计技术修复

**修复版同源完整回放已完成，有限语义与原始价费核验通过；不等于全旧算法逐tick等价或盈利晋级。** 原043/原21核心/20分钟TimeoutExpired原样保留，本阶段只改10秒与1秒Fraction累计求和方式，没有改规则/阈值/动作/费用/持有期。

每条新unique成交向两窗口累加精确total/net，接收时刻推进后按原严格左边界移除；重复tradeId不累加、不刷新latestunique，冲突UNKNOWN、参考book/暖机/cooldown/500反向容量原路径保持。10秒/1秒缓存只在该资产ingest行更新，跨资产消息不会误清；没有epsilon近似。

## 有限等价与接口边界

10个新增合成测试全部行输出和四缓存与原deque直接Fraction求和一致，覆盖同ns多成交、恰好1s/10s、dup/conflict、cold/ref、qualified/cool/precut、断连拒绝与新实例重warm、BTC/ETH/SUI交错静默。

支持接口限定**正常ingest(row)后的同row内部candidate**；外部直接candidate(asset,later_time)未先ingest会缺过期更新，修复版硬拒该调用，不宣称所有旧公开API兼容。断conn仍按原拒绝，未来分段需新实例warm/cool与同conn出口，不能跨连接拼收益。

完整job013原255697行只运行一次，经济PID98552、supervisor98550、原生session54442退出0；实际离线wall42.695050291秒，原20分钟未完成不是可比完整运行基准，不能给可靠加速比或当模型/API/order/hotpath时延。

旧算法在固定每币首/中/末27点+全部7最终实际asof（共34点）按因果prefix重算、与修复版同点candidate字段一致；独立原trade/book数学与动作核通过。**完整255697逐tick旧parity和整个旧event集合未证明**，原运行已timeout；有限点、数学缓存不冒充第三方完整策略重放。

## 固定主结果：15秒/0延迟，独立500容量

本源277.96647秒短冲击簇有7事件（6延续、1衰减），每fee7主行均有效，fee5正3、fee10正2；不是7个独立冲击或账户交易。

|规则/资产|事件数|5bps均值USDT|10bps均值USDT|
|---|---:|---:|---:|
|延续/XRP|1|+0.5492331|+0.0506662|
|延续/SUI|4|−0.2317496375|−0.730774275|
|延续/PEPE|1|−0.022848|−0.521696|
|衰减/XRP|1|−1.4785979|−1.9769958|
|其他规则×资产|0|null|null|

全540actual/1080shadow分母、210实际/420影子条件保留；所有420报价情景均有效，原始firststrictafter/250ms、完整depth、fee-inclusive500/nextlot、退出sameqty、gross/fees/net核一致。两方向shadow不选best为实际；不同qty/动作/fee/hold/币不合账户收益。原cost12事件与压力7无完全相同asof，但仍共用同一短市场冲击段，不是独立日期或独立N。

输入source/cuts完全同043，wrapper/修复都在已看数据之后，不是新OOS；短样本和费用假设未验证，不能挑XRP单次小正晋级。Jev/Decisions实际provider仍0调用，保证金/融资/撮合/完整市场tape未知。

## 验收与停止

旧043失败、原readonly core/source、受影响接口、预登记/测试/actualfreeze、native退出、34点等价/原数学、420quotes、1620完整分母与重合检查全部保存。多seenIDs仍保留全stream语义，缓存不保证永久常数内存。

新增045采集按单独授权运行至02:45，未用其live数据算收益；未新付费/模型/私有/订单/安装/策略配置。总体12小时目标仍ACTIVE至03:16:33UTC。技术层有限通过，不取代后续新源和真实AI验证。
