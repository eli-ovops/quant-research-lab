"""Bounded websocket verification of public screen leads; no monitor state writes."""
import argparse
import hashlib
import json
import threading
import time
from collections import Counter
from decimal import Decimal as D
from pathlib import Path
from detector import Book, validate_books
from evidence import Journal, audit_worker
from monitor import collect, Episodes, delayed_estimate
from screen_markets import AMOUNTS, SCENARIOS, order_rules, needs_recheck, summarize, dump


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--screen-dir',type=Path,required=True)
    p.add_argument('--seconds',type=int,default=180)
    p.add_argument('--proxy-port',type=int,default=7890)
    a=p.parse_args()
    if not 10<=a.seconds<=600:p.error('bounded duration must be 10..600 seconds')
    parent=a.screen_dir.resolve();out=parent/'stream-check';out.mkdir()
    catalog=json.loads((parent/'catalog.json').read_text())
    rest=[json.loads(line) for line in (parent/'depth-observations.jsonl').read_text().splitlines()]
    symbols=sorted({r['symbol'] for r in rest if needs_recheck(r)})
    selected=[m for m in catalog if m['symbol'] in symbols]
    rules={v:{m['symbol']:order_rules(m).get(v) for m in selected} for v in ['okx','gate']}
    config=dict(symbols=symbols,venues=['okx','gate'],amounts_usdt=AMOUNTS,fee_scenarios=SCENARIOS,
        buffer_bps='5',order_rules=rules,live_trading=False,simulation_enabled=False,
        duration_seconds=a.seconds,started_ms=time.time()*1000,total_capital_usdt='2000',
        scope='All positive raw REST spread leads or invalid HTTP responses, no top-N limit',
        selection_bias='REST is a sequential short survey; other coins may develop spreads later',
        qualification='UNKNOWN',fee_basis='ASSUMPTIONS_NOT_ACCOUNT_RATES_OR_UPPER_BOUNDS',
        delay_policy='One first-positive higher_gate observation per symbol/direction/amount rechecked after >=1s; not fills',
        source_sha256={})
    source=out/'source';source.mkdir();root=Path(__file__).resolve().parent
    for name in ['screen_stream.py','screen_markets.py','detector.py','monitor.py','evidence.py','replay.py']:
        raw=(root/name).read_bytes();(source/name).write_bytes(raw)
        config['source_sha256'][name]=hashlib.sha256(raw).hexdigest()
    dump(out/'config.json',config)
    lock,stop=threading.Lock(),threading.Event()
    journal=Journal(out,max_bytes=512*1024**2,min_free=20*1024**3)
    books={v:{s:Book() for s in symbols} for v in config['venues']}
    threads=[threading.Thread(target=audit_worker,args=(v,symbols,books[v],lock,stop,journal,a.proxy_port),daemon=True) for v in books]
    tracker=Episodes();pairs=[];pending=[];checked=set();delay_results=[];failure=None;sample=0
    deadline=time.monotonic()+a.seconds
    print(json.dumps({'phase':'stream_start','symbols':len(symbols),'seconds':a.seconds,'run_dir':str(out)}),flush=True)
    try:
        for t in threads:t.start()
        with (out/'observations.jsonl').open('x') as log,(out/'events.jsonl').open('x') as events:
            while time.monotonic()<deadline and not stop.is_set():
                with lock:
                    views={v:{s:b.view() for s,b in bs.items()} for v,bs in books.items()}
                    now,mono=time.time()*1000,time.monotonic()
                    results=collect(views,now,mono,config)
                    for r in results:
                        r.update(actual_all_in_profit='UNKNOWN',route_eligibility='BLOCKED_UNKNOWN')
                        if r['status']=='ESTIMATE_ONLY':
                            capital=D(r['buy_cost_usdt'])*2+D(r['gross_usdt'])+D(r['fees_usdt'])+200
                            r.update(capital_with_200_usdt_reserve=str(capital),within_2000_budget=capital<=2000,
                                headroom_after_target_0_5_usdt=str(D(r['net_usdt'])-D('.5')),
                                headroom_after_target_1_usdt=str(D(r['net_usdt'])-1))
                    journal.append('decision',observed_ms=now,mono=mono,results=results)
                    for event in tracker.update(results,now):
                        journal.append('event',**event);events.write(json.dumps(event)+'\n')
                    remaining=[]
                    for due,original in pending:
                        if mono<due:remaining.append((due,original));continue
                        b,s=[views[v][original['symbol']] for v in [original['buy'],original['sell']]]
                        delayed=delayed_estimate(original,b,s,now,mono)
                        event=dict(event='delay_check',observed_ms=now,mono=mono,original=original,
                            actual_delay_ms=(mono-original['observed_mono'])*1000,delayed=delayed)
                        journal.append('event',**event);events.write(json.dumps(event)+'\n');delay_results.append(event)
                    pending=remaining
                    for r in results:
                        key=(r['symbol'],r['buy'],r['sell'],r['amount_usdt'])
                        if r['scenario']=='higher_gate' and r['status']=='ESTIMATE_ONLY' and D(r['net_usdt'])>0 and r['within_2000_budget'] and key not in checked:
                            checked.add(key);original=dict(r,observed_mono=mono,observed_ms=now)
                            pending.append((mono+1,original))
                    journal.flush()
                for symbol in symbols:
                    row=dict(symbol=symbol,observed_ms=now,phase='websocket',
                        quality=validate_books(views['okx'][symbol],views['gate'][symbol],now,mono)['status'],
                        strict_quality=validate_books(views['okx'][symbol],views['gate'][symbol],now,mono,500,100)['status'],
                        results=[r for r in results if r['symbol']==symbol])
                    pairs.append(row);log.write(json.dumps(row)+'\n')
                log.flush();events.flush();sample+=1
                if sample%30==0:print(json.dumps({'phase':'stream_progress','samples':sample,'remaining_seconds':round(max(0,deadline-time.monotonic())),'quality':dict(Counter(p['quality'] for p in pairs[-len(symbols):]))}),flush=True)
                stop.wait(max(0,1-(time.monotonic()-mono)))
    except Exception as exc:
        failure=type(exc).__name__
        raise
    finally:
        stop.set()
        for t in threads:t.join(timeout=10)
        with lock:
            if any(t.is_alive() for t in threads):failure='worker_shutdown_timeout'
            journal.append('run_end',observed_ms=time.time()*1000,reason='failure' if failure or journal.failure else 'bounded_duration_complete',failure=failure or journal.failure)
            journal.close()
        summary=summarize(selected,pairs)
        dump(out/'summary.json',dict(completed_ms=time.time()*1000,failure=failure or journal.failure,samples=sample,
            pair_observations=len(pairs),quality_counts=dict(Counter(p['quality'] for p in pairs)),
            strict_quality_counts=dict(Counter(p['strict_quality'] for p in pairs)),
            independent_base100_anomalies=tracker.serial,pending_delay_checks=len(pending),
            delay_statuses=dict(Counter(e['delayed']['status'] for e in delay_results)),
            profitable_symbols_verified=[],markets=summary))
        print(json.dumps({'phase':'stream_complete','samples':sample,'failure':failure or journal.failure,'run_dir':str(out)}),flush=True)
    if failure or journal.failure:raise SystemExit(1)


if __name__=='__main__':main()
