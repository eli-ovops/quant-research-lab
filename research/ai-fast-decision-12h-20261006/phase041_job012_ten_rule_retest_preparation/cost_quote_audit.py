from pathlib import Path
from fractions import Fraction as F
from bisect import bisect_right
import json,gzip,hashlib,math,importlib.util
P=Path(__file__).resolve().parent
module=importlib.util.spec_from_file_location('arithmetic',P/'pressure_fixed/event_quote_audit.py');arith=importlib.util.module_from_spec(module);module.loader.exec_module(arith)
def main():
 p=json.loads((P/'protocol.json').read_text());events=json.loads((P/'eight_fixed/costshock_events.json').read_text());out=json.loads((P/'eight_fixed/costshock_price_fee_deltas.json').read_text());spec={s['instId']:s for s in json.loads((P/'eight_fixed/instruments.json').read_text())};books={a:[] for a in spec};digest=hashlib.sha256()
 with gzip.open(Path(p['source'])/'raw/ws_messages.jsonl.gz','rb') as f:
  for line in f:
   digest.update(line);r=json.loads(line)
   if r['channel']!='books5' or r['instId'] not in spec:continue
   raw=json.loads(r['raw'])
   for b in raw.get('data',[]):books[r['instId']].append({'ns':r['os_shared_ns'],'ordinal':r['local_ordinal'],'conn':r['connectionId'],'asks':[(F(z[0]),F(z[1])) for z in b['asks']],'bids':[(F(z[0]),F(z[1])) for z in b['bids']]})
 assert digest.hexdigest()==p['sourcehash_terminal_pending'];checks=[]
 for r in out:
  e=next(e for e in events if e['event_id']==r['event_id']);bs=books[r['asset']];ts=[b['ns'] for b in bs];target=e['source_asof_shared_ns']+r['delay_ms']*1000000;idx=bisect_right(ts,target)
  if idx>=len(bs):assert r['status']=='censored';checks.append({'status':'UNKNOWN_NO_ENTRY'});continue
  entry=bs[idx];exit_target=entry['ns']+r['hold_seconds']*1000000000;j=bisect_right(ts,exit_target)
  if j>=len(bs):assert r['status']=='censored';checks.append({'status':'UNKNOWN_NO_EXIT'});continue
  exit=bs[j];assert entry['conn']==exit['conn']==e['connectionId'];reason='expired_entry_quote' if entry['ns']-target>250000000 else 'expired_exit_quote' if exit['ns']-exit_target>250000000 else None
  if reason:
   assert r['status']=='censored' and r['reason']==reason and r['price_fee_delta_USDT'] is None;checks.append({'status':'UNKNOWN','reason':reason});continue
  sp=spec[r['asset']];unit=F(sp['ctVal'])*F(sp['ctMult']);side=e['direction']*(1 if r['action']=='FOLLOW' else -1);fee=F(r['fee_each_side_bps'],10000);entrylevels=entry['asks'] if side==1 else entry['bids'];exitlevels=exit['bids'] if side==1 else exit['asks'];q=arith.size(entrylevels,unit,F(sp['lotSz']),F(sp['minSz']),fee)
  E=arith.notional(entrylevels,q,unit);X=arith.notional(exitlevels,q,unit)
  assert q is not None and X is not None and E*(1+fee)<=500 and F(r['contracts'])==q and r['entry_ordinal']==entry['ordinal'] and r['exit_ordinal']==exit['ordinal']
  gross=side*(X-E);fees=(X+E)*fee;net=gross-fees
  for key,value in [('entry_notional_USDT',E),('exit_notional_USDT',X),('gross_price_delta_USDT',gross),('fee_USDT',fees),('price_fee_delta_USDT',net)]:assert math.isclose(r[key],float(value),rel_tol=1e-12,abs_tol=1e-10)
  checks.append({'status':'observed','asset':r['asset'],'action':r['action'],'fee':r['fee_each_side_bps'],'delay':r['delay_ms'],'hold':r['hold_seconds'],'entry_ordinal':entry['ordinal'],'exit_ordinal':exit['ordinal'],'contracts_exact':str(q),'net_exact':str(net)})
 (P/'cost_event_quote_audit.json').write_text(json.dumps({'status':'PASS_FINITE_COST_EVENT_ORIGINAL_QUOTE_QTY_FEE','events':len(events),'conditions':len(checks),'observed':sum(r['status']=='observed' for r in checks),'unknown':sum(r['status']!='observed' for r in checks),'checks':checks,'sameOwner_finite_notthirdparty_fullstrategy':True,'actual_orders_orprovider':False},indent=2)+'\n');print(len(checks))
if __name__=='__main__':main()
