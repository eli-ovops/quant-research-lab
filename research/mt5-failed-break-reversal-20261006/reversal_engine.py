from pathlib import Path
import json,hashlib,datetime as dt
from decimal import Decimal
from frozen_frequency_engine import Account,Market,ms,iso,M5,DAY,MIN,load_ticks,writecsv,norm
B=Path(__file__).resolve().parent
def economics(original,high,low,maxask,minbid,bid,ask,slip):
 side=-original;entry=norm(Decimal(str(ask if side==1 else bid))+Decimal(side)*Decimal(str(slip)),'nearest')
 sl=norm(Decimal(str(minbid))-Decimal('.0001'),'floor') if side==1 else norm(Decimal(str(maxask))+Decimal('.0001'),'ceil')
 tp=norm(high if side==1 else low,'floor' if side==1 else 'ceil')
 valid=sl<entry<tp if side==1 else tp<entry<sl
 exitSL=norm(Decimal(str(sl))-Decimal(side)*Decimal(str(slip)),'nearest')
 risk=abs(Decimal(str(entry))-Decimal(str(exitSL)))*100000+7
 gain=Decimal(side)*(Decimal(str(tp))-Decimal(str(entry)))*100000-7
 return {'side':side,'entry_estimate':entry,'sl':sl,'tp':tp,'direction_valid':valid,'risk_perlot':float(risk),'netTP_perlot':float(gain),'netRR':float(gain/risk)}
class Reversal(Account):
 def __init__(self,cost):
  super().__init__(1,cost);self.watch=None;self.used_day=None;self.watch_counts={};self.raw_box=None
 def count(self,key):self.watch_counts[key]=self.watch_counts.get(key,0)+1
 def candidate(self,t,bid,ask,k,day,ma,box):
  if self.used_day==day:return
  super().candidate(t,bid,ask,k,day,ma,box)
  if self.pending:self.pending['rawhigh'],self.pending['rawlow']=box
 def open(self,t,bid,ask):
  p=dict(self.pending);self.pending=None;self.used_day=t//DAY*DAY
  self.watch={**p,'triggered':t,'nextbar':(t//M5+1)*M5,'maxask':ask,'minbid':bid}
  self.count('watch');self.log(t,'WATCH',original_side=p['side'],edge=p['entry'],rawhigh=p['rawhigh'],rawlow=p['rawlow'],bid=bid,ask=ask,firstbar=self.watch['nextbar'])
 def cancel(self,t,reason,**kw):
  self.count(reason);self.log(t,'CANCEL_WATCH',reason=reason,triggered=self.watch['triggered'],**kw);self.watch=None
 def resolve(self,t,bid,ask,bidbars,askbars):
  w=self.watch
  if not w:return
  w['maxask']=max(w['maxask'],ask);w['minbid']=min(w['minbid'],bid)
  if t>=w['expiry']:self.cancel(t,'13_expiry');return
  if self.lock or self.day_open>=1:self.cancel(t,'lock_cap');return
  while t>=w['nextbar']+M5:
   k=w['nextbar'];book=bidbars if w['side']==1 else askbars
   if k not in book:self.cancel(t,'missing_bar',bar_start=k);return
   close=book[k][3];inside=w['rawlow']<close<w['rawhigh']
   self.log(t,'CLOSED_BAR',bar_start=k,bar_end=k+M5,close=close,original_side=w['side'],inside=inside)
   w['nextbar']+=M5
   if not inside:continue
   q=bid if w['side']==1 else ask
   if not w['rawlow']<q<w['rawhigh']:self.cancel(t,'first_quote_outside',bid=bid,ask=ask,decision_bar=k);return
   ev=economics(w['side'],w['rawhigh'],w['rawlow'],w['maxask'],w['minbid'],bid,ask,self.slip)
   self.log(t,'REVERSAL_DECISION',triggered=w['triggered'],decision_bar=k,original_side=w['side'],maxask=w['maxask'],minbid=w['minbid'],rawhigh=w['rawhigh'],rawlow=w['rawlow'],bid=bid,ask=ask,**ev)
   if not ev['direction_valid']:self.cancel(t,'invalid_SLTP');return
   if ev['netRR']<3:self.cancel(t,'netRR_below3',netRR=ev['netRR']);return
   self.pending={'side':ev['side'],'entry':ev['entry_estimate'],'sl':ev['sl'],'tp':ev['tp'],'expiry':t//DAY*DAY+21*60*MIN,'placed':t}
   self.watch=None;self.count('RR_pass');Account.open(self,t,bid,ask)
   if self.pos:self.events[-1].update(original_side=w['side'],watch_trigger=w['triggered'],decision_bar=k,decision_boundary=k+M5,rawhigh=w['rawhigh'],rawlow=w['rawlow'],visible_maxask=w['maxask'],visible_minbid=w['minbid'],planned_netRR=ev['netRR'],TP_basis='opposite_rawbox',position_expiry=self.pos['expiry'])
   return
 def close(self,t,bid,ask,reason):
  p=self.pos;expiry=p['expiry'];reason='TIME21' if reason=='TIME13' else reason;done=super().close(t,bid,ask,reason)
  if done:self.events[-1].update(netR=self.events[-1]['net_trade_pnl']/p['planned_risk'],exit_deadline=expiry,exit_delay_seconds=max((t-expiry)/1000,0) if reason=='TIME21' else 0,opened=p['opened'])
  return done
 def tick(self,ctx,bidbars,askbars):
  if self.watch:self.resolve(ctx[0],ctx[1],ctx[2],bidbars,askbars)
  super().step(ctx)
 def output(self):
  r=self.result();nets=[e['net_trade_pnl'] for e in self.events if e['event']=='CLOSE'];ws=[x for x in nets if x>0];ls=[-x for x in nets if x<0];streak=mx=0
  for n in nets:streak=streak+1 if n<0 else 0;mx=max(mx,streak)
  nr=[e['netR'] for e in self.events if e['event']=='CLOSE']
  r.update(arm='F',watch_counts=self.watch_counts,watch_end=self.watch,win_rate=len(ws)/len(nets) if nets else None,actual_avg_payoff_ratio=(sum(ws)/len(ws))/(sum(ls)/len(ls)) if ws and ls else None,consecutive_losses=mx,netR=nr,average_netR=sum(nr)/len(nr) if nr else None,realized_netR_ge3=sum(x>=3 for x in nr),realized_netR_ge5=sum(x>=5 for x in nr),historical_swap='UNKNOWN',known_cost_only=True,overnightUTC=sum(e['timestamp'][:10]!=iso(e['opened'])[:10] for e in self.events if e['event']=='CLOSE'))
  return r
def main():
 p=json.loads((B/'protocol.json').read_text());f=json.loads((B/'execution_freeze.json').read_text())
 for n,h in f['hashes'].items():assert hashlib.sha256((B/n).read_bytes()).hexdigest()==h
 results=[]
 for src in p['inputs']:
  data=Path(src['path']);assert hashlib.sha256(data.read_bytes()).hexdigest()==src['sha256'];start,end=ms(src['start']),ms(src['end']);market=Market();askbars={};accounts=[Reversal(c) for c in ['base','stress']]
  for t,bid,ask in load_ticks(data,'utc'):
   if t>=end:break
   k=t//M5*M5
   if k not in askbars:askbars[k]=[ask,ask,ask,ask]
   else:askbars[k][3]=ask
   ctx=market.ingest(t,bid,ask)
   if t<start:continue
   for a in accounts:a.tick(ctx,market.bars5,askbars)
  for a in accounts:
   a.finish_day();r=a.output();r['period']=src['name'];folder=B/(src['name']+'_'+a.cost);folder.mkdir();writecsv(folder/'ledger.csv',a.events);writecsv(folder/'equity.csv',a.equity);writecsv(folder/'daily.csv',a.daily);(folder/'results.json').write_text(json.dumps(r,indent=2));results.append(r)
 (B/'run_results.json').write_text(json.dumps({'four':results,'history_used_not_holdout':True,'network':0,'actual_model_effort_speed':'UNKNOWN'},indent=2));print(json.dumps(results,indent=2))
if __name__=='__main__':main()

