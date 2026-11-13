"""Atomic offline scenario journal using Python's bundled SQLite."""
import json
import sqlite3
import time
from pathlib import Path
from paper_ledger import digest
from paper_experiment import initial_experiment,step
from experiment_protocol import validate_window


def implementation_hash():
    root=Path(__file__).parent
    names=('paper_ledger.py','paper_baselines.py','paper_experiment.py',
           'experiment_store.py','experiment_protocol.py','decision-prompt-v1.md')
    return digest({n:(root/n).read_text() for n in names})


def process(database,decision_path,books,specs,operating_cost_usdt=None,protocol=None):
    """Persist all four scenario states or none; invalid market observations persist.

    Decision must already have been committed. This records paper transitions,
    not real orders, and provides no external timestamp attestation.
    """
    envelope=json.loads(Path(decision_path).read_text())
    decision=envelope['decision']
    if digest(decision)!=envelope['sha256']:
        raise ValueError('DECISION_HASH_MISMATCH')
    code=implementation_hash()
    protocol_hash=digest(protocol)
    con=sqlite3.connect(str(database),timeout=5,isolation_level=None)
    try:
        con.execute('PRAGMA synchronous=FULL')
        con.execute('BEGIN IMMEDIATE')
        con.execute('CREATE TABLE IF NOT EXISTS events (seq INTEGER PRIMARY KEY, slot TEXT UNIQUE NOT NULL, body TEXT NOT NULL, sha256 TEXT NOT NULL)')
        previous='';state=initial_experiment()
        for seq,slot,body,sha in con.execute('SELECT seq,slot,body,sha256 FROM events ORDER BY seq'):
            event=json.loads(body)
            if digest(event)!=sha or event['previous']!=previous or slot!=event['decision']['slot']:
                raise ValueError('JOURNAL_INTEGRITY_ERROR')
            if event['implementation_hash']!=code:
                raise ValueError('IMPLEMENTATION_CHANGED')
            if event['protocol_hash']!=protocol_hash:
                raise ValueError('PROTOCOL_CHANGED')
            state=event['state'];previous=sha
        if decision['slot'] in state['slots']:
            raise ValueError('DUPLICATE_WINDOW')
        now=time.time_ns()//1000000
        if protocol is not None:
            validate_window(protocol,decision,now)
            if not state['slots'] and decision['window_index']>0:
                # A missed first window must not move the benchmark entry date.
                for arm in state['scenarios'].values():
                    arm['baselines']['entry_attempted']=True
        result=step(state,decision,books,specs,now,operating_cost_usdt)
        event={'previous':previous,'implementation_hash':code,'decision':decision,
               'decision_sha256':envelope['sha256'],'books':books,'specs':specs,
               'operating_cost_usdt':operating_cost_usdt,'observed_ms':now,
               'state':result,'scope':'PAPER_ONLY', 'protocol':protocol,
               'protocol_hash':protocol_hash,
               'mode':'DEVELOPMENT' if protocol is None else 'SCHEDULE_CHECKED_PAPER'}
        con.execute('INSERT INTO events(slot,body,sha256) VALUES(?,?,?)',
                    (decision['slot'],json.dumps(event,sort_keys=True),digest(event)))
        con.execute('COMMIT')
        return result
    except BaseException:
        if con.in_transaction:con.execute('ROLLBACK')
        raise
    finally:
        con.close()
