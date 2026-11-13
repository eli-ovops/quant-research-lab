from pathlib import Path
import datetime as dt,json,hashlib,csv,argparse,math
from decimal import Decimal,ROUND_FLOOR
from reference_august_engine import norm
from frozen_prior_engine import load_ticks,ms,iso,MIN,DAY,writecsv
B=Path(__file__).resolve().parent;M5=5*MIN;M15=15*MIN;UTC=dt.timezone.utc
class Market:
 def __init__(self):self.bars5={};self.bars15={};self.current_k=None;self.ma49=None;self.frozen_boxes={}
 def ingest(self,t,bid,ask):
  for width,book in [(M5,self.bars5),(M15,self.bars15)]:
   k=t//width*width
   if k not in book:book[k]=[bid,bid,bid,bid]
   else:r=book[k];r[1]=max(r[1],bid);r[2]=min(r[2],bid);r[3]=bid
  k=t//M5*M5
  if k!=self.current_k:
   keys=list(range(k-49*M5,k,M5));self.ma49=sum(self.bars5[x][3] for x in keys) if all(x in self.bars5 for x in keys) else None;self.current_k=k
  day=t//DAY*DAY;end=day+3*60*MIN
  if t>=end and day not in self.frozen_boxes:
   keys=list(range(end-4*60*MIN,end,M15));self.frozen_boxes[day]=(max(self.bars15[x][1] for x in keys),min(self.bars15[x][2] for x in keys)) if all(x in self.bars15 for x in keys) else None
  ma=(self.ma49+bid)/50 if self.ma49 is not None else None
  return (t,bid,ask,k,day,ma,self.frozen_boxes.get(day))
class Account:
 def __init__(self,cap,cost):
  self.cap=cap;self.cost=cost;self.slip=0 if cost=='base' else .0001;self.cash=500.;self.pos=None;self.pending=None;self.day=None;self.day_start=None;self.day_open=0;self.lock=False;self.completed=False;self.next_candidate=0;self.last_candidate_bar=None
  self.events=[];self.equity=[];self.daily=[];self.rejections={};self.counts={'cooldown_ticks':0,'cap_block_ticks':0,'day_lock_ticks':0,'loss_lock_days':0,'TP_deferred_quotes':0};self.peak=500.;self.dd=0.;self.worst_float=0.;self.max_equity=500.;self.max_realized=500.;self.target_equity=None;self.target_realized=None;self.last_equity=500.;self.last_tick=None
 def log(self,t,event,**kw):self.events.append({'timestamp':iso(t),'event':event,'cap':self.cap,'cost':self.cost,'day_OPEN_count':self.day_open,'cash':self.cash,**kw})
 def reject(self,t,reason,**kw):
  self.rejections[reason]=self.rejections.get(reason,0)+1;self.log(t,'REJECT',reason=reason,**kw)
 def floating(self,bid,ask):return self.pos['side']*((bid if self.pos['side']==1 else ask)-self.pos['entry'])*self.pos['lot']*100000 if self.pos else 0.
 def finish_day(self):
  if self.day is not None:self.daily.append({'day':iso(self.day)[:10],'start_equity':self.day_start,'end_equity':self.last_equity,'contribution':self.last_equity-self.day_start,'OPEN_count':self.day_open,'locked':self.lock,'no_trade':self.day_open==0})
 def open(self,t,bid,ask):
  if self.lock or self.day_open>=self.cap:
   self.reject(t,'losslock_on_trigger' if self.lock else 'cap_on_trigger');self.pending=None;return
  p=self.pending;side=p['side'];quote=ask if side==1 else bid;entry=norm(quote+side*self.slip,'nearest');exitSL=norm(p['sl']-side*self.slip,'nearest');unit=abs(Decimal(str(entry))-Decimal(str(exitSL)))*Decimal(100000)+Decimal(7);equity=self.cash;budget=Decimal(str(equity))*Decimal('.01');lotunits=(budget/unit/Decimal('.01')).to_integral_value(rounding=ROUND_FLOOR);lot=float(min(Decimal(100),lotunits*Decimal('.01')))
  if lot<.01:
   self.reject(t,'minlot_over_riskbudget',riskbudget=float(budget),risk_perlot=float(unit),minlot_risk=float(unit*Decimal('.01')));self.pending=None;self.completed=True;self.next_candidate=(t//M5+1)*M5;return
  planned=lot*float(unit);fee=lot*7/2;margin=lot*100000*entry/100
  if equity-fee<margin:
   self.reject(t,'margin_insufficient',riskbudget=float(budget),lot=lot,margin=margin);self.pending=None;self.completed=True;self.next_candidate=(t//M5+1)*M5;return
  assert planned<=float(budget)+1e-8
  before=self.cash;self.cash-=fee;self.day_open+=1;assert self.day_open<=self.cap
  self.pos={**p,'entry':entry,'lot':lot,'entry_fee':fee,'margin':margin,'opened':t,'risk_budget':float(budget),'planned_risk':planned,'preentry_equity':equity};self.pending=None
  self.log(t,'OPEN',side=side,lot=lot,entry=entry,bid=bid,ask=ask,quote=quote,sl=p['sl'],tp=p['tp'],fee=fee,margin=margin,risk_budget=float(budget),risk_perlot=float(unit),planned_risk=planned,planned_risk_pct=planned/equity*100,preentry_equity=equity,cash_before=before,cash_after=self.cash,slip_USD=abs(entry-quote)*lot*100000,spread_diag_USD=(ask-bid)/2*lot*100000,eligible_after=self.next_candidate)
 def close(self,t,bid,ask,reason):
  p=self.pos;side=p['side'];quote=bid if side==1 else ask;candidate=Decimal(str(quote))-Decimal(side)*Decimal(str(self.slip))
  if reason=='TP':
   if not (candidate>=Decimal(str(p['tp'])) if side==1 else candidate<=Decimal(str(p['tp']))):self.counts['TP_deferred_quotes']+=1;return False
   price=p['tp'];slipUSD=0
  else:price=norm(candidate,'nearest');slipUSD=abs(price-quote)*p['lot']*100000
  pnl=side*(price-p['entry'])*p['lot']*100000;fee=p['lot']*7/2;net=pnl-fee-p['entry_fee'];before=self.cash;self.cash+=pnl-fee
  self.log(t,'CLOSE',side=side,lot=p['lot'],entry=p['entry'],price=price,bid=bid,ask=ask,quote=quote,reason=reason,fee=fee,entry_fee=p['entry_fee'],pnl=pnl,net_trade_pnl=net,planned_risk=p['planned_risk'],risk_budget=p['risk_budget'],actual_loss=max(-net,0),loss_over_plan=max(-net-p['planned_risk'],0),cash_before=before,cash_after=self.cash,slip_USD=slipUSD,spread_diag_USD=(ask-bid)/2*p['lot']*100000,TP_limit=p['tp'],TP_candidate=float(candidate))
  self.pos=None;self.completed=True;self.next_candidate=(t//M5+1)*M5;self.max_realized=max(self.max_realized,self.cash)
  if self.cash>=650 and self.target_realized is None:self.target_realized=iso(t)
  return True
 def candidate(self,t,bid,ask,k,day,ma,box):
  if ma is None:self.reject(t,'MA_missing');return
  if box is None:self.reject(t,'box_missing');return
  side=1 if bid>ma else -1 if bid<ma else 0
  if not side:return
  high,low=box;rawentry=high+.0001 if side==1 else low-.0001;rawsl=low-.0001 if side==1 else high+.0001;rawtp=rawentry+side*abs(rawentry-rawsl)*1.3;entry=norm(rawentry,'nearest');sl=norm(rawsl,'floor' if side==1 else 'ceil');tp=norm(rawtp,'floor' if side==1 else 'ceil')
  if (side==1 and entry<=ask) or (side==-1 and entry>=bid):
   self.reject(t,'illegal_breakout_stop',side=side,entry=entry,bid=bid,ask=ask,reentry=self.completed);return
  self.pending={'side':side,'entry':entry,'sl':sl,'tp':tp,'expiry':day+13*60*MIN,'placed':t}
  self.log(t,'PENDING',side=side,entry=entry,sl=sl,tp=tp,bid=bid,ask=ask,MA=ma,reentry=self.completed,eligible_after=self.next_candidate)
 def step(self,ctx):
  t,bid,ask,k,day,ma,box=ctx
  if self.day!=day:
   self.finish_day();self.day=day;self.day_start=self.cash+self.floating(bid,ask);self.day_open=0;self.lock=False;self.completed=False;self.next_candidate=0;self.last_candidate_bar=None
  eqbefore=self.cash+self.floating(bid,ask)
  if not self.lock and eqbefore<=self.day_start*.95:
   self.lock=True;self.counts['loss_lock_days']+=1;self.log(t,'DAY_LOCK',equity=eqbefore,day_start=self.day_start)
  if self.pending and t>=self.pending['expiry']:self.log(t,'CANCEL_PENDING',reason='13window');self.pending=None
  if self.pos:
   p=self.pos;side=p['side']
   if (side==1 and bid<=p['sl']) or (side==-1 and ask>=p['sl']):self.close(t,bid,ask,'SL')
   elif (side==1 and bid>=p['tp']) or (side==-1 and ask<=p['tp']):self.close(t,bid,ask,'TP')
   if self.pos and t>=self.pos['expiry']:self.close(t,bid,ask,'TIME13')
  eqafter=self.cash+self.floating(bid,ask)
  if not self.lock and eqafter<=self.day_start*.95:
   self.lock=True;self.counts['loss_lock_days']+=1;self.log(t,'DAY_LOCK',equity=eqafter,day_start=self.day_start)
  active=day+3*60*MIN<=t<day+13*60*MIN
  if active and not self.pos:
   if self.lock:
    self.counts['day_lock_ticks']+=1
    if self.pending:self.log(t,'CANCEL_PENDING',reason='losslock');self.pending=None
   elif self.day_open>=self.cap:self.counts['cap_block_ticks']+=1
   else:
    if self.pending and ((self.pending['side']==1 and ask>=self.pending['entry']) or (self.pending['side']==-1 and bid<=self.pending['entry'])):self.open(t,bid,ask)
    if not self.pos and not self.pending:
     if self.completed:
      if t<self.next_candidate:self.counts['cooldown_ticks']+=1
      elif self.last_candidate_bar!=k:
       self.last_candidate_bar=k;self.candidate(t,bid,ask,k,day,ma,box)
     else:self.candidate(t,bid,ask,k,day,ma,box)
  floating=self.floating(bid,ask);eq=self.cash+floating;self.last_equity=eq;self.peak=max(self.peak,eq);self.dd=max(self.dd,1-eq/self.peak);self.worst_float=min(self.worst_float,floating);self.max_equity=max(self.max_equity,eq)
  if eq>=650 and self.target_equity is None:self.target_equity=iso(t)
  margin=self.pos['margin'] if self.pos else 0
  row={'timestamp':iso(t),'cash':self.cash,'equity':eq,'floating':floating,'margin':margin,'free_margin':eq-margin,'OPEN_count_day':self.day_open,'locked':self.lock}
  if self.equity and ms(self.equity[-1]['timestamp'])//MIN==t//MIN:self.equity[-1]=row
  else:self.equity.append(row)
  self.last_tick=t
 def result(self):
  closed=[e for e in self.events if e['event']=='CLOSE'];opens=[e for e in self.events if e['event']=='OPEN'];nets=[e['net_trade_pnl'] for e in closed];gp=sum(x for x in nets if x>0);gl=-sum(x for x in nets if x<0);weekdays=[d for d in self.daily if dt.date.fromisoformat(d['day']).weekday()<5]
  return {'cap':self.cap,'cost':self.cost,'final':self.last_equity,'net':self.last_equity-500,'return':self.last_equity/500-1,'DD_quote':self.dd,'PF_net':gp/gl if gl>0 else None,'trades':len(opens),'closed':len(closed),'wins':sum(x>0 for x in nets),'losses':sum(x<0 for x in nets),'day_average_20_weekdays':len(opens)/20,'day_max':max([d['OPEN_count'] for d in weekdays] or [0]),'days_actual15':sum(d['OPEN_count']>=15 for d in weekdays),'no_trade_weekdays':sum(d['OPEN_count']==0 for d in weekdays),'commission':sum(e.get('fee',0) for e in self.events),'slip':sum(e.get('slip_USD',0) for e in self.events),'spread_diag_not_added':sum(e.get('spread_diag_USD',0) for e in self.events),'worst_floating':self.worst_float,'plannedrisk_pct_max':max([e['planned_risk_pct'] for e in opens] or [0]),'loss_over_plan_count':sum(e['loss_over_plan']>1e-7 for e in closed),'max_actual_trade_loss':max([e['actual_loss'] for e in closed] or [0]),'rejections':self.rejections,'counters':self.counts,'max_equity':self.max_equity,'max_realized':self.max_realized,'target650_equity':self.target_equity,'target650_realized':self.target_realized,'position_end':self.pos,'no_target_exit':True,'nativeEA':False}
def main():
 proto=json.loads((B/'protocol.json').read_text());freeze=json.loads((B/'execution_freeze.json').read_text())
 assert hashlib.sha256(Path(__file__).read_bytes()).hexdigest()==freeze['engine_sha256']
 data=Path(proto['input_readonly']['path']);assert hashlib.sha256(data.read_bytes()).hexdigest()==proto['input_readonly']['sha256']
 ticks=load_ticks(data,'utc');start=ms(proto['period_UTC'][0]);end=ms(proto['period_UTC'][1]);market=Market();accounts=[Account(c,n) for c in [1,5,15] for n in ['base','stress']]
 for t,bid,ask in ticks:
  if t<start:market.ingest(t,bid,ask);continue
  if t>=end:continue
  ctx=market.ingest(t,bid,ask)
  for a in accounts:a.step(ctx)
 results=[]
 for a in accounts:
  a.finish_day();out=B/('cap'+str(a.cap)+'_'+a.cost);assert not out.exists();out.mkdir();r=a.result();results.append(r);writecsv(out/'ledger.csv',a.events);writecsv(out/'equity.csv',a.equity);writecsv(out/'daily.csv',a.daily);(out/'results.json').write_text(json.dumps(r,indent=2))
 assert hashlib.sha256(Path(__file__).read_bytes()).hexdigest()==freeze['engine_sha256']
 (B/'run_results.json').write_text(json.dumps({'six_configs':results,'engine_sha256':freeze['engine_sha256'],'input_sha256':proto['input_readonly']['sha256'],'actual_model':'UNKNOWN','no_network':True,'history_used_not_holdout':True},indent=2));print(json.dumps(results,indent=2))
if __name__=='__main__':main()
