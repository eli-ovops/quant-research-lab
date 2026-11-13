"""Offline strategy research orchestration. No network, credentials, or orders."""
import argparse, datetime, hashlib, json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEGACY = ROOT / 'research/feasibility-20260926/trend/variants_20260926/admissible_periods_20260926'
sys.path.insert(0, str(LEGACY))
import engine, independent, independent_metrics as im, source_gate

POLICY = {
    'version': 1, 'instrument_type': 'SPOT', 'assets': ['BTC', 'ETH'],
    'entry_hours': 24, 'exit_hours': 4, 'periods': ['middle', 'latest'],
    'conditions': ['baseline', 'fee2', 'slip20', 'delay1'],
    'modes': ['trend', 'hold'], 'initial_usdt': 2000, 'reserve_usdt': 400,
    'per_asset_budget_cap_usdt': 800, 'classification': 'EXPLORATORY_REUSED_HISTORY',
    'parameter_optimization': False, 'live_execution_allowed': False,
    'promotion': 'BLOCKED_NO_UNSEEN_VALIDATION',
}

def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def verify(a, b, case):
    fills = [(f['t'], f['coin'], f['side'], f['qty'], f['price'], f['base_fee'], f['quote_fee'], f['cash_after']) for f in a['fills']]
    im.assert_close(fills, b['fills'], 'fills')
    if [(s['signal'],s['due'],s['coin'],s['side']) for s in a['signals']] != b['signals']:
        raise ValueError('signal_replay_mismatch')
    if [(r['t'],r['coin'],r['side'],r['phase']) for r in a['rejections']] != b['rejections']:
        raise ValueError('rejection_replay_mismatch')
    if [(x['due'],x['coin'],x['side'],x['signal']) for x in a['cancellations'] if x['reason']=='period_end_pending_cancelled'] != b['pending']:
        raise ValueError('pending_replay_mismatch')
    if len(a['curve']) != len(b['curve']):
        raise ValueError('curve_length_mismatch')
    for x,y in zip(a['curve'],b['curve']):
        im.assert_close({k:x[k] for k in y}, y, 'curve')
    im.assert_close(a['metrics'], im.compute(case,b), 'metrics')

def futures_gate():
    # No boolean attestations or spot substitutions can unlock a missing adapter.
    return {'status': 'BLOCKED', 'execution_allowed': False, 'validated_equity': None,
        'reasons': ['SWAP adapter and independent replay not implemented',
        'Point-in-time contract specs, funding settlements and mark-price path not admitted',
        'Margin tiers, liquidation, latency and fill model not validated'],
        'legacy_spot_results_are_not_futures_results': True}

def run(out):
    out = Path(out).resolve()
    out.mkdir(parents=True, exist_ok=False)  # preserve every previous experiment
    started = datetime.datetime.now(datetime.timezone.utc).isoformat()
    files = [Path(__file__), Path(__file__).with_name('test_system.py')] + [LEGACY / n for n in ['engine.py','independent.py','independent_metrics.py','source_gate.py']]
    freeze = {'created_utc': started, 'policy': POLICY, 'code_sha256': {str(p):sha(p) for p in files}}
    engine.dump(out/'freeze.json', freeze)
    engine.dump(out/'futures_gate.json', futures_gate())
    try:
        raw, proof = source_gate.load()
        specs = {c: json.loads((LEGACY.parent.parent/'raw'/(c+'_spec.txt')).read_text())['data'][0] for c in engine.COINS}
        engine.dump(out/'spec_snapshot.json', specs)
        results=[]; gates={}
        for period in POLICY['periods']:
            selected,start,end,checks = source_gate.for_period(raw,period)
            gates[period]={'start_ms':start,'end_ms':end,'checks':checks}
            for condition in POLICY['conditions']:
                for mode in POLICY['modes']:
                    ident=period+'_'+mode+'_'+condition
                    case=dict(raw=selected,spec=specs,start=start,end=end,entry=24,exit=4,condition=condition,mode=mode,synthetic=False)
                    a=engine.run(**case); b=independent.replay(case); verify(a,b,case)
                    engine.export(out/'scenarios'/ident,a)
                    engine.dump(out/'scenarios'/ident/'independent_events.json',{k:v for k,v in b.items() if k!='curve'})
                    metrics={k:v for k,v in a['metrics'].items() if k not in ['daily_returns','daily_utc_keys','cluster_intervals']}
                    results.append(dict(id=ident,period=period,mode=mode,condition=condition,accounting_replay='PASS',metrics=metrics))
                    engine.dump(out/'progress.json',{'completed':len(results),'planned':16,'last':ident})
                    print('verified',ident,flush=True)
        for row in results:
            hold=next(x for x in results if x['period']==row['period'] and x['condition']==row['condition'] and x['mode']=='hold')
            row['excess_vs_hold_usdt']=row['metrics']['net_pnl']-hold['metrics']['net_pnl']
        for p,h in freeze['code_sha256'].items():
            if sha(p)!=h: raise ValueError('code_changed_during_run:'+p)
        engine.dump(out/'input_gate.json',{'source':proof,'periods':gates,'early':'BLOCKED_ORIGINAL_DATA_DEFECTS','specs':'Historical validity not proven; recorded spec snapshot only'})
        engine.dump(out/'results.json',{'status':'COMPLETE_EXPLORATORY_ONLY','policy':POLICY,'scenarios':results,'cash_control_pnl_usdt':0})
        lines=['# 策略系统离线复测','', '结论：账本和独立回放可以核对；尚无独立未见样本，不能据此批准实盘或认定盈利能力。', '',
          'BTC/ETH 现货、1小时数据。24小时突破买入、4小时跌破退出；收盘决策，下一小时开盘代理成交。2000 USDT 组合，保留400，每币投入上限800。', '',
          '基础：每边10bps费用+5bps滑点；fee2：每边20bps费用；slip20：每边20bps滑点；delay1：额外延迟1小时。各场景独立，不相加。', '',
          '|时期|策略|成本情景|净损益 U|最大回撤|闭合交易|胜率|相对持有 U|', '|---|---|---|---:|---:|---:|---:|---:|']
        for r in results:
            m=r['metrics']; win='N/A' if m['win_rate'] is None else format(m['win_rate']*100,'.2f')+'%'
            lines.append(f"|{r['period']}|{r['mode']}|{r['condition']}|{m['net_pnl']:.2f}|{m['max_drawdown']*100:.2f}%|{m['closed_trades']}|{win}|{r['excess_vs_hold_usdt']:.2f}|")
        lines += ['', '现金对照：收益0，未计利息。16个场景全部报告，无择优或参数优化。', '',
          '证据边界：所有历史已经看过，只能称探索性复测；middle/latest 不是重新获得的独立留出集。原始早期缺陷区间未替换或缩短。',
          '逐小时信号、成交、拒绝、待处理订单、现金、库存、权益及指标与第二实现核对通过。该通过仅代表条件会计一致，不代表真实成交。',
          '历史合约/交易规格的有效时间未证明；开盘价与固定滑点是代理，未重建盘口、排队和订单失败。期末平仓也是代理。',
          '合约通道明确 BLOCKED：资金费、标记价格、保证金阶梯、强平路径与合约独立回放尚未接齐。不得将本结果乘以杠杆。',
          'TradingAgents 全流程未连接；本轮是确定性规则对照，未冒充 AI 多代理策略。HyperFrames 不参与收益计算。',
          '进入下一阶段需预先冻结候选和验证期，再取得未见数据；若继续调规则，原验证期必须转为探索数据。旧轮询保持暂停，系统不具备下单入口。']
        (out/'REPORT.md').write_text('\n'.join(lines)+'\n')
        engine.dump(out/'receipt.json',{'status':'COMPLETE_EXPLORATORY_ONLY','scenarios_verified':len(results),'freeze_sha256':sha(out/'freeze.json'),'results_sha256':sha(out/'results.json'),'finished_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()})
    except Exception as e:
        engine.dump(out/'failure.json',{'status':'FAILED','type':type(e).__name__,'reason':str(e)})
        raise

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__); sub=p.add_subparsers(dest='command',required=True)
    r=sub.add_parser('retest');r.add_argument('--out',required=True)
    sub.add_parser('futures-gate'); a=p.parse_args()
    if a.command=='retest':run(a.out)
    else:print(json.dumps(futures_gate(),ensure_ascii=False,indent=2))
