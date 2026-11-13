# 阶段018：固定PEPE/WIF/BONK公开资格

三个预先固定候选均通过公开规格、单次盘口首5档500USDT入口含费容量与闭合分钟网格检查；只证明数据与单位可用，不证明15秒机会、alpha或可买。共9个专用public调用，无重试/替换币、没有收益计算、模型、key/private/安装或新WS采集。

|候选|ctVal / ctMult|lot / min|tick|单盘口spread bps|180根闭合1m range中位数 / p90 bps|
|---|---:|---:|---:|---:|---:|
|PEPE-USDT-SWAP|10000000 PEPE / 1|0.1 / 0.1|0.000000001|2.3493|7.0348 / 14.1110|
|WIF-USDT-SWAP|1 WIF / 1|1 / 1|0.0001|4.0593|12.0943 / 20.3915|
|BONK-USDT-SWAP|100000 BONK / 1|1 / 1|0.000000001|2.7141|8.0983 / 16.2955|

均为对应instId/live/linear/USDT结算SWAP，真实ctVal/ctMult/lot/min/tick及币单位来自本轮public原信封，不猜缩放。首5档两方向、每腿5/10bps假设共12入口容量案例用原Fraction数量规则估算，独立Fraction核价量与grid、notional＋入口费≤500通过；未计算立即反向价费收益或未来退出。单次盘口不保证后续深度、partial、真实费用或撮合。

每币180根confirm=1闭合分钟OHLC合法、UTC一分钟网格无gap，排除1根forming。high-low/close范围仅过去单边分钟代理；不能等同未来/秒级双边可执行空间，最大分钟范围不用于选赢家/放宽015门槛。旧六币数据的时间段与本轮不同，也不作严格同市场状态排名。

全部三个固定候选及原9信封保存raw/，request开始/完成UTC与provider requestTime、endpoint可核；这些时间不是精确服务器同步或model/network时延。没有失败也没有扫其它币。qualified_instruments.json提供原样可追溯规格，results/audit/manifest保存有限资格层；旧固定八配置、费用/hold/seed均未改。

尚未授权/启动下一source，所有现有collector均终态。实际AI/provider/盈利结果null，Decisions未知，12h总代码目标ACTIVE，等待PMO对下一有限步骤派单，不自行采集。
