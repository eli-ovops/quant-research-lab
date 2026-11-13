from pathlib import Path
import json,hashlib,datetime as dt
from regime_engine import Arm,Factors,ms,iso,M5,DAY,MIN,load_ticks,writecsv
B=Path(__file__).resolve().parent
class Confirm(Arm):
 def __init__(self,cost):
  super().__init__('C',cost);self.arm='E';self.watch=None;self.used_watch_day=None;self.confirm_counts={}
 def count(self,reason):self.confirm_counts[reason]=self.confirm_counts.get(reason,0)+1
 def candidate(self,t,bid,ask,k,day,ma,box):
  if self.used_watch_day==day:return
  return super().candidate(t,bid,ask,k,day,ma,box)
 def open(self,t,bid,ask):
  p=dict(self.pending);k=t//M5*M5;self.used_watch_day=t//DAY*DAY
  self.watch={**p,'triggered':t,'starts':[k+M5,k+2*M5,k+3*M5],'decision_boundary':k+4*M5}
  self.pending=None;self.count('watch');self.log(t,'WATCH',side=p['side'],edge=p['entry'],sl=p['sl'],starts=self.watch['starts'],decision_boundary=k+4*M5,bid=bid,ask=ask)
 def resolve(self,t,bid,ask,bidbars,askbars):
  w=self.watch
  if not w:return
  reason=None
  if t>=w['expiry']:reason='13_expiry'
  elif self.lock or self.day_open>=self.cap:reason='lock_cap'
  else:
   book=bidbars if w['side']==1 else askbars
   done=[k for k in w['starts'] if t>=k+M5]
   if any(k not in book for k in done):reason='missing_bar'
   elif any(not (book[k][3]>w['entry'] if w['side']==1 else book[k][3]<w['entry']) for k in done):reason='close_back_inside'
  if reason is None and t>=w['decision_boundary']:
   book=bidbars if w['side']==1 else askbars
   missing=[k for k in w['starts'] if k not in book]
   if missing:reason='missing_bar'
   else:
    closes=[book[k][3] for k in w['starts']]
    self.log(t,'CONFIRM_DECISION',side=w['side'],edge=w['entry'],starts=w['starts'],closes=closes,triggered=w['triggered'],decision_boundary=w['decision_boundary'],bid=bid,ask=ask)
    if not all(c>w['entry'] if w['side']==1 else c<w['entry'] for c in closes):reason='close_back_inside'
    elif not ((ask>w['entry'] and ask>w['sl']) if w['side']==1 else (bid<w['entry'] and bid<w['sl'])):reason='first_quote_back_inside_or_SL'
    else:
     self.pending={key:w[key] for key in ['side','entry','sl','tp','expiry','placed']}
     self.watch=None;self.count('confirmed')
     Arm.open(self,t,bid,ask)
     if self.pos:self.events[-1].update(confirmation_trigger=w['triggered'],confirmation_starts=w['starts'],confirmation_closes=closes,confirmation_boundary=w['decision_boundary'],confirmation_delay_seconds=(t-w['triggered'])/1000,confirmation_edge=w['entry'],SL_distance=abs(self.pos['entry']-w['sl']))
     return
  if reason:self.count(reason);self.log(t,'CANCEL_WATCH',reason=reason,triggered=w['triggered'],edge=w['entry']);self.watch=None
 def tick(self,ctx,stats,bidbars,askbars):
  t,bid,ask=ctx[:3]
  self.stats=stats
  if self.watch:self.resolve(t,bid,ask,bidbars,askbars)
  self.step_factor(ctx,stats)
 def finish_result(self,count):
  r=self.arm_result(count);r['confirmation_counts']=self.confirm_counts;r['watch_end']=self.watch;return r
def main():
 p=json.loads((B/'protocol.json').read_text());f=json.loads((B/'execution_freeze.json').read_text())
 for name,h in f['hashes'].items():assert hashlib.sha256((B/name).read_bytes()).hexdigest()==h
 output=[]
 for src in p['inputs']:
  data=Path(src['path']);assert hashlib.sha256(data.read_bytes()).hexdigest()==src['sha256']
  start,end=ms(src['start']),ms(src['end']);market=Factors();askbars={};accounts=[Arm('C',c) for c in ['base','stress']]+[Confirm(c) for c in ['base','stress']];n=0
  for t,bid,ask in load_ticks(data,'utc'):
   if t>=end:break
   k=t//M5*M5
   if k not in askbars:askbars[k]=[ask,ask,ask,ask]
   else:r=askbars[k];r[1]=max(r[1],ask);r[2]=min(r[2],ask);r[3]=ask
   ctx,stats=market.ingest(t,bid,ask)
   if t<start:continue
   n+=1
   for a in accounts:
    if isinstance(a,Confirm):a.tick(ctx,stats,market.bars5,askbars)
    else:a.step_factor(ctx,stats)
  for a in accounts:
   a.finish_day();r=a.finish_result(n) if isinstance(a,Confirm) else a.arm_result(n);r.update(period=src['name'],day_average=len([e for e in a.events if e['event']=='OPEN'])/(20 if src['name']=='August' else 10))
   folder=B/(src['name']+'_'+a.arm+'_'+a.cost);folder.mkdir();writecsv(folder/'ledger.csv',a.events);writecsv(folder/'equity.csv',a.equity);writecsv(folder/'daily.csv',a.daily);(folder/'results.json').write_text(json.dumps(r,indent=2));output.append(r)
 (B/'run_results.json').write_text(json.dumps({'eight':output,'no_network':True,'actual_model_effort_speed':'UNKNOWN'},indent=2))
 print(json.dumps([{k:r.get(k) for k in ['period','arm','cost','net','trades','DD_quote','PF_net','confirmation_counts']} for r in output],indent=2))
if __name__=='__main__':main()
