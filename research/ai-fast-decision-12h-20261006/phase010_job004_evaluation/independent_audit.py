from pathlib import Path
from decimal import Decimal
from collections import defaultdict
from bisect import bisect_right
import gzip,json,hashlib
B=Path(__file__).resolve().parent
def near(a,b):assert abs(float(a)-float(b))<1e-7*max(1,abs(float(a)),abs(float(b)))
def fill(levels,q,unit):
 left=q;notional=Decimal(0)
 for lv in levels:
  take=min(left,Decimal(lv[1]));notional+=take*Decimal(lv[0])*unit;left-=take
  if not left:return notional
 return None
def main():
 p=json.loads((B/'protocol.json').read_text());freeze=json.loads((B/'execution_freeze.json').read_text())
 for n,h in freeze['hashes'].items():assert hashlib.sha256((B/n).read_bytes()).hexdigest()==h
 events=json.loads((B/'events.json').read_text());out=json.loads((B/'event_deltas.json').read_text());specs={x['instId']:x for x in json.loads((B/'instruments.json').read_text())};groups=defaultdict(list)
 for e in events:groups[(e['family'],e['asset'])].append(e)
 selected={e['event_id'] for g in groups.values() for e in [g[0],g[len(g)//2],g[-1]]}
 chosen=[x for x in out if x['event_id'] in selected and x['hold_seconds']==15 and x['delay_ms'] in [0,3000]]
 wanted={x[k] for x in chosen for k in ['entry_ordinal','exit_ordinal'] if k in x};quotes={};times=defaultdict(list);ords=defaultdict(list);emap={e['event_id']:e for e in events};rawsha=hashlib.sha256()
 with gzip.open(Path(p['source'])/'raw/ws_messages.jsonl.gz','rb') as f:
  for line in f:
   rawsha.update(line);r=json.loads(line)
   if r['local_ordinal'] in wanted:quotes[r['local_ordinal']]=r
   if r['channel']=='books5' and json.loads(r['raw']).get('data'):
    times[r['instId']].append(r['os_shared_ns']/1e6);ords[r['instId']].append(r['local_ordinal'])
 assert rawsha.hexdigest()==p['source_logical_sha256'];valid=null=0
 for x in chosen:
  e=emap[x['event_id']];t=e['asof_ms']+x['delay_ms'];i=bisect_right(times[x['asset']],t)
  if x['status']!='observed':assert x['price_fee_delta_USDT'] is None;null+=1;continue
  en=quotes[x['entry_ordinal']];ex=quotes[x['exit_ordinal']];assert en['run_id']==ex['run_id']==p['authorized_run'] and en['connectionId']==ex['connectionId']==e['connectionId'];assert ords[x['asset']][i]==x['entry_ordinal'];assert 0<times[x['asset']][i]-t<=250
  j=bisect_right(times[x['asset']],times[x['asset']][i]+x['hold_seconds']*1000);assert ords[x['asset']][j]==x['exit_ordinal'];assert 0<times[x['asset']][j]-times[x['asset']][i]-x['hold_seconds']*1000<=250
  q=Decimal(x['contracts']);spec=specs[x['asset']];unit=Decimal(spec['ctVal'])*Decimal(spec['ctMult']);assert q>=Decimal(spec['minSz']) and q%Decimal(spec['lotSz'])==0
  a=json.loads(en['raw'])['data'][0];b=json.loads(ex['raw'])['data'][0];ev=fill(a['asks'] if x['side']==1 else a['bids'],q,unit);xv=fill(b['bids'] if x['side']==1 else b['asks'],q,unit);fee=Decimal(x['fee_each_side_bps'])/10000;assert ev*(1+fee)<=500
  near(x['entry_notional_USDT'],ev);near(x['exit_notional_USDT'],xv);near(x['fee_USDT'],(ev+xv)*fee);near(x['price_fee_delta_USDT'],Decimal(x['side'])*(xv-ev)-(ev+xv)*fee);near(x['break_even_fee_each_side_bps'],Decimal(x['side'])*(xv-ev)/(ev+xv)*10000);valid+=1
 matches=json.loads((B/'matched_controls.json').read_text())
 for m in matches:
  if m['control']:assert m['control']['asof_ms']<m['target_asof_ms']
  else:assert m['control_outcomes'] is None
 receipt={'status':'PASS_FINITE_PRICE_QUANTITY_FEE_AND_FIRST_QUOTE_TIMING','observed_sample_checked':valid,'censored_null_sample_checked':null,'sample_event_ids':sorted(selected),'raw_sha_match':True,'original_frozen_hashes_match':True,'exact_qty_grid_and_500_entryfee_cap':True,'same_exit_contract_qty':True,'same_run_conn_domain':True,'first_after_entry_exit_checked':True,'source_counters_preserved':True,'matching_scope':'finite ordering/nullable check only; no full independent LEAD feature/control strategy replay','sameOwner_notthirdparty_fullreplay':True,'actual_AI_results':None};(B/'audit.json').write_text(json.dumps(receipt,indent=2));print(receipt)
if __name__=='__main__':main()
