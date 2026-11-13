"""Continuous public-data observation. No orders or credential access."""
import argparse
import fcntl
import json
import os
import signal
import threading
import time
from collections import Counter
from datetime import datetime, timezone
from decimal import Decimal as D
from pathlib import Path
from detector import Book, evaluate, worker, sell
from universe import save_scan


def delayed_estimate(original, buy, sale):
    """Reprice the ORIGINAL base quantity, not a new budget-sized trade."""
    check=evaluate(buy,sale,D(original['amount_usdt']),D(0),D(0),D(0))
    if check['status']!='ESTIMATE_ONLY':return {'status':check['status']}
    qty=D(original['quantity'])
    cost=sell(buy['asks'],qty);revenue=sell(sale['bids'],qty)
    if cost is None or revenue is None:return {'status':'INSUFFICIENT_DEPTH'}
    fees=cost*D(original['buy_fee_bps'])/10000+revenue*D(original['sell_fee_bps'])/10000
    return {'status':'ESTIMATE_ONLY','quantity':str(qty),'buy_cost_usdt':str(cost),
            'net_usdt':str(revenue-cost-fees-cost*D(5)/10000),
            'limitation':'Both legs repriced together; not a fill or failed-leg simulation'}


def opportunity_events(results, active, last_recorded, now):
    """Record entry, exit, and at most one continuing observation per minute."""
    events = []
    for r in results:
        key = '|'.join(r[k] for k in ['symbol', 'buy', 'sell', 'amount_usdt'])
        positive = r['status'] == 'ESTIMATE_ONLY' and D(r['net_usdt']) > 0
        if positive:
            if key not in active or now-last_recorded.get(key, 0) >= 60:
                events.append(dict(r, event='candidate' if key not in active else 'continuing', observed_ms=now*1000))
                last_recorded[key] = now
            active.add(key)
        elif key in active:
            events.append(dict(r, event='ended' if r['status']=='ESTIMATE_ONLY' else 'data_unavailable', observed_ms=now*1000))
            active.remove(key)
    return events


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--proxy-port', type=int, default=7890)
    parser.add_argument('--seconds', type=int, default=0, help='0 means until stopped')
    parser.add_argument('--universe', action='store_true', help='rank and rotate up to 50 public research markets')
    args = parser.parse_args()
    root = Path(__file__).resolve().parent/'monitor'
    root.mkdir(exist_ok=True)
    with (root/'process.lock').open('a') as singleton:
        try:
            fcntl.flock(singleton, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise SystemExit('monitor already running')
        started = time.time()
        output = root/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
        output.mkdir()
        selection = json.loads((root/'universe.json').read_text()) if args.universe else None
        symbols, venues = ([m['symbol'] for m in selection['selected']] if selection else ['ZECUSDT','UNIUSDT']), ['okx','gate']
        metadata = {m['symbol']:m for m in selection['selected']} if selection else {}
        config = dict(symbols=symbols, venues=venues, amounts_usdt=['100','500','1000'],
                      fee_bps_each='10', extra_buffer_bps='5', live_trading=False,
                      fee_source='2026-09-23 OKX account API and Gate account screenshot; actual fill fees unverified',
                      excludes=['inventory rebalancing','failed leg losses','order precision and minimum validation'],
                      sampling_seconds=1, raw_depth_retained=False)
        if selection:
            config.update(universe_mode=True, fee_source='New symbols: OKX assumed 10bps; Gate max(displayed account 10bps, public pair fee). Per-symbol account fees unverified.',
                          symbol_metadata=metadata,universe_updated_ms=selection['updated_ms'])
        (output/'config.json').write_text(json.dumps(config,indent=2))
        stop, lock = threading.Event(), threading.Lock()
        for sig in [signal.SIGTERM, signal.SIGINT]:
            signal.signal(sig, lambda *_: stop.set())
        stream_stop = threading.Event()
        def connect(symbols):
            books = {v:{s:Book() for s in symbols} for v in venues}
            threads=[]
            for v in venues:
                for offset in range(0,len(symbols),10):
                    chunk=symbols[offset:offset+10]
                    t=threading.Thread(target=worker,args=(v,chunk,{s:books[v][s] for s in chunk},lock,stream_stop,output,args.proxy_port,False,'-'+str(offset)),daemon=True)
                    t.start();threads.append(t)
            return books,threads
        books,threads=connect(symbols)
        refresh_state={'last_error':None}
        def refresh():
            while not stop.wait(900):
                try:
                    save_scan(root,args.proxy_port);refresh_state['last_error']=None
                except Exception as exc:
                    refresh_state['last_error']={'type':type(exc).__name__,'at_ms':time.time()*1000}
        if selection: threading.Thread(target=refresh,daemon=True).start()
        counts, best = Counter(), {}
        active, last_recorded = set(), {}
        candidates = 0
        pending=[]

        def save_status(state, results):
            status = dict(state=state, pid=os.getpid(), started_ms=started*1000, updated_ms=time.time()*1000,
                          run_dir=str(output), config=config, counts=dict(counts), candidate_events=candidates,
                          active_candidates=sorted(active), latest=results, best=list(best.values()))
            status['universe_refresh']=refresh_state
            tmp = root/'status.tmp'
            tmp.write_text(json.dumps(status,indent=2))
            tmp.replace(root/'status.json')

        results = []
        try:
            with (output/'opportunities.jsonl').open('a',buffering=1) as events:
                while not stop.is_set() and (args.seconds == 0 or time.time()-started < args.seconds):
                    if selection:
                        updated=json.loads((root/'universe.json').read_text())
                        if updated['updated_ms']!=selection['updated_ms']:
                            selection=updated
                            next_symbols=[m['symbol'] for m in selection['selected']]
                            if next_symbols!=symbols:
                                stream_stop.set()
                                for t in threads:t.join(timeout=10)
                                if any(t.is_alive() for t in threads):raise RuntimeError('old streams did not stop')
                                for key in sorted(active):
                                    events.write(json.dumps({'event':'universe_changed','key':key,'observed_ms':time.time()*1000})+'\n')
                                active.clear();last_recorded.clear()
                                symbols=next_symbols;stream_stop=threading.Event();books,threads=connect(symbols)
                            metadata={m['symbol']:m for m in selection['selected']}
                            config.update(symbols=symbols,symbol_metadata=metadata,universe_updated_ms=selection['updated_ms'])
                    with lock:
                        views={v:{s:b.view() for s,b in bs.items()} for v,bs in books.items()}
                    next_pending=[]
                    for due,original in pending:
                        if time.monotonic()<due:
                            next_pending.append((due,original));continue
                        if original['symbol'] not in symbols:
                            delayed={'status':'UNIVERSE_CHANGED'}
                        else:
                            delayed=delayed_estimate(original,views[original['buy']][original['symbol']],views[original['sell']][original['symbol']])
                        events.write(json.dumps(dict(event='delay_check',signal_ms=original['observed_ms'],observed_ms=time.time()*1000,
                            actual_delay_ms=time.time()*1000-original['observed_ms'],symbol=original['symbol'],buy=original['buy'],sell=original['sell'],
                            amount_usdt=original['amount_usdt'],original_net_usdt=original['net_usdt'],delayed=delayed))+'\n')
                    pending=next_pending
                    results=[]
                    for symbol in symbols:
                        for buy,sale in [venues, venues[::-1]]:
                            for amount in config['amounts_usdt']:
                                fees={'okx':D(metadata.get(symbol,{}).get('okx_fee_bps','10')),'gate':D(metadata.get(symbol,{}).get('gate_fee_bps','10'))}
                                r=evaluate(views[buy][symbol],views[sale][symbol],D(amount),fees[buy],fees[sale],D(5))
                                r.update(symbol=symbol,buy=buy,sell=sale,amount_usdt=amount,observed_ms=time.time()*1000)
                                r.update(buy_fee_bps=str(fees[buy]),sell_fee_bps=str(fees[sale]),research_only=True)
                                results.append(r)
                                counts[r['status']]+=1
                                key=(symbol,buy,sale,amount)
                                if r['status']=='ESTIMATE_ONLY' and (key not in best or D(r['net_usdt'])>D(best[key]['net_usdt'])):
                                    best[key]=r
                    for event in opportunity_events(results, active, last_recorded, time.time()):
                        if event['event']=='candidate':
                            candidates+=1
                            pending.append((time.monotonic()+1,event.copy()))
                        events.write(json.dumps(event)+'\n')
                    save_status('running',results)
                    stop.wait(1)
        finally:
            stop.set()
            stream_stop.set()
            for t in threads: t.join(timeout=10)
            save_status('stopped',results)


if __name__ == '__main__':
    main()
