from pathlib import Path
import csv,json,datetime,hashlib
P=Path(__file__).resolve().parent
# Columns preserve explicit unknowns rather than imputed zero performance.
data=[
('1.1','同标的/线性反向/计价结算/乘数/币张金额单位','适用','instFamily BTC/ETH-USDT; ctType linear; settleCcy USDT; q=n*ctVal*ctMult','all_futures,BTC_futures,ETH_futures,BTC_family,ETH_family','analyze.py:eligible / universe.csv','四次家族查询+全量清单','0个符合产品','无实施产品，不报收益','USD_UM非USDT；历史规格未核','是'),
('1.2','最小量/步长/金额/精度/最大量','适用','现货基础币扣费后向步长配平；合约规格必须有对应有效产品','BTC_spot,ETH_spot,all_futures','universe.csv; analyze.py rounding test','现货规格读取/舍入边界','现货规格已存；对应合约不存在','2,000U实际可下单性不成立','历史张数/金额限制UNKNOWN','是'),
('1.3','上市下市迁移/历史版本/地区账户权限/幸存偏差','适用','先固定BTC/ETH，不从存续合约构造历史集合','discontinuation,BTC_delivery,ETH_delivery,all_futures','report.md; protocol.json','公告与交割记录与产品清单交叉','最后到期2026-06-26','当前路线不可实施','历史版本/地区/权限UNKNOWN','是'),
('2.1','官方来源/时区/采集时刻/交易所时钟/接收时间','适用','原始字节SHA256; UTC milliseconds','time; sources.json','collect.py; results.json','哈希全验；服务器与请求中点比较','19份成功来源，time RTT401ms/中点差157.5ms','不是成交延迟保证','网络往返非撮合延迟','是-正面执行结论'),
('2.2','完整性/重复缺口乱序/陈旧不同步/重连/异常价','适用','一次性REST；结算点排序、重复检测；无盘口连续性假设','BTC_settlement,ETH_settlement,BTC_delivery,ETH_delivery','analyze.py settlement audit','4点每币、唯一时间戳检查','稀疏片段，完整历史UNKNOWN','无法估计完整路径损失','缺完整盘口与标记路径；无重连采样','是'),
('2.3','指数标记价/未来填充/事后修订/历史盘口','适用','每日标记均价和到期指数均价分离；禁止填充','daily,delivery_rule','report.md','官方定义与原始响应对照','未把现在规格/盘口冒充历史','历史真实成交收益UNKNOWN','历史修订/版本UNKNOWN','是'),
('3.1','买ask卖bid/多档深度/容量/时延冲击','適用但产品门槛失败未执行','预注册100档、age<=2s/skew<=1s；仍不保证同时成交','protocol.json; all_futures','protocol.json','无有效产品即停止','无任何盘口成本填充','滑点/容量UNKNOWN，非0','真实同步盘口UNKNOWN','是'),
('3.2','排队撤单/部分成交/拒单/单腿失败/网络平台故障','适用','taker也可能拒单/部分成交；maker未成交不记收益','protocol.json','report.md','无订单；风险识别','真实执行未验证','紧急损失无已证实上界','全部UNKNOWN','是'),
('3.3','价格限制/强制退出/紧急平仓/K线先后/重复消费盘口','适用；K线先后不适用','无K线策略/未消费历史盘口；无替代合约成交模拟','protocol.json; results.json','report.md','交易次数0','没有假设止损一定成交','尾部损失UNKNOWN','价格限制与故障退出费未核','是'),
('4.1','开平每腿maker/taker/优惠/费率有效期','适用','spot .001; future .0005公开示例；无优惠','fees,futures_fees','cash_ledger in analyze.py','合成现金恒等式6案例','场景非实际账户费率','倍增预登记未运行','实际费率/地区费表UNKNOWN','是'),
('4.2','扣费币种/基础币缩水/精度取整','适用','gross=q/(1-a)上取整；残余显式跟踪','fees,BTC_spot,ETH_spot','analyze.py rounding test','基础币数量边界','合成残余9.98e-9 BTC','仅单测不是实际持仓','真实成交分笔取整UNKNOWN','是'),
('4.3','资金费/借贷/交割费与日结算费','适用','普通定期非永续；无借贷；每日结算零费不同于交割.0001示例','daily,fees; protocol.json','cash_ledger; report.md','平仓/交割两个分支分别检验','不同时扣平仓与交割费','费用门槛约26.023/30.025bps纯代数','本产品无有效现价与实际费率','是'),
('4.4','转账兑换再平衡/出入金','适用','研究约束禁止转账/借贷；资金已在交易所是假设情景','protocol.json','report.md','不执行资金操作','非到手收益口径','真实入出金兑换费用UNKNOWN','不能默认为免费','是'),
('5.1','统一资本/现货现金保证金备用/共享竞争/净总敞口/库存','适用','2000总资本；spot<=900; margin900; remainder reserve；逐一独立情景','protocol.json','cash_ledger; report.md','独立现金式与价差式','无实际配置资金；不叠加场景','收益分母2000，结果null','实际账户库存UNKNOWN','是'),
('5.2','抵押品重复使用/折扣/补仓时间/清算ADL','适用','现货不计入合约抵押；不得自动补仓；M-C+q(F0-Ft)','BTC_tiers,ETH_tiers','report.md','公共tiers只作参考，不套精确清算','首档mmr .0065/.02；适用性未证实','有限保证金不能承受任意上涨','实际清算/ADL/补入可达性UNKNOWN','是'),
('5.3','盯市与已实现/每日结算价重置','适用；isolated与cross需分开','sum q(Fprev-Fnext)=q(Ffirst-Flast)','BTC_settlement,ETH_settlement,daily','settlement_audit.csv; analyze.py','逐段求和独立对首末差；双计反例','两币均恒等；非账户实证','BTC2318.38546/ETH107.66904 每基础币价差','无完整现金路径或账户流水','是-真实账务'),
('6.1','价格基差/费用/利息汇兑/残余/权益恒等','适用','期末=2000-毛现货成本-开费+净卖现货+空头差-退费','protocol.json; fees','cash_ledger','两个独立代数路径6案例','合成对账通过；真实交易0','实际净损益null','真实两腿交易流水不存在','是'),
('6.2','税务/稳定币平台风险/基础设施/人工成本','适用','税前研究；运营5/20U敏感性预注册但未运行','protocol.json','report.md','未知明确列出','不称到手收益','脱锚/冻结可影响整账户；未定量','地区税率/开销/违约概率UNKNOWN','是'),
('7.1','最大回撤恢复/单笔单日尾损/最差行情/集中度/锁定期','适用','0个独立完成交易不得统计；到期日不保证故障退出','results.json','report.md','样本计数和数据门槛','全部绩效统计UNKNOWN','不报告零回撤','完整事件样本缺失','是'),
('7.2','极端价格基差/脱锚停机下市/无法同时退出/风险预算','适用','有限空头保证金的上涨损失无界；不自动融通现货收益','discontinuation; protocol.json','report.md','停办事实+现金约束推导','明确路径风险；无用户风险预算','+25/50/100%压力预注册未执行','尾部概率/清算精确阈值UNKNOWN','是'),
('8.1','独立经济事件/相关性/区块区间/重复场景','适用','每币3段结算不算3笔策略交易；无bootstrap假精度','results.json; settlement_audit.csv','report.md','独立完成交易0','置信区间不可估','收益正期望UNKNOWN','样本不足','是'),
('8.2','现金机会成本/风险暴露可比/额外风险收益','适用；趋势基准不适用','总账户2000；现金年率0/2/5%仅情景；不可当可获取报价','protocol.json','report.md','产品先决失败不跑收益表','无可获取现金基准证据','机会成本金额UNKNOWN','实际替代现金回报/风险溢价UNKNOWN','是'),
('9.1','原始代码配置哈希/命令依赖/边界测试/随机种子','适用','标准库Python3.9.6；无随机无需种子；离线复现','sources.json; manifest.json','analyze.py; results.json','SHA256/身份拒绝/舍入/现金对账','测试通过，经济可行性未通过','无安装及生产改动','独立B审查待做','是-最终验收'),
('9.2','费用滑点延迟流动性退出压力/未见区间/选择偏差','适用','A-v1固定币/平台/资金；产品失败停止；不为盈利换产品','protocol.json; protocol_outcome.json','report.md','预登记早于本地数据；全部22相关产品列出','无绩效调参；无真正封存样本','敏感性未运行不能称稳健','未见费后交易证据缺失','是')]
cols=['id','item','applicability','formula_assumption','source_and_raw_evidence','implementation','validation_method','result','amount_or_sensitivity','residual_unknown','blocks_positive_conclusion','checked_utc']
with (P/'coverage.csv').open('w') as f:
 w=csv.writer(f);w.writerow(cols)
 for row in data:w.writerow([*row,datetime.datetime.now(datetime.timezone.utc).isoformat()])
print('coverage rows',len(data))
