# 跨币种布林反弹测试

固定原规则：下跌ER20≥0.30、布林20/2下轨回归，持有72h；不逐币优化。
现货1h构造4h；测试2023至2026上半年，统一130根4h预热。基础每边10bps费用+5bps滑点；压力每边20+10bps。延迟同时顺延入场与退出。

|币|延迟h|不重叠样本|基础均值|压力均值|压力中位数|去最好5次后压力均值|最差一次|
|---|---:|---:|---:|---:|---:|---:|---:|

## 数据门槛

{"BTC": {"status": "BLOCKED", "reason": "OHLCV_invalid_or_zero"}, "ETH": {"status": "BLOCKED", "reason": "OHLCV_invalid_or_zero"}, "SOL": {"status": "BLOCKED", "reason": "OHLCV_invalid_or_zero"}, "XRP": {"status": "BLOCKED", "reason": "OHLCV_invalid_or_zero"}, "DOGE": {"status": "BLOCKED", "reason": "OHLCV_invalid_or_zero"}, "ADA": {"status": "BLOCKED", "reason": "OHLCV_invalid_or_zero"}, "LINK": {"status": "BLOCKED", "reason": "OHLCV_invalid_or_zero"}, "LTC": {"status": "BLOCKED", "reason": "OHLCV_invalid_or_zero"}}

## 零延迟分年压力均值与原筛选门槛


## 解释限制

均值是独立情景的事件收益，不是账户收益；跨币相关性、资金共享及容量未模拟，不得相加。
BTC/ETH按统一预热期重算，可能与旧80小时预热后再丢弃130根4h的数据起点不同；没有为获得有利结果选择时期。
新币种仍来自当前存续交易对，有幸存者及人工选币偏差；同一历史宏观行情不是独立时间留出集。
完整时间戳、闭合K线、OHLCV与双实现事件重建核验通过只说明数据/计算条件成立；未核验全部小时与日线交叉源、历史订单规格或可成交性。
匹配对照仅按原零延迟计算，不冒充延迟后重新匹配。去最好/最差5次为敏感性诊断，不是可执行规则。
无强平/资金费模拟，不是合约验证；无样本外验证或显著性验收，不凭最佳币种宣布策略成功。不重启轮询。
