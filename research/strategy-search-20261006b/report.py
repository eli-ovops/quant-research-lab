import json,csv
from pathlib import Path
R=Path(__file__).resolve().parent

def pct(x):return 'UNKNOWN' if x is None else f'{x*100:.2f}%'
def main():
 x=json.loads((R/'results.json').read_text());p=json.loads((R/'protocol.json').read_text());rec=json.loads((R/'collection_receipt.json').read_text())
 columns=['id','family','product','leverage','horizon','cost','evaluated','invalid','trades','targets','losses','zeros','no_trade','mean','median','worst','control_mean','paired_mean','positive_folds']
 with (R/'all_configurations.csv').open('w') as f:
  writer=csv.writer(f);writer.writerow(columns)
  for r in x['screen']:
   c=r['config'];s=r['strategy'];writer.writerow([c['id'],c['rule']['family'],c['product'],c['leverage'],c['horizon_hours'],c['cost'],s['evaluated'],s['invalid'],s['trades'],s['targets'],s['losses'],s['zeros'],s['no_trade'],s['mean_return'],s['median_return'],s['worst_return'],r['control']['mean_return'],r['paired_mean'],sum(v['mean_return']>0 for v in r['folds'])])
 passed=[r for r in x['holdout'] if r['paper_eligible']]
 lines=['# 扩展策略研究：500美元独立账户','',f'完成：{x["completed_utc"]}。360个配置；15个已研究币种筛选，8个新增币种采集、其中5个通过双产品数据预检。新增返回{rec["candles"]:,}根行情；逐账户独立审计{x["audited_episodes"]:,}次。',
 f'当前结果：{len(passed)}个配置通过本批纸面试验候选门槛；实盘盈利与可执行性均未验证。','',
 '六类方法：趋势、放量突破、震荡回归、K线形态、15分钟短线反转、有上限三档马丁。每类5个固定组合，1倍现货/3倍和10倍条件合约，24小时/7天，基础/压力成本，共360配置。所有亏损组与模型清零保留。各配置是替代实验，不可把不同配置收益相加。','',
 '每个币种每个窗口独立500美元，同一窗口内多笔交易连续扣款，不重置本金；一般策略最多使用95%余额作买入/保证金，马丁依次20%、40%、80%，三连亏终止。达到650或跌至250在收盘检测后下一开盘退出，跳空可以超过预设损失。1日最多8次/7日最多40次入场。',
 '', '## 新币种检验','', '|配置|有效账户|交易|达650|亏损/清零|平均收益|最差|对照平均|差值|纸面候选|','|---|---:|---:|---:|---:|---:|---:|---:|---:|---|']
 for r in x['holdout']:
  s=r['strategy'];lines.append(f'|{r["config"]["id"]}|{s["evaluated"]}|{s["trades"]}|{s["targets"]}|{s["losses"]}/{s["zeros"]}|{pct(s["mean_return"])}|{pct(s["worst_return"])}|{pct(r["control"]["mean_return"])}|{pct(r["paired_mean"])}|{r["paper_eligible"]}|')
 if not x['holdout']:lines+=['','没有配置通过预注册筛选门槛，没有为了取得新币种赢家而放宽条件或继续翻看新币种收益。']
 for r in x['holdout']:
  u=r['uncertainty'];lines+=['',f'**{r["config"]["id"]}**：{u["date_clusters"]}个日期簇；平均收益90%区间[{pct(u["mean_ci90"][0])}, {pct(u["mean_ci90"][1])}]，相对对照差90%区间[{pct(u["paired_ci90"][0])}, {pct(u["paired_ci90"][1])}]。这些不是多个候选同时覆盖的置信区间，也不是翻倍概率。',f'三个时段平均：{", ".join(pct(v["mean_return"]) for v in r["folds"])}。']
 diag=json.loads((R/'diagnostic_summary.json').read_text())
 lines+=['','## 各方法完整筛选概况','','下表统计平均收益为正的配置数量，每格分母30；不是独立成功概率。基础/压力为同配置的两套成本情景。','', '|方法|基础成本正均值|压力成本正均值|','|---|---:|---:|']
 labels={'trend':'趋势','breakout':'放量突破','range':'震荡回归','pattern':'K线形态','scalp':'15分钟短线','martingale':'有上限马丁'}
 for family,d in diag.items():lines.append(f'|{labels[family]}|{d["positive_base"]}/30|{d["positive_stress"]}/30|')
 lines+=['','事后诊断：压力成本中平均最高的趋势配置七天均值约+0.12%、中位数0、最差−5.03%；三个时段均值约−0.33%、−0.03%、+0.72%，没有账户达到650。此项是筛选内诊断，不是入选候选，更不是可以下单的建议。','', '本批研究完成，但寻找可尝试策略的目标尚未达成。以上只否定本批具体规则与成本模型，不能推出其他方法都不可盈利。']
 lines+=['','## 判断边界','',
 ('筛选数据全部曾用于旧研究，不能视作全新样本外。本轮无配置通过筛选，新增五币未进入信号/账本/收益计算。' if not x['selected'] else '筛选数据全部曾用于旧研究，不能视作全新样本外。本轮新增五币在选优落盘后才进入信号/账本/收益计算。')+'新币与旧币共用市场时段，不代表独立市场环境；历史项目是否曾接触这些价格无法完全排除。当前仍上市币种带来幸存者偏差。',
 '候选门槛：压力成本、各组数据有效、至少30次平仓和3次达到650、整体平均为正、三个时段至少两个为正、平均优于固定时点随机方向对照；新币种还须日期簇bootstrap两项90%区间下界均大于0。通过也只是下一步纸面试验资格，不是稳定赚钱或实盘放行。',
 '对照与策略有相同风险退出和资金上限，但入场机会频率不同，不是严格相同市场暴露；账户数与交易数不是独立样本数。多重尝试和不同配置间高度相关仍需谨慎。',
 '现货使用历史OHLC代理成交，未验证实际滑点/撮合容量；合约虽然使用真实SWAP交易价格、合约数量与结算资金费，缺历史标记价和保证金档位，固定维护保证金压力模型不能证明真实强平顺序。所有合约真实达标、真实强平、真实盈利仍UNKNOWN。',
 '15分钟级短线规则不能证明秒级剥头皮可行；无盘口/逐笔数据时不伪称验证做市成交。有上限马丁不能用无限补仓把亏损消掉，相关账户终止与清零必须计入。',
 'ETC、ATOM、ICP在必要时段存在零成交K线，于策略收益计算前按双产品数据可用性排除，无替代币，原始数据保留。有效检验币为OP、ARB、UNI、AAVE、FIL。',
 '', '## 文件入口','',
 '- all_configurations.csv：全部360个筛选配置，包含亏损、清零、空仓和成本。','- results.json：全部配置分币种、分时段以及后续检验。','- ledgers/：逐账户完整资金/持仓事件与权益，包括全部失败及对照。','- protocol.json、selection.json、execution_seal.json、data_manifest.json：规则、选优、代码和原始数据哈希。','- REFERENCES.md：GitHub/Skill来源与采用范围；第三方代码未安装或运行。','',
 '无实盘、无密钥读取、无自动续批或旧监控恢复。仍保留原研究文件；本轮新增文件均作为审计与复现证据保留。']
 (R/'REPORT.md').write_text('\n'.join(lines)+'\n')
if __name__=='__main__':main()
