# 两项机制最小只读试验｜2026-10-06

**本轮有实测结果，但没有可执行盈利证据。** Compound 的100 USDC假设价差为+4.360068 USDC，库存却不足；Polymarket冻结路径50份费用前已为−0.45，按读取的交易费率估算后为−1.44180。以上都是当前单样本研究，未执行交易、未完成附件的30天／7天回放。

唯一Owner `/root/conversion_collateral`。已读全局细则§0/2/3/4、附件前两项、agent-reach与backtesting-frameworks。目标路由 Astra/medium，实际 model/effort/speed 均 **UNKNOWN**。使用公开RPC、Gamma、CLOB只读接口；没有钱包秘密、签名、下单、转账、安装或生产动作。

## 1. Compound III：报价成立，100U库存容量不成立

冻结 Ethereum USDC Comet `0xc3d688B66703497DAA19211EEdff47f25384cdc3`，WETH抵押品，Uniswap v3 WETH→USDC直连0.05%路径，100 USDC固定规模。没有按结果换池。

全部报价与状态固定在区块 **26130865**，2026-10-06 04:11:59 UTC。区块哈希见results.json。

| 实核项 | 结果 |
|---|---:|
| getReserves | 8,398,823.426594 USDC |
| targetReserves | 20,000,000 USDC |
| isBuyPaused | false |
| getCollateralReserves(WETH) | 0.00000043867600775 WETH |
| quoteCollateral(WETH,100 USDC) | 0.038657597202873272 WETH |
| DEX同区块回款，已含池费与价格冲击 | 104.360068 USDC |
| 回款减100，尚未扣链上成本 | +4.360068 USDC |
| 库存对应购买额线性上界 | 约0.001134773 USDC |

储备门槛与开关满足，但100U请求所需抵押品远大于库存。官方源码 `buyCollateral` 独立检查库存，报价函数不会检查库存。因此 **UPPER_BOUND_NOT_EXECUTABLE_INVENTORY**：+4.36不能记录为可赚利润，也不能用同一尘埃库存反复累计交易次数。未发送真实或模拟有余额购买交易；不可执行判断来自只读状态与代码门槛。

预言机WETH价格2699.87468468 USD，USDC价格0.999871 USD。WETH feed更新时间距该区块3396秒；已取得round与updatedAt，但未验证feed heartbeat/deviation配置，故不能宣称完整预言机健康验收。区块base fee为0.138804816 gwei；QuoterV2给出的90071仅是兑换报价内部gas估计，**不能当作买抵押品+授权+兑换整笔gas**。完整gas、priority fee、排序竞争、失败成本及下一块末到达均未测。没有运行30天历史，当前库存不足不否定整个清算机制。

证据：`raw/comet_state.{body,meta.json}`、`raw/comet_dex_oracle.{body,meta.json}`。官方仓库当前合约文件已变为 `CometWithExtendedAssetList.sol`；原 `contracts/Comet.sol` 返回404，原错保留，随后依据一次仓库树定位实际文件，没有反复重试同一路径。源码规则见 `raw/CometWithExtendedAssetList.sol:1122`、`:1149`。地址部署来自官方roots.json与[Uniswap官方部署表](https://developers.uniswap.org/docs/protocols/v3/deployments/v3-ethereum-deployments)。RPC回执不是部署字节码完整审计。

## 2. Polymarket：完整五结果路径的所读盘口上界为负

冻结选择：首次取得的100个active/未closed事件按id升序，在3–5个列明结果、negRisk=true且非augmented事件中选首个。选中 **32228 — Balance of Power: 2026 Midterms**，A是最小market id **562828（Democrats Sweep）**。完整全集：Democrats Sweep、D Senate/R House、R Senate/D House、Republicans Sweep、Other。这里Other是固定非augmented全集兜底项，不是动态占位；链上questionCount实核为5，determined=false。

Gamma标识五市场version=v1。对旧CTF adapter `0xd91E80cF2E7be2e162c6513ceD06f1dD0dA35296`逐个eth_call的五个position ID与本次CLOB资产ID全部一致；getMarketData解码出conversion fee **0 bps**。`col()`返回 **USDC.e `0x2791bca1f2de4661ed88a30c99a7a9449aa84174`**，`decimals()`实核6。不能仅凭文档把它换成新Protocol V2 NegRiskModule；当前文档明确两种体系并存。

| 腿 | 动作 | 最优可成交价 | 该价深度 |
|---|---|---:|---:|
| Democrats Sweep | 买NO ask | 0.35 | 9,418.81 |
| D Senate/R House | 卖YES bid | 0.01 | 37,405.60 |
| R Senate/D House | 卖YES bid | 0.26 | 44,818.72 |
| Republicans Sweep | 卖YES bid | 0.07 | 223,077.45 |
| Other | 卖YES bid | 0.001 | 66,741.61 |

50份买价17.50，卖回17.05，**毛差−0.45**。五腿Gamma feeSchedule均rate=0.04/exponent=1/takerOnly=true；按官方公式 `shares × rate × p × (1-p)`，逐腿汇总舍入5位估算交易费0.99180，转换费0，**未扣gas差额−1.44180**。legacy `taker_base_fee=1000`与现代feeSchedule字段同时存在，计算使用现代feeSchedule及官方公式，不把旧字段当1000bps直接套用；精确逐笔撮合的舍入与返佣未复现。

500报价单位资金上限若包含买入交易费、不含未知gas，可容纳 **1392.369799份**，买入及买费499.99999965，毛差−12.531328191，扣估算交易费后−40.150328191；全部所读深度足够。该容量是假设盘口保留、转换完成且不另占gas资金的账面容量，不是实际下单许可或保证可成交量。

**同步与抵押单位限制：** 同一次books批量请求不保证五腿同一时间。返回盘口timestamp跨度 **7.896秒**，最旧盘口距接收约 **12.336秒**，未获取共同sequence或历史撤单。因此状态为 **OBSERVED_BOOK_UPPER_BOUND_NEGATIVE_NOT_SEQUENTIAL_BACKTEST**，是“若所读报价同时保持”的条件上界；不能称真正同一时点上界。链上adapter查询使用latest且晚于盘口，不保证同块。新CLOB资金体系涉及pUSD/CTF collateral adapter，未验证pUSD与USDC.e转换ramp的实际手续费、可用性及顺序到账；本表保留CLOB美元报价单位，不能冒称全流程同抵押资产净利润。即使把所有交易费、转换费、gas及ramp成本都宽松设为零，所读价差仍负，因此此样本不值得继续顺序执行验证；这不否定其他时间／事件。

未做：真实买入结算→转换到账→逐腿卖出的时序回放、未卖完退出、7天10事件历史。当前A市场CLOB seconds_delay=0；其他腿撮合延迟未单独取得，不能把它推广为全流程零等待。没有以历史赔率代替盘口。

证据：`selected_event.json`、`raw/poly_books.*`、`raw/poly_market.*`、`raw/poly_adapter.*`、`raw/poly_collateral_decimals.*`；转换字段布局与收费源码见 `raw/MarketData.sol`、`raw/NegRiskAdapter.sol`。

## 复算与验收边界

运行 `python3 recompute.py` **只读本地raw，不联网**，生成results.json；标准库Decimal处理盘口金额，纯Python Keccak实现已核空串及transfer selector标准向量。原始HTTP请求、起止时间、响应hash保留在meta，所有交付文件hash列于SHA256SUMS.json。`probe.py`/`collect.py`/`verify.py`是此次有限采集程序，重新运行会取得新快照并覆盖同名原始证据，不应当成离线复算入口。

26个公开请求操作：8个API/RPC HTTP请求（其中RPC batch合计21个方法）、7个gh API请求、11个web读取/定位操作。40次预算按实际请求操作计，batch子方法另列，不隐藏调用量；无轮询、未安装依赖，总落盘证据约数MB，精确字节见SHA256SUMS.json。所有生成文件均作为复算／交接证据保留，无一次性无用途文件需要清理。

本轮最小快照实验已完成，完整附件研究未完成。父任务验收应分别记录规则已读、实际路由UNKNOWN、两项实测结果和未完成历史/顺序执行，不将它们统称回测完成或套利有效。

公开一手依据：[Compound官方源码](https://github.com/compound-finance/comet/blob/main/contracts/CometWithExtendedAssetList.sol)、[Polymarket转换说明](https://docs.polymarket.com/concepts/negative-risk)、[合约版本与地址](https://docs.polymarket.com/resources/contracts)、[盘口说明](https://docs.polymarket.com/market-data/prices-order-books)、[费用公式](https://docs.polymarket.com/trading/fees)、[adapter源码](https://github.com/Polymarket/neg-risk-ctf-adapter/blob/main/src/NegRiskAdapter.sol)。网页访问中Compound旧域重定向与新域工具不可读、猜测的pUSD页路径不可读原错见sources.json；没有绕过访问控制。
