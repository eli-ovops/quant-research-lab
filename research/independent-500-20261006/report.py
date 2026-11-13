"""Render complete bounded-research results, not investment advice or fills."""
import json,gzip,collections
from pathlib import Path
R=Path(__file__).resolve().parent

def pc(x):return 'UNKNOWN' if x is None else f'{100*x:.2f}%'
def main():
    x=json.loads((R/'results.json').read_text());q=json.loads((R/'data_manifest.json').read_text());receipt=json.loads((R/'collection_receipt.json').read_text())
    lines=['# 500 USDT 独立账户研究','',f'完成时间：{x["completed_utc"]}。120 个预注册配置，原计划16币，TON接口不存在而于收益计算前排除，实际15币。',f'正式采集行情返回 {receipt["candles"]:,} 根（另有预检10根；裁剪后使用264,960根）；原始证据逐文件哈希保留。独立账本审计 {x["audited_episodes"]:,} 次。','',
    '每个模拟账户独立500 USDT，24小时或7天内目标净值650。每组最多一笔交易、不补款；全部亏损与缺失保留。不同配置、杠杆、持有期的结果不能相加作为一个账户的收益。','',
    '## 结论边界','',
    '本批留下1条初步线索：现货20小时通道突破、最长7天。它在确认段平均为正，但5个达标账户全在同一周；验证段压力成本配置与随机对照各5/45达标，达标率优势消失。两条杠杆合约候选确认未通过。尚未找到可宣称稳定盈利的策略。',
    '这是历史时间切分研究；部分行情曾在其他研究中出现，不是盲测或前向实盘证据。每个配置在开发段和验证段运行；最多每产品/持有期选择一个，选择落盘后才将确认段价格用于信号、账本及收益计算。不得看确认结果后换候选。',
    '现货使用历史OHLC成交代理、假设手续费和滑点，规格采用当前值，历史有效性未知；没有实际成交验证。5倍/10倍使用真实SWAP交易价格和realizedRate资金费，但缺历史标记价格和维持保证金档位，强平检查为固定参数合成模型，true_target、true_liquidation及实际可行性始终UNKNOWN。模型清零不等于交易所真实强平。',
    '目标在15分钟收盘检测、下一根开盘代理退出；末日结束用最后收盘代理。不模拟持续重入或无限尝试。大量尝试中的个别赚钱不能证明可复用优势；统计包含亏损组，相关币种/配置不算独立样本。','',
    '## 确认段候选','', '|配置|有效/计划|达650|亏损/模型清零|均值收益|中位数|最差|随机对照达标率|达标率差（百分点）|研究候选|','|---|---:|---:|---:|---:|---:|---:|---:|---:|---|']
    for r in x['confirmation']:
        s=r['strategy'];b=r['control'];lines.append(f'|{r["config"]["id"]}|{s["evaluated"]}/{s["scheduled"]}|{s["targets"]}|{s["losses"]}/{s["zeros"]}|{pc(s["mean_return"])}|{pc(s["median_return"])}|{pc(s["worst_return"])}|{pc(b["target_rate"])}|{pc(r["paired_target_improvement"])}|{r["research_repeatability_candidate"]}|')
    if not x['confirmation']:lines+=['','没有配置达到预注册验证段筛选条件，因此未以其他配置替补，也未运行确认段收益筛选。']
    lines+=['','## 确认段的时间集中度','']
    for conf in x['confirmation']:
        buckets=collections.defaultdict(list)
        with gzip.open(R/'ledgers'/f'confirmation_{conf["config"]["id"]}.jsonl.gz','rt') as f:
            for line in f:
                row=json.loads(line);buckets[row['start']].append(row['metrics'])
        lines.append(f'- {conf["config"]["id"]}：{len(buckets)}个起始时间窗口，币种共用市场时段，不能把账户数当独立样本数。')
        if conf['config']['product']=='SPOT':
            for start,items in buckets.items():
                from datetime import datetime,timezone
                day=datetime.fromtimestamp(start/1000,timezone.utc).strftime('%Y-%m-%d')
                vals=[m['return'] for m in items if m['return'] is not None]
                lines.append(f'  - {day} UTC开始：平均{pc(sum(vals)/len(vals))}，达标{sum(m["target_hit"] is True for m in items)}/{len(items)}。')
            lines.append('本次现货5个达标账户全部集中在同一周；尚不能区分规则优势与共同上涨行情，不能称稳定盈利策略。')
    lines+=['','## 全部验证段配置','', '|配置|有效/计划|达650|亏损|清零|空仓|均值|中位数|最差|随机对照达标率|达标率差（百分点）|','|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for r in x['screening']:
        if r['period']!='validation':continue
        s=r['strategy'];lines.append(f'|{r["config"]["id"]}|{s["evaluated"]}/{s["scheduled"]}|{s["targets"]}|{s["losses"]}|{s["zeros"]}|{s["no_trade"]}|{pc(s["mean_return"])}|{pc(s["median_return"])}|{pc(s["worst_return"])}|{pc(r["control"]["target_rate"])}|{pc(r["paired_target_improvement"])}|')
    lines+=['','## 数据与可复核产物','',f'缺失时间点合计 {sum(a["missing"] for a in q["quality"])}；零量记录 {sum(a["zero_volume"] for a in q["quality"])}；未确认记录 {sum(a["unconfirmed"] for a in q["quality"])}。无效窗口在对应配置中保留为invalid，不视为零盈亏。',
    '- protocol.json：全部冻结条件与预算。', '- selection.json：确认收益计算前保存的选择及输入哈希。','- execution_seal.json、data_manifest.json：代码/规则/原始数据哈希。','- results.json：全配置分时段和分币种统计、对照。','- episode_metrics.jsonl.gz：逐账户结果；ledgers/*.jsonl.gz：完整事件与权益轨迹，含亏损和对照。','',
    '成本：现货基础单边10bps手续费+5bps滑点，压力20bps+10bps；合约基础5bps+5bps，压力10bps+10bps；费率未经账户核实。合约资金费为结算费率×所持基础币数量×结算时间的交易开盘价格代理，结束边界使用最后收盘代理。','',
    '研究候选只表示通过本批明确筛选，不表示保证30%、真实可成交盈利或稳定成功概率。没有自动开启下一批，没有实盘订单。']
    (R/'REPORT.md').write_text('\n'.join(lines)+'\n')
if __name__=='__main__':main()
