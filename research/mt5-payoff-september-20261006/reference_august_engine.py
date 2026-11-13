from pathlib import Path
import datetime as dt,json,csv,hashlib,argparse,math
from decimal import Decimal,ROUND_HALF_UP,ROUND_FLOOR,ROUND_CEILING
from frozen_prior_engine import Research,load_ticks,window_ticks,ms,iso,MIN,DAY,writecsv
B=Path(__file__).resolve().parent;UTC=dt.timezone.utc
def norm(value,mode):
 x=Decimal(str(value));unit=Decimal('0.00001');nearest=x.quantize(unit,rounding=ROUND_HALF_UP)
 if abs(x-nearest)<=Decimal('0.0000000001'):return float(nearest)
 return float(x.quantize(unit,rounding={'nearest':ROUND_HALF_UP,'floor':ROUND_FLOOR,'ceil':ROUND_CEILING}[mode]))
class Execution(Research):
 def __init__(self,scenario):
  super().__init__(commission=7,balance=500,lot=.1);self.scenario=scenario;self.slip=0 if scenario=='base' else .0001;self.deferred=0;self.target_equity_first=None;self.target_realized_first=None
 def open(self,t,bid,ask):
  p=self.pending;side=p['side'];q=p['lot'];quote=ask if side==1 else bid;rawpx=quote+side*self.slip;px=norm(rawpx,'nearest');margin=q*100000*px/100;fee=q*7/2
  if q<.01 or abs(round(q/.01)*.01-q)>1e-10:self.reject('lot_min_step');self.pending=None;return
  if self.cash-fee<margin:self.reject('insufficient_margin');self.pending=None;return
  before=self.cash;self.cash-=fee;self.pos={**p,'entry':px,'margin':margin,'opened':t,'entry_fee':fee};self.pending=None
  plan=abs(px-p['sl'])*q*100000;planexec=abs(px-(p['sl']-side*self.slip))*q*100000+q*7
  self.log(t,'OPEN',side=side,lot=q,price=px,quote=quote,bid=bid,ask=ask,sl=p['sl'],tp=p['tp'],margin=margin,fee=fee,cash_before=before,cash_after=self.cash,spread_mid_diagnostic=(ask-bid)/2*q*100000,point_proxy=.00001,leverage_proxy=100,planned_SL_risk_USD=plan,planned_SL_risk_pct_of_balance=plan/before*100,planned_SL_execution_risk_USD=planexec,planned_SL_execution_risk_pct_balance=planexec/before*100,execution_slippage_USD=abs(rawpx-quote)*q*100000,execution_rounding_price_delta=px-rawpx,scenario=self.scenario)
 def close(self,t,bid,ask,reason,price=None):
  p=self.pos;side=p['side'];q=p['lot'];quote=bid if side==1 else ask;candidate_decimal=Decimal(str(quote))-Decimal(str(side))*Decimal(str(self.slip));candidate=float(candidate_decimal)
  if reason=='TP_LIMIT':
   legal=candidate_decimal>=Decimal(str(p['tp'])) if side==1 else candidate_decimal<=Decimal(str(p['tp']))
   if not legal:self.deferred+=1;p['tp_deferred_count']=p.get('tp_deferred_count',0)+1;return
   exitpx=p['tp'];slipUSD=0;filltype='conservative_limit_after_adverse_quote_legal'
  else:
   exitpx=norm(candidate,'nearest');slipUSD=abs(candidate-quote)*q*100000;filltype='adverse_market_or_stop'
  pnl=side*(exitpx-p['entry'])*q*100000;fee=q*7/2;before=self.cash;self.cash+=pnl-fee;net=pnl-fee-p['entry_fee']
  self.log(t,'CLOSE',side=side,lot=q,entry=p['entry'],price=exitpx,quote=quote,bid=bid,ask=ask,reason=reason,pnl=pnl,net_trade_pnl=net,fee=fee,entry_fee=p['entry_fee'],cash_before=before,cash_after=self.cash,spread_mid_diagnostic=(ask-bid)/2*q*100000,execution_slippage_USD=slipUSD,TP_limit=p['tp'],TP_candidate_price=candidate,fill_type=filltype,tp_deferred_count=p.get('tp_deferred_count',0),scenario=self.scenario)
  self.pos=None
  if self.cash>=650 and self.target_realized_first is None:self.target_realized_first=iso(t)
 def tick(self,t,bid,ask):
  prior_events=len(self.events);super().tick(t,bid,ask)
  if self.pending and len(self.events)>prior_events and self.events[-1]['event']=='PENDING':
   p=self.pending;side=p['side'];rawentry=p['entry'];rawsl=p['sl'];rawtp=p['tp'];p['entry']=norm(rawentry,'nearest');p['sl']=norm(rawsl,'floor' if side==1 else 'ceil');p['tp']=norm(rawtp,'floor' if side==1 else 'ceil')
   self.events[-1].update(entry_raw=rawentry,SL_raw=rawsl,TP_raw=rawtp,entry=p['entry'],sl=p['sl'],tp=p['tp'],entry_round_delta=p['entry']-rawentry,SL_round_delta=p['sl']-rawsl,TP_round_delta=p['tp']-rawtp,bid=bid,ask=ask)
   if (side==1 and p['entry']<=ask) or (side==-1 and p['entry']>=bid):
    self.events[-1]['event']='PENDING_REJECTED_NORMALIZED_LEVEL';self.pending=None;self.placed=False;self.reject('invalid_rounded_pending_level')
  if self.equity[-1]['equity']>=650 and self.target_equity_first is None:self.target_equity_first=iso(t)
 def summary_month(self):
  out=super().summary();nets=[r['net_trade_pnl'] for r in self.events if r['event']=='CLOSE'];gp=sum(x for x in nets if x>0);gl=-sum(x for x in nets if x<0);out.update(scenario=self.scenario,net_return=out['marked_pnl']/500,profit_factor_net_trades=gp/gl if gl>0 else None,wins=sum(x>0 for x in nets),losses=sum(x<0 for x in nets),flat=sum(x==0 for x in nets),gross_netwinning_USD=gp,gross_netlosing_USD=gl,execution_slippage_USD=sum(x.get('execution_slippage_USD',0) for x in self.events),TP_deferred_quote_count=self.deferred,target30_equity_first=self.target_equity_first,target30_realized_first=self.target_realized_first,target_exit_added=False)
  return out
def main():
 p=argparse.ArgumentParser();p.add_argument('--scenario',required=True,choices=['base','stress']);args=p.parse_args();out=B/args.scenario;assert not out.exists();out.mkdir();codehash=hashlib.sha256(Path(__file__).read_bytes()).hexdigest();priorhash=hashlib.sha256((B/'frozen_prior_engine.py').read_bytes()).hexdigest()
 audit=json.loads((B/'dataaudit.json').read_text());freeze=json.loads((B/'dataaudit_freeze.json').read_text());assert hashlib.sha256((B/'dataaudit.json').read_bytes()).hexdigest()==freeze['dataaudit_sha256']
 inputpath=Path(audit['input']['path']);assert hashlib.sha256(inputpath.read_bytes()).hexdigest()==audit['input']['sha256'];ticks,warm=window_ticks(load_ticks(inputpath,'utc'),ms('2026-08-03T00:00:00Z'),ms('2026-08-29T00:00:00Z'))
 m=Execution(args.scenario)
 for x in warm:m.warmup_ingest(*x)
 for x in ticks:m.tick(*x)
 metrics=m.summary_month();weeks=[];prior=500
 for s,e in [('2026-08-03T00:00:00Z','2026-08-08T00:00:00Z'),('2026-08-10T00:00:00Z','2026-08-15T00:00:00Z'),('2026-08-17T00:00:00Z','2026-08-22T00:00:00Z'),('2026-08-24T00:00:00Z','2026-08-29T00:00:00Z')]:
  equity=[r for r in m.equity if ms(s)<=ms(r['timestamp'])<ms(e)];ending=equity[-1]['equity'] if equity else prior;closed=[r for r in m.events if r['event']=='CLOSE' and ms(s)<=ms(r['timestamp'])<ms(e)];weeks.append({'start':s,'end_exclusive':e,'account_start_equity':prior,'account_end_equity':ending,'contribution_USD':ending-prior,'closed_trades':len(closed),'same_account_not_reset':True});prior=ending
 result={'status':'CONDITIONAL_OBSERVED_QUOTE_MONTH_NOT_NATIVE_OR_PROFITABILITY','metrics':metrics,'weeks':weeks,'continuous_500_account':True,'data_source_complete':'UNKNOWN','source_tick_resolution':'observedseconds, not fullmarket','scenario_parameters':{'roundtrip_fee_perlot':7,'market_stop_slippage':m.slip,'TP':'limit only when quote adverse candidate satisfieslimit'},'input_sha256':audit['input']['sha256'],'code_sha256':codehash,'prior_code_sha256':priorhash}
 assert hashlib.sha256(Path(__file__).read_bytes()).hexdigest()==codehash
 writecsv(out/'ledger.csv',m.events);writecsv(out/'equity.csv',m.equity);(out/'results.json').write_text(json.dumps(result,indent=2));(out/'runtime.json').write_text(json.dumps({'code_before_after_sha256':codehash,'prior_sha256':priorhash,'protocol_sha256':hashlib.sha256((B/'protocol.json').read_bytes()).hexdigest(),'dataaudit_sha256':freeze['dataaudit_sha256'],'finished_utc':dt.datetime.now(UTC).isoformat(),'actual_model':'UNKNOWN'},indent=2));print(json.dumps(result,indent=2))
if __name__=='__main__':main()
