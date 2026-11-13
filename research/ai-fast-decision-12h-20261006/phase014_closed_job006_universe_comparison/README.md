# 阶段014：闭合六币报价样本与固定规则/基准

结论：扩展到固定DOGE/XRP/SUI后出现一笔费后正报价事件，但未显示可用策略。15s/0名义延迟/每腿5bps的328个有效动作仅1个正（另18删失），所有币/机制/方向主均值仍负；10bps时没有正例。实际AI/provider结果仍null，不因更高分钟range或一笔正例晋级、选币或改规则。

唯一正例event94：SUI FLOW FADE，5bps价费差额+0.21666765USDT，10bps同事件−0.28236470。该asof属于13基准冻结前、14代码cut前开发区间；不能冒称控制完整前向获利。

job006原session49659 exit0、PID48225不存在，20:02:56.976173正常deadline/errornull；完整gzip CRC/EOF、126344条/140724485logical/15802694gzip、rawhash ac64fc7e1cd7557643f7acfe464d73c3a2c6bc78f2329dbad6c1ee0ae2a220d1、ordinal/run/domain/OS序及初100核验通过。每12频道含1订阅ACK，final计数含ACK，actual_data_channel_counts另列真实行情数。首版终态脚本将data-only与全frame比较导致断言失败，accept_terminal_v1和terminal_v1日志保留；修正只改核账口径，没有改source/core。当前所有collector终态，未自动续开。

元数据由012真实public specs注册，DOGE ctVal1000、XRP100、SUI1且SUI lot/min1，source及spec hash在首次新结果前绑定。原6规则、15s主/5,30s诊断、五延迟、两费、500USDT Fraction容量与合约单位未改；LEAD仅ETH/SOL，本段只有SOL一个LEAD事件，没有为新增币设置beta。173事件=FLOW68/BOOK104/LEAD1，10380条件行9902有效/478null，未把金额、币、动作、窗相加成组合收益。

主表15s/0delay，均值USDT仅报价及假设双腿费，不是账户PnL或含融资真实经济净收益。有效/删失为5bps每个动作，10bps分母保留原文件。

|机制/币|有效/删失|FOLLOW均值5 / 10bps|FADE均值5 / 10bps|
|---|---:|---:|---:|
|FLOW_IMPULSE/BTC|2/0|-0.2581 / -0.7542|-0.7354 / -1.2315|
|FLOW_IMPULSE/ETH|1/0|-0.2591 / -0.7569|-0.7401 / -1.2379|
|FLOW_IMPULSE/SOL|12/0|-0.4991 / -0.9976|-0.5819 / -1.0804|
|FLOW_IMPULSE/DOGE|16/1|-0.5749 / -1.0736|-0.5393 / -1.0380|
|FLOW_IMPULSE/XRP|8/0|-0.4882 / -0.9862|-0.5784 / -1.0761|
|FLOW_IMPULSE/SUI|24/4|-0.6273 / -1.1260|-0.4670 / -0.9659|
|BOOK_STATE/BTC|32/4|-0.4766 / -0.9727|-0.5195 / -1.0156|
|BOOK_STATE/ETH|35/0|-0.4662 / -0.9637|-0.5325 / -1.0299|
|BOOK_STATE/SOL|3/0|-0.5265 / -1.0255|-0.5541 / -1.0531|
|BOOK_STATE/DOGE|4/0|-0.5498 / -1.0485|-0.5659 / -1.0647|
|BOOK_STATE/XRP|17/1|-0.5084 / -1.0071|-0.5607 / -1.0595|
|BOOK_STATE/SUI|8/0|-0.5773 / -1.0763|-0.5257 / -1.0246|
|BTC_TRANSMISSION/SOL|1/0|-0.7877 / -1.2862|-0.2921 / -0.7906|

所有无事件group也在primary_vs_A_summary/all_signal_summary中明确0分母/null，未补0成功率；全部median/尾部/正比与诊断窗/费用/延迟保留，不挑最佳窗。

时间切分是两个独立标签：13真实UTC冻结19:48:42.510074（OS无实测证据，保持null，不回填）；14真实代码freeze/cut19:58:51.099939、OS20650331812000。13前98signal/159grid asof，13后但14前53/103，14后22/41。主fee5按13前190有效/1正，13后138有效/0正；按14后42有效/0正、另2删失。原007阈值先于整段注册，但基准冻结及wrapper后置历史必须保留，wholeepisode不是全盲OOS。preparation_cut_receipt仅早期准备快照，实际codecut另存，后续source绑定不移动该cut。

A基准为同信号asof严格1s received mid动量：85方向、81真零WAIT、7缺/过老ref UNKNOWN。BOOK500ms特征不当1s，未来同timestamp ordinal被拒。WAIT明确不交易/无费用，UNKNOWN为null；更少亏往往来自少做单，非alpha。paired_signal_vs_A.json仅保留同event同fee双方有效/WAIT的配对差，另列缺失，防把不同分母均值当精确增益。各组A统计、原特征及全部outcomes留档。

B固定35s timegrid由run首actual共享clock+1s起，固定SHA256 seed/run/asset/index方向、不择利润/未来quote，gridbook和其后entry均首后quote≤250ms。同qty退出、同fee，303grid asof/9拒绝，6币时间grid基准每费用有效均负。它的频率/分母与信号不同，不是matched随机试验或无冲击反事实。

|B时间grid币|fee5有效/删失|mean5 / mean10|
|---|---:|---:|
|BTC-USDT-SWAP|47/2|-0.4903 / -0.9864|
|ETH-USDT-SWAP|50/2|-0.4989 / -0.9964|
|SOL-USDT-SWAP|50/2|-0.5338 / -1.0324|
|DOGE-USDT-SWAP|51/1|-0.5498 / -1.0485|
|XRP-USDT-SWAP|43/4|-0.5253 / -1.0238|
|SUI-USDT-SWAP|43/8|-0.5319 / -1.0307|

100ms时间簇、重叠持有、同源冲击导致相关性，不能按跨币动作数量宣称独立样本N。较少亏不等于利润或AI增益；旧job004/005只作各自参考，不叠加收益。

3项新asset/hash/cut适配测试PASS；旧core/controls/run_adapter原字节一致。有限异实现从原gzip核152有效金额/数量/双腿费/首afterquote时序及20null、166原1s符号、303gridseed/首book；另476signal+grid实际原row wall/shared cohort核通过。不是第三方或完整独立策略复放。suite counters invalidclock/book/repeat/conflict/missingtrade均0，cooldown2944。真实fees/funding/queue/partial/mark/全市场完整性未知，spread已含VWAP不重扣。

阶段结果证据：protocol、pre_execution_code_freeze/execution_freeze、cohort_cut、capture_terminal_receipt、source_guard_receipt、events/outcomes及全summaries、baseline_A/B文件、paired_signal_vs_A、tests/audit/cohort_audit、manifest。总12小时目标ACTIVE；下一有限业务/采集需PMO另派，没有后台续采。
