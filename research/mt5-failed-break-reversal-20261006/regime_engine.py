from pathlib import Path
import json,hashlib,datetime as dt,csv
from decimal import Decimal
from frozen_frequency_engine import Account,Market,ms,iso,MIN,DAY,M5,load_ticks,writecsv,norm
B=Path(__file__).resolve().parent;UTC=dt.timezone.utc
ARMS={'A':(False,1.3,13),'B':(True,1.3,13),'C':(False,5,21),'D':(True,5,21)}
class Factors(Market):
 def __init__(self):super().__init__();self.factor_k=None;self.stats={}
 def ingest(self,t,bid,ask):
  ctx=super().ingest(t,bid,ask);k=ctx[3]
  if k!=self.factor_k:
   self.factor_k=k;keys=list(range(k-61*M5,k,M5));complete=all(x in self.bars5 for x in keys)
   self.stats={'complete':complete,'latest_start':k-M5,'completed_at':k,'oldest_start':k-61*M5,'ER':None,'ATR':None,'net60':None,'direction':0}
   if complete:
    closes=[self.bars5[x][3] for x in keys];net=closes[-1]-closes[0];den=sum(abs(b-a) for a,b in zip(closes,closes[1:]));trs=[]
    for x in range(k-14*M5,k,M5):
     r=self.bars5[x];prev=self.bars5[x-M5][3];trs.append(max(r[1]-r[2],abs(r[1]-prev),abs(r[2]-prev)))
    self.stats.update(ER=abs(net)/den if den else 0.,ATR=sum(trs)/14,net60=net,direction=1 if net>0 else -1 if net<0 else 0)
  return ctx,dict(self.stats)
def gate(stats,side,bid,ask):
 if not stats.get('complete'):return False,'closed_warmup_missing'
 if stats['ER']<.35:return False,'ER_below35'
 if stats['ATR']<(ask-bid)*10:return False,'ATR_spread_below10'
 if stats['direction']!=side:return False,'closed_direction_mismatch'
 return True,'pass'
class Arm(Account):
 def __init__(self,arm,cost):
  super().__init__(1,cost);self.arm=arm;self.filtered,self.RR,self.exit_hour=ARMS[arm];self.stats={};self.filter_wait=0;self.filter_checked_bar=None;self.filter_counts={};self.reject_log_bars={};self.diagnostics=[];self.live_diagnostics=[];self.exposure_sum=0.;self.overnight=0
 def log(self,t,event,**kw):
  super().log(t,event,**kw);self.events[-1].update(arm=self.arm,ER_before=self.stats.get('ER'),ATR_before=self.stats.get('ATR'),closed_direction=self.stats.get('direction'),closed_complete=self.stats.get('complete'),latest_closed_start=self.stats.get('latest_start'),closed_completed_at=self.stats.get('completed_at'),exit_hour=self.exit_hour)
 def candidate(self,t,bid,ask,k,day,ma,box):
  if not self.filtered:return super().candidate(t,bid,ask,k,day,ma,box)
  if t<self.filter_wait:return
  if ma is None or box is None:return super().candidate(t,bid,ask,k,day,ma,box)
  side=1 if bid>ma else -1 if bid<ma else 0
  if not side:return
  high,low=box;entry=norm(high+.0001 if side==1 else low-.0001,'nearest')
  if (side==1 and entry<=ask) or (side==-1 and entry>=bid):
   self.rejections['illegal_breakout_stop']=self.rejections.get('illegal_breakout_stop',0)+1
   if self.reject_log_bars.get('illegal')!=k:self.log(t,'REJECT',reason='illegal_breakout_stop',side=side,entry=entry,bid=bid,ask=ask,aggregation='first_per_M5; countallticks');self.reject_log_bars['illegal']=k
   return
  if self.filter_checked_bar==k:return
  self.filter_checked_bar=k;passed,why=gate(self.stats,side,bid,ask);self.filter_counts['proposal_'+why]=self.filter_counts.get('proposal_'+why,0)+1
  self.log(t,'FILTER_CHECK',stage='proposal',side=side,bid=bid,ask=ask,passed=passed,reason=why,spread=ask-bid)
  if not passed:self.filter_wait=k+M5;return
  return super().candidate(t,bid,ask,k,day,ma,box)
 def open(self,t,bid,ask):
  if self.filtered:
   passed,why=gate(self.stats,self.pending['side'],bid,ask);self.filter_counts['trigger_'+why]=self.filter_counts.get('trigger_'+why,0)+1;self.log(t,'FILTER_CHECK',stage='trigger',side=self.pending['side'],bid=bid,ask=ask,passed=passed,reason=why,spread=ask-bid)
   if not passed:self.log(t,'FILTER_CANCEL',reason=why);self.pending=None;self.filter_wait=(t//M5+1)*M5;return
  super().open(t,bid,ask)
  if self.pos:
   p=self.pos;entry=p['entry'];side=p['side'];priceR=abs(entry-p['sl'])
   if self.RR==5:
    target=Decimal(str(entry))+Decimal(side)*Decimal(5)*abs(Decimal(str(entry))-Decimal(str(p['sl'])));p['tp']=norm(target,'floor' if side==1 else 'ceil');p['expiry']=t//DAY*DAY+self.exit_hour*60*MIN;self.events[-1].update(tp=p['tp'],TP_basis='actualentrySL_5R',position_expiry=p['expiry'])
   else:self.events[-1].update(TP_basis='legacy_pending_1p3R',position_expiry=p['expiry'])
   diag={'trade_id':len(self.diagnostics)+1,'opened':t,'deadline21':t//DAY*DAY+21*60*MIN,'entry':entry,'SL':p['sl'],'side':side,'lot':p['lot'],'plan':p['planned_risk'],'priceR':priceR,'ER_at_open':self.stats.get('ER'),'MFE_net':-1e100,'MAE_net':1e100,'holding_MFE_net':-1e100,'holding_MAE_net':1e100,'MFE_priceR':-1e100,'MAE_priceR':1e100,'observations':0,'completed21':False,'actual_close':None,'first_postexit_SL_touch':None}
   p['trade_id']=diag['trade_id'];self.events[-1]['trade_id']=diag['trade_id'];self.diagnostics.append(diag);self.live_diagnostics.append(diag)
 def close(self,t,bid,ask,reason):
  p=self.pos;tid=p.get('trade_id');expiry=p['expiry'];reason='TIME21' if reason=='TIME13' and self.exit_hour==21 else reason
  done=super().close(t,bid,ask,reason)
  if done:
   e=self.events[-1];e.update(trade_id=tid,netR=e['net_trade_pnl']/e['planned_risk'],exit_deadline=expiry,exit_delay_seconds=max((t-expiry)/1000,0) if reason.startswith('TIME') else 0)
   if tid:
    d=self.diagnostics[tid-1];d['actual_close']=t;d['actual_net']=e['net_trade_pnl'];d['realized_netR']=e['netR'];d['exit_reason']=reason;self.overnight+=t//DAY!=d['opened']//DAY
  return done
 def step_factor(self,ctx,stats):
  self.stats=stats;super().step(ctx);t,bid,ask,k,day,ma,box=ctx;self.exposure_sum+=self.pos is not None
  keep=[]
  for d in self.live_diagnostics:
   side=d['side'];candidate=norm(Decimal(str(bid if side==1 else ask))-Decimal(side)*Decimal(str(self.slip)),'nearest');gross=side*(candidate-d['entry'])*d['lot']*100000;net=gross-d['lot']*7;pure=side*(candidate-d['entry'])/d['priceR'] if d['priceR'] else 0
   if net>d['MFE_net']:d['MFE_quote_time']=t
   d['MFE_net']=max(d['MFE_net'],net);d['MAE_net']=min(d['MAE_net'],net);d['MFE_priceR']=max(d['MFE_priceR'],pure);d['MAE_priceR']=min(d['MAE_priceR'],pure);d['observations']+=1
   if d['actual_close'] is None or t<=d['actual_close']:d['holding_MFE_net']=max(d['holding_MFE_net'],net);d['holding_MAE_net']=min(d['holding_MAE_net'],net)
   elif d['first_postexit_SL_touch'] is None and ((side==1 and bid<=d['SL']) or (side==-1 and ask>=d['SL'])):d['first_postexit_SL_touch']=t
   if t>=d['deadline21']:d['completed21']=True;d['end_quote']=t;d['delay21_seconds']=(t-d['deadline21'])/1000
   else:keep.append(d)
  self.live_diagnostics=keep
 def arm_result(self,quote_count):
  result=super().result();closed=[e for e in self.events if e['event']=='CLOSE'];nets=[e['net_trade_pnl'] for e in closed];winners=[x for x in nets if x>0];losers=[-x for x in nets if x<0];streak=maxstreak=0
  for x in nets:streak=streak+1 if x<0 else 0;maxstreak=max(maxstreak,streak)
  for d in self.diagnostics:
   d['netMFE_R']=d['MFE_net']/d['plan'];d['netMAE_R']=d['MAE_net']/d['plan'];d['holding_netMFE_R']=d['holding_MFE_net']/d['plan'];d['holding_netMAE_R']=d['holding_MAE_net']/d['plan'];d['MFE_after_exit_not_revenue']=True;d['SL_already_exited_then_extended_peak']=d.get('exit_reason')=='SL' and d.get('MFE_quote_time',0)>d.get('actual_close',1e100);d['extended_peak_after_sameSL_touch']=d['first_postexit_SL_touch'] is not None and d.get('MFE_quote_time',0)>d['first_postexit_SL_touch']
  grosspositive=sum(winners);maxwin=max(winners) if winners else 0
  result.update(arm=self.arm,filtered=self.filtered,RR=self.RR,time_exit=self.exit_hour,win_rate=len(winners)/len(nets) if nets else None,avg_net_winner=sum(winners)/len(winners) if winners else None,avg_net_loser=sum(losers)/len(losers) if losers else None,actual_avg_payoff_ratio=(sum(winners)/len(winners))/(sum(losers)/len(losers)) if winners and losers else None,consecutive_losses=maxstreak,max_winner_share_grosspositive=maxwin/grosspositive if grosspositive else None,max_winner_date=next((e['timestamp'][:10] for e in closed if e['net_trade_pnl']==maxwin),None),realized_netR=[e['netR'] for e in closed],realized_netR_ge3=sum(e['netR']>=3 for e in closed),realized_netR_ge5=sum(e['netR']>=5 for e in closed),diagnostic_netMFE_R_ge3=sum(d['netMFE_R']>=3 for d in self.diagnostics),diagnostic_netMFE_R_ge5=sum(d['netMFE_R']>=5 for d in self.diagnostics),diagnostic_priceMFE_R_ge3=sum(d['MFE_priceR']>=3 for d in self.diagnostics),diagnostic_priceMFE_R_ge5=sum(d['MFE_priceR']>=5 for d in self.diagnostics),filter_counts=self.filter_counts,market_exposure_quote_fraction=self.exposure_sum/quote_count,overnightUTC=self.overnight,time21_delay_exits=[{'timestamp':e['timestamp'],'delay':e['exit_delay_seconds']} for e in closed if e['reason']=='TIME21'],historical_swap='UNKNOWN notzeroverified',known_cost_only=True)
  return result
def main():
 proto=json.loads((B/'protocol.json').read_text());freeze=json.loads((B/'execution_freeze.json').read_text());codehash=hashlib.sha256(Path(__file__).read_bytes()).hexdigest();assert codehash==freeze['engine_sha256'];data=Path(proto['input']['path']);assert hashlib.sha256(data.read_bytes()).hexdigest()==proto['input']['sha256']
 market=Factors();arms=[Arm(a,cost) for a in ['A','B','C','D'] for cost in ['base','stress']];start=ms(proto['period_UTC'][0]);end=ms(proto['period_UTC'][1]);count=0
 for t,bid,ask in load_ticks(data,'utc'):
  ctx,stats=market.ingest(t,bid,ask)
  if t<start or t>=end:continue
  count+=1
  for a in arms:a.step_factor(ctx,stats)
 results=[]
 for a in arms:
  a.finish_day();folder=B/(a.arm+'_'+a.cost);assert not folder.exists();folder.mkdir();result=a.arm_result(count);results.append(result);writecsv(folder/'ledger.csv',a.events);writecsv(folder/'equity.csv',a.equity);writecsv(folder/'daily.csv',a.daily);(folder/'diagnostics.json').write_text(json.dumps(a.diagnostics,indent=2));(folder/'results.json').write_text(json.dumps(result,indent=2))
 assert hashlib.sha256(Path(__file__).read_bytes()).hexdigest()==codehash
 (B/'run_results.json').write_text(json.dumps({'eight':results,'code_sha256':codehash,'input_sha256':proto['input']['sha256'],'actual_model':'UNKNOWN','no_network':True},indent=2));print(json.dumps(results,indent=2))
if __name__=='__main__':main()
