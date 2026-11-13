"""Fixed, public-only 24h multi-market study, isolated from the existing observer."""
import argparse
import fcntl
import gzip
import hashlib
import json
import os
import signal
import subprocess
import sys
import threading
import time
from collections import Counter
from datetime import datetime,timezone
from decimal import Decimal as D
from pathlib import Path
from detector import Book,validate_books
from evidence import Journal,audit_worker,atomic_json
from monitor import collect,Episodes,delayed_estimate
from screen_markets import order_rules,network_status

ROOT=Path(__file__).resolve().parent
SOURCE_NAMES=['leadlag_engine.py','leadlag_watch.py','wide_replay.py','test_wide_watch.py','screen_markets.py','detector.py','evidence.py','monitor.py','replay.py']


def deadline_overdue(now_ms,deadline_ms):
    return now_ms>deadline_ms+40000


def build_universe(screen):
    catalog=json.loads((screen/'catalog.json').read_text())
    markets=[dict(m) for m in catalog if m['depth_screen_enabled']]
    meta={}
    with gzip.open(screen/'public-responses.jsonl.gz','rt') as f:
        for _ in range(3):
            r=json.loads(next(f));meta[r['url']]=r['response']
    for m in markets:
        if m['symbol']=='EDGEUSDT':
            m['gate_pair']=next(x for x in meta['https://api.gateio.ws/api/v4/spot/currency_pairs'] if x['id']=='EDGEX_USDT')
            m['gate_currency']=next(x for x in meta['https://api.gateio.ws/api/v4/spot/currencies'] if x['currency']=='EDGEX')
            assert any(x.get('addr','').lower()=='0xb0076de78dc50581770bba1d211ddc0ad4f2a241' for x in m['gate_currency']['chains'])
            m.update(gate_id='EDGEX_USDT',gate_name='edgeX',identity='PUBLIC_CONTRACT_MATCH')
        m['gate_deposit']=network_status(m['gate_currency'],'deposit')
        m['gate_withdraw']=network_status(m['gate_currency'],'withdraw')
        m['route_eligibility']='BLOCKED_UNKNOWN'
    if len({m['symbol'] for m in markets})!=len(markets):raise ValueError('duplicate assets')
    return markets


def accumulate(stats,rows):
    for r in rows:
        key='|'.join(str(r[k]) for k in ['symbol','buy','sell','scenario','amount_usdt'])
        a=stats.setdefault(key,dict(observations=0,valid=0,positive=0,above_0_5=0,above_1=0,net_sum='0',min_net=None,max_net=None,statuses={}))
        a['observations']+=1;a['statuses'][r['status']]=a['statuses'].get(r['status'],0)+1
        if r['status']!='ESTIMATE_ONLY':continue
        x=D(r['net_usdt']);a['valid']+=1;a['positive']+=int(x>0)
        a['above_0_5']+=int(x>=D('.5'));a['above_1']+=int(x>=1)
        a['net_sum']=str(D(a['net_sum'])+x)
        a['min_net']=str(min(D(a['min_net']),x)) if a['min_net'] is not None else str(x)
        a['max_net']=str(max(D(a['max_net']),x)) if a['max_net'] is not None else str(x)


def worker(run):
    from leadlag_engine import Study, PARAMETERS
    config=json.loads((run/'config.json').read_text());symbols=config['symbols']
    stop,lock=threading.Event(),threading.Lock()
    for sig in [signal.SIGINT,signal.SIGTERM]:signal.signal(sig,lambda *_:stop.set())
    native=config['native_symbols'];books={v:{n:Book() for n in native[v].values()} for v in config['venues']}
    journal=Journal(run,config['max_evidence_bytes'],20*1024**3)
    threads=[threading.Thread(target=audit_worker,args=(v,list(books[v]),books[v],lock,stop,journal,config['proxy_port']),daemon=True) for v in books]
    study=Study(config);samples=0;failure=None
    def status(state,reason=None):
        atomic_json(run/'status.json',dict(state=state,reason=reason,pid=os.getpid(),updated_ms=time.time()*1000,samples=samples,deadline_ms=config['deadline_ms'],failure=failure or journal.failure,coverage=dict(study.counts),latest=study.latest,pending=len(study.pending),signals=study.serial,journal_bytes=journal.total+(journal.raw.tell() if journal.raw else 0),closed_shards=len(journal.files)))
    status('starting')
    for t in threads:t.start()
    try:
        with (run/'events.jsonl').open('x',buffering=1) as log:
            while not stop.is_set() and time.time()*1000<config['deadline_ms']:
                with lock:
                    now,mono=time.time()*1000,time.monotonic()
                    views={v:{s:books[v][n].view() for s,n in native[v].items()} for v in books}
                    events=study.step(views,now,mono)
                    for event in events:
                        journal.append('leadlag_event',**event);log.write(json.dumps(event)+'\n')
                    samples+=1
                    if samples%20==0:journal.flush();status('running')
                stop.wait(max(0,.1-(time.monotonic()-mono)))
    except Exception as exc:failure=type(exc).__name__+': '+str(exc)
    finally:
        stop.set()
        for t in threads:t.join(timeout=12)
        if any(t.is_alive() for t in threads):failure='worker_shutdown_timeout'
        journal.append('study_end',observed_ms=time.time()*1000,pending_censored=len(study.pending))
        journal.close()
        status('failed' if failure or journal.failure else 'stopped','duration_complete' if time.time()*1000>=config['deadline_ms'] else 'interrupted')
    return 1 if failure or journal.failure else 0


def supervise(state_root,screen,seconds,group_size,proxy):
    state_root.mkdir(parents=True,exist_ok=True)
    with (state_root/'process.lock').open('a') as singleton:
        try:fcntl.flock(singleton,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:raise SystemExit('wide watch already running')
        markets=build_universe(screen)
        started=time.time()*1000;deadline=started+seconds*1000
        run=state_root/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');run.mkdir()
        stop=threading.Event()
        for sig in [signal.SIGINT,signal.SIGTERM]:signal.signal(sig,lambda *_:stop.set())
        batches=[markets[i:i+group_size] for i in range(0,len(markets),group_size)]
        config=dict(mode='leadlag_public_study',started_ms=started,deadline_ms=deadline,duration_seconds=seconds,
            symbols=[m['symbol'] for m in markets],symbol_count=len(markets),amounts_usdt=['100','250','500'],
            fee_scenarios={'base':{'okx':'10','gate':'10'},'higher_gate':{'okx':'10','gate':'20'}},buffer_bps='5',
            live_trading=False,simulation_enabled=False,universe_rotation=False,auto_extend=False,
            fee_basis='ASSUMED_NOT_VERIFIED_ACCOUNT_RATES',qualification='UNKNOWN_BLOCKS_EXECUTION',
            max_evidence_bytes=256*1024**3,min_free_bytes=20*1024**3,
            metadata_source=str(screen),metadata_refresh=False,
            asset_mapping='OKX EDGE-USDT uses Gate EDGEX_USDT; all other same-code identities UNKNOWN',
            limitations=['Snapshot metadata may change during 24h','No fills or complete fees/route validation','1s comparisons can miss shorter-lived anomalies','100USDT primary episodes; all sizes retained in stats','Positive observations are not independent trades'])
        from leadlag_engine import PARAMETERS
        config.update(study_parameters=PARAMETERS,limitations=['Causal event study, not fills or portfolio simulation','Signal uses local availability and validated exchange timestamps','Feed/network delays can mimic leadership','Fixed horizons are separate research scenarios, not optimized exits','Identity and account fees unverified; no live trades'])
        atomic_json(run/'config.json',config);atomic_json(run/'universe.json',markets)
        groups=[];processes=[];logs=[];failure=None
        for i,batch in enumerate(batches):
            group=run/('group-%02d'%i);group.mkdir();source=group/'source';source.mkdir();hashes={}
            for name in SOURCE_NAMES:
                raw=(ROOT/name).read_bytes();(source/name).write_bytes(raw);hashes[name]=hashlib.sha256(raw).hexdigest()
            gc=dict(config,venues=['okx','gate'],symbols=[m['symbol'] for m in batch],group_id=i,
                source_sha256=hashes,proxy_port=proxy,max_evidence_bytes=config['max_evidence_bytes']*len(batch)//len(markets),
                native_symbols={v:{m['symbol']:m[v+'_id'].replace('-','').replace('_','') for m in batch} for v in ['okx','gate']},
                order_rules={v:{m['symbol']:order_rules(m).get(v) for m in batch} for v in ['okx','gate']})
            atomic_json(group/'config.json',gc);groups.append(group)
        def publish(state,reason=None):
            summaries=[]
            for group,proc in zip(groups,processes):
                sp=group/'status.json';s=json.loads(sp.read_text()) if sp.exists() else {}
                summaries.append(dict(group=group.name,run_dir=str(group),pid=proc.pid,exit_code=proc.poll(),
                    **{k:s.get(k) for k in ['state','reason','updated_ms','samples','failure','journal_bytes','closed_shards','anomaly_count']}))
            atomic_json(state_root/'status.json',dict(mode='leadlag_public_study',state=state,reason=reason,pid=os.getpid(),
                updated_ms=time.time()*1000,started_ms=started,deadline_ms=deadline,run_dir=str(run),symbol_count=len(markets),
                groups=summaries,failure=failure,live_trading=False,simulation_enabled=False,qualification='UNKNOWN'))
        try:
            for group in groups:
                if stop.is_set() or time.time()*1000>=deadline:break
                log=(group/'process.log').open('x');logs.append(log)
                processes.append(subprocess.Popen([sys.executable,str(group/'source/leadlag_watch.py'),'--worker',str(group)],stdout=log,stderr=subprocess.STDOUT))
                publish('starting');stop.wait(.7)
            while not stop.is_set() and any(p.poll() is None for p in processes):
                failures=[p.returncode for p in processes if p.poll() not in [None,0]]
                if failures:failure='worker_failed';stop.set();break
                publish('running');stop.wait(3)
                if deadline_overdue(time.time()*1000,deadline):failure='worker_deadline_overrun';stop.set();break
        except Exception as exc:failure=type(exc).__name__
        finally:
            for proc in processes:
                if proc.poll() is None:proc.terminate()
            for proc in processes:
                try:proc.wait(timeout=30)
                except subprocess.TimeoutExpired:failure='worker_shutdown_timeout';proc.kill();proc.wait()
            for log in logs:log.close()
            if len(processes)!=len(groups):failure=failure or 'incomplete_group_start'
            if any(p.returncode!=0 for p in processes):failure=failure or 'worker_failed'
            reason='duration_complete' if time.time()*1000>=deadline else 'interrupted'
            publish('failed' if failure else 'stopped',reason)
            atomic_json(run/'final_status.json',json.loads((state_root/'status.json').read_text()))
        return 1 if failure else 0


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--worker',type=Path)
    p.add_argument('--screen-dir',type=Path);p.add_argument('--state-root',type=Path,default=ROOT/'leadlag_watch')
    p.add_argument('--seconds',type=int,default=86400);p.add_argument('--group-size',type=int,default=50)
    p.add_argument('--proxy-port',type=int,default=7890);a=p.parse_args()
    if a.worker:raise SystemExit(worker(a.worker))
    if not a.screen_dir or not 10<=a.seconds<=86400 or not 1<=a.group_size<=50:p.error('screen-dir, seconds 10..86400, group-size 1..50 required')
    raise SystemExit(supervise(a.state_root.resolve(),a.screen_dir.resolve(),a.seconds,a.group_size,a.proxy_port))
