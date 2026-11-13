from pathlib import Path
from decimal import Decimal as D,ROUND_CEILING
from collections import defaultdict
import json,csv,hashlib,datetime,gzip,io
P=Path(__file__).resolve().parents[2]/'trend'/'resume_20260926';O=P.parent;OUT=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
get=lambda n:json.loads((P/n).read_text())
counts={}
for label,rows in [('source',get('sources.json')),('manifest',get('manifest.json')['files']),('original',get('resume_record.json')['original_files'])]:
 assert all(sha(Path(r['path']))==r['sha256'] for r in rows),label
 counts[label]=len(rows)
seal=get('seal.json')
for n,k in [('analyze.py','analysis_sha256'),('validate.py','validator_sha256'),('protocol.json','protocol_sha256'),('sources.json','sources_sha256'),('results_preseal.json','preseal_results_sha256'),('benchmark_calibration.json','benchmark_calibration_sha256')]:assert sha(P/n)==seal[k],n
bars={};overlap=0;new=0
for c in ['BTC','ETH']:
 d={}
 for base in [O,P]:
  for f in sorted((base/'raw').glob(c+'_daily_*.txt')):
   obj=json.loads(f.read_text());assert obj['code']=='0'
   for r in obj['data']:
    t=int(r[0]);assert r[-1]=='1' and t%86400000==0
    if t in d:assert r==d[t];overlap+=1
    else:d[t]=r
    if base==P:new+=1
 stamps=sorted(d);assert all(b-a==86400000 for a,b in zip(stamps,stamps[1:]));bars[c]=d
 for a,b in get('protocol.json')['periods'].values():
  ms=lambda s:int(datetime.datetime.fromisoformat(s).replace(tzinfo=datetime.timezone.utc).timestamp()*1000)
  assert all(t in d for t in range(ms(a)-40*86400000,ms(b)+86400000,86400000))
identity={}
for c in ['BTC','ETH']:
 with gzip.open(P/'raw'/f'identity_{c}_20200101.bin','rt') as f:rows=list(csv.DictReader(f))
 assert all(r['exchange']=='okex' and r['symbol']==c+'-USDT' for r in rows)
 prices=[D(r['price']) for r in rows];ohlc=[prices[0],max(prices),min(prices),prices[-1]]
 assert ohlc==list(map(D,bars[c][1577836800000][1:5]))
 identity[c]={'trades':len(rows),'OHLC':list(map(str,ohlc))}
F=list(csv.DictReader((P/'fills_all.csv').open()));E=list(csv.DictReader((P/'equity_all.csv').open()));T=list(csv.DictReader((P/'trades_all.csv').open()));results=get('results_all.json')['scenarios'];checked=[]
for r in results:
 key=(r['period'],r['variant']);same=lambda x:(x['period'],x['variant'])==key
 fills=list(filter(same,F));eq=list(filter(same,E));trades=list(filter(same,T));cash=D(2000);inv={'BTC':D(0),'ETH':D(0)};dust=inv.copy();byday=defaultdict(list)
 for f in fills:byday[f['date']].append(f)
 fee=D('.002') if key[1]=='fee2' else D('.003') if key[1]=='severe' else D('.001');peak=D(2000);dd=D(0)
 for e in eq:
  for f in byday[e['date']]:
   c=f['coin'];q=D(f['gross_qty']);px=D(f['price'])
   if f['side']=='buy':
    basefee=(q*fee/D('1e-8')).to_integral_value(rounding=ROUND_CEILING)*D('1e-8');assert basefee==D(f['base_fee']);cash-=q*px;inv[c]+=q-basefee
   else:
    charge=(q*px*fee/D('1e-8')).to_integral_value(rounding=ROUND_CEILING)*D('1e-8');assert charge==D(f['quote_fee']);cash+=q*px-charge;dust[c]+=inv[c]-q;inv[c]=D(0)
   assert cash==D(f['cash_after'])
  assert cash==D(e['cash'])
  for c in inv:assert inv[c]==D(e[c+'_qty']) and dust[c]==D(e[c+'_dust'])
  v=D(e['valuation_equity']);peak=max(peak,v);dd=max(dd,1-v/peak)
 assert all(v==0 for v in inv.values());pnl=cash-D(2000)
 assert abs(pnl-D(str(r['net_pnl'])))<D('1e-9') and abs(dd-D(str(r['max_drawdown'])))<D('1e-12')
 assert sum((D(t['proceeds'])-D(t['cost']) for t in trades),D(0))==pnl
 assert sum((D(t['price_pnl'])-D(t['fees'])-D(t['slippage_and_tick'])-D(t['dust_writeoff']) for t in trades),D(0))==pnl
 checked.append({'period':key[0],'variant':key[1],'net':str(pnl),'drawdown':str(dd),'fills':len(fills),'days':len(eq)})
assert len(checked)==27
out={'hashes_verified':counts,'seal_hashes_verified':6,'bars':{c:len(d) for c,d in bars.items()},'new_rows':new,'overlap_identical9fields':overlap,'all_periods_with_warmup_complete':True,'identity_trade_capture':identity,'cash_inventory_daily_checks':len(E),'scenarios':checked,'no_strategy_rerun':True,'no_C_writes':True}
(OUT/'trend_resume_checks.json').write_text(json.dumps(out,indent=2));print(json.dumps({k:v for k,v in out.items() if k!='scenarios'},indent=2));print('reserved main',[r for r in checked if r['period']=='sealed_exploratory' and r['variant']=='main'])
