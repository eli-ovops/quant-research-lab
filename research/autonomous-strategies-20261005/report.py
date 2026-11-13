"""Read completed artifacts and describe bounded research without new selection."""
from pathlib import Path
import json,csv,gzip,collections,statistics
P=Path(__file__).resolve().parent

def main():
 s=json.loads((P/'summary.json').read_text());rows=s['rows'];proto=json.loads((P/'protocol.json').read_text())
 with (P/'all_results.csv').open('w',newline='') as f:
  w=csv.writer(f);w.writerow(['period','candidate','condition','total_return','max_drawdown','closed_trades','final_equity','fees','mean_exposure','audit'])
  for r in rows:
   m=r['metrics'];w.writerow([r['period'],r['candidate'],r['condition'],m['total_return'],m['max_drawdown'],m['closed_trades'],m['final_equity'],m['fees'],m['exposure'],r['audit']['status']])
 md=['# 自主策略研究：本轮结果','',f"本轮条件门槛通过：{', '.join(s['conditional_pass']) or '无'}。这不等于已找到可实盘盈利的策略。",'',
 '预登记20个候选 × 3种成本/延迟条件，共60个配置；8币共享2000 USDT纸面现货账本。最大回撤门槛50%。',
 '基础：每边手续费10bps、滑点5bps；压力：每边20bps、滑点10bps；延迟压力：另延迟1小时。费率均为假设，未核账户等级。',
 '所有收益均是独立场景，禁止相加；4H闭合信号，次小时开盘成交代理；10%入场现金储备、单币25%目标上限，市价漂移不连续调仓。',
 '', '## 选优与后续时段检验','',
 f"2025-01至2026-06验证段按固定规则选出：{', '.join(s['selected']) or '无'}。先保存selection.json，再读确认段；失败不更换候选。",
 '2023—2024为开发段；两段旧历史均被此前研究使用。2026-07至09小时数据本轮新采，但此前见过部分ETH日线/快照，不能称完全盲测，更不能称未来实盘。','']
 if s['selected']:
  md+=['|候选/控制|时段|成本条件|组合收益|最大回撤|闭合交易数|核验|','|---|---|---|---:|---:|---:|---|']
  for r in rows:
   if r['candidate'] in s['selected'] or (r['candidate']=='control_hold' and r['period']=='confirmation'):
    m=r['metrics'];md.append(f"|{r['candidate']}|{r['period']}|{r['condition']}|{m['total_return']:.2%}|{m['max_drawdown']:.2%}|{m['closed_trades']}|{r['audit']['status']}|")
 md+=['','## 验证段全部候选（压力条件）','','|候选|收益|回撤|交易数|三条件验证门槛|','|---|---:|---:|---:|---|']
 from evaluate import eligible
 for c in proto['candidates']:
  cr=[r for r in rows if r['candidate']==c['id'] and r['period']=='validation'];r=next(r for r in cr if r['condition']=='stress');m=r['metrics']
  md.append(f"|{c['id']}|{m['total_return']:.2%}|{m['max_drawdown']:.2%}|{m['closed_trades']}|{'通过' if eligible(cr,30) else '未通过'}|")
 md+=['','## 证据与仍未解决的问题','',
 f"- {len(rows)}个分期/场景结果均有逐小时权益、信号、成交与独立回放；核验PASS {sum(r['audit']['status']=='PASS' for r in rows)}个。开发/验证/确认复用同一配置，不是额外调参。",
 '- 24项合成测试通过。独立回放覆盖全部闭合信号、现金/库存、双边费用、取整、退出、dust和逐小时权益；发现过浮点tick bug，已修十进制定价后原配置重跑，v1证据保留。',
 '- 原始行情：8币2023-01至2026-09。交易区间缺失、零量、未闭合、OHLC非法均拒绝；预热期零量保留，依赖这些数据的信号拒绝。',
 '- 新增区间17,664根；请求返回19,200根（含重叠），64次K线及8次规格公共调用。未花满100万根或6小时上限，不为凑满预算增加候选。',
 '- 只选今天仍存在的8个币，存在幸存者偏差。当前交易规格被用作历史代理，有效性UNKNOWN。',
 '- 小时开盘/收盘及固定滑点不能证明排队、深度、成交和容量；小时收盘回撤不等于盘中最坏回撤，50%门槛不是实盘亏损保证。',
 '- 多候选选择会放大偶然性；未证明经多重检验调整后的显著收益，也未进行真正未来的预登记纸面验证。',
 '- 控制组90%等权持有，轮动因单币上限通常仅投入25%或50%；这是预登记的绝对收益比较，并非等风险比较，未超越控制组不等于证明没有风险调整后的优势。闭合交易数包含期末代理退出。',
 '- 合约资金费、标记价格路径、维持保证金与强平尚缺；不得把现货收益乘杠杆当合约结果。',
 '- 无密钥、私有账户、下单、付款、安装或旧监控重启。本轮未重启旧轮询。',
 '', '完整逐项结果见all_results.csv，分币交易归因见all_trade_diagnostics.csv（不是单币独立策略收益）；冻结见protocol.json/evaluation_freeze_v2.json；全部账本见results_v2/*.json.gz。']
 report_text='\n'.join(md)+'\n'
 report_text=report_text.replace('本轮条件门槛通过：无。这不等于已找到可实盘盈利的策略。','最终晋级：0个；保留一个有研究价值的候选，但尚未证实可实盘盈利。')
 if s['selected']==['reversion_2.5_18']:
  report_text=report_text.replace('## 验证段全部候选','## 候选的固定规则与关键解释\n\n`reversion_2.5_18`：4H布林带20期、2.5倍总体标准差；上一根收盘在下轨外、当前收盘重返带内，且此前ER20≥0.30并处于下行，才发出买入信号。次小时开盘代理买入，每个触发币目标占组合11.25%，持有18根4H（72小时）后代理退出，不重叠加仓。\n\n确认段压力场景平均资金暴露仅6.62%，收益7.09%、回撤2.05%；90%等权持有收益52.98%、回撤12.42%。所以绝对收益控制门槛失败，但两者承担风险不同，不能据此断言回归规则没有价值。不得临时换成有利指标将本轮翻判通过。\n\n确认段仅18笔退出，均非期末强制退出；尚不足以证明稳定性。下一次若获新的研究范围，应先预登记等风险控制与真正未见时段验证，保留本轮候选和参数，不按这些结果挑币或再调参。本轮不启动任何新轮询。\n\n'+'## 验证段全部候选')
 (P/'REPORT.md').write_text(report_text)
 # Descriptive trade contribution only, never used for candidate changes.
 with (P/'all_trade_diagnostics.csv').open('w',newline='') as f:
  w=csv.writer(f);w.writerow(['candidate','period','condition','coin','trades','pnl_quote_sum','median_trade_return','worst_trade_return','note'])
  for r in rows:
   path=P/'results_v2'/f"{r['period']}__{r['candidate']}__{r['condition']}.json.gz"
   with gzip.open(path,'rt') as g:x=json.load(g)
   by=collections.defaultdict(list)
   for t in x['trades']:by[t['coin']].append(t)
   for coin,ts in sorted(by.items()):w.writerow([r['candidate'],r['period'],r['condition'],coin,len(ts),sum(t['pnl'] for t in ts),statistics.median(t['return_fraction'] for t in ts),min(t['return_fraction'] for t in ts),'trade descriptive only; residual dust may remain'])
 print('REPORT.md/all_results.csv/all_trade_diagnostics.csv written')
if __name__=='__main__':main()
