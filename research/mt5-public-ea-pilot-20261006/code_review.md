# 候选源码和说明核查

本轮未取得任何mq5附件。以下行号是官方web解析页面行号，不是本地mq5源码行号；原始web回执保存在rawsource。candidate1只能说明核查，candidate2仅inline片段代码核查，candidate3仅发行者声明。

| 项 | 候选1 Session ORB | 候选2 Asian | 候选3 Pair Pro |
|---|---|---|---|
|原源|code/76153 L84列17.76KB mq5；附件读取失败，未取得|articles/17239 L538列49.79KB mq5；附件失败；inline已读|market/product/148319，付费470USD，版本2.2；未提供/取得源码|
|入场|说明L93/97/102：M1 OR，图表闭合bar确认后市价；预设本轮M5|inline L370–404：当前BID与当前bar MA比较，BuyStop/SellStop，ORDER_TIME_GTC|product L92/101–118：两符号关系偏离，阈值/相关过滤；准确公式未知|
|硬SL/TP|说明L102/117–118：对侧区间+30points，2R；实际是否总附单UNKNOWN|inline L386–404实际pending order传入区间外SL与1.3R TP；非市价maker或限价单|是否下券商硬SL/TPUNKNOWN；产品Close Target不等硬TP|
|时间/TZ|说明L107–110/128：broker/server08:00，OR30min后入场窗120min，DST由broker决定|L136–142/190–191：23→03，13退出；TimeCurrent“假设GMT”，非自动GMT转换|product L118时间filter；serverTZ/默认小时UNKNOWN|
|lot/risk|说明L116/119–120：balance1%，固定lot模式默认关闭；取整、tickvalue、保证金逻辑UNKNOWN|L127：固定0.1lot，不是按账户1%动态risk；L382参数叫pips但乘_Point|默认lot、beta敞口、保证金对冲UNKNOWN；产品L131–132仅推荐资金/lot|
|重复/最大仓|说明L112：每session最多1；跨session已有仓阻止和最大总仓UNKNOWN|L147/233/390–406 ordersPlaced成功后锁当session；不是完整最大持仓证明|product L94声称每symbol1仓，未由源码验证|
|跨日|会话结束清绘图不等平仓；实际持仓跨日/退出UNKNOWN|L422–468：13点PositionClose+cancel；失败打印日志，magic筛选未限定Symbol；不能保证实际平仓成功|L96“不打算长期拖仓”不等强制每日退出；具体carryUNKNOWN|
|grid/martingale|完整源码未取得，UNKNOWN，不能因简单宣传判定不存在|已见片段固定lot/单次session，无增仓倍数；完整附件未取得，不作全局证明|发行者L94声明非grid/martingale；独立验证UNKNOWN|
|依赖/风险|broker规格、M1历史、bar边、订单reject/重试、重启状态UNKNOWN|L119 CTrade标准库、L165 MA；L267 box范围包含03:00起点bar，需核已闭合性；L373 CopyBuffer shift0是当前MA；L517 trailing magic=0同symbol其他EA仓也可能被修改|完整计算、配对资产identity、newsfilters、外部信号依赖UNKNOWN|

候选2的重要差异不能悄悄修正：`BreakoutOffsetPips=10`但乘`_Point`，5位EURUSD时实际10points=1pip，不是10pips。ComputeBox使用`rates.time<=sessionEnd`可能纳入03:00未闭合bar；是否附件另有修复UNKNOWN。关闭函数按magic、不按symbol；trailing传magic0可能影响同symbol其他仓。没有运行或修改此EA。

候选3信号页2329290 L51/77/78/183/191/268–285：公开显示增长481.77%、复制50USD/月、80%增长集中16天、Sharpe0.11、最大depositload98.93%、equity DD21.22%、EURUSD分项显示约-55USD；产品与信号不是本轮独立账务/源码/复测证据。截图/收益数字不支持500USD可复制或非马丁验证。未支付470USD或订阅。
