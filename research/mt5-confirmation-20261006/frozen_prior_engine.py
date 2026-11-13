"""Explicit research reconstruction of MQL5 article17239, not attached/native EA."""
from pathlib import Path
import csv,datetime as dt,json,math,argparse,hashlib,sys
UTC=dt.timezone.utc;DAY=86400000;MIN=60000
def ms(x):
 t=dt.datetime.fromisoformat(x.replace('Z','+00:00'))
 if t.tzinfo is None:raise ValueError('UTC adapter timestamp requires explicit timezone')
 return int(t.timestamp()*1000)
def iso(x):return dt.datetime.fromtimestamp(x/1000,UTC).isoformat()
def window_ticks(all_ticks,start,end):
 if end<=start:raise ValueError('end must be after start')
 return [x for x in all_ticks if start<=x[0]<end],[x for x in all_ticks if start-5*60*MIN<=x[0]<start]
def load_ticks(path,fmt):
 ticks=[]
 with Path(path).open() as f:
  if fmt=='utc':
   for r in csv.DictReader(f):ticks.append((ms(r['timestamp']),float(r['bid']),float(r['ask'])))
  else:
   for r in csv.reader(f):
    if len(r)!=4:raise ValueError('HistData tick requires DateTime,Bid,Ask,Volume, not M1')
    t=dt.datetime.strptime(r[0],'%Y%m%d %H%M%S%f').replace(tzinfo=dt.timezone(dt.timedelta(hours=-5)))
    ticks.append((int(t.timestamp()*1000),float(r[1]),float(r[2])))
 prev=None
 for t,b,a in ticks:
  if not math.isfinite(b+a) or not 0<b<=a:raise ValueError('invalid bidask')
  if prev is not None and t<prev:raise ValueError('unsorted ticks; no silent sorting')
  prev=t
 return ticks
class Research:
 def __init__(self,commission=7,balance=500,lot=.1):
  self.cash=balance;self.commission=commission;self.lot=lot;self.initial=balance;self.pending=None;self.pos=None;self.session=None;self.box=None;self.placed=False
  self.m15={};self.m5={};self.events=[];self.equity=[];self.rejections={};self.last_tick=None;self.peak=balance;self.dd=0.;self.worst_float=0.;self.margin_breaches=0;self.tick_count=0
 def reject(self,key):self.rejections[key]=self.rejections.get(key,0)+1
 def warmup_ingest(self,t,bid,ask):
  """Only ingest already-arrived quotes. Never orders, cash, equity or session decisions."""
  assert 0<bid<=ask
  for width,book in [(15*MIN,self.m15),(5*MIN,self.m5)]:
   k=t//width*width
   if k not in book:book[k]=[bid,bid,bid,bid]
   else:r=book[k];r[1]=max(r[1],bid);r[2]=min(r[2],bid);r[3]=bid
 def log(self,t,event,**kw):self.events.append({'timestamp':iso(t),'event':event,'cash':self.cash,**kw})
 def close(self,t,bid,ask,reason,price=None):
  p=self.pos;exitpx=(bid if p['side']==1 else ask) if price is None else price
  pnl=p['side']*(exitpx-p['entry'])*p['lot']*100000;fee=p['lot']*self.commission/2
  before=self.cash;self.cash+=pnl-fee
  spreadcost=(ask-bid)/2*p['lot']*100000
  self.log(t,'CLOSE',side=p['side'],lot=p['lot'],entry=p['entry'],price=exitpx,bid=bid,ask=ask,reason=reason,pnl=pnl,fee=fee,cash_before=before,cash_after=self.cash,spread_mid_diagnostic=spreadcost)
  self.pos=None
 def open(self,t,bid,ask):
  p=self.pending;side=p['side'];px=ask if side==1 else bid;lot=p['lot'];margin=lot*100000*px/100;fee=lot*self.commission/2
  # Source uses fixed0.1. Proxy min/step/leverage are explicit research constraints.
  if lot<.01-1e-12 or abs(round(lot/.01)*.01-lot)>1e-10:self.reject('lot_min_step');self.pending=None;return
  if self.cash-fee<margin:self.reject('insufficient_margin');self.pending=None;return
  before=self.cash;self.cash-=fee
  self.pos={**p,'entry':px,'margin':margin,'opened':t};self.pending=None
  self.log(t,'OPEN',side=side,lot=lot,price=px,bid=bid,ask=ask,sl=p['sl'],tp=p['tp'],margin=margin,fee=fee,cash_before=before,cash_after=self.cash,spread_mid_diagnostic=(ask-bid)/2*lot*100000,point_proxy=.00001,leverage_proxy=100,planned_SL_risk_USD=abs(px-p['sl'])*lot*100000,planned_SL_risk_pct_of_balance=abs(px-p['sl'])*lot*100000/before*100)
 def tick(self,t,bid,ask):
  assert 0<bid<=ask
  # Prior ticks only. Current MA value uses evolving currentM5 bid, never futurebarclose.
  self.warmup_ingest(t,bid,ask)
  day=t//DAY*DAY;end=day+3*60*MIN;exit=day+13*60*MIN
  if t>=end and self.session!=end:
   self.session=end;self.placed=False;self.box=None
   keys=list(range(end-4*60*MIN,end,15*MIN))
   if all(k in self.m15 for k in keys):self.box=(max(self.m15[k][1] for k in keys),min(self.m15[k][2] for k in keys))
   else:self.reject('incomplete_session_box')
  # Existing exit first on reached tick, no invented end-of-file close.
  if self.pos:
   p=self.pos
   if p['side']==1:
    if bid<=p['sl']:self.close(t,bid,ask,'SL_GAP_ACTUAL_BID')
    elif bid>=p['tp']:self.close(t,bid,ask,'TP_LIMIT',p['tp'])
   else:
    if ask>=p['sl']:self.close(t,bid,ask,'SL_GAP_ACTUAL_ASK')
    elif ask<=p['tp']:self.close(t,bid,ask,'TP_LIMIT',p['tp'])
  if t>=exit:
   if self.pos:self.close(t,bid,ask,'SOURCE_TIME_EXIT')
   self.pending=None;self.box=None;self.placed=False
  elif t>=end:
   if self.pending and ((self.pending['side']==1 and ask>=self.pending['entry']) or (self.pending['side']==-1 and bid<=self.pending['entry'])):self.open(t,bid,ask)
   if self.box and not self.placed and not self.pending and not self.pos:
    k=t//(5*MIN)*5*MIN;past=sorted(x for x in self.m5 if x<k)
    if len(past)<49:self.reject('MA_warmup_missing')
    else:
     # Requires49 actual consecutive closed M5 bars, no interpolation.
     last=past[-49:]
     if last!=list(range(k-49*5*MIN,k,5*MIN)):self.reject('MA_grid_gap')
     else:
      ma=(sum(self.m5[x][3] for x in last)+bid)/50
      side=1 if bid>ma else -1 if bid<ma else 0
      high,low=self.box;offset=10*.00001
      if side:
       entry=high+offset if side==1 else low-offset;sl=low-offset if side==1 else high+offset;tp=entry+side*abs(entry-sl)*1.3
       if (side==1 and entry<=ask) or (side==-1 and entry>=bid):self.reject('invalid_stop_pending_level')
       else:
        self.pending={'side':side,'lot':self.lot,'entry':entry,'sl':sl,'tp':tp};self.placed=True;self.log(t,'PENDING',side=side,entry=entry,sl=sl,tp=tp,MA=ma,latest_price=bid)
  floating=0 if not self.pos else self.pos['side']*((bid if self.pos['side']==1 else ask)-self.pos['entry'])*self.pos['lot']*100000
  margin=0 if not self.pos else self.pos['margin'];equity=self.cash+floating
  self.peak=max(self.peak,equity);self.dd=max(self.dd,1-equity/self.peak);self.worst_float=min(self.worst_float,floating);self.margin_breaches+=equity<margin;self.tick_count+=1
  row={'timestamp':iso(t),'cash':self.cash,'floating_pnl':floating,'equity':equity,'margin':margin,'free_margin':equity-margin}
  if self.equity and ms(self.equity[-1]['timestamp'])//MIN==t//MIN:self.equity[-1]=row
  else:self.equity.append(row)
  self.last_tick=(t,bid,ask)
 def summary(self):
  peak=self.initial;dd=0
  for x in self.equity:peak=max(peak,x['equity']);dd=max(dd,1-x['equity']/peak)
  equity=self.equity[-1]['equity'] if self.equity else self.initial
  forced=equity-(self.pos['lot']*self.commission/2 if self.pos else 0)
  return {'cash':self.cash,'marked_equity':equity,'marked_pnl':equity-self.initial,'max_tick_drawdown':self.dd,'worst_floating_pnl':self.worst_float,'tick_count':self.tick_count,'unmodeled_margin_breach_ticks':self.margin_breaches,'equity_file_resolution':'last tick each minute; DD/worst floating computed every tick','closed_trades':sum(x['event']=='CLOSE' for x in self.events),'opened_trades':sum(x['event']=='OPEN' for x in self.events),'commission_USD':sum(x.get('fee',0) for x in self.events),'spread_mid_diagnostic_USD':sum(x.get('spread_mid_diagnostic',0) for x in self.events),'open_position':self.pos,'terminal_forced_exit_estimate_equity':forced,'forced_exit_executed':False,'overnight_swap':'UNKNOWN if position overnight','rejections':self.rejections,'native_MT5':False,'original_attached_EA_reproduced':False}
def writecsv(p,rows):
 fields=sorted(set(k for r in rows for k in r)) if rows else ['timestamp','event']
 with p.open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
def main():
 parser=argparse.ArgumentParser();parser.add_argument('--csv',required=True);parser.add_argument('--warmup-csv');parser.add_argument('--format',choices=['utc','histdata'],required=True);parser.add_argument('--commission',type=float,choices=[0,7],default=7);parser.add_argument('--output',required=True);parser.add_argument('--start',default='2026-09-21T00:00:00Z');parser.add_argument('--end',default='2026-09-26T00:00:00Z');parser.add_argument('--data-audit');args=parser.parse_args()
 out=Path(args.output);assert not out.exists(),'choose new output directory, no evidence overwrite';out.mkdir()
 source_hash=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
 runtime={'source_path':str(Path(__file__).resolve()),'source_sha256_before':source_hash,'argv':sys.argv,'started_utc':dt.datetime.now(UTC).isoformat(),'protocol_sha256':hashlib.sha256((Path(__file__).parent/'protocol.json').read_bytes()).hexdigest(),'python':sys.version,'commission':args.commission,'source_format':args.format,'strategy':'article17239 declared research variant fixed0.1lot'}
 all_ticks=load_ticks(args.csv,args.format);start=ms(args.start);end=ms(args.end);ticks,warmup=window_ticks(all_ticks,start,end)
 if args.warmup_csv:warmup+=load_ticks(args.warmup_csv,args.format)
 warmup=[x for x in warmup if start-5*60*MIN<=x[0]<start]
 warmup.sort(key=lambda x:x[0]) # stable: keep every quote and equal-time original order
 observed_days=sorted(set(iso(x[0])[:10] for x in ticks));gaps=[{'from':iso(a[0]),'to':iso(b[0]),'ms':b[0]-a[0]} for a,b in zip(ticks,ticks[1:]) if b[0]-a[0]>5*MIN]
 audit={'source':str(Path(args.csv).resolve()),'sha256':hashlib.sha256(Path(args.csv).read_bytes()).hexdigest(),'time_format':args.format,'histdata_timezone':'fixedEST UTC-5, noDST','ticks':len(ticks),'observed_days':observed_days,'gaps_gt5min':gaps,'first':iso(ticks[0][0]) if ticks else None,'last':iso(ticks[-1][0]) if ticks else None,'full5days_certified':False,'why_not_certified':'market hours and source completeness require separate raw-source audit; observed dates alone insufficient'}
 audit['warmup_ticks']=len(warmup);audit['warmup_first']=iso(warmup[0][0]) if warmup else None;audit['warmup_last']=iso(warmup[-1][0]) if warmup else None
 model=Research(args.commission)
 for x in warmup:model.warmup_ingest(*x)
 for x in ticks:model.tick(*x)
 result={'status':'CONDITIONAL_PARTIAL_DATA_RESEARCH_ONLY','full_week_pnl':None,'research_marked_metrics':model.summary(),'dataaudit':audit,'not_profitability_evidence':True}
 if args.data_audit:
  data_proof=json.loads(Path(args.data_audit).read_text());assert data_proof['input']['sha256']==audit['sha256'];assert data_proof['period_UTC']==[args.start,args.end]
  result['source_data_audit_sha256']=hashlib.sha256(Path(args.data_audit).read_bytes()).hexdigest();result['all_five_sessions_data_pass']=data_proof['all_five_sessions_data_pass']
  if data_proof['all_five_sessions_data_pass']:
   result['status']='CONDITIONAL_OBSERVED_FIVE_SESSIONS_RESEARCH_ONLY';result['full_week_pnl']=model.summary()['marked_pnl']
 runtime['source_sha256_after']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest();assert runtime['source_sha256_after']==source_hash
 runtime['finished_utc']=dt.datetime.now(UTC).isoformat();runtime['input_sha256']=audit['sha256'];runtime['warmup_sha256']=hashlib.sha256(Path(args.warmup_csv).read_bytes()).hexdigest() if args.warmup_csv else None
 (out/'runtime_receipt.json').write_text(json.dumps(runtime,indent=2))
 (out/'results.json').write_text(json.dumps(result,indent=2));writecsv(out/'ledger.csv',model.events);writecsv(out/'equity.csv',model.equity);print(json.dumps(result,indent=2))
if __name__=='__main__':main()
