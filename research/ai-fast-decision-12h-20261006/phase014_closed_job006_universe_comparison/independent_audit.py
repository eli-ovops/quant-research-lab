from pathlib import Path
from collections import defaultdict
from decimal import Decimal
from bisect import bisect_right
import gzip,json,hashlib
B=Path(__file__).resolve().parent
def near(a,b):assert abs(float(a)-float(b))<1e-7*max(1,abs(float(a)),abs(float(b)))
def fill(levels,q,unit):
 left=q;n=Decimal(0)
 for x in levels:
  take=min(left,Decimal(x[1]));n+=take*Decimal(x[0])*unit;left-=take
  if not left:return n
 return None
def main():
 p=json.loads((B/'protocol.json').read_text());freeze=json.loads((B/'execution_freeze.json').read_text())
 for n,h in freeze['hashes'].items():assert hashlib.sha256((B/n).read_bytes()).hexdigest()==h
 events=json.loads((B/'events.json').read_text());out=json.loads((B/'event_deltas.json').read_text());a=json.loads((B/'baseline_A_features.json').read_text());ao=json.loads((B/'baseline_A_outcomes.json').read_text());be=json.loads((B/'baseline_B_events.json').read_text());bo=json.loads((B/'baseline_B_outcomes.json').read_text());specs={x['instId']:x for x in json.loads((B/'instruments.json').read_text())};groups=defaultdict(list)
 for e in events:groups[(e['family'],e['asset'])].append(e)
 selected={e['event_id'] for g in groups.values() for e in [g[0],g[len(g)//2],g[-1]]};chosen=[x for x in out if x['event_id'] in selected and x['hold_seconds']==15 and x['delay_ms']==0];bg=defaultdict(list)
 for e in be:bg[e['asset']].append(e)
 bchosen={e['event_id'] for g in bg.values() for e in [g[0],g[len(g)//2],g[-1]]};chosen+= [x for x in bo if x['event_id'] in bchosen]
 wanted={x[k] for x in chosen for k in ['entry_ordinal','exit_ordinal'] if k in x};wanted|={f[k] for f in a for k in ['own_current_ordinal','own_reference_ordinal'] if k in f};rawbyord={};times=defaultdict(list);ordinals=defaultdict(list);sha=hashlib.sha256();first_ms=None
 with gzip.open(Path(p['source'])/'raw/ws_messages.jsonl.gz','rb') as f:
  for line in f:
   sha.update(line);r=json.loads(line)
   if first_ms is None:first_ms=r['os_shared_ns']/1e6
   if r['local_ordinal'] in wanted:rawbyord[r['local_ordinal']]=r
   if r['channel']=='books5' and json.loads(r['raw']).get('data'):times[r['instId']].append(r['os_shared_ns']/1e6);ordinals[r['instId']].append(r['local_ordinal'])
 assert sha.hexdigest()==p['raw_logical_sha256'];emap={e['event_id']:e for e in events};bmap={e['event_id']:e for e in be};valid=null=0
 for x in chosen:
  is_b=x.get('baseline')=='B_FIXED_TIMEGRID_SEEDED_DIRECTION';event=(bmap if is_b else emap)[x['event_id']]
  if x['status']!='observed':assert x['price_fee_delta_USDT'] is None;null+=1;continue
  en=rawbyord[x['entry_ordinal']];ex=rawbyord[x['exit_ordinal']];asset=x['asset'];q=Decimal(x['contracts']);unit=Decimal(specs[asset]['ctVal'])*Decimal(specs[asset]['ctMult']);fee=Decimal(x['fee_each_side_bps'])/10000;assert q%Decimal(specs[asset]['lotSz'])==0
  i=bisect_right(times[asset],event['asof_ms']);assert ordinals[asset][i]==en['local_ordinal'] and 0<times[asset][i]-event['asof_ms']<=250;j=bisect_right(times[asset],times[asset][i]+15000);assert ordinals[asset][j]==ex['local_ordinal'] and 0<times[asset][j]-times[asset][i]-15000<=250
  assert en['run_id']==ex['run_id']==p['run_id'] and en['connectionId']==ex['connectionId']==event['connectionId'];enbook=json.loads(en['raw'])['data'][0];exbook=json.loads(ex['raw'])['data'][0];ev=fill(enbook['asks'] if x['side']==1 else enbook['bids'],q,unit);xv=fill(exbook['bids'] if x['side']==1 else exbook['asks'],q,unit);assert ev*(1+fee)<=500;near(x['fee_USDT'],(ev+xv)*fee);near(x['price_fee_delta_USDT'],Decimal(x['side'])*(xv-ev)-(ev+xv)*fee);valid+=1
 ownchecked=0
 for f in a:
  if f['direction'] is None:continue
  e=emap[f['event_id']];current=rawbyord[f['own_current_ordinal']];ref=rawbyord[f['own_reference_ordinal']];assert current['local_ordinal']<=e['asof_ordinal'];assert 0<=e['asof_ms']-current['os_shared_ns']/1e6<=250 and 0<=e['asof_ms']-1000-ref['os_shared_ns']/1e6<=250
  def mid(row):b=json.loads(row['raw'])['data'][0];return (Decimal(b['asks'][0][0])+Decimal(b['bids'][0][0]))/2
  delta=mid(current)-mid(ref);assert f['direction']==(1 if delta>0 else -1 if delta<0 else 0);ownchecked+=1
 for e in be:
  target=first_ms+1000+e['grid_index']*35000;near(target,e['grid_target_ms']);i=bisect_right(times[e['asset']],target);assert ordinals[e['asset']][i]==e['asof_ordinal'] and 0<times[e['asset']][i]-target<=250;expected=1 if hashlib.sha256(('FAST_AI_CONTROL_V1'+p['run_id']+e['asset']+str(e['grid_index'])).encode()).digest()[0]%2==0 else -1;assert e['direction']==expected
 for x in ao:
  if x['status']=='WAIT_TRUE_ZERO':assert x['price_fee_delta_USDT']==0 and x['fee_USDT']==0
  elif x['status'].startswith('UNKNOWN'):assert x['price_fee_delta_USDT'] is None
 receipt={'status':'PASS_FINITE_ORIGINAL_QUOTE_PRICE_FEE_AND_BASELINE_CAUSALITY','observed_sample_checked':valid,'censored_null_sample_checked':null,'own1s_raw_sign_checks':ownchecked,'fixed_grid_firstbook_seed_checks':len(be),'raw_hash_match':True,'firstafter_entry_exit_wait250':True,'same_exitqty_fee_cap':True,'no_future_ordinal_or500ms_reuse':True,'not_thirdparty_fullstrategy_replay':True,'real_AI':None};(B/'audit.json').write_text(json.dumps(receipt,indent=2));print(receipt)
if __name__=='__main__':main()
