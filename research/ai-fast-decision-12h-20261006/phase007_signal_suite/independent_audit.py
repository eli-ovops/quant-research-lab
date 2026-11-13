from pathlib import Path
from decimal import Decimal
import json,hashlib
B=Path(__file__).resolve().parent
def near(a,b):assert abs(float(a)-float(b))<1e-7*max(1,abs(float(a)),abs(float(b))),(a,b)
p=json.loads((B/'protocol.json').read_text());f=json.loads((B/'execution_freeze.json').read_text())
for n,h in f['hashes'].items():assert hashlib.sha256((B/n).read_bytes()).hexdigest()==h
source=Path(p['dev_source']['path']);blob=source.read_bytes();assert hashlib.sha256(blob).hexdigest()==p['dev_source']['sha256'];rows=[json.loads(x) for x in blob.splitlines()];byord={x['local_ordinal']:x for x in rows};specs={x['instId']:x for x in json.loads((B/'instruments.json').read_text())};events=json.loads((B/'dev_events.json').read_text());out=json.loads((B/'dev_event_deltas.json').read_text());books={a:[] for a in specs};trades={a:[] for a in specs}
for r in rows:
 a=r['instId']
 if a not in specs:continue
 for d in json.loads(r['raw']).get('data',[]):
  if r['channel']=='books5':books[a].append({'ordinal':r['local_ordinal'],'time':r['monotonic_ns']/1e6,'conn':r['connectionId'],'asks':[(Decimal(x[0]),Decimal(x[1])) for x in d['asks']],'bids':[(Decimal(x[0]),Decimal(x[1])) for x in d['bids']]})
  elif r['channel']=='trades':trades[a].append({'ordinal':r['local_ordinal'],'time':r['monotonic_ns']/1e6,'side':1 if d['side']=='buy' else -1,'value':Decimal(d['px'])*Decimal(d['sz'])*Decimal(specs[a]['ctVal'])*Decimal(specs[a]['ctMult'])})
checked=0;cool={}
for e in events:
 a=e['asset'];now=e['asof_ms'];past=[b for b in books[a] if b['ordinal']<=e['asof_ordinal']];cur=past[-1];lookback=500 if e['family']=='BOOK_STATE' else 1000;ref=[b for b in past if b['time']<=now-lookback][-1];assert cur['ordinal']==e['latest_book_ordinal'] and ref['ordinal']==e['reference_book_ordinal'];assert 0<=now-cur['time']<=250 and 0<=now-lookback-ref['time']<=250;flows=[t for t in trades[a] if t['ordinal']<=e['asof_ordinal'] and now-1000<t['time']<=now];total=sum(t['value'] for t in flows);net=sum(t['value']*t['side'] for t in flows);near(e['imbalance'],net/total);assert e['clock_view']=='LEGACY_INTERNAL' and e['source_asof_shared_ns'] is None
 if e['family']=='BOOK_STATE':
  for side in ['asks','bids']:assert [x[0] for x in cur[side][:3]]==[x[0] for x in ref[side][:3]]
  bid=sum(px*q for px,q in cur['bids'][:3]);ask=sum(px*q for px,q in cur['asks'][:3]);imb=(bid-ask)/(bid+ask);side=1 if imb>0 else -1;opp='asks' if side==1 else 'bids';ratio=sum(px*q for px,q in cur[opp][:3])/sum(px*q for px,q in ref[opp][:3]);near(e['top3_imbalance'],imb);near(e['opposing_depth_ratio'],ratio);assert abs(imb)>=Decimal('.8') and ratio<=Decimal('.5') and abs(net/total)>=Decimal('.5') and net*side>0
 key=(e['family'],a);assert now-cool.get(key,-1e99)>=35000;cool[key]=now;checked+=1
old=json.loads((B.parent/'phase005_numeric_v12/events.json').read_text());expected=[e for e in old if e['cohort']=='dev_prefix'];flow=[e for e in events if e['family']=='FLOW_IMPULSE'];assert len(flow)==len(expected)
for e,x in zip(flow,expected):
 for k in ['asset','asof_ms','asof_ordinal','direction','impulse_bps','imbalance','flow_total_USDT','flow_net_USDT','latest_book_ordinal','reference_book_ordinal']:near(e[k],x[k]) if isinstance(x[k],(int,float)) else None
 assert e['asset']==x['asset']
def fill(lv,q,u):
 rem=q;n=Decimal(0)
 for px,sz in lv:
  take=min(rem,sz);n+=take*px*u;rem-=take
  if rem==0:return n
 return None
emap={e['event_id']:e for e in events};valid=0;null=0
for r in out:
 if r['status']!='observed':assert r['price_fee_delta_USDT'] is None;null+=1;continue
 e=emap[r['event_id']];a=e['asset'];entry=next(b for b in books[a] if b['time']>e['asof_ms']+r['delay_ms']);exit=next(b for b in books[a] if b['time']>entry['time']+r['hold_seconds']*1000);assert entry['ordinal']==r['entry_ordinal'] and exit['ordinal']==r['exit_ordinal'];assert entry['time']-e['asof_ms']-r['delay_ms']<=250 and exit['time']-entry['time']-r['hold_seconds']*1000<=250;q=Decimal(r['contracts']);unit=Decimal(specs[a]['ctVal'])*Decimal(specs[a]['ctMult']);en=fill(entry['asks'] if r['side']==1 else entry['bids'],q,unit);ex=fill(exit['bids'] if r['side']==1 else exit['asks'],q,unit);fee=Decimal(r['fee_each_side_bps'])/10000;assert en*(1+fee)<=500;near(r['price_fee_delta_USDT'],Decimal(r['side'])*(ex-en)-(en+ex)*fee);valid+=1
states=json.loads((B/'dev_compact_states_v2.json').read_text());assert all(s['is_live']==False and s['source_asof_shared_ns'] is None and s['source_latest_book_shared_ns'] is None for s in states);assert not any(k in s for s in states for k in ['pnl','price_fee_delta_USDT','exit_VWAP'])
result={'status':'PASS_FINITE_DEV_AUDIT','dev_events_checked':checked,'flow_original_v12_asof_features_exact':True,'observed_depth_fee_timing_checked':valid,'censored_null_checked':null,'association_real_dev_events':sum(e['family']=='BTC_TRANSMISSION' for e in events),'association_validation':'syntheticpredicate/causal tests only no realevent performance','stateV2_history_no_live_or_future_labels':True,'006_future_evaluation':'NOT_RUN','sameOwner_notthirdpartyfullreplay':True};(B/'audit.json').write_text(json.dumps(result,indent=2));print(result)

