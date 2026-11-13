import json,math,csv,datetime,pathlib,hashlib
from dataaudit import load,ts,iso,DAY,sha
B=pathlib.Path(__file__).resolve().parent
ASSETS=['BTC','ETH']
def fill(cash,qty,asset,dq,reference,fee,slip,t,reason,signals,ledger):
 if abs(dq)<1e-12:return cash
 beforeq=qty[asset];beforecash=cash;side='BUY' if dq>0 else 'SELL'
 px=reference*(1+slip if dq>0 else 1-slip);notional=abs(dq)*px;fees=notional*fee;slippage=abs(dq)*abs(px-reference)
 cash-=dq*px+fees;qty[asset]+=dq
 assert cash>=-1e-7 and qty[asset]>=-1e-12
 ledger.append({'timestamp':iso(t),'asset':asset,'side':side,'quantity':abs(dq),'reference_price':reference,'execution_price':px,'execution_notional':notional,'fee_USDT':fees,'slippage_USDT':slippage,'cash_before':beforecash,'cash_after':cash,'quantity_before':beforeq,'quantity_after':qty[asset],'reason':reason,'signal_latest_bar':iso(signals[0]) if signals else '', 'signal_old_bar':iso(signals[1]) if signals else ''})
 return cash
def rebalance(cash,qty,opens,on,fee,slip,t,signals,ledger):
 before=cash+sum(qty[c]*opens[c] for c in ASSETS)
 def cost(e):
  ans=0
  for c in ASSETS:
   dq=(.5*e/opens[c] if on[c] else 0)-qty[c]
   p=opens[c]*(1+slip if dq>0 else 1-slip)
   ans+=abs(dq)*abs(p-opens[c])+abs(dq)*p*fee
  return ans
 lo,hi=0.,before
 for _ in range(90):
  m=(lo+hi)/2
  if before-cost(m)-m>=0:lo=m
  else:hi=m
 desired={c:(.5*lo/opens[c] if on[c] else 0.) for c in ASSETS}
 for sign in [-1,1]:
  for c in ASSETS:
   dq=desired[c]-qty[c]
   if dq*sign>1e-12:cash=fill(cash,qty,c,dq,opens[c],fee,slip,t,'weekly_rebalance',signals,ledger)
 return cash
def simulate(raw,start,end,mode,fee,slip,lookback=90):
 cash=500.;qty={c:0. for c in ASSETS};ledger=[];daily=[]
 for t in range(start,end,DAY):
  opens={c:float(raw[c][t][1]) for c in ASSETS};closes={c:float(raw[c][t][4]) for c in ASSETS}
  if mode=='trend' and datetime.datetime.fromtimestamp(t/1000,datetime.timezone.utc).weekday()==0:
   signal=(t-DAY,t-(lookback+1)*DAY)
   on={c:float(raw[c][signal[0]][4])>float(raw[c][signal[1]][4]) for c in ASSETS}
   cash=rebalance(cash,qty,opens,on,fee,slip,t,signal,ledger)
  elif mode=='hold' and t==start:
   for c in ASSETS:
    q=250/(opens[c]*(1+slip)*(1+fee));cash=fill(cash,qty,c,q,opens[c],fee,slip,t,'benchmark_initial',None,ledger)
  if t==end-DAY:
   for c in ASSETS:
    cash=fill(cash,qty,c,-qty[c],closes[c],fee,slip,t+DAY-1,'terminal_liquidation',None,ledger)
  values={c:qty[c]*closes[c] for c in ASSETS};equity=cash+sum(values.values())
  daily.append({'bar_timestamp':iso(t),'cash':cash,'BTC_qty':qty['BTC'],'ETH_qty':qty['ETH'],'BTC_close':closes['BTC'],'ETH_close':closes['ETH'],'BTC_value':values['BTC'],'ETH_value':values['ETH'],'equity':equity,'exposure':sum(values.values())/equity})
 return ledger,daily
def metrics(ledger,daily):
 prev=peak=500.;dd=0;changes=[]
 for row in daily:
  e=row['equity'];changes.append(e/prev-1);peak=max(peak,e);dd=max(dd,1-e/peak);prev=e
 r=prev/500-1
 return {'final_equity_USDT':prev,'net_pnl_USDT':prev-500,'net_return':r,'max_drawdown':dd,'return_drawdown_ratio':r/dd if dd>0 else None,'turnover_two_sided_initial_capital':sum(x['quantity']*x['reference_price'] for x in ledger)/500,'individual_trade_legs':len(ledger),'weekly_trade_legs':sum(x['reason']=='weekly_rebalance' for x in ledger),'fees_USDT':sum(x['fee_USDT'] for x in ledger),'slippage_USDT':sum(x['slippage_USDT'] for x in ledger),'mean_daily_close_market_exposure':sum(x['exposure'] for x in daily)/len(daily),'active_days_fraction':sum(x['exposure']>1e-12 for x in daily)/len(daily),'worst_day_return':min(changes),'days':len(daily)}
def csvwrite(p,rows):
 with p.open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]) if rows else ['timestamp']);w.writeheader();w.writerows(rows)
def main():
 proto=json.loads((B/'protocol.json').read_text());freeze=json.loads((B/'freeze.json').read_text());assert sha(B/'protocol.json')==freeze['protocol_sha256'] and sha(B/'dataaudit.json')==freeze['dataaudit_sha256']
 raw,files,summary=load();assert files==proto['source_files']
 out=[]
 for period in proto['periods']:
  for scenario,cc in proto['costs'].items():
   fee=cc['fee_bps_each_side']/10000;slip=cc['slip_bps_each_side']/10000
   for mode in ['trend','hold','cash']:
    leg,day=simulate(raw,ts(period['evaluated_start']),ts(period['evaluated_end_exclusive']),mode,fee,slip)
    prefix=period['id']+'_'+scenario+'_'+mode
    csvwrite(B/(prefix+'_ledger.csv'),leg);csvwrite(B/(prefix+'_equity.csv'),day)
    out.append({'period':period['id'],'start':period['evaluated_start'],'end_exclusive':period['evaluated_end_exclusive'],'cost':scenario,'mode':mode,'ledger_file':prefix+'_ledger.csv','equity_file':prefix+'_equity.csv',**metrics(leg,day)})
 def get(period,mode):return next(x for x in out if x['period']==period and x['mode']==mode and x['cost']=='stress')
 last=get('2025-2026H1','trend');hold=get('2025-2026H1','hold')
 checks={'last_stress_positive':last['net_return']>0,'one_earlier_stress_positive':any(get(p,'trend')['net_return']>0 for p in ['2020-2022','2023-2024']),'last_DD_below_hold':last['max_drawdown']<hold['max_drawdown'],'last_return_DD_improvement':last['return_drawdown_ratio'] is not None and hold['return_drawdown_ratio'] is not None and last['return_drawdown_ratio']>hold['return_drawdown_ratio']}
 result={'protocol_sha256':sha(B/'protocol.json'),'scenarios':out,'acceptance_checks':checks,'decision':'HISTORICAL_CONDITIONAL_CANDIDATE' if all(checks.values()) else 'REJECT_FIXED_RULE','scope':'retrospective technical rule diagnostic; no new revenue mechanism, no independent holdout or live promotion','network_calls':0}
 (B/'results.json').write_text(json.dumps(result,indent=2,ensure_ascii=False));print(json.dumps({'decision':result['decision'],'checks':checks,'stress_trend':[x for x in out if x['cost']=='stress' and x['mode']=='trend'],'stress_hold':[x for x in out if x['cost']=='stress' and x['mode']=='hold']},indent=2))
if __name__=='__main__':main()
