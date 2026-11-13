"""Public-only research universe; ticker scores are not executable profits."""
import json, time, statistics, re
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import requests

URLS = {
 'okx_instruments':'https://www.okx.com/api/v5/public/instruments?instType=SPOT',
 'gate_pairs':'https://api.gateio.ws/api/v4/spot/currency_pairs',
 'gate_currencies':'https://api.gateio.ws/api/v4/spot/currencies',
 'okx_tickers':'https://www.okx.com/api/v5/market/tickers?instType=SPOT',
 'gate_tickers':'https://api.gateio.ws/api/v4/spot/tickers'}

def fetch(key, port):
 r=requests.get(URLS[key],proxies={'https':f'http://127.0.0.1:{port}'} if port else {},timeout=20)
 r.raise_for_status();d=r.json()
 if isinstance(d,dict):
  if d.get('code')!='0':raise ValueError('public API rejected')
  return d['data']
 return d

def common_markets(okx,gate,currencies):
 om={r['baseCcy']:r for r in okx if r['quoteCcy']=='USDT' and r['state']=='live' and r.get('ruleType','normal')=='normal'}
 cm={r['currency']:r for r in currencies}
 result={};excluded={}
 for r in gate:
  base=r['base']
  if r['quote']!='USDT' or base not in om:continue
  reason=None;c=cm.get(base)
  if base in ['BTC','ETH']:reason='user excluded'
  elif r.get('trade_status')!='tradable' or r.get('type','normal')!='normal' or r.get('st_tag'):reason='market restricted'
  elif re.search(r'(3L|3S|5L|5S)$',base):reason='leveraged token'
  elif not c or any(c.get(k,False) for k in ['delisted','trade_disabled','deposit_disabled','withdraw_disabled','withdraw_delayed']):reason='Gate transfer unavailable or unknown'
  if reason:excluded[base]=reason;continue
  result[base+'USDT']={'base':base,'gate_id':r['id'],'okx_id':om[base]['instId'],
    'gate_fee_bps':str(max(10,float(r.get('fee') or '0.2')*100)), 'okx_fee_bps':'10',
    'gate_name':r.get('base_name',c.get('name')),'identity_verified':False,
    'okx_transfer_status':'UNKNOWN','account_fee_verified':False}
 return result,excluded

def scan(port=7890,rounds=5,count=50):
 with ThreadPoolExecutor(max_workers=3) as ex:
  futures={k:ex.submit(fetch,k,port) for k in ['okx_instruments','gate_pairs','gate_currencies']}
  data={k:f.result() for k,f in futures.items()}
 markets,excluded=common_markets(data['okx_instruments'],data['gate_pairs'],data['gate_currencies'])
 scores={s:[] for s in markets};quarantine=set()
 for n in range(rounds):
  with ThreadPoolExecutor(max_workers=2) as ex:
   a=ex.submit(fetch,'okx_tickers',port);b=ex.submit(fetch,'gate_tickers',port)
   ot={r['instId']:r for r in a.result()};gt={r['currency_pair']:r for r in b.result()}
  for sym,m in markets.items():
   try:
    o=ot[m['okx_id']];g=gt[m['gate_id']]
    ob,oa,gb,ga=map(float,[o['bidPx'],o['askPx'],g['highest_bid'],g['lowest_ask']])
    if min(ob,oa,gb,ga)<=0 or ob>=oa or gb>=ga:continue
    if abs(time.time()*1000-int(o['ts']))>5000:continue
    if max(oa/ga,ga/oa)>1.05:quarantine.add(sym);continue
    gross=max(gb/oa-1,ob/ga-1)*10000
    scores[sym].append(gross-float(m['okx_fee_bps'])-float(m['gate_fee_bps'])-5)
   except (KeyError,ValueError,ZeroDivisionError):continue
  if n+1<rounds:time.sleep(2)
 ranked=[]
 for sym,vals in scores.items():
  if sym in quarantine or len(vals)<max(1,rounds-1):continue
  ranked.append(dict(symbol=sym,**markets[sym],screen_samples=len(vals),
   screen_positive=sum(v>0 for v in vals),screen_median_net_bps=statistics.median(vals),screen_peak_net_bps=max(vals)))
 ranked.sort(key=lambda r:(r['screen_positive'],r['screen_median_net_bps'],r['screen_peak_net_bps']),reverse=True)
 if not ranked:raise ValueError('no research candidates')
 return dict(updated_ms=time.time()*1000,common_eligible=len(markets),ranked_count=len(ranked),
  excluded=excluded,quarantined=sorted(quarantine),selected=ranked[:count],ranking=ranked,
  method='Repeated best bid/ask cost screen, no market-cap ranking. Depth checked by monitor. Identity, OKX transfer status and new account fees unverified; all research-only.',
  source_urls=URLS)

def save_scan(root,port=7890,rounds=5):
 result=scan(port,rounds);root=Path(root);root.mkdir(exist_ok=True)
 archive=root/('universe-'+str(int(result['updated_ms']))+'.json')
 archive.write_text(json.dumps(result,ensure_ascii=False,indent=2))
 tmp=root/'universe.tmp';tmp.write_text(json.dumps(result,ensure_ascii=False,indent=2));tmp.replace(root/'universe.json')
 return result

if __name__=='__main__':
 r=save_scan(Path(__file__).parent/'monitor');print(json.dumps({'eligible':r['common_eligible'],'selected':[m['symbol'] for m in r['selected']]},ensure_ascii=False))
