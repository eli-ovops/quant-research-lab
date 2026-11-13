# 阶段022：真实本地历史状态构建耗时

当前整prefix回放/digest的状态工厂存在明确本地结构瓶颈：10k和100k测点的全部6次都超过250ms预算。不是实际provider慢，也不能把历史状态建成或schema通过称liveTTL通过。固定三点各3次未挑最快/移动测点；9工厂成功，实际失败0，失败保留机制另由必要合成测试核过。

单位ms，旧006六币历史已在内存后计时，is_live=false、feature/send时钟不补造；明确未发送请求。

|prefix行数|factory三次|validate三次|canonical state三次|build_request三次|
|---:|---|---|---|---|
|113|5.119 / 2.918 / 2.781|0.744 / 0.593 / 0.557|0.095 / 0.083 / 0.082|1.371 / 1.199 / 1.207|
|10000|365.157 / 255.490 / 254.472|0.552 / 0.520 / 0.524|0.059 / 0.059 / 0.059|0.797 / 0.935 / 0.789|
|100000|3108.526 / 2814.204 / 2908.651|0.524 / 0.650 / 0.525|0.058 / 0.058 / 0.057|0.759 / 0.795 / 0.842|

canonical envelope独立约0.057–0.095ms，45个stage原始OS start/end/ns全留timing_records。build_request本身含重复validate；不要把单独validate、state/envelope两种序列化或整个benchmark调用相加当实际生产链路。无provider/网络/订单确认成绩或p95认证。

原主测量先在单流解压/JSONparse后保存113/10k/100k前缀，再从内存测工厂，加载不在factory start/end中。原loading_records包含流式组合/先前checkpoint copy开销，不将其假称单项纯JSON时间。后另在数据前冻结load_components作为独立加载分项测量，不重测factory或改变旧记录：compressed file read1.631ms、SHA5.271ms、整份已闭合gzip解压134.519ms、splitlines69.706ms；JSONparse累计113/10k/100k分别0.626/57.360/680.818ms。整源解压包含额外26344行，但它们不进任何工厂测点或收益计算。

测量在同host已有缓存/正常负载且公共collector运行时进行，没有控制冷缓存、CPU调度或硬件环境，因此不能外推其它机器或可靠尾延迟。实际OS CLOCK_MONOTONIC及当前boot/domain留loading_records，与已验共享钟域一致；不用历史source的绝对age或synthetic send_clock伪造真实API。100k耗时2.8–3.1秒，符合全历史循环＋全prefix digest的O(n)结构，足以证明当前实现不能可靠在250ms内构建长期输入；不把三点当严格复杂度拟合或统计独立样本。

下一最小安全方向是保持原Features/ExactFlow、ordinal/run/domain及公式不变，逐收到消息增量更新状态；决策时只取当前/1s参考与滚动流、不可变小快照，prefix完整性hash在ingest时维护。需要下一scope做等价和实际耗时验证，本阶段没有修改原builder/rule，也没有自行实施优化。此工程瓶颈与当前价费空间不足是两层证据，不能靠更快模型宣称盈利。

2必要测试PASS，有限日志独立核45stage elapsed差分、4加载分项和3JSONparse checkpoint、固定9次顺序、原hash不变。不是第三方或完整live链路复放。旧V3.1仍transport硬禁用，新盘口内容hash/容量执行证据未实现，真实provider调用/费用/key/安装0，API latency=null。job008原PID54627/session57237不改，不读live收益。总12h ACTIVE，等正式续接才执行下一scope。
