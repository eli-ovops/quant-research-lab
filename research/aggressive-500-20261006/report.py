import json,csv,statistics,gzip
from pathlib import Path
R=Path(__file__).resolve().parent
def pct(v):return 'UNKNOWN' if v is None else f'{100*v:.2f}%'
def main():
 x=json.loads((R/'results.json').read_text());p=json.loads((R/'protocol.json').read_text());lines=['# 激进500美元路径探索','', '目标：低真实成本发现高风险探索候选。不同配置的模拟亏损不合并；候选自身全部亏损保留。没有实盘投入。','',f'完成{x["configs"]}个配置，{x["strategy_accounts"]:,}个策略账户窗口，连同对照审计{x["audited_episodes"]:,}次。','', '规则：10/20倍条件SWAP，500初始，650收盘检测后下一开盘退出；账户级50%止损取消，单笔ATR止损仍保留，维护保证金代理触发可全额清零。资金不补充，窗口内连续交易，24小时最多8次、7天最多40次入场。费用为未核验假设：基础单边费用5bps+滑点5bps；压力10bps+10bps，结算资金费另计。', '', '筛选仅按压力成本下达到650的频率排序，均值用于同频率破同分；不要求稳定盈利。每类/持有窗口最多一个，冻结后才计算新增五币结果，不事后换候选。', '', '## 冻结候选在新增币种的表现', '', '|候选|有效窗口|到650|亏损|清零|平均收益|中位数|最差|目标日期簇|', '|---|---:|---:|---:|---:|---:|---:|---:|---:|']
 for r in x['holdout']:
  s=r['strategy'];lines.append(f'|{r["config"]["id"]}|{s["evaluated"]}|{s["targets"]}|{s["losses"]}|{s["zeros"]}|{pct(s["mean_return"])}|{pct(s["median_return"])}|{pct(s["worst_return"])}|{r["target_date_clusters"]}|')
 for r in x['holdout']:
  s=r['strategy'];lines+=['',f'### {r["config"]["id"]}',f'原样规则：`{json.dumps(r["config"]["rule"],ensure_ascii=False)}`。',f'探索性复现（至少两个日期簇达到650）：{r["exploratory_reproduced"]}；这不等于盈利验收。平均对照收益{pct(r["control"]["mean_return"])}，相对对照{pct(r["paired_mean"])}；全部{ s["trades"]}次平仓，{s["no_trade"]}个未入场窗口。',f'三个时段均值：{", ".join(pct(v["mean_return"]) for v in r["folds"])}。',f'按日期聚类90%均值区间：{[pct(v) for v in r["uncertainty"]["mean_ci90"]]}。日期簇不是独立市场环境，区间未作多重比较校正。','', '|币种|账户数|到650|亏损|清零|平均收益|最差|','|---|---:|---:|---:|---:|---:|---:|']
  for coin,v in r['by_coin'].items():lines.append(f'|{coin}|{v["evaluated"]}|{v["targets"]}|{v["losses"]}|{v["zeros"]}|{pct(v["mean_return"])}|{pct(v["worst_return"])}|')
 lines+=['','## 证据边界','','- 原15币历史价格已经参与以前研究，只能作为探索筛选。新增OP、ARB、UNI、AAVE、FIL在上一批未计算策略收益，本批在selection.json落盘后才计算；与旧币共用2026-07-10至10-05市场时段，不是未来/完全独立样本外。','- 所有窗口各自500美元；不同配置与币种的结果不能相加为组合收益。目标频率是历史比例，不是未来概率；低胜率或负均值不会被隐瞒。','- 无历史标记价/保证金档位、无真实成交与深度，2%维护保证金+0.2%清算费仅代理；真实强平、真实盈利UNKNOWN。20倍提高了路径敏感性，不能把OHLC结果解释为真实可成交。','- 已读取的合约规格支持20倍，但历史规格和实际账户允许杠杆未验证。没有调用账户API。','- 原规则的账户250止损只在本次新研究取消，不改旧结果；单笔止损及资金费完整计入。','- 研究候选只表示值得进一步观察，不授权实盘。没有自动轮询、无限补本金或后台常驻。','', '文件：protocol.json预注册；selection.json筛选封存；results.json完整统计；ledgers/完整逐账户与对照；execution_seal.json代码hash；data_manifest.json原始数据hash。']
 (R/'REPORT.md').write_text('\n'.join(lines)+'\n')
 with (R/'all_configurations.csv').open('w') as f:
  w=csv.writer(f);w.writerow(['phase','id','accounts','targets','losses','zeros','no_trade','mean_return','median_return','worst_return','paired_mean'])
  for r in x['screen']+x['holdout']:
   s=r['strategy'];w.writerow([r['phase'],r['config']['id'],s['evaluated'],s['targets'],s['losses'],s['zeros'],s['no_trade'],s['mean_return'],s['median_return'],s['worst_return'],r['paired_mean']])
if __name__=='__main__':main()
