# 独立状态与问题草案：pressure_transition_v1

family 为 CONTINUATION_FOLLOW_V1 或 PRESSURE_DECAY_FADE_V1，版本不别名V3.1。provider adapter NOT_IMPLEMENTED；不是已接入Jev/Decisions，不发送任何问题。

asof状态仅含实际received OS/wall、run/conn/boot/domain/ordinal、当前book及10s/1s参考ordinal、实际10s贸易warmup、原九币单位规格；精确去重total10/net10/total1/net1/prior9，rate=9*total1/prior9、imb1/10、10s midpoint冲击、dominant10与参考对手top5；当前两方向500容量/同qtyreverse必要位移、fee5及固定5bp、最新新去重trade age。缺消息/缺ID/冲突/clock错位为UNKNOWN或WAIT，不伪造量、时间或把无消息当耗竭。

条件是过去收到状态的观察代理，不证明真实强平、撤单、流动性补偿或未来净收益。准入只COMMON10及两互斥固定分支；等号边界照protocol。未来即使qualified也不保证edge，没有追加risk、confidence或target-profit策略。

问题草案仅作研究界面：在合格既有shock方向下，过去1s主动成交是否持续，或是否收缩且双向？返回WAIT或已预登记的branch动作作格式标记，而非重新择优调阈值。实际branch固定：continuation→FOLLOW；decay→FADE。所有future_path/outcome/price_fee_delta/后报价/胜率标签禁止输入状态或模型。

未来同一实际qualified asof可另保存FOLLOW/FADE两shadow，原fee/hold/delay/500容量，各自实际contracts记录；数量不匹配不称严格sameqty配对，censored/无事件都保留。shadow不是额外cfg，不能事后选best当模型成绩或改变branch；旧13timegrid另列只是无条件频率benchmark，非匹配随机因果反事实。
