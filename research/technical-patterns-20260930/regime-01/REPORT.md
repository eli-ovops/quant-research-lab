# 布林回归与市场状态

结论：震荡状态跨币筛选通过的持有时长：[]。筛选通过也不等于独立验证通过。

|币|小时|状态|样本|费后均值bps|压力均值bps|不重叠样本|不重叠压力bps|匹配支持率|匹配超额bps|
|---|---:|---|---:|---:|---:|---:|---:|---:|---:|
|BTC|24|range|102|-30.07|-59.96|92|-55.39|100.0%|-5.81|
|BTC|24|up|0|N/A|N/A|0|N/A|0.0%|N/A|
|BTC|24|down|119|-9.75|-39.71|99|-59.78|42.9%|-45.04|
|BTC|72|range|102|-25.77|-55.68|84|-50.02|100.0%|-14.88|
|BTC|72|up|0|N/A|N/A|0|N/A|0.0%|N/A|
|BTC|72|down|119|35.86|5.77|81|-75.01|42.9%|-0.37|
|ETH|24|range|93|-69.73|-99.51|86|-105.91|100.0%|-51.92|
|ETH|24|up|0|N/A|N/A|0|N/A|0.0%|N/A|
|ETH|24|down|116|20.55|-9.50|105|-18.67|47.4%|-3.99|
|ETH|72|range|93|-52.04|-81.87|79|-118.72|100.0%|-31.15|
|ETH|72|up|0|N/A|N/A|0|N/A|0.0%|N/A|
|ETH|72|down|116|73.15|42.95|91|42.08|47.4%|17.30|

range=震荡；up=上涨趋势；down=下跌趋势。均为信号之前的状态。

## 分年与筛选失败原因

- BTC 24h range：2023: n=27, 8.72bps；2024: n=37, -84.14bps；2025: n=23, 32.02bps；2026: n=15, -61.71bps。失败项：['stress_mean_not_positive', 'nonoverlap_stress_not_positive', 'fewer_than3_positive_years_with10_events', 'no_positive_matched_excess']
- BTC 24h up：2023: n=0, N/Abps；2024: n=0, N/Abps；2025: n=0, N/Abps；2026: n=0, N/Abps。失败项：['fewer_than30_events', 'fewer_than20_nonoverlapping_events', 'stress_mean_not_positive', 'nonoverlap_stress_not_positive', 'fewer_than3_positive_years_with10_events', 'matched_support_below80pct', 'no_positive_matched_excess']
- BTC 24h down：2023: n=31, -15.69bps；2024: n=33, 28.50bps；2025: n=36, -22.59bps；2026: n=19, -42.17bps。失败项：['stress_mean_not_positive', 'nonoverlap_stress_not_positive', 'fewer_than3_positive_years_with10_events', 'matched_support_below80pct', 'no_positive_matched_excess']
- BTC 72h range：2023: n=27, -96.01bps；2024: n=37, -45.16bps；2025: n=23, 32.15bps；2026: n=15, 59.67bps。失败项：['stress_mean_not_positive', 'nonoverlap_stress_not_positive', 'fewer_than3_positive_years_with10_events', 'no_positive_matched_excess']
- BTC 72h up：2023: n=0, N/Abps；2024: n=0, N/Abps；2025: n=0, N/Abps；2026: n=0, N/Abps。失败项：['fewer_than30_events', 'fewer_than20_nonoverlapping_events', 'stress_mean_not_positive', 'nonoverlap_stress_not_positive', 'fewer_than3_positive_years_with10_events', 'matched_support_below80pct', 'no_positive_matched_excess']
- BTC 72h down：2023: n=31, 25.96bps；2024: n=33, 26.02bps；2025: n=36, 94.32bps；2026: n=19, -41.65bps。失败项：['nonoverlap_stress_not_positive', 'matched_support_below80pct', 'no_positive_matched_excess']
- ETH 24h range：2023: n=23, 17.29bps；2024: n=25, -100.26bps；2025: n=26, -52.59bps；2026: n=19, -158.39bps。失败项：['stress_mean_not_positive', 'nonoverlap_stress_not_positive', 'fewer_than3_positive_years_with10_events', 'no_positive_matched_excess']
- ETH 24h up：2023: n=0, N/Abps；2024: n=0, N/Abps；2025: n=0, N/Abps；2026: n=0, N/Abps。失败项：['fewer_than30_events', 'fewer_than20_nonoverlapping_events', 'stress_mean_not_positive', 'nonoverlap_stress_not_positive', 'fewer_than3_positive_years_with10_events', 'matched_support_below80pct', 'no_positive_matched_excess']
- ETH 24h down：2023: n=31, 71.72bps；2024: n=35, 61.14bps；2025: n=31, -20.75bps；2026: n=19, -70.34bps。失败项：['stress_mean_not_positive', 'nonoverlap_stress_not_positive', 'fewer_than3_positive_years_with10_events', 'matched_support_below80pct', 'no_positive_matched_excess']
- ETH 72h range：2023: n=23, -74.31bps；2024: n=25, -117.74bps；2025: n=26, 104.34bps；2026: n=19, -152.63bps。失败项：['stress_mean_not_positive', 'nonoverlap_stress_not_positive', 'fewer_than3_positive_years_with10_events', 'no_positive_matched_excess']
- ETH 72h up：2023: n=0, N/Abps；2024: n=0, N/Abps；2025: n=0, N/Abps；2026: n=0, N/Abps。失败项：['fewer_than30_events', 'fewer_than20_nonoverlapping_events', 'stress_mean_not_positive', 'nonoverlap_stress_not_positive', 'fewer_than3_positive_years_with10_events', 'matched_support_below80pct', 'no_positive_matched_excess']
- ETH 72h down：2023: n=31, 167.14bps；2024: n=35, 71.15bps；2025: n=31, 86.80bps；2026: n=19, -98.76bps。失败项：['matched_support_below80pct']

## 边界

数据截至2026年6月底，2026只是半年；最初130根4h作为指标预热，首段不是完整2023年。状态阈值未搜索，策略来自此前结果，故整体仍有研究选择偏差。
这只是单一ER20状态定义，失败不能证明任何震荡过滤都无效。无信号对照按同月/小时/状态匹配，仅保留至少5个对照的事件；支持不足即拒绝筛选。
去重检查按时间贪心保留、不叠加同币事件；不是完整组合，不同状态各自独立。费用为假设，真实成交、合约资金费/强平未模拟。
没有做显著性检验、状态交互因果推断或全量第二实现回放，不给盈利概率。不重启轮询，不自动优化下一轮。
