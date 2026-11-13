# 阶段026：10s冲击后压力持续/衰减的两固定规则准备

只完成预登记/实现/必要边界层，7tests及有限synthetic一致数学检查PASS，没有历史/live收益计算。新增CONTINUATION_FOLLOW_V1与PRESSURE_DECAY_FADE_V1，总10配置≤12；旧8规则、费率、容量、hold和code不改，025原58613继续有限probe不受影响。

COMMON10固定：同run/conn/boot/实际OS域，真实received trade warmup≥10s、current book≤250ms，10s与1s参考target error≤250ms；精确tradeID/source去重10s total/net，absimb10≥0.8且与10s midpoint位移同方向。当前双方向500容量＋同qty反向depth的fee5必要位移都可估，abs10≥max required＋固定5bps（等号合格，<才拒），dominant10≥ref10对手top5名义规模。没有费用降档或过去winner择门槛。

当前1s必须total1>0、最新新去重trade received age≤250ms；重复不刷新age。prior9=total10−total1>0，rate r=9*total1/prior9精确；嵌套还核|net10−net1|≤prior9，不能接受不可能的窗口总/净量。CONTINUATION：r≥1、absimb1≥0.8且与shock方向同号→FOLLOW。DECAY：r≤0.25且absimb1≤0.2→FADE。互斥，不把零消息、网络缺采或缺ID当耗竭；missing/conflict为UNKNOWN拒绝。

每币每rule35s冷却仅完整qualified后启动。未来必须PressureRules(forward_cut_ns=execution_freeze真实OS cut)，source在cut前仅更新因果warmup、拒绝输出且不消耗冷却；不能先跑precut事件再过滤，从而让旧冷却影响第一个前向事件。025从22:06开始早于新cut，其较早前缀只可作warmup；需同时保留warmup/eligible消息分母，不伪称全段新OOS。

完整代码/tests/protocol实际cut为execution_freeze记录的22:20:17.734314UTC（OS/采样bracket原件同文件），不是开始写协议的时点。此时尚无任何经济结果。输入source单位九币原字节与025/018注册核过。protocol先于未来收益明确same-asof FOLLOW+FADE shadows、原500容量/费/hold/delay，各自qty不匹配不当严格同qty配对；actual branch只用预登记方向，不能事后best当模型成绩或救参数。13grid可另列无条件频率benchmark，非匹配因果对照。

未来仍独立500U情景、15s主/5与30diag、五delay、fee5/10每腿，不把窗口/方向/资产相加为组合。压力与旧1s成本门槛是独立新假设，没有降低旧门槛。这里的成交/价格都是收到观察代理，不称真实强平、撤单、流动性补偿或未来可获利，完整市场/网络仍UNKNOWN。

独立state_pressure_transition_v1/question草案见pressure_state_question.md，不别名V3.1。provider adapter NOT_IMPLEMENTED/实际API0，future_path/outcome/price_fee_delta标签禁止模型输入，qualification也不保证edge。所有qualified行为目前仅SYNTHETIC fixture，非真实市场事件或模型成功。

7tests涵盖等号与1E-30邻界、嵌套一致/不可能窗口拒绝、1s/10s边界、unique fresh/repeat/conflict/缺ID、zero-message WAIT、域/clock因果、warmup及precut不占冷却、shadow固定。有限异实现exact Fraction重新核两真实一致synthetic向量及公开规格，未来原raw audit入口已登记，非第三方策略复放。最初DECAY fixture的net10=369造成prior净量367>总量360不可行，按审查改为362并保留不可行拒绝测试，所有改动均在实数据结果前。

source/newrule bytehash/actualcut见protocol/execution_freeze，audit/results无profit，manifest封存当前准备。总12h ACTIVE，不启动新WS或模型、不触025/旧代码，闭合后真实评价由root下一有限scope授权。
