from pathlib import Path
from collections import defaultdict
from bisect import bisect_right
from decimal import Decimal
import json,hashlib,datetime as dt
B=Path(__file__).resolve().parent
def near(a,b):assert abs(float(a)-float(b))<1e-7*max(1,abs(float(a)),abs(float(b))),(a,b)
def fill(levels,q,unit):
 left=q;value=Decimal(0)
 for price,amount in levels:
  take=min(left,amount);value+=take*price*unit;left-=take
  if left==0:return value
 return None
p=json.loads((B/'protocol.json').read_text());inp=json.loads((B/'input_freeze.json').read_text());f=json.loads((B/'execution_freeze.json').read_text())
for n,h in f['hashes'].items():assert hashlib.sha256((B/n).read_bytes()).hexdigest()==h
assert hashlib.sha256(Path(inp['path']).read_bytes()).hexdigest()==inp['sha256'];events=json.loads((B/'events.json').read_text());out=json.loads((B/'event_price_fee_deltas.json').read_text());specs={x['instId']:x for x in json.loads((B/'instruments.json').read_text())};groups=defaultdict(list)
for e in events:groups[(e['asset'],e['cohort'])].append(e)
selected={e['event_id'] for g in groups.values() for e in [g[0],g[len(g)//2],g[-1]]};chosen=[r for r in out if r['event_id'] in selected and r['hold_seconds']==15 and r['delay_ms'] in [0,1000,3000]];chosen+=[r for reason in sorted({r['reason'] for r in out if r['status']!='observed'}) for r in [x for x in out if x['reason']==reason][:2]];wanted_ord={r[k] for r in chosen for k in ['entry_ordinal','exit_ordinal'] if k in r};books=defaultdict(list);times=defaultdict(list);trades=defaultdict(list);meta={};channels=defaultdict(int);seq_missing=defaultdict(int);exchange_reversals=defaultdict(int);lastExchange={};lastOrdinal=0;lastMono=-1;ordinal_good=True;mono_good=True;firstwall=None;lastwall=None
with Path(inp['path']).open() as raw:
 for line in raw:
  r=json.loads(line);ordinal_good &=r['local_ordinal']==lastOrdinal+1;mono_good &=r['monotonic_ns']>=lastMono;lastOrdinal=r['local_ordinal'];lastMono=r['monotonic_ns'];firstwall=r['receive_wall_ns'] if firstwall is None else firstwall;lastwall=r['receive_wall_ns'];a=r['instId'];o=json.loads(r['raw']);t=r['monotonic_ns']/1e6;key=str(r['channel'])+'|'+str(a);channels[key]+=1
  if r['local_ordinal'] in wanted_ord:meta[r['local_ordinal']]=r
  for d in o.get('data',[]):
   if d.get('ts'):
    ex=int(d['ts']);exchange_reversals[key]+=key in lastExchange and ex<lastExchange[key];lastExchange[key]=ex
   seq_missing[key]+='prevSeqId' not in d
   if r['channel']=='books5':
    asks=[(Decimal(x[0]),Decimal(x[1])) for x in d['asks'] if Decimal(x[1])>0];bids=[(Decimal(x[0]),Decimal(x[1])) for x in d['bids'] if Decimal(x[1])>0]
    if not asks or not bids or bids[0][0]>=asks[0][0]:continue
    b={'t':t,'ordinal':r['local_ordinal'],'conn':r['connectionId'],'asks':asks,'bids':bids,'mid':(asks[0][0]+bids[0][0])/2,'wall_ns':r['receive_wall_ns']};books[a].append(b);times[a].append(t)
   if r['channel']=='trades':trades[a].append({'t':t,'ordinal':r['local_ordinal'],'conn':r['connectionId'],'notional':Decimal(d['px'])*Decimal(d['sz'])*Decimal(specs[a]['ctVal'])*Decimal(specs[a]['ctMult']),'side':1 if d['side']=='buy' else -1})
assert ordinal_good and mono_good and lastOrdinal==inp['final']['messages'];cut=dt.datetime.fromisoformat(p['cohort_asof_cutoff_UTC']);epoch=dt.datetime(1970,1,1,tzinfo=dt.timezone.utc);delta=cut-epoch;cut_ns=((delta.days*86400+delta.seconds)*1000000+delta.microseconds)*1000;features=0
for e in events:
 if e['event_id'] not in selected:continue
 a=e['asset'];now=e['asof_ms'];booklist=[b for b in books[a] if b['ordinal']<=e['asof_ordinal'] and b['conn']==e['connectionId']];latest=booklist[-1];ref=[b for b in booklist if b['t']<=now-1000][-1];flows=[x for x in trades[a] if now-1000<x['t']<=now and x['ordinal']<=e['asof_ordinal'] and x['conn']==e['connectionId']];total=sum(x['notional'] for x in flows);net=sum(x['notional']*x['side'] for x in flows);imb=net/total;imp=(latest['mid']/ref['mid']-1)*10000;near(e['imbalance'],imb);near(e['impulse_bps'],imp);near(e['flow_total_USDT'],total);assert abs(imb)>=Decimal('.8') and abs(imp)>=3 and imb*imp>0;assert 0<=now-1000-ref['t']<=250 and 0<=now-latest['t']<=250
 expected='dev_prefix' if e['asof_ordinal']<=20000 else 'prefreeze_remainder' if e['asof_receive_wall_ns']<cut_ns else 'postfreeze_new';assert e['cohort']==expected;features+=1
emap={e['event_id']:e for e in events};observed=censored=0
def firstbook(a,target,conn):
 i=bisect_right(times[a],target)
 return books[a][i] if i<len(books[a]) and books[a][i]['conn']==conn else None
for r in chosen:
 e=emap[r['event_id']];a=r['asset'];entry=firstbook(a,e['asof_ms']+r['delay_ms'],e['connectionId'])
 if r['status']!='observed':
  assert r['price_fee_delta_USDT'] is None
  if r['reason']=='no_postdecision_book':assert entry is None
  elif r['reason']=='expired_entry_quote':assert entry and entry['t']-e['asof_ms']-r['delay_ms']>250
  elif r['reason'] in ['no_posthold_book','expired_exit_quote']:
   exit=firstbook(a,entry['t']+r['hold_seconds']*1000,e['connectionId']);assert exit is None if r['reason']=='no_posthold_book' else exit['t']-entry['t']-r['hold_seconds']*1000>250
  elif r['reason']=='minlot_or_entrydepth':
   unit=Decimal(specs[a]['ctVal'])*Decimal(specs[a]['ctMult']);levels=entry['asks'] if r['side']==1 else entry['bids'];budget=Decimal(500)/(1+Decimal(r['fee_each_side_bps'])/10000);assert sum(price*qty*unit for price,qty in levels)<budget or Decimal(specs[a]['minSz'])*unit*levels[0][0]>budget
  censored+=1;continue
 assert entry and entry['ordinal']==r['entry_ordinal'];exit=firstbook(a,entry['t']+r['hold_seconds']*1000,e['connectionId']);assert exit and exit['ordinal']==r['exit_ordinal'];assert 0<entry['t']-e['asof_ms']-r['delay_ms']<=250 and 0<exit['t']-entry['t']-r['hold_seconds']*1000<=250;q=Decimal(r['contracts']);unit=Decimal(specs[a]['ctVal'])*Decimal(specs[a]['ctMult']);step=Decimal(specs[a]['lotSz']);assert q>=Decimal(specs[a]['minSz']) and q%step==0;side=r['side'];en=fill(entry['asks'] if side==1 else entry['bids'],q,unit);ex=fill(exit['bids'] if side==1 else exit['asks'],q,unit);fee=Decimal(r['fee_each_side_bps'])/10000;assert en is not None and ex is not None and en*(1+fee)<=500;nxt=fill(entry['asks'] if side==1 else entry['bids'],q+step,unit);assert nxt is None or nxt*(1+fee)>500;near(r['fee_USDT'],(en+ex)*fee);near(r['price_fee_delta_USDT'],Decimal(side)*(ex-en)-(en+ex)*fee);near(r['underlying_quantity'],q*unit);observed+=1
prefixref=json.loads((B.parent/'phase002_opportunity/v11/events.json').read_text());dev=[e for e in events if e['cohort']=='dev_prefix'];assert len(dev)==len(prefixref)
for x,y in zip(dev,prefixref):
 for k,v in y.items():assert x[k]==v,(k,x[k],v)
audit={'status':'PASS_FINITE_SAMPLED_AUDIT','features_sampled':features,'observed_outcomes_sampled':observed,'censored_outcomes_sampled':censored,'sampling':'first/middle/last perasset/cohort primary15s delays0/1000/3000 eachcost/action plusfirst2per censorreason','dev_prefix_events_exact_v11_regression':True,'core_source_hash_unchanged':True,'raw_ordinal_contiguous':ordinal_good,'processmono_nondecreasing':mono_good,'first_receive_wall_ns':firstwall,'last_receive_wall_ns':lastwall,'channel_messages_raw':dict(channels),'prevseq_missing_record_count':dict(seq_missing),'exchange_ts_backsteps':dict(exchange_reversals),'fullsource_completeness':'UNKNOWN','sameOwner_not_thirdparty_fullreplay':True};(B/'audit.json').write_text(json.dumps(audit,indent=2));print(audit)
