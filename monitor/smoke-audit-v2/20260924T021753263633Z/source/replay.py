"""Independent raw-message replay. Does not import the live book or cost calculator."""
import argparse
import gzip
import hashlib
import json
from collections import Counter
from decimal import Decimal as D
from pathlib import Path


def empty(connection=None):
    return dict(bids={},asks={},valid=False,seq=None,ts=0,mono=0,ref=None,connection_id=connection)


def reduce_frame(books,row):
    venue=row['venue']
    if row['raw']=='pong':return
    try:
        msg=json.loads(row['raw'])
        if venue=='gate' and msg.get('channel')=='spot.order_book' and msg.get('event')=='update':
            d=msg['result'];symbol=d['s'].replace('_','')
            changes=[(d['bids'],d['asks'],int(d['t']),d['lastUpdateId'],True,None)]
        elif venue=='okx' and 'arg' in msg and 'data' in msg:
            symbol=msg['arg']['instId'].replace('-','')
            changes=[(d['bids'],d['asks'],int(d['ts']),d['seqId'],msg['action']=='snapshot',d.get('prevSeqId')) for d in msg['data']]
        else:return
        b=books[venue][symbol]
        for bids,asks,ts,seq,snapshot,prev in changes:
            if not isinstance(seq,int) or seq<0 or ts<=0:raise ValueError('sequence')
            if venue=='gate' and b['seq'] is not None and (seq<b['seq'] or ts<b['ts']):raise ValueError('regression')
            if venue=='okx':
                if snapshot and prev!=-1:raise ValueError('snapshot')
                if not snapshot and (not b['valid'] or prev is None or prev!=b['seq']):raise ValueError('chain')
                if not snapshot and seq==prev and (bids or asks):raise ValueError('same seq changed')
            parsed=[]
            for rows in (bids,asks):
                levels={}
                for v in rows:
                    p,q=D(v[0]),D(v[1])
                    if not p.is_finite() or not q.is_finite() or p<=0 or q<0:raise ValueError('level')
                    levels[p]=q
                parsed.append(levels)
            if snapshot:b['bids'],b['asks']={},{}
            for target,updates in zip(['bids','asks'],parsed):
                for p,q in updates.items():
                    if q:b[target][p]=q
                    else:b[target].pop(p,None)
            if not b['bids'] or not b['asks'] or max(b['bids'])>=min(b['asks']):raise ValueError('crossed')
            b.update(valid=True,seq=seq,ts=ts,mono=row['mono'],ref=row['journal_seq'])
    except Exception:
        for b in books[venue].values():b['valid']=False


def quality(b,s,now,mono,age=2000,skew=500):
    for x in (b,s):
        if not x['valid']:return 'INVALID_BOOK'
        if not -250<=now-x['ts']<=age or not 0<=(mono-x['mono'])*1000<=age:return 'STALE_OR_CLOCK_ERROR'
    return 'UNSYNCHRONIZED' if abs(b['ts']-s['ts'])>skew else 'VALID'


def walk(rows,quantity):
    total=D(0)
    for price,size in rows:
        used=min(quantity,size)
        total+=used*price
        quantity-=used
        if quantity==0:return total
    return None


def calculate(b,s,amount,bfee,sfee,buffer,now,mono,quantity=None):
    status=quality(b,s,now,mono)
    if status!='VALID':return dict(status=status)
    if quantity is None:
        left,qty=D(amount),D(0)
        for price,size in sorted(b['asks'].items()):
            money=min(left,price*size)
            qty+=money/price
            left-=money
            if left==0:break
        if left:return dict(status='INSUFFICIENT_DEPTH')
        cost=D(amount)
    else:
        qty=D(quantity)
        cost=walk(sorted(b['asks'].items()),qty)
    revenue=walk(sorted(s['bids'].items(),reverse=True),qty)
    if cost is None or revenue is None:return dict(status='INSUFFICIENT_DEPTH')
    fees=cost*D(bfee)/10000+revenue*D(sfee)/10000
    return dict(status='ESTIMATE_ONLY',quantity=str(qty),buy_cost_usdt=str(cost),
                net_usdt=str(revenue-cost-fees-cost*D(buffer)/10000))


def replay(run):
    run=Path(run)
    config=json.loads((run/'config.json').read_text())
    manifest=json.loads((run/'journal_manifest.json').read_text())
    errors=[]
    def error(msg):
        if len(errors)<30:errors.append(msg)
    for name,digest in config['source_sha256'].items():
        if hashlib.sha256((run/'source'/name).read_bytes()).hexdigest()!=digest:error('source hash '+name)
    if config.get('qualification_sha256') and hashlib.sha256((run/'qualification.json').read_bytes()).hexdigest()!=config['qualification_sha256']:
        error('qualification hash')
    books={v:{s:empty() for s in config['symbols']} for v in config['venues']}
    seen,decisions,compared,delays=0,0,0,0
    counts,coverage,events=Counter(),Counter(),Counter()
    anomaly_state={};serial=0;expected_events=[]
    last_kind=None;first_ms=last_ms=None
    primary_best={}
    def compare(calc,recorded,seq):
        if calc['status']!=recorded['status']:
            error('status mismatch at '+str(seq));return
        if calc['status']=='ESTIMATE_ONLY':
            for k in ['quantity','net_usdt']:
                if abs(D(calc[k])-D(recorded[k]))>D('1e-18'):error(k+' mismatch at '+str(seq))
    for entry in manifest['files']:
        path=run/entry['file']
        if path.name!=entry['file']:raise ValueError('unsafe shard path')
        if hashlib.sha256(path.read_bytes()).hexdigest()!=entry['sha256']:
            error('shard hash '+path.name)
        with gzip.open(path,'rt') as f:
            for line in f:
                row=json.loads(line);seq=row['journal_seq'];kind=row['kind'];last_kind=kind
                if seq!=seen+1:error('journal sequence gap at '+str(seq))
                seen=seq
                if kind=='connect':
                    books[row['venue']]={s:empty(row['connection_id']) for s in config['symbols']}
                elif kind=='disconnect':
                    for b in books[row['venue']].values():b['valid']=False
                elif kind=='frame':reduce_frame(books,row)
                elif kind=='decision':
                    decisions+=1
                    now,mono=row['observed_ms'],row['mono']
                    first_ms=now if first_ms is None else first_ms;last_ms=now
                    expected_keys={(s,b,a,n,f) for s in config['symbols'] for b,a in [('okx','gate'),('gate','okx')] for n in config['amounts_usdt'] for f in config['fee_scenarios']}
                    actual_keys=set()
                    for r in row['results']:
                        actual_keys.add((r['symbol'],r['buy'],r['sell'],r['amount_usdt'],r['scenario']))
                        b,s=books[r['buy']][r['symbol']],books[r['sell']][r['symbol']]
                        fees=config['fee_scenarios'][r['scenario']]
                        calc=calculate(b,s,r['amount_usdt'],fees[r['buy']],fees[r['sell']],config['buffer_bps'],now,mono)
                        compare(calc,r,seq);compared+=1;counts[calc['status']]+=1
                        if r['book_refs']!=[b['ref'],s['ref']]:error('book reference mismatch '+str(seq))
                        if r['connection_ids']!=[b['connection_id'],s['connection_id']]:error('connection mismatch '+str(seq))
                        if r['strict_quality']!=quality(b,s,now,mono,500,100):error('strict quality mismatch '+str(seq))
                        if r['scenario']=='base' and r['amount_usdt']=='100':
                            key=r['symbol']+'|'+r['buy']+'|'+r['sell']
                            coverage[key+'|'+calc['status']]+=1
                            coverage[key+'|strict_'+quality(b,s,now,mono,500,100)]+=1
                            if calc['status']=='ESTIMATE_ONLY':
                                primary_best[key]=max(primary_best.get(key,D('-Infinity')),D(calc['net_usdt']))
                            state=anomaly_state.get(key);etype=None
                            if calc['status']=='ESTIMATE_ONLY' and D(calc['net_usdt'])>0:
                                if state is None:
                                    serial+=1;state=[serial,False,0];anomaly_state[key]=state;etype='anomaly_open'
                                elif state[1]:etype='anomaly_resumed'
                                state[1],state[2]=False,0
                            elif state is not None and calc['status']!='ESTIMATE_ONLY':
                                if not state[1]:etype='data_unavailable'
                                state[1],state[2]=True,0
                            elif state is not None:
                                state[1]=False;state[2]+=1
                                if state[2]>=3:etype='ended';del anomaly_state[key]
                            if etype:expected_events.append((etype,state[0]))
                    if actual_keys!=expected_keys or len(row['results'])!=len(expected_keys):error('missing/duplicate decision scenarios '+str(seq))
                elif kind=='event':
                    events[row['event']]+=1
                    if row['event']=='delay_check':
                        delays+=1;o=row['original'];b,s=books[o['buy']][o['symbol']],books[o['sell']][o['symbol']]
                        q=quality(b,s,row['observed_ms'],row['mono'])
                        if q!='VALID':calc={'status':q}
                        elif [b['connection_id'],s['connection_id']]!=o['connection_ids']:calc={'status':'CONNECTION_CHANGED'}
                        elif b['ref']==o['book_refs'][0] or s['ref']==o['book_refs'][1]:calc={'status':'NO_NEW_BOOK'}
                        else:calc=calculate(b,s,None,o['buy_fee_bps'],o['sell_fee_bps'],o['buffer_bps'],row['observed_ms'],row['mono'],o['quantity'])
                        compare(calc,row['delayed'],seq)
                        if row['actual_delay_ms']<1000:error('early delay check '+str(seq))
                        if calc['status']=='ESTIMATE_ONLY':
                            cash=o.get('hypothetical_available_cash_usdt')
                            can='UNKNOWN' if cash is None else ('YES' if D(calc['buy_cost_usdt'])*(1+D(o['buy_fee_bps'])/10000)<=D(cash) else 'NO')
                            if row['delayed']['affordability']!=can:error('affordability mismatch '+str(seq))
                    elif not expected_events or expected_events.pop(0)!=(row['event'],row['episode_id']):
                        error('episode mismatch '+str(seq))
    if expected_events:error('missing episode events')
    if seen!=manifest['last_seq']:error('manifest sequence mismatch')
    complete=last_kind=='run_end'
    if not decisions:error('no decisions to validate')
    return dict(passed=not errors,complete=complete,errors=errors,journal_records=seen,decisions=decisions,
                estimates_compared=compared,delays_compared=delays,independent_anomalies=serial,
                first_ms=first_ms,last_ms=last_ms,counts=dict(counts),coverage=dict(coverage),events=dict(events),
                primary_best_assumed_net={k:str(v) for k,v in primary_best.items()},
                limitation='Replay proves arithmetic and reconstruction consistency only; not fills, routes or profit.')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--run-dir',required=True,type=Path)
    args=parser.parse_args();result=replay(args.run_dir)
    print(json.dumps(result,ensure_ascii=False,indent=2))
    raise SystemExit(0 if result['passed'] and result['complete'] else 1)
