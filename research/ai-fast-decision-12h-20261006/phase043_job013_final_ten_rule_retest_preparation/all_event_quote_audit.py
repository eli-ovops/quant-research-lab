from pathlib import Path
from fractions import Fraction as F
from bisect import bisect_right
import gzip,json,hashlib,math
P=Path(__file__).resolve().parent
def size(levels,unit,step,minimum,fee):
 left=F(500)/(1+fee);qty=F(0)
 for px,available in levels:
  take=min(available,left/(px*unit));qty+=take;left-=take*px*unit
  if left==0:break
 if left>0:return None
 qty=(qty//step)*step
 return qty if qty>=minimum else None
def notional(levels,qty,unit):
 left=qty;cash=F(0)
 for price,available in levels:
  take=min(left,available);cash+=take*price*unit;left-=take
  if left==0:return cash
 return None
def main():
 p=json.loads((P/'protocol.json').read_text());spec={s['instId']:s for s in json.loads((P/'eight_fixed/instruments.json').read_text())};books={a:[] for a in spec};h=hashlib.sha256()
 with gzip.open(Path(p['source'])/'raw/ws_messages.jsonl.gz','rb') as stream:
  for line in stream:
   h.update(line);r=json.loads(line)
   if r['channel']!='books5' or r['instId'] not in spec:continue
   for d in json.loads(r['raw']).get('data',[]):
    asks=[(F(z[0]),F(z[1])) for z in d['asks']];bids=[(F(z[0]),F(z[1])) for z in d['bids']]
    assert asks and bids and asks[0][0]>bids[0][0] and all(px>0 and q>0 for px,q in asks+bids)
    books[r['instId']].append({'ns':r['os_shared_ns'],'ordinal':r['local_ordinal'],'conn':r['connectionId'],'asks':asks,'bids':bids})
 assert h.hexdigest()==p['sourcehash_terminal_pending'];result={}
 for family,evfile,outfile in [('cost','eight_fixed/costshock_events.json','eight_fixed/costshock_price_fee_deltas.json'),('pressure','pressure_fixed/pressure_events.json','pressure_fixed/pressure_shadow_outcomes.json')]:
  if not (P/evfile).exists() or not (P/outfile).exists():
   result[family]={'events':None,'conditions':None,'observed':None,'unknown':None,'scope':'NOT_AVAILABLE_RUNTIME_PENDING_OR_INCOMPLETE','checks':[]};continue
  events=json.loads((P/evfile).read_text());out=json.loads((P/outfile).read_text());emap={e['event_id']:e for e in events};checks=[]
  for r in out:
   e=emap[r['event_id']];a=r['asset'];sp=spec[a];unit=F(sp['ctVal'])*F(sp['ctMult']);step=F(sp['lotSz']);fee=F(r['fee_each_side_bps'],10000);side=e['direction']*(1 if r['action']=='FOLLOW' else -1);bs=books[a];times=[b['ns'] for b in bs];target=e['source_asof_shared_ns']+r['delay_ms']*1000000;i=bisect_right(times,target);reason=None;entry=exit=None;qty=E=X=None
   if i>=len(bs):reason='no_postdecision_book'
   else:
    entry=bs[i]
    if entry['ns']-target>250000000:reason='expired_entry_quote'
    else:
     levels=entry['asks'] if side==1 else entry['bids'];qty=size(levels,unit,step,F(sp['minSz']),fee)
     if qty is None:reason='minlot_or_entrydepth'
     else:
      E=notional(levels,qty,unit)
      if E is None:reason='entry_depth'
      else:
       xtarget=entry['ns']+r['hold_seconds']*1000000000;j=bisect_right(times,xtarget)
       if j>=len(bs):reason='no_posthold_book'
       else:
        exit=bs[j]
        if exit['ns']-xtarget>250000000:reason='expired_exit_quote'
        else:
         X=notional(exit['bids'] if side==1 else exit['asks'],qty,unit)
         if X is None:reason='exit_depth'
   if reason:
    assert r['status']=='censored' and r['reason']==reason and r['price_fee_delta_USDT'] is None,(family,r,reason);checks.append({'event_id':r['event_id'],'status':'UNKNOWN','reason':reason,'action':r['action'],'fee':r['fee_each_side_bps'],'delay':r['delay_ms'],'hold':r['hold_seconds']});continue
   assert entry['conn']==exit['conn']==e['connectionId'] and r['status']=='observed' and F(r['contracts'])==qty and r['entry_ordinal']==entry['ordinal'] and r['exit_ordinal']==exit['ordinal'] and E*(1+fee)<=500
   nextcash=notional(entry['asks'] if side==1 else entry['bids'],qty+step,unit);assert nextcash is None or nextcash*(1+fee)>500
   gross=side*(X-E);fees=(X+E)*fee;net=gross-fees
   for key,value in [('entry_notional_USDT',E),('exit_notional_USDT',X),('fee_USDT',fees),('gross_price_delta_USDT',gross),('price_fee_delta_USDT',net)]:assert math.isclose(r[key],float(value),rel_tol=1e-12,abs_tol=1e-10)
   checks.append({'event_id':r['event_id'],'status':'observed','asset':a,'action':r['action'],'fee':r['fee_each_side_bps'],'delay':r['delay_ms'],'hold':r['hold_seconds'],'qty':str(qty),'net_exact':str(net),'entry_ordinal':entry['ordinal'],'exit_ordinal':exit['ordinal'],'nextlot_rejected':True})
  result[family]={'events':len(events),'conditions':len(out),'observed':sum(r['status']=='observed' for r in checks),'unknown':sum(r['status']!='observed' for r in checks),'scope':'REAL_QUOTE_FINITE' if out else 'NOT_APPLICABLE_NO_REAL_EVENTS','checks':checks}
 (P/'all_event_quote_audit.json').write_text(json.dumps({'status':'PASS_FINITE_ALL_NEW_EVENT_QUOTE_QTY_FEE_AND_CENSOR_REASONS','sourcehash':h.hexdigest(),'families':result,'sameOwner_notthirdparty_fullstrategy':True,'real_API_order':False},indent=2)+'\n');print({k:{x:y for x,y in v.items() if x!='checks'} for k,v in result.items()})
if __name__=='__main__':main()
