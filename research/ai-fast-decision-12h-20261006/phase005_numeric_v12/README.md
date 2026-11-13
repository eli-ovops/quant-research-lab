# v1.2：精确容量数值修复
本轮必要正确性修复已完成有限验收，12小时总任务继续。旧phase005 PARTIAL_FAIL及全部v1.1代码/结果保留；没有把源码字节不变说成runtime未变。新core仅size_capacity改变，用Fraction精确值替代会留下+1E-137的Decimal逐层残余。

策略触发/事件asof/动作/3bps/.8/35s/15s主/5,30s诊断/5延迟/5,10bps/500容量完全不调。v1.2将budget=500/(1+fee)、单位/price/available/step转为精确Fraction，最后partial档一次耗完remaining并归0；integer floor(q/step)回Decimal contracts，核minlot、同qty五档notional及fee≤500。没有epsilon，没有吞掉真实不足或改变出口数量。

5项新增必要tests PASS：两个原实际假不足案例、真实depth/min不足、恰好grid/严格不足、费用后cap与exit同qty、AST证明仅sizing函数变化。16:31:31UTC代码/协议/input hash在v12首次结果前冻结，整份141.7MB raw只读索引、不复制。数据和旧结果已看，是修复回放而非新OOS；先前postfreeze标签仍只是核心阈值早于新data，adapter/修复晚于数据。

全4320条件公平重算：72个触发和全部事件字段完全一致，4314条件整个结果字段完全相同；只有6条从numeric假删失变观察，均为负，没有只补赢家。均来自ETH事件14/prefreeze/FADE/人工delay3000ms：
|hold s|5bps price_fee_delta|10bps price_fee_delta|
|---:|---:|---:|
|15主|-0.60603160|-1.10534320|
|5诊断|-0.58764080|-1.08696160|
|30诊断|-0.64833044|-1.14762088|

该组六个mean的N都由2→3。15s主/3000/FADE prefreeze ETH均值，5bps -0.59968406→-0.60179991，10bps -1.09583232→-1.09900261；5s与30s各自变化见numeric_comparison_audit，不据此选hold。0delay主和postcorefreeze新段结果均无变化。qty在所有原有效行未变，仅恢复先前无qty的6行；剩余删失仍保留null、不填零PnL。

有限异实现审计原raw核22特征、236有效、34删失抽样PASS；独立rational两案例精确remaining=0且floor contracts对应所有holds，完整对照核全部4314无影响/6恢复，PASS。不是第三方全策略独立复放，不是实际成交。全部产物仍price_fee_delta事件研究、非500U连续账户、实际费层/融资/mark/margin UNKNOWN；funding仅沿用已有实际时点flags，没有网络或现金融资补值。

代码版本、独立comparison/audit、tests、protocol/input/sourcehash/结果与summary全部保留；旧readonly入口hash复核一致。0新网络/API/key/install/收费/model调用，实际model/effort/speed UNKNOWN，目标Sol medium。修复已在新采集前冻结；phase006新共享clock collector有单独PID/协议，当前不是本回放新OOS，实际采集及后续数据验收另报。

