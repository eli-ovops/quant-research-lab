# Phase005完整捕获扩展（数值删失验收部分失败）
原001完整45min捕获已正常归档，72事件（dev4/prefreeze remainder15/postcorefreeze53）、64个100ms锚定描述簇。观察到的主条件价差均值仍为负，但事件引擎6条删失被证实是数值残余误拒，当前整体实现验收PARTIAL_FAIL，不能使用历史初版audit PASS代替当前状态。已获授权在独立phase005_numeric_v12修复；这里不覆写core或补填null收益。

0人工delay/15s主/每腿5bps，独立每资产每cohort平均事件price_fee_delta USDT（不是账户）：
|cohort|资产|观察/删失|FOLLOW均值|FADE均值|
|---|---|---:|---:|---:|
|dev_prefix|BTC|1/0|-0.605424|-0.378564|
|dev_prefix|ETH|1/0|-0.407321|-0.595001|
|dev_prefix|SOL|2/0|-0.601860|-0.478760|
|prefreeze remainder|BTC|5/1|-0.522034|-0.465486|
|prefreeze remainder|ETH|2/1|-0.386216|-0.616216|
|prefreeze remainder|SOL|4/2|-0.303438|-0.776388|
|postcorefreeze|BTC|9/0|-0.497948|-0.499237|
|postcorefreeze|ETH|9/1|-0.442126|-0.557777|
|postcorefreeze|SOL|29/5|-0.553341|-0.527685|

summary保留全部资产/cohort/动作/人工delay/hold/5及10bps的均值、中位、经验尾部/正值比例与N，不相加不同币种、配置或窗口。新段SOL FOLLOW此条件仅1/29正单笔，最大+0.037562；均值为负，不挑该赢家。10bps新段六个动作均值约-0.94至-1.06。5/30s仅诊断，不择最优；人工delay不是AI时延。72事件中16个在8个多事件近接收簇，不能当独立N。

事件asof按原消息壁钟≥v1.1实际冻结15:41:45.496551UTC为postcorefreeze；初始≤20000 ordinal为dev，剩余早段为prefreeze。连续feature/cooldown不重置。core逐字节不变，原dev240条件价差旧字段精确复现。adapter/去重/资金费质量协议16:13才冻结且数据已结束，不能称完整前向/OOS；只说新数据在核心阈值冻结后到达、未用于选择当时core阈值。tradeId重复/冲突/缺失均0，去重本次无输入或asof变化，count未乘作volume。

完整4320条件的删失：260 expired_exit_quote、240 expired_entry_quote、20缺未来出口、6 minlot/entrydepth。最后6源于2个sizing案例：真实五档深度足、floor qty满足min，但Decimal残余+1E-137使budget>0返回None。所有null及原件保留、不得将该6称真实不足或报告全部删失通过。numeric_censor_diagnosis含正向quote/精确trace；未填exit或收益。初版有限audit曾核22特征、234有效及38 null；追加原因核明确失败，当前audit/result已撤下整体PASS，原回执另存。

数据层当前入口CAPTURE_ACCEPTANCE；raw最终217912条/141714246B、SHA ed09711a3a95d3c049d7a252fb4892ceee7c4cbeba78ed021c3437f2ad7d6bff，只读不复制。原PID26221/session83334正常停止、source未改。完整ordinal/processmono连续、无>50ms相邻wall跳变，但book gaps最长3.4–3.7s、trades4.8–5.6s；prevSeq缺失、聚合/变化推送，完整市场数据UNKNOWN，不能把无推送等同漏采。旧processmono不倒填OSshared。

3次公开funding history有16:00实际时点/rate；SOL事件49有40不同诊断rows跨时点，仅flag、资金费不填现金，真实mark/tier/margin/financing UNKNOWN，非全经济净结果。资金费raw/time/window摘要保留，未私有查询或付费。0模型/key/install，无新collector；global12h继续。NEXT_CAPTURE_PROPOSAL未启动v2，下一步先独立数值修复与全部公平复核后由PMO派新采集。

