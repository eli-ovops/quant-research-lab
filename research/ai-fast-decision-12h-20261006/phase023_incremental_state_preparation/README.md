# 阶段023：独立增量状态接口的离线等价与耗时

固定有效数据的有限接口层通过：113/10000/100000各3次，共9次snapshot与冻结V3.1 canonical逐字段、整state SHA以及完整prefix SHA全部一致；9snapshot/9validate成功。hot snapshot约0.166–0.286ms，未超250ms。这不是liveTTL、provider/订单确认或盈利验收，所有状态is_live=false，实际API latency=null。

|已ingest行数|hot snapshot三次ms|validate三次ms|canonical serialize三次ms|
|---:|---|---|---|
|113|0.188 / 0.179 / 0.166|0.747 / 0.607 / 0.575|0.098 / 0.089 / 0.081|
|10000|0.235 / 0.179 / 0.175|0.517 / 0.550 / 0.536|0.061 / 0.056 / 0.059|
|100000|0.286 / 0.180 / 0.180|0.798 / 0.542 / 0.524|0.085 / 0.084 / 0.081|

没有每次snapshot回放全prefix：每收到一行只更新原Features/ExactFlow和滚动源/盘口/1s流witness。prefix hasher累计的是精确旧canonical list JSON：`[`，各canonical(row)间`,`；snapshot复制hash状态并加入`]`，不是替换成另一种链hash。原始row复制不可变，当前/参考record及exactflow witness原价量、ruleSHA、费用/容量、判定均沿冻结V3.1。旧所有代码/collector未修改，六币registry相同；新增三币模型资格仍NOT_VALIDATED。

保持1s＋250ms参考容差并保留边界前一盘口；只裁book历史/当期witness，不忘掉原seen tradeID。重复不重乘成交量，冲突及无效状态不能被先前cached成功快照掩盖；current/ref/freshness和history/send禁止仍由原校验检查。新增wall单调、ms/ns匹配、rawarg/非正报价等guard是安全加严；固定有效prefix等价，不等于与旧factory所有非法输入的错误类型/行为完全相同，不为速度放松guard。

100000行ingest测量一次总6.441秒，单行mean0.064414ms/median0.062ms/经验p95 0.072ms/max76.308ms；异常尾值未删。JSONparse另计557.409ms，gzip read/decompress另计207.393ms，source gzip SHA实核receipt。参考每点仅构造一次，3个hot结果反复与同点reference比；参考回放/全prefix parity检查/内存统计均在hot及ingest计时外，不把它们或重复validate相加冒充真实链路。当前缓存、同host负载与同时collector运行未控制，不能外推真实API/可靠tail latency。

retention不是永久常数空间：113/10k/100k粗略递归Python对象估计约0.57/3.45/24.52MB（非RSS，可能漏slots引用等，不是硬限）。100k时各币book缓存7–14条、raw book同规模、近期witness0–7；但两个seen ID字典各26708个，随整段增长。会话生命周期或后续内存边界需要另scope验证，不在本阶段悄悄丢ID改变规则。driver/reference原rows不计入这份cache估计。

6必要测试PASS：cold、historyTTL、精确1s边界、repeat/conflict、source/clock/ordinal/futurefield错位、prefix hash及状态等价，另失败timing/partial日志保存测试。第一测量driver在任何ingest前误把registry list当函数调用而失败，v1 code/freeze/error/hashreceipt保存，修driver后新freeze；不是旧参考结果或慢样本被替换。真实测量无ingest/validate失败，若失败会先保存actualstart/end/error/行号/partial再停未知state。

有限字段审计另进行一次增量重ingest（不作第二测速、不重建旧reference、不跑策略），独立整JSON prefix SHA和原source/current/ref价量及exactflow与三point golden state SHA对上，并保存audited_snapshot_*.json供PMO原件核。不是第三方完整live回放。三个真实旧数据snapshot均不qualified；合格行为仅必要synthetic测试，不当真实策略事件/模型成功。

证据：protocol/execution_freeze、原core字节副本、tests、timing_records、ingest_timing、retention_records、source_integrity_receipt、audit及三个原件快照。实际model/network/private/key/paid/install/新规则0；job00854627/session57237不动，不读live收益。总12h ACTIVE，localhot可行不替代费后机会存在或真实执行证据。
