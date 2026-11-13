import sys,json,pathlib,gzip,collections,statistics,hashlib
from decimal import Decimal as D
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[2]))
from replay import empty,reduce_frame,walk
ROOT=pathlib.Path(__file__).resolve().parents[2]
run=pathlib.Path(json.loads((ROOT/'leadlag_watch/status.json').read_text())['run_dir'])
report={'run_dir':str(run),'scope':'closed raw shards only; exploratory, no holdout validation','groups':[]};results=[];signals=[]
for g in sorted(run.glob('group-*')):
 cfg=json.loads((g/'config.json').read_text());manifest=json.loads((g/'journal_manifest.json').read_text()) if (g/'journal_manifest.json').exists() else None
 # Closed shards are all except the last while recording. Fixed snapshot; never read mutable last shard.
 paths=sorted(g.glob('journal-*.jsonl.gz'))[:-1]
 events=[json.loads(l) for l in (g/'events.jsonl').read_text().splitlines()];byid=collections.defaultdict(dict);targets=set()
 for e in events:
  byid[e['event_id']].setdefault(e['event'],[]).append(e)
  if e['event']=='lead_signal':targets.update(e['book_refs']);targets.update(e['baseline_refs'])
  elif e.get('book_ref'):targets.add(e['book_ref'])
 books={v:{n:empty() for n in cfg['native_symbols'][v].values()} for v in ['okx','gate']};snaps={};shards=[];lastseq=0
 for path in paths:
  shards.append({'file':path.name,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
  with gzip.open(path,'rt') as f:
   for line in f:
    row=json.loads(line);seq=row['journal_seq'];lastseq=seq;v=row.get('venue')
    if row['kind']=='connect':books[v]={n:empty(row['connection_id']) for n in books[v]}
    elif row['kind']=='disconnect':
     for b in books[v].values():b['valid']=False
    elif row['kind']=='frame':
     reduce_frame(books,row)
     if seq in targets:
      for n,b in books[v].items():
       if b['ref']==seq:snaps[seq]=dict(b,bids=dict(b['bids']),asks=dict(b['asks']),received_ms=row['received_ms'])
 for eid,ev in byid.items():
  sig=ev['lead_signal'][0];refs=sig['book_refs'];base=sig['baseline_refs']
  if all(ref in snaps for ref in list(refs)+list(base)):
   leadidx=['okx','gate'].index(sig['leader']);a=snaps[base[leadidx]];b=snaps[refs[leadidx]]
   def top(x):return max(x['bids']),min(x['asks'])
   ab,aa=top(a);bb,ba=top(b)
   signals.append(dict(symbol=sig['symbol'],leader=sig['leader'],venue=sig['venue'],mid_bps=sig['moves_bps'][sig['leader']],bid_bps=float((bb/ab-1)*10000),ask_bps=float((ba/aa-1)*10000),spread_before_bps=float((aa-ab)/((aa+ab)/2)*10000),spread_after_bps=float((ba-bb)/((ba+bb)/2)*10000),arrival_age_ms=b['received_ms']-b['ts']))
  if 'entry_observation' not in ev:continue
  entry=ev['entry_observation'][0]
  if entry.get('book_ref') not in snaps:continue
  b=snaps[entry['book_ref']];ebid,eask=max(b['bids']),min(b['asks']);emid=(ebid+eask)/2
  for out in ev.get('outcome',[]):
   if out.get('book_ref') not in snaps:continue
   x=snaps[out['book_ref']];xbid,xask=max(x['bids']),min(x['asks']);xmid=(xbid+xask)/2
   for sc in out['scenarios']:
    if sc['status']!='ESTIMATE_ONLY' or sc['amount_usdt']!='100':continue
    q=D(sc['quantity']);cost=walk(sorted(b['asks'].items()),q);rev=walk(sorted(x['bids'].items(),reverse=True),q)
    if cost is None or rev is None:continue
    fee=(cost+rev)*D(sc['fee_bps'])/10000;buffer=cost*D(5)/10000;net=rev-cost-fee-buffer
    results.append(dict(symbol=sig['symbol'],leader=sig['leader'],venue=sig['venue'],event_id=eid,group=g.name,fee_bps=sc['fee_bps'],horizon=out['horizon_seconds'],mid_change_usdt=float(q*(xmid-emid)),spread_cost_usdt=float(q*((eask-emid)+(xmid-xbid))),depth_cost_usdt=float((cost-q*eask)+(q*xbid-rev)),fees_usdt=float(fee),buffer_usdt=float(buffer),net_usdt=float(net),calculation_matches=abs(net-D(sc['net_usdt']))<D('1e-15'),cost_matches=abs(cost-D(sc['cost_usdt']))<D('1e-15'),exit_matches=abs(rev-D(sc['exit_revenue_usdt']))<D('1e-15')))
 report['groups'].append(dict(group=g.name,closed_shards=len(paths),last_seq=lastseq,reference_count=len(snaps),shards=shards));print(g.name,'done',flush=True)
report['signals']=signals;report['results']=results
pathlib.Path(__file__).with_name('audit.json').write_text(json.dumps(report,ensure_ascii=False))
print('signals',len(signals),'results',len(results),'mismatches',sum(not (r['calculation_matches'] and r['cost_matches'] and r['exit_matches']) for r in results))
print('leader_mid_up_but_bid_not_up',sum(r['bid_bps']<=0 for r in signals),'ask_not_up',sum(r['ask_bps']<=0 for r in signals))
for h in [1,3,10,30]:
 rows=[r for r in results if r['horizon']==h and r['fee_bps']==(20 if r['venue']=='gate' else 10)]
 print(h,len(rows),{k:round(statistics.mean(r[k] for r in rows),5) for k in ['mid_change_usdt','spread_cost_usdt','depth_cost_usdt','fees_usdt','buffer_usdt','net_usdt']})
