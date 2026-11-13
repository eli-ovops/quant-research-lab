"""Fixed, finite public evidence study. No account access or execution path."""
import argparse
import fcntl
import hashlib
import json
import os
import signal
import threading
import time
from collections import Counter
from datetime import datetime, timezone
from decimal import Decimal as D
from pathlib import Path
from detector import Book, evaluate, sell, validate_books
from evidence import Journal, EvidenceFailure, atomic_json, audit_worker


def delayed_estimate(original, buy, sale, now_ms=None, mono=None):
    check = validate_books(buy, sale, now_ms, mono)
    if check['status'] != 'VALID':
        return check
    # Both venues must have supplied a subsequent frame on the same connections.
    if 'book_refs' in original:
        if [buy['connection_id'], sale['connection_id']] != original['connection_ids']:
            return {'status':'CONNECTION_CHANGED'}
        if any(b.get('ref') == old for b,old in zip([buy,sale], original['book_refs'])):
            return {'status':'NO_NEW_BOOK'}
    qty = D(original['quantity'])
    if not qty.is_finite() or qty <= 0:
        return {'status':'INVALID_INPUT'}
    cost, revenue = sell(buy['asks'], qty), sell(sale['bids'], qty)
    if cost is None or revenue is None:
        return {'status':'INSUFFICIENT_DEPTH'}
    buy_fee = cost*D(original['buy_fee_bps'])/10000
    fees = buy_fee+revenue*D(original['sell_fee_bps'])/10000
    net = revenue-cost-fees-cost*D(original.get('buffer_bps','5'))/10000
    cash = original.get('hypothetical_available_cash_usdt')
    affordable = 'UNKNOWN' if cash is None else ('YES' if cost+buy_fee <= D(cash) else 'NO')
    return dict(status='ESTIMATE_ONLY', quantity=str(qty), buy_cost_usdt=str(cost),
                net_usdt=str(net), affordability=affordable, book_refs=[buy.get('ref'),sale.get('ref')],
                limitation='Assumed quote fees; no inventory, order rounding, fills, or failed-leg validation')


class Episodes:
    """One anomaly per symbol/direction, primary 100 USDT, exit after 3 valid negatives."""
    def __init__(self):
        self.active = {}
        self.serial = 0

    def update(self, rows, now_ms):
        events = []
        for row in rows:
            if row['amount_usdt'] != '100' or row['scenario'] != 'base':
                continue
            key = '|'.join(row[k] for k in ['symbol','buy','sell'])
            state = self.active.get(key)
            valid = row['status'] == 'ESTIMATE_ONLY'
            positive = valid and D(row['net_usdt']) > 0
            event = None
            if positive:
                if state is None:
                    self.serial += 1
                    state = {'id':self.serial,'opened_ms':now_ms,'unknown':False,'negative_count':0}
                    self.active[key] = state
                    event = 'anomaly_open'
                elif state['unknown']:
                    event = 'anomaly_resumed'
                state['unknown'],state['negative_count'] = False,0
            elif state is not None and not valid:
                if not state['unknown']:
                    event = 'data_unavailable'
                state['unknown'],state['negative_count'] = True,0
            elif state is not None:
                state['unknown'] = False
                state['negative_count'] += 1
                if state['negative_count'] >= 3:
                    event = 'ended'
                    del self.active[key]
            if event:
                capacity = [r for r in rows if r['scenario']=='base' and all(r[k]==row[k] for k in ['symbol','buy','sell'])]
                events.append(dict(row, event=event, episode_id=state['id'], opened_ms=state['opened_ms'],
                                   observed_ms=now_ms, capacity_scenarios=capacity))
        return events


def collect(views, now_ms, mono, config):
    rows = []
    for symbol in config['symbols']:
        for buy,sale in [('okx','gate'),('gate','okx')]:
            b,s = views[buy][symbol],views[sale][symbol]
            for name,fees in config['fee_scenarios'].items():
                for amount in config['amounts_usdt']:
                    r = evaluate(b,s,D(amount),D(fees[buy]),D(fees[sale]),D(config['buffer_bps']),now_ms,mono)
                    strict = validate_books(b,s,now_ms,mono,500,100)
                    r.update(symbol=symbol,buy=buy,sell=sale,amount_usdt=amount,scenario=name,
                             buy_fee_bps=fees[buy],sell_fee_bps=fees[sale],buffer_bps=config['buffer_bps'],
                             strict_quality=strict['status'], book_refs=[b['ref'],s['ref']],
                             connection_ids=[b['connection_id'],s['connection_id']],
                             hypothetical_available_cash_usdt=str(D(amount)*(1+D(fees[buy])/10000)),
                             classification='ANOMALY_ONLY', executable=False)
                    rows.append(r)
    return rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--proxy-port',type=int,default=7890)
    parser.add_argument('--seconds',type=int,default=86400)
    parser.add_argument('--state-root',type=Path,default=Path(__file__).resolve().parent/'monitor')
    args = parser.parse_args()
    if not 1 <= args.seconds <= 86400:
        parser.error('duration must be 1..86400 seconds; no indefinite or automatic renewal')
    root = args.state_root.resolve()
    root.mkdir(parents=True,exist_ok=True)
    with (root/'process.lock').open('a') as singleton:
        try:
            fcntl.flock(singleton,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:
            raise SystemExit('monitor already running')
        started, start_mono = time.time(),time.monotonic()
        run = root/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
        run.mkdir()
        config = dict(mode='audit_v2', symbols=['LSKUSDT','GUSDT'], venues=['okx','gate'],
                      duration_seconds=args.seconds,deadline_ms=(started+args.seconds)*1000,
                      amounts_usdt=['100','500','1000'],primary_amount_usdt='100',
                      fee_scenarios={'base':{'okx':'10','gate':'10'},'higher_gate':{'okx':'10','gate':'20'}},
                      fee_basis='ASSUMPTIONS_NOT_VERIFIED_ACCOUNT_FEES_OR_UPPER_BOUND',
                      buffer_bps='5',max_age_ms=2000,max_skew_ms=500,strict_age_ms=500,strict_skew_ms=100,
                      live_trading=False,simulation_enabled=False,universe_rotation=False,raw_depth_retained=True,
                      max_evidence_bytes=4*1024**3,min_disk_free_bytes=20*1024**3,
                      excludes=['fee currency effects','precision and minimum order constraints','inventory and NAV',
                                'rebalancing','failed-leg loss','actual simultaneous execution'])
        source_dir = run/'source'
        source_dir.mkdir()
        hashes = {}
        for name in ['monitor.py','detector.py','evidence.py','replay.py','qualification.py',
                     'test_detector.py','test_monitor.py','test_evidence.py','test_universe.py','universe.py']:
            src = Path(__file__).resolve().parent/name
            raw = src.read_bytes()
            (source_dir/name).write_bytes(raw)
            hashes[name] = hashlib.sha256(raw).hexdigest()
        config['source_sha256'] = hashes
        atomic_json(run/'config.json',config)
        qualification = Path(__file__).resolve().parent/'monitor'/'qualification.json'
        if qualification.exists():
            raw = qualification.read_bytes()
            (run/'qualification.json').write_bytes(raw)
            config['qualification_sha256'] = hashlib.sha256(raw).hexdigest()
            atomic_json(run/'config.json',config)
        stop,lock = threading.Event(),threading.Lock()
        for sig in [signal.SIGTERM,signal.SIGINT]:
            signal.signal(sig,lambda *_:stop.set())
        journal = Journal(run, config['max_evidence_bytes'],config['min_disk_free_bytes'])
        books = {v:{s:Book() for s in config['symbols']} for v in config['venues']}
        threads = [threading.Thread(target=audit_worker,args=(v,config['symbols'],books[v],lock,stop,journal,args.proxy_port),daemon=True) for v in books]
        counts,coverage = Counter(),Counter()
        episodes = Episodes()
        results,pending = [],[]
        samples = 0
        failure = None

        def status(state,reason=None):
            atomic_json(root/'status.json',dict(mode='audit_v2',state=state,reason=reason,pid=os.getpid(),
                updated_ms=time.time()*1000,started_ms=started*1000,run_dir=str(run),config=config,
                qualification='UNKNOWN_BLOCKS_SIMULATION_AND_EXECUTION',counts=dict(counts),coverage=dict(coverage),
                samples=samples,active_anomalies=episodes.active,anomaly_count=episodes.serial,
                latest=results,failure=failure or journal.failure,journal_seq=journal.seq,
                closed_shards=len(journal.files),journal_bytes=journal.total+(journal.raw.tell() if journal.raw else 0)))
        status('starting')
        for thread in threads:
            thread.start()
        try:
            with (run/'opportunities.jsonl').open('x',buffering=1) as eventlog:
                while not stop.is_set() and time.monotonic()-start_mono < args.seconds:
                    with lock:
                        now_ms,mono = time.time()*1000,time.monotonic()
                        views = {v:{s:b.view() for s,b in bs.items()} for v,bs in books.items()}
                        results = collect(views,now_ms,mono,config)
                        journal.append('decision',observed_ms=now_ms,mono=mono,results=results)
                        events = episodes.update(results,now_ms)
                        due, pending = [p for p in pending if p[0]<=mono],[p for p in pending if p[0]>mono]
                        for _,original in due:
                            b,s = views[original['buy']][original['symbol']],views[original['sell']][original['symbol']]
                            events.append(dict(event='delay_check',episode_id=original['episode_id'],
                                symbol=original['symbol'],buy=original['buy'],sell=original['sell'],amount_usdt='100',
                                observed_ms=now_ms,actual_delay_ms=now_ms-original['observed_ms'],original=original,
                                mono=mono,delayed=delayed_estimate(original,b,s,now_ms,mono)))
                        for event in events:
                            journal.append('event',**event)
                            eventlog.write(json.dumps(event)+'\n')
                            if event['event']=='anomaly_open':
                                pending.append((mono+1,event))
                        samples += 1
                        for r in results:
                            counts[r['status']] += 1
                            if r['scenario']=='base' and r['amount_usdt']=='100':
                                key = r['symbol']+'|'+r['buy']+'>'+r['sell']
                                coverage[key+'|'+r['status']] += 1
                                coverage[key+'|strict_'+r['strict_quality']] += 1
                        for v in books:
                            for sym,b in views[v].items():
                                q = validate_books(b,b,now_ms,mono)
                                coverage[v+'|'+sym+'|'+q['status']] += 1
                        journal.flush()
                        status('running')
                    stop.wait(1)
        except Exception as exc:
            failure = type(exc).__name__
        finally:
            stop.set()
            for thread in threads:
                thread.join(timeout=12)
            reason = 'duration_complete' if time.monotonic()-start_mono>=args.seconds else 'interrupted'
            if any(t.is_alive() for t in threads):
                failure = 'worker_shutdown_timeout'
            # Workers must be gone before finalizing evidence.
            if not any(t.is_alive() for t in threads):
                try:
                    with lock:
                        journal.append('run_end',observed_ms=time.time()*1000,reason=reason,
                                       open_episodes=episodes.active,pending_delays=len(pending))
                        journal.close()
                except Exception as exc:
                    failure = failure or type(exc).__name__
            status('failed' if failure or journal.failure else 'stopped',reason)
            atomic_json(run/'final_status.json',json.loads((root/'status.json').read_text()))
        print(run,flush=True)
        if failure or journal.failure:
            raise SystemExit(1)


if __name__=='__main__':
    main()
