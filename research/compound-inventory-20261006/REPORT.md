# Compound历史库存续验｜本轮受阻

**没有取得历史库存数据；不能判断过去30天是否存在足够100 USDC购买的WETH库存。** 首个archive探针被HTTP 403 Forbidden拒绝。本轮不是“历史无机会”，不是策略否定，也未完成12点检查或30天回放。

唯一Owner `/root/conversion_collateral`；所读规则仍为 `ROUTING-2026-09-30-v3`，目标Astra/medium，实际model/effort/speed UNKNOWN。沿用backtesting-frameworks的固定样本、成本与库存不可重复消费约束。只写本目录，前轮conversion-collateral封存文件未修改。

## 已完成

在发起历史请求之前写入protocol.json，冻结：Ethereum USDC Comet `0xc3d688B66703497DAA19211EEdff47f25384cdc3`、WETH、Uniswap v3 WETH→USDC fee500，固定100 USDC交易规模及500 USDC资本上限。

区块区间 **25914865–26130865**，以30天×7200块/天近似，12个等块间隔粗样本：

25914865、25934501、25954138、25973774、25993410、26013047、26032683、26052320、26071956、26091592、26111229、26130865。

相邻间隔19636或19637块。截止区块对应2026-10-06 04:11:59 UTC来自前轮已封存回执；本轮没有取得首端header，**实际时间跨度尚未核实，不能把近似216000块说成精确30天**。即使12点将来全部成功，也只是粗采样，不能代表区间内每个区块。

先用距截止区块7200块的 **26123665** 检验历史读取。一个公开HTTP POST批量包含：

1. `eth_getBlockByNumber(0x18e9d91, false)`；准确参数以raw元数据为准。
2. 固定该历史块的 `getCollateralReserves(WETH)`。
3. 固定该历史块的 `getReserves()`。

请求URL `https://ethereum-rpc.publicnode.com`；原错 **`<HTTPError 403: 'Forbidden'>`**。请求起止Unix时间、完整方法与参数见 `raw/archive_probe.meta.json`。无JSON-RPC成功结果，错误响应body未被采集helper捕获，所以拒绝来自何层、是否针对历史读取均为 **UNKNOWN**。先前最新块接口成功不证明本轮历史接口可用。

报错后定向读取LOCAL_BLOCKERS的403/RPC/archive/eth_call条目，没有已验证的适用替代；遵守拒绝不绕过及无新依据不重试要求。未改User-Agent、代理、身份或配置，未换通道重发。只读工具清单也没有可直接替代的已知Ethereum archive工具。

## 未完成及证据边界

- 12个冻结样本实际状态：0个成功，全部UNKNOWN；不是库存为零。
- 全区间AbsorbCollateral(WETH)事件：后续通过独立Blockscout公开API请求固定区间，返回HTTP403/error code 1010，无事件数据。不能称未请求，也不能推断没有清算。没有从事后成功交易反挑样本。
- 同区块DEX报价、下一块库存/储备门槛/暂停/DEX：均未运行。
- 完整购买与兑换模拟、余额覆盖、gas/priority/排序、失败费用：均未运行。
- 库存账本初始余额/清算流入/购买流出：UNKNOWN。实际模拟购买数0、扣减0仅表示没有执行研究指令，不能当作历史无交易证据。
- 真实有库存案例、可执行价差、净收益：均未得到，results.json使用null/UNKNOWN，不填0利润。

下一步需要**有证据支持、符合公开访问规则的archive读取入口**，或者现成且可核的历史状态导出；取得该前提后继续同一冻结样本，不换市场、日期或依据价差挑样本。403本身不是协议不支持archive的证明，也不授权绕过拒绝。没有开展其他方向研究。

## 验证与资源

本轮累计4次公开请求操作：原archive探针1次，独立官方信息探针3次。原RPC批包含3个子方法，历史数据成功0，低于20次上限；没有以剩余额度为理由重复失败。`python3 -B recompute.py`只做本地覆盖与失败证据复算，验证12样本唯一且等间距、协议冻结早于请求、输出确定一致。`validation.json`与SHA256SUMS.json保留校验。`run.py`仅包含首次探针入口，raw同名文件防覆盖；不要把它当作已恢复访问的证明。

## 后续三项独立公开信息补核

父任务明确允许其他独立官方服务及链浏览器现有公开信息，禁止对原403请求修改身份或绕过。已完成以下一次性补核并停止：

| 来源 | 实际查询 | 当前结果 |
|---|---|---|
| Etherscan | 固定Comet地址官方事件页 | HTTP403 Forbidden，无事件正文 |
| LlamaRPC官方站 | 官方文档入口，核是否有无认证历史服务 | HTTP526，未取得文档，未猜RPC地址继续调用 |
| Blockscout Ethereum | 固定区间25914865–26130865、固定Comet、AbsorbCollateral/WETH筛选 | HTTP403，完整错误body为error code: 1010，无logs |

证据分别为raw/etherscan_address.txt、raw/llamarpc_official.txt、raw/blockscout_absorb.meta.json及raw/blockscout_absorb_error.body。Blockscout请求参数没有得到成功回执验证。各次失败不等于所有公开历史服务不可用，403也不证明archive能力不支持。未重试原资源、改UA/身份/代理、安装或读取账户。必要缺口仍是可合法访问且有证据支持的历史状态来源；历史交易日期及金额也尚未取得。

无安装、签名、账户/秘密读取、下单、转账、生产或后台操作。文件均为本轮证据与复算材料，保留用于恢复及交接；没有清理或声称释放空间。状态应记：**冻结方案/探针/错误交付完成；历史库存业务验收未完成、受阻。**
