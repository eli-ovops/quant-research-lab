from pathlib import Path
from decimal import Decimal
import json,gzip,hashlib
B=Path(__file__).resolve().parent
def near(a,b):assert abs(float(a)-float(b))<1e-7*max(1,abs(float(a)),abs(float(b)))
p=json.loads((B/'protocol.json').read_text());f=json.loads((B/'execution_freeze.json').read_text())
for n,h in f['hashes'].items():assert hashlib.sha256((B/n).read_bytes()).hexdigest()==h
r=json.loads((B/'results.json').read_text());assert r['future_result'] is None
events=json.loads((B/'dev_events.json').read_text());out=json.loads((B/'dev_event_deltas.json').read_text());specs={x['instId']:x for x in json.loads((B/'instruments.json').read_text())};groups={}
for e in events:groups.setdefault((e['family'],e['asset']),[]).append(e)
selected={e['event_id'] for g in groups.values() for e in [g[0],g[len(g)//2],g[-1]]};chosen=[x for x in out if x['event_id'] in selected and x['delay_ms']==0 and x['hold_seconds']==15];ordinals={x[k] for x in chosen for k in ['entry_ordinal','exit_ordinal'] if k in x};quotes={}
with gzip.open(Path(p['dev_source'])/'raw/ws_messages.jsonl.gz','rb') as raw:
 for line in raw:
  row=json.loads(line)
  if row['local_ordinal'] in ordinals:quotes[row['local_ordinal']]=row
def fill(levels,q,unit):
 left=q;n=Decimal(0)
 for lv in levels:
  price,sz=Decimal(lv[0]),Decimal(lv[1]);take=min(left,sz);n+=take*price*unit;left-=take
  if left==0:return n
 return None
valid=zero=0
for x in chosen:
 if x['status']!='observed':assert x['price_fee_delta_USDT'] is None;zero+=1;continue
 en=quotes[x['entry_ordinal']];ex=quotes[x['exit_ordinal']];assert en['run_id']==ex['run_id'] and en['connectionId']==ex['connectionId'];q=Decimal(x['contracts']);unit=Decimal(specs[x['asset']]['ctVal'])*Decimal(specs[x['asset']]['ctMult']);a=json.loads(en['raw'])['data'][0];b=json.loads(ex['raw'])['data'][0];ev=fill(a['asks'] if x['side']==1 else a['bids'],q,unit);xv=fill(b['bids'] if x['side']==1 else b['asks'],q,unit);fee=Decimal(x['fee_each_side_bps'])/10000;assert ev*(1+fee)<=500;near(x['fee_USDT'],(ev+xv)*fee);near(x['price_fee_delta_USDT'],Decimal(x['side'])*(xv-ev)-(ev+xv)*fee);near(x['break_even_fee_each_side_bps'],Decimal(x['side'])*(xv-ev)/(ev+xv)*10000);valid+=1
m=json.loads((B/'dev_matched_controls.json').read_text());assert m==[] and not any(e['family']=='BTC_TRANSMISSION' for e in events)
a={'status':'PASS_FINITE_DEVELOPMENT_PRICE_FEE_AUDIT','observed_primary_sample_checked':valid,'censored_null_sample_checked':zero,'segments':r['development_segments'],'crossrun_fill_not_allowed':True,'real_association_controls':'NOT_VALIDATED no realdev LEAD events','matched_unmatched_zero_not_percent':True,'future_result':None,'AI_results':None,'sameOwner_notthirdparty_fullreplay':True};(B/'audit.json').write_text(json.dumps(a,indent=2));print(a)

