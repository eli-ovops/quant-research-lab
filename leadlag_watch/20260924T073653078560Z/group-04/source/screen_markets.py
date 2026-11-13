"""Bounded public-only universe/depth research, independent of the frozen monitor."""
import argparse
import csv
import gzip
import hashlib
import json
import re
import threading
import time
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from decimal import Decimal as D
from pathlib import Path
from statistics import median
import requests
from detector import levels, evaluate, validate_books

URLS={
 'okx_instruments':'https://www.okx.com/api/v5/public/instruments?instType=SPOT',
 'gate_pairs':'https://api.gateio.ws/api/v4/spot/currency_pairs',
 'gate_currencies':'https://api.gateio.ws/api/v4/spot/currencies'}
AMOUNTS=['100','250','500']
SCENARIOS={'base':{'okx':'10','gate':'10'},'higher_gate':{'okx':'10','gate':'20'}}


def dump(path,value):
 Path(path).write_text(json.dumps(value,ensure_ascii=False,indent=2))


def network_status(currency,side):
 chains=currency.get('chains')
 if not isinstance(chains,list) or not chains:return 'UNKNOWN'
 known=[]
 for c in chains:
  flag=c.get(side+'_disabled')
  delay=c.get('withdraw_delayed') if side=='withdraw' else False
  if flag is False and delay is False:known.append('ENABLED')
  elif flag is True or delay is True:known.append('BLOCKED')
  else:known.append('UNKNOWN')
 if 'ENABLED' in known:return 'PUBLIC_ENABLED_SOME_NETWORK'
 if all(s=='BLOCKED' for s in known):return 'PUBLIC_BLOCKED_ALL_NETWORKS'
 return 'UNKNOWN'


def common_catalog(okx,gate,currencies):
 om={r['baseCcy']:r for r in okx if r.get('quoteCcy')=='USDT'}
 gm={r['base']:r for r in gate if r.get('quote')=='USDT'}
 cm={r['currency']:r for r in currencies}
 rows=[]
 for base in sorted(om.keys() & gm.keys()):
  o,g=om[base],gm[base];c=cm.get(base,{})
  reasons=[]
  if base in ['BTC','ETH']:reasons.append('USER_EXCLUDED_BTC_ETH')
  if o.get('state')!='live' or g.get('trade_status')!='tradable':reasons.append('MARKET_NOT_OPEN')
  if o.get('ruleType') not in [None,'normal'] or g.get('type') not in [None,'normal']:reasons.append('SPECIAL_MARKET')
  if re.search(r'(3L|3S|5L|5S)$',base):reasons.append('LEVERAGED_TOKEN')
  if g.get('st_tag') is True:reasons.append('GATE_ST_TAG')
  if c.get('delisted') is True or c.get('trade_disabled') is True:reasons.append('GATE_CURRENCY_RESTRICTED')
  rows.append(dict(base=base,symbol=base+'USDT',okx_id=o['instId'],gate_id=g['id'],
   gate_name=g.get('base_name',c.get('name')),okx_instrument=o,gate_pair=g,gate_currency=c,
   gate_deposit=network_status(c,'deposit'),gate_withdraw=network_status(c,'withdraw'),
   identity='UNKNOWN',okx_network_status='UNKNOWN',account_fees='UNKNOWN',route_eligibility='BLOCKED_UNKNOWN',
   excluded_reasons=reasons,depth_screen_enabled=not reasons))
 return rows


def order_rules(m):
 o,g=m['okx_instrument'],m['gate_pair']
 try:
  def zero(value):return '0' if value is None else str(value)
  return {'okx':dict(lot=o['lotSz'],min_qty=o['minSz'],min_quote='0',max_qty=o['maxMktSz'],max_quote=o['maxMktAmt']),
   'gate':dict(lot=str(D(10)**(-int(g['amount_precision']))),min_qty=zero(g['min_base_amount']),
       min_quote=zero(g['min_quote_amount']),max_qty=g.get('market_order_max_stock'),max_quote=g.get('market_order_max_money'))}
 except (KeyError,ValueError,TypeError):return {}


class Capture:
 def __init__(self,out,port):
  self.out,self.port=out,port;self.lock=threading.Lock();self.seq=0
  self.stream=gzip.open(out/'public-responses.jsonl.gz','wt')
  self.pacing={v:threading.Lock() for v in ['okx','gate']};self.last={v:0 for v in self.pacing}
 def get(self,venue,url):
  with self.pacing[venue]:
   wait=.16-(time.monotonic()-self.last[venue])
   if wait>0:time.sleep(wait)
   self.last[venue]=time.monotonic()
  row=dict(venue=venue,url=url,requested_ms=time.time()*1000)
  try:
   response=requests.get(url,proxies={'https':f'http://127.0.0.1:{self.port}'} if self.port else {},timeout=12)
   row.update(received_ms=time.time()*1000,received_mono=time.monotonic(),http_status=response.status_code)
   response.raise_for_status();row['response']=response.json()
   if venue=='okx' and row['response'].get('code')!='0':raise ValueError('public API rejected')
  except Exception as exc:
   row.update(error=type(exc).__name__,received_ms=time.time()*1000,received_mono=time.monotonic())
  with self.lock:
   self.seq+=1;row['capture_ref']=self.seq
   self.stream.write(json.dumps(row,separators=(',',':'))+'\n');self.stream.flush()
  return row
 def close(self):self.stream.close()


def view(row,venue):
 if 'error' in row:raise ValueError('HTTP_ERROR')
 d=row['response']['data'][0] if venue=='okx' else row['response']
 bids,asks=levels(d['bids']),levels(d['asks'])
 bids={p:q for p,q in bids.items() if q>0};asks={p:q for p,q in asks.items() if q>0}
 ts=int(d['ts']) if venue=='okx' else int(d['update'])
 current=ts if venue=='okx' else int(d['current'])
 return dict(valid=bool(bids and asks and max(bids)<min(asks)),bids=sorted(bids.items(),reverse=True),
  asks=sorted(asks.items()),ts=ts,generation_ms=current,received=row['received_mono'])


def depth_pair(capture,market,phase):
 urls={'okx':'https://www.okx.com/api/v5/market/books?instId='+market['okx_id']+'&sz=100',
       'gate':'https://api.gateio.ws/api/v4/spot/order_book?currency_pair='+market['gate_id']+'&limit=100&with_id=true'}
 with ThreadPoolExecutor(max_workers=2) as pool:
  futures={v:pool.submit(capture.get,v,u) for v,u in urls.items()};raw={v:f.result() for v,f in futures.items()}
 now,mono=time.time()*1000,time.monotonic();rules=order_rules(market)
 out=dict(symbol=market['symbol'],phase=phase,observed_ms=now,mono=mono,
  refs={v:r['capture_ref'] for v,r in raw.items()},results=[])
 try:books={v:view(r,v) for v,r in raw.items()}
 except (ValueError,KeyError,IndexError,TypeError) as exc:
  out['error']=type(exc).__name__;out['quality']='INVALID_RESPONSE';return out
 # Conservative last-change check for Gate, plus response-generation freshness.
 out['timestamps']={v:{'exchange_book_ms':b['ts'],'exchange_generation_ms':b['generation_ms'],
   'received_ms':raw[v]['received_ms']} for v,b in books.items()}
 response_fresh=all(-250<=now-b['generation_ms']<=2000 for b in books.values())
 q=validate_books(books['okx'],books['gate'],now,mono)
 out['quality']=q['status'] if response_fresh else 'STALE_RESPONSE'
 out['strict_quality']=validate_books(books['okx'],books['gate'],now,mono,500,100)['status'] if response_fresh else 'STALE_RESPONSE'
 if books['okx']['valid'] and books['gate']['valid']:
  out['raw_top_gross_bps']={buy+'>'+sale:str((books[sale]['bids'][0][0]/books[buy]['asks'][0][0]-1)*10000) for buy,sale in [('okx','gate'),('gate','okx')]}
 for buy,sale in [('okx','gate'),('gate','okx')]:
  for scenario,fees in SCENARIOS.items():
   for amount in AMOUNTS:
    rulepair={k:rules.get(v) for k,v in [('buy',buy),('sell',sale)]}
    r=evaluate(books[buy],books[sale],D(amount),D(fees[buy]),D(fees[sale]),D(5),now,mono,order_rules=rulepair) if response_fresh else {'status':'STALE_RESPONSE'}
    r.update(buy=buy,sell=sale,amount_usdt=amount,scenario=scenario,
      identity='UNKNOWN',route_eligibility='BLOCKED_UNKNOWN',actual_all_in_profit='UNKNOWN',executable=False)
    if r['status']=='ESTIMATE_ONLY':
     r['headroom_after_target_0_5_usdt']=str(D(r['net_usdt'])-D('.5'))
     r['headroom_after_target_1_usdt']=str(D(r['net_usdt'])-1)
     # Both venues need prepositioned assets. Use observed replacement value, not free inventory.
     r['capital_with_200_usdt_reserve']=str(D(r['buy_cost_usdt'])+(D(r['buy_cost_usdt'])+D(r['gross_usdt']))+D(r['fees_usdt'])+200)
     r['within_2000_budget']=D(r['capital_with_200_usdt_reserve'])<=2000
    out['results'].append(r)
 return out


def needs_recheck(pair):
 # Include positive gross leads even when quality failed; never reclassify invalid as profit.
 return any(D(x)>0 for x in pair.get('raw_top_gross_bps',{}).values()) or pair.get('quality')=='INVALID_RESPONSE'


def summarize(catalog,pairs):
 group=defaultdict(list)
 for p in pairs:group[p['symbol']].append(p)
 summary=[]
 for m in catalog:
  ps=group[m['symbol']]
  item={k:m[k] for k in ['symbol','base','gate_name','gate_deposit','gate_withdraw','excluded_reasons','route_eligibility']}
  item.update(depth_checks=len(ps),quality_counts=dict(Counter(p['quality'] for p in ps)),directions=[])
  for buy,sale in [('okx','gate'),('gate','okx')]:
   scenarios=[]
   for amount in AMOUNTS:
    rows=[r for p in ps for r in p['results'] if r['buy']==buy and r['sell']==sale and r['amount_usdt']==amount and r['scenario']=='higher_gate']
    valid=[r for r in rows if r['status']=='ESTIMATE_ONLY' and r['within_2000_budget']]
    vals=[D(r['net_usdt']) for r in valid]
    scenarios.append(dict(amount_usdt=amount,valid=len(valid),observations=len(ps),
      quality_valid_over_budget=sum(r['status']=='ESTIMATE_ONLY' and not r['within_2000_budget'] for r in rows),
      positive=sum(x>0 for x in vals),above_0_5=sum(x>=D('.5') for x in vals),above_1=sum(x>=1 for x in vals),
      min_net=str(min(vals)) if vals else None,max_net=str(max(vals)) if vals else None,
      median_net=str(median(vals)) if vals else None,
      repeated_margin_0_5=len(vals)>=3 and sum(x>=D('.5') for x in vals)>=.8*len(ps),
      best_headroom_after_target_0_5=str(max(vals)-D('.5')) if vals else None,
      max_capital_with_reserve=str(max(D(r['capital_with_200_usdt_reserve']) for r in valid)) if valid else None))
   item['directions'].append(dict(buy=buy,sell=sale,amounts=scenarios))
  best=max((D(x['max_net']) for d in item['directions'] for x in d['amounts'] if x['max_net'] is not None),default=D('-Infinity'))
  item['best_assumed_net']=str(best) if best.is_finite() else None
  amounts=[a for d in item['directions'] for a in d['amounts']]
  repeated=[a for a in amounts if a['repeated_margin_0_5']]
  item['research_signal']='REPEATED_ASSUMED_MARGIN' if repeated else ('ISOLATED_ASSUMED_MARGIN' if best>=D('.5') else ('NO_VALID_ESTIMATE' if best==D('-Infinity') else 'BELOW_RESEARCH_THRESHOLD'))
  item['priority_median_net']=str(max(D(a['median_net']) for a in repeated)) if repeated else None
  summary.append(item)
 summary.sort(key=lambda m:(m['research_signal']=='REPEATED_ASSUMED_MARGIN',D(m['priority_median_net'] or m['best_assumed_net'] or '-Infinity')),reverse=True)
 return summary


def main():
 parser=argparse.ArgumentParser();parser.add_argument('--proxy-port',type=int,default=7890)
 parser.add_argument('--recheck-rounds',type=int,default=5)
 args=parser.parse_args()
 if not 1<=args.recheck_rounds<=10:parser.error('rechecks 1..10')
 root=Path(__file__).resolve().parent;out=root/'research'/('market-screen-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ'));out.mkdir(parents=True)
 config=dict(started_ms=time.time()*1000,amounts_usdt=AMOUNTS,total_capital_usdt='2000',reserve_scenario_usdt='200',
  fee_scenarios=SCENARIOS,buffer_bps='5',fee_basis='ASSUMPTIONS_NOT_ACCOUNT_RATES_OR_UPPER_BOUNDS',
   cost_targets_usdt=['0.5','1'],identity_and_routes='UNKNOWN_BLOCKS_EXECUTION',recheck_rounds=args.recheck_rounds,
  repeated_margin_rule='At least 3 valid in-budget observations and >=80% of all observations above 0.5 USDT in higher_gate scenario; research only',
  scope='All common exact-base-code USDT spot pairs; other quote assets, unit conversions and alias mapping out of scope',
  limitation='Sporadic REST samples, not continuous monitoring or simultaneous fill evidence. Gate last-change age filter can reject quiet but legitimate books.',
  sources=URLS)
 hashes={};source=out/'source';source.mkdir()
 for name in ['screen_markets.py','detector.py','test_screen_markets.py']:
  raw=(root/name).read_bytes();(source/name).write_bytes(raw);hashes[name]=hashlib.sha256(raw).hexdigest()
 config['source_sha256']=hashes;dump(out/'config.json',config)
 capture=Capture(out,args.proxy_port);pairs=[]
 print(json.dumps({'run_dir':str(out),'phase':'metadata'}),flush=True)
 try:
  with ThreadPoolExecutor(max_workers=3) as pool:
   fs={k:pool.submit(capture.get,'okx' if k.startswith('okx') else 'gate',url) for k,url in URLS.items()}
   meta={k:f.result() for k,f in fs.items()}
  if any('error' in x for x in meta.values()):raise RuntimeError('metadata request failed; see raw capture')
  catalog=common_catalog(meta['okx_instruments']['response']['data'],meta['gate_pairs']['response'],meta['gate_currencies']['response'])
  dump(out/'catalog.json',catalog);active=[m for m in catalog if m['depth_screen_enabled']]
  print(json.dumps({'phase':'all_common_depth','common_codes':len(catalog),'depth_targets':len(active),'excluded':len(catalog)-len(active)}),flush=True)
  with (out/'depth-observations.jsonl').open('x') as log:
   def round_for(markets,phase):
    batch=[]
    with ThreadPoolExecutor(max_workers=3) as pool:
     fs={pool.submit(depth_pair,capture,m,phase):m for m in markets}
     for n,f in enumerate(as_completed(fs),1):
      row=f.result();batch.append(row);pairs.append(row);log.write(json.dumps(row)+'\n');log.flush()
      if n%40==0:print(json.dumps({'phase':phase,'completed':n,'total':len(markets)}),flush=True)
    return batch
   first=round_for(active,'all_common_initial')
   # No fixed top-N: every positive raw lead, plus invalid HTTP responses, gets repeated checks.
   targets={p['symbol'] for p in first if needs_recheck(p)}
   selected=[m for m in active if m['symbol'] in targets]
   print(json.dumps({'phase':'repeat_depth','targets':len(selected)}),flush=True)
   for n in range(args.recheck_rounds):
    time.sleep(2);round_for(selected,'repeat_'+str(n+1))
    print(json.dumps({'phase':'repeat_depth','round_complete':n+1,'targets':len(selected)}),flush=True)
  summary=summarize(catalog,pairs)
  dump(out/'summary.json',dict(completed_ms=time.time()*1000,common_codes=len(catalog),depth_targets=len(active),
   pair_observations=len(pairs),quality_counts=dict(Counter(p['quality'] for p in pairs)),
   positive_research_symbols=[m['symbol'] for m in summary if m['research_signal'] in ['REPEATED_ASSUMED_MARGIN','ISOLATED_ASSUMED_MARGIN']],
   repeated_research_symbols=[m['symbol'] for m in summary if m['research_signal']=='REPEATED_ASSUMED_MARGIN'],
   verified_profitable_symbols=[],markets=summary))
  with (out/'all-common-markets.csv').open('w',newline='',encoding='utf-8-sig') as f:
   cols=['symbol','gate_name','excluded_reasons','depth_checks','quality_counts','gate_deposit','gate_withdraw','best_assumed_net','research_signal','route_eligibility']
   w=csv.DictWriter(f,fieldnames=cols);w.writeheader()
   for m in summary:w.writerow({k:json.dumps(m[k],ensure_ascii=False) if isinstance(m[k],(list,dict)) else m[k] for k in cols})
  print(json.dumps({'phase':'complete','run_dir':str(out),'research_candidates':[m['symbol'] for m in summary if m['research_signal'] in ['REPEATED_ASSUMED_MARGIN','ISOLATED_ASSUMED_MARGIN']],'verified_profitable':0}),flush=True)
 finally:
  capture.close()
  path=out/'public-responses.jsonl.gz';dump(out/'capture-manifest.json',dict(file=path.name,bytes=path.stat().st_size,sha256=hashlib.sha256(path.read_bytes()).hexdigest(),responses=capture.seq))
  (out/'README.md').write_text('本目录为本次全市场筛选的源码、配置、原始公开响应、观测、汇总和CSV证据，全部保留。所有正值均为假设费用下研究线索，账户费用、同一资产与充提回程未核验，没有任何实盘或模拟成交授权。现有audit_v2监控未修改。\n')


if __name__=='__main__':main()
