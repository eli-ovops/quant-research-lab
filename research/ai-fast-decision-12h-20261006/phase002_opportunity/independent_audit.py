from pathlib import Path
import json,hashlib
from decimal import Decimal
B=Path(__file__).resolve().parent
def near(a,b):assert abs(float(a)-float(b))<1e-7*max(1,abs(float(a)),abs(float(b))),(a,b)
def fill(levels,qty,unit):
 left=qty;value=Decimal(0)
 for l in levels:
  p,q=Decimal(l[0]),Decimal(l[1]);take=q if q<left else left;value+=take*p*unit;left-=take
  if left==0:return value
 return None
proto=json.loads((B/'protocol.json').read_text());freeze=json.loads((B/'execution_freeze.json').read_text())
for n,h in freeze['hashes'].items():assert hashlib.sha256((B/n).read_bytes()).hexdigest()==h
raw=(B/'prefix.jsonl').read_bytes();assert hashlib.sha256(raw).hexdigest()==freeze['prefix_sha256'];rows=[json.loads(x) for x in raw.splitlines()];events=json.loads((B/'events.json').read_text());outcomes=json.loads((B/'event_price_fee_deltas.json').read_text());specs={x['instId']:x for x in json.loads((B/'instruments.json').read_text())};books={a:[] for a in specs};trades={a:[] for a in specs}
for r in rows:
 a=r['instId']
 if a not in specs:continue
 o=json.loads(r['raw']);t=r['monotonic_ns']/1e6
 for d in o.get('data',[]):
  if r['channel']=='books5' and d.get('asks') and d.get('bids') and Decimal(d['bids'][0][0])<Decimal(d['asks'][0][0]):books[a].append({'t':t,'ordinal':r['local_ordinal'],'conn':r['connectionId'],'raw':d,'mid':(Decimal(d['asks'][0][0])+Decimal(d['bids'][0][0]))/2})
  if r['channel']=='trades':trades[a].append({'t':t,'ordinal':r['local_ordinal'],'conn':r['connectionId'],'amount':Decimal(d['sz'])*Decimal(d['px'])*Decimal(specs[a]['ctVal'])*Decimal(specs[a]['ctMult']),'side':1 if d['side']=='buy' else -1})
accepted={};eventmap={e['event_id']:e for e in events}
for e in events:
 a=e['asset'];now=e['asof_ms'];before=[b for b in books[a] if b['ordinal']<=e['asof_ordinal'] and b['conn']==e['connectionId']];latest=before[-1];reference=[b for b in before if b['t']<=now-1000][-1];flows=[f for f in trades[a] if f['ordinal']<=e['asof_ordinal'] and now-1000<f['t']<=now and f['conn']==e['connectionId']]
 net=sum(f['amount']*f['side'] for f in flows);total=sum(f['amount'] for f in flows);imb=net/total;imp=(latest['mid']/reference['mid']-1)*10000
 near(e['imbalance'],imb);near(e['impulse_bps'],imp);near(e['flow_total_USDT'],total);near(e['flow_net_USDT'],net);assert abs(imb)>=Decimal('.8') and abs(imp)>=3 and imb*imp>0;assert 0<=now-latest['t']<=250;assert min(f['t'] for f in trades[a])<=now-1000;assert now-accepted.get(a,-1e99)>=35000;accepted[a]=now
 assert latest['ordinal']==e['latest_book_ordinal'] and reference['ordinal']==e['reference_book_ordinal']
observed=censored=0
for r in outcomes:
 e=eventmap[r['event_id']];a=e['asset'];available=[b for b in books[a] if b['conn']==e['connectionId'] and b['t']>e['asof_ms']+r['delay_ms']]
 if r['status']!='observed':assert r['price_fee_delta_USDT'] is None;censored+=1;continue
 entry=available[0];exit=[b for b in books[a] if b['conn']==e['connectionId'] and b['t']>entry['t']+r['hold_seconds']*1000][0];assert r['entry_ordinal']==entry['ordinal'] and r['exit_ordinal']==exit['ordinal'];unit=Decimal(specs[a]['ctVal'])*Decimal(specs[a]['ctMult']);q=Decimal(r['contracts']);step=Decimal(specs[a]['lotSz']);assert q>=Decimal(specs[a]['minSz']) and q%step==0
 side=r['side'];en=fill(entry['raw']['asks'] if side==1 else entry['raw']['bids'],q,unit);ex=fill(exit['raw']['bids'] if side==1 else exit['raw']['asks'],q,unit);assert en is not None and ex is not None;fee=Decimal(r['fee_each_side_bps'])/10000;assert en*(1+fee)<=500
 nxt=fill(entry['raw']['asks'] if side==1 else entry['raw']['bids'],q+step,unit);assert nxt is None or nxt*(1+fee)>500
 gross=Decimal(side)*(ex-en);fees=(en+ex)*fee;near(r['entry_notional_USDT'],en);near(r['exit_notional_USDT'],ex);near(r['fee_USDT'],fees);near(r['price_fee_delta_USDT'],gross-fees);near(r['underlying_quantity'],q*unit);observed+=1
result={'status':'PASS','scope':'sameOwner different implementation accepted-feature/strictfirstquote/Decimalquantity/depth/twolegfee_delta audit; notfullstrategy independently duplicated','events_checked':len(events),'observed_outcomes_checked':observed,'censored_null_checked':censored,'cash_delta_not_account_PnL':True,'model_calls':0};(B/'audit.json').write_text(json.dumps(result,indent=2));print(result)

