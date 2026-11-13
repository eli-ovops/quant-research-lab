"""V2 conditional hourly accounting. Offline only; no network/exchange order API."""
from decimal import Decimal as D, ROUND_FLOOR, ROUND_CEILING, getcontext
from pathlib import Path
import json, datetime, math, statistics, gzip, csv
getcontext().prec=36
H=3600000;COINS=('BTC','ETH');Z=D(0);CAP=D(2000);RESERVE=D(400)
CONDITIONS={'baseline':(D('.001'),D('.0005'),0),'fee2':(D('.002'),D('.0005'),0),'slip20':(D('.001'),D('.002'),0),'delay1':(D('.001'),D('.0005'),1)}
def enc(x):
 if isinstance(x,D):return str(x)
 raise TypeError(type(x).__name__)
def dump(path,obj):Path(path).write_text(json.dumps(obj,default=enc,ensure_ascii=False,indent=2)+'\n')
def down(x,unit):return (x/unit).to_integral_value(rounding=ROUND_FLOOR)*unit
def up(x,unit):return (x/unit).to_integral_value(rounding=ROUND_CEILING)*unit
def gate(raw,start,end):
 if start%H or end%H or start>=end:raise ValueError('invalid_hour_boundaries')
 data={};wanted=set(range(start-80*H,end,H))
 for c in COINS:
  d={}
  for r in raw.get(c,[]):
   if len(r)!=9:raise ValueError('invalid_raw_fields')
   t=int(r[0]);v=list(map(D,r[1:8]))
   if t%H or str(r[8])!='1' or not all(x.is_finite() for x in v):raise ValueError('unaligned_unconfirmed_nonfinite')
   if not (0<v[2]<=min(v[0],v[3])<=max(v[0],v[3])<=v[1]) or any(x<0 for x in v[4:]) or v[4]==0:raise ValueError('invalid_price_or_zero_volume')
   b=dict(zip(('o','h','l','c','vol','volCcy','volCcyQuote'),v))
   if t in d and d[t]!=b:raise ValueError('conflicting_duplicate')
   d[t]=b
  if not wanted.issubset(d):raise ValueError('warmup_or_hour_gap:'+c)
  data[c]=d
 return data

def quote(side,qty_or_budget,ref,spec,fee,slip,available=None):
 """Return a conditional legal order quote or a rejection reason."""
 try:
  ref=D(ref);lot=D(spec['lotSz']);tick=D(spec['tickSz']);minimum=D(spec['minSz']);maximum=D(spec['maxMktSz'])
  if not all(x.is_finite() and x>0 for x in (ref,lot,tick,minimum,maximum)):return None,'invalid_quote_or_spec'
  px=up(ref*(1+slip),tick) if side=='buy' else down(ref*(1-slip),tick)
  if px<=0:return None,'invalid_quote'
  q=down(qty_or_budget/px,lot) if side=='buy' else down(qty_or_budget,lot)
  if q<minimum or q>maximum:return None,'min_max_size'
  amt=q*px
  if spec.get('maxMktAmt') and amt>D(spec['maxMktAmt']):return None,'max_market_amount'
  if spec.get('minMktAmt') and amt<D(spec['minMktAmt']):return None,'min_market_amount'
  if available is not None and (amt if side=='buy' else q)>D(available):return None,'insufficient_balance'
  cost=up(q*fee if side=='buy' else amt*fee,D('0.00000001'))
  if (side=='buy' and cost>=q) or (side=='sell' and cost>=amt):return None,'fee_exceeds_order'
  return {'px':px,'qty':q,'fee':cost,'amount':amt},None
 except (KeyError,TypeError,ValueError,ArithmeticError):return None,'invalid_quote_or_spec'

def run(raw,spec,start,end,entry=24,exit=4,condition='baseline',mode='trend',overrides=None,synthetic=False):
 if entry not in (24,48,72) or exit not in (4,8,12) or condition not in CONDITIONS or mode not in ('trend','hold'):raise ValueError('not_frozen_configuration')
 if overrides and not synthetic:raise ValueError('fault_injection_synthetic_only')
 data=gate(raw,start,end);fee,slip,delay=CONDITIONS[condition]
 for c in COINS:
  if spec[c].get('instType')!='SPOT' or spec[c].get('baseCcy')!=c or spec[c].get('quoteCcy')!='USDT':raise ValueError('wrong_product')
 cash=CAP;positions={};dust={c:Z for c in COINS};pending={};fills=[];trades=[];curve=[];signals=[];rejects=[];cancellations=[];counter=0
 overrides=overrides or {}
 checked_fills=0;ledger_cash=CAP;ledger_base={c:Z for c in COINS}
 def settings(c,t,phase):
  o=overrides.get(str(t)+':'+c+':'+phase,{})
  return dict(spec[c],**o.get('spec',{})),o
 def sell(c,t,ref,phase,sig):
  nonlocal cash
  h=positions[c];sp,ov=settings(c,t,phase);q,reason=quote('sell',h['net'],ov.get('quote',ref),sp,fee,slip,ov.get('available',h['net']))
  if q is None:
   rejects.append(dict(t=t,coin=c,side='sell',phase=phase,reason=reason,retained_qty=h['net'],cash=cash,signal=sig));return False
  del positions[c];sold=q['qty'];rem=h['net']-sold;received=q['amount']-q['fee'];cash+=received;dust[c]+=rem
  exec_t=t+H if phase=='terminal' else t
  tr=dict(coin=c,id=h['id'],entry_t=h['entry_t'],exit_t=exec_t,entry_signal=h['signal'],exit_signal=sig,phase=phase,gross_qty=h['gross'],net_qty=h['net'],sold_qty=sold,dust_qty=rem,entry_ref=h['ref'],exit_ref=ref,entry_px=h['px'],exit_px=q['px'],entry_cost=h['cost'],proceeds=received,net_pnl=received-h['cost'],price_pnl=h['net']*(ref-h['ref']),fees=h['base_fee']*h['px']+q['fee'],slippage=h['net']*h['ref']*slip+sold*ref*slip,tick_rounding=h['net']*(h['px']-h['ref']*(1+slip))+sold*(ref*(1-slip)-q['px']),dust_writeoff=rem*ref,holding_hours=D(exec_t-h['entry_t'])/H)
  assert abs(tr['net_pnl']-(tr['price_pnl']-tr['fees']-tr['slippage']-tr['tick_rounding']-tr['dust_writeoff']))<D('1e-22')
  trades.append(tr);fills.append(dict(t=exec_t,bar_t=t,coin=c,side='sell',phase=phase,signal=sig,qty=sold,price=q['px'],base_fee=Z,quote_fee=q['fee'],cash_delta=received,cash_after=cash,dust_added=rem,id=h['id']));return True
 for t in range(start,end,H):
  orders=[]
  if mode=='hold' and t==start+delay*H:orders=[(c,'buy',None) for c in COINS]
  for c in COINS:
   if c in pending and pending[c]['due']==t:
    item=pending.pop(c);orders.append((c,item['side'],item['signal']))
  exited=set()
  for c,side,sig in orders:
   if side=='sell':
    if c in positions:
     if sell(c,t,data[c][t]['o'],'open',sig):exited.add(c)
    else:cancellations.append(dict(coin=c,t=t,reason='incompatible_sell'))
  buyers=[]
  for c,side,sig in orders:
   if side=='buy':
    if c not in positions and c not in exited:buyers.append((c,sig))
    else:cancellations.append(dict(coin=c,t=t,reason='incompatible_buy'))
  available=max(Z,cash-RESERVE);budget=min(D(800),available/len(buyers)) if buyers else Z
  for c,sig in buyers:
   ref=data[c][t]['o'];sp,ov=settings(c,t,'open');q,reason=quote('buy',budget,ov.get('quote',ref),sp,fee,slip,ov.get('available',cash-RESERVE))
   if q is None:rejects.append(dict(t=t,coin=c,side='buy',phase='open',reason=reason,budget=budget,cash=cash,signal=sig));continue
   assert q['amount']<=budget and cash-q['amount']>=RESERVE
   cash-=q['amount'];counter+=1
   positions[c]=dict(id=counter,entry_t=t,signal=sig,ref=ref,px=q['px'],gross=q['qty'],base_fee=q['fee'],net=q['qty']-q['fee'],cost=q['amount'])
   fills.append(dict(t=t,bar_t=t,coin=c,side='buy',phase='open',signal=sig,qty=q['qty'],price=q['px'],base_fee=q['fee'],quote_fee=Z,cash_delta=-q['amount'],cash_after=cash,dust_added=Z,id=counter))
  if t==end-H:
   for c in COINS:
    if c in positions:sell(c,t,data[c][t]['c'],'terminal',None)
  marked={c:(positions[c]['net']*data[c][t]['c'] if c in positions else Z) for c in COINS};raw_equity=cash+sum(marked.values(),Z);value=cash;liq=cash;unresolved=False
  for c,h in positions.items():
   sp,ov=settings(c,t,'mark');q,_=quote('sell',h['net'],ov.get('quote',data[c][t]['c']),sp,fee,slip,ov.get('available',h['net']))
   if q is None:unresolved=True;value+=marked[c]
   else:value+=q['amount']-q['fee'];liq+=q['amount']-q['fee']
  # A rejected terminal exit is not rescued by an executable-looking close mark.
  if t==end-H and positions:unresolved=True;value=raw_equity
  row=dict(t=t,close_t=t+H,cash=cash,raw_equity=raw_equity,valuation_equity=value,liquidation_equity_proxy=None if unresolved else liq,unresolved=unresolved,active_positions=len(positions))
  for c in COINS:row.update({c+'_qty':positions[c]['net'] if c in positions else Z,c+'_dust':dust[c],c+'_mark':data[c][t]['c'],c+'_exposure':marked[c]/raw_equity if raw_equity else Z,c+'_dust_mark':dust[c]*data[c][t]['c']})
  curve.append(row)
  if mode=='trend' and t<end-H:
   for c in COINS:
    if c in pending:continue
    close=data[c][t]['c'];side=None
    if c not in positions and close>max(data[c][t-j*H]['h'] for j in range(1,entry+1)):side='buy'
    elif c in positions and close<min(data[c][t-j*H]['l'] for j in range(1,exit+1)):side='sell'
    if side:
     sig=dict(coin=c,side=side,bar_t=t,signal=t+H,due=t+(1+delay)*H)
     signals.append(sig);pending[c]=dict(side=side,signal=t+H,due=sig['due'])
  for f in fills[checked_fills:]:
   ledger_cash+=f['cash_delta'];ledger_base[f['coin']]+=f['qty']-f['base_fee'] if f['side']=='buy' else -f['qty']
  checked_fills=len(fills)
  assert cash==ledger_cash
  for c in COINS:
   assert abs(ledger_base[c]-(positions[c]['net'] if c in positions else Z)-dust[c])<D('1e-24')
 for c,item in pending.items():cancellations.append(dict(coin=c,t=end,reason='period_end_pending_cancelled',**item))
 assert abs(cash-CAP-(sum((tr['net_pnl'] for tr in trades),Z)-sum((h['cost'] for h in positions.values()),Z)))<D('1e-22')
 result=dict(classification='SYNTHETIC_VALIDATION_ONLY' if synthetic else 'EXPLORATORY_REUSED_HISTORY',entry=entry,exit=exit,condition=condition,mode=mode,start=start,end=end,fills=fills,trades=trades,curve=curve,signals=signals,rejections=rejects,cancellations=cancellations,open_positions=positions,dust=dust)
 result['metrics']=metrics(result);return result

def metrics(run):
 curve=run['curve'];eq=[CAP]+[r['valuation_equity'] for r in curve];peak=CAP;peak_i=0;maxdd=Z;longest=0;recoveries=[];under_start=None
 for i,e in enumerate(eq):
  if e>=peak:
   if under_start is not None:recoveries.append(i-under_start);under_start=None
   peak=e;peak_i=i
  else:
   if under_start is None:under_start=peak_i
   maxdd=max(maxdd,1-e/peak);longest=max(longest,i-peak_i)
 daily={}
 for r in curve:daily[r['t']//(24*H)]=r['valuation_equity']
 dayeq=[CAP]+list(daily.values());dr=[b/a-1 for a,b in zip(dayeq,dayeq[1:])]
 trades=run['trades'];pnls=[t['net_pnl'] for t in trades];wins=[v for v in pnls if v>0];losses=[v for v in pnls if v<0];winners=sorted(wins,reverse=True);runloss=0;maxloss=0
 for v in pnls:runloss=runloss+1 if v<0 else 0;maxloss=max(maxloss,runloss)
 spans=sorted([(t['entry_t'],t['exit_t']) for t in trades]+[(h['entry_t'],run['end']) for h in run['open_positions'].values()]);merged=[]
 for a,b in spans:
  if merged and a<merged[-1][1]:merged[-1][1]=max(b,merged[-1][1])
  else:merged.append([a,b])
 turnover=sum((abs(f['cash_delta'])+f['quote_fee'] for f in run['fills']),Z)
 total=lambda k:sum((t[k] for t in trades),Z)
 return dict(final_equity=eq[-1],net_pnl=eq[-1]-CAP,return_full_2000=eq[-1]/CAP-1,final_cash=curve[-1]['cash'],unresolved_positions=len(run['open_positions']),liquidation_equity_proxy=curve[-1]['liquidation_equity_proxy'],fills=len(run['fills']),closed_trades=len(trades),rejections=len(run['rejections']),turnover_usdt=turnover,turnover_multiple=turnover/CAP,win_rate=D(len(wins))/len(pnls) if pnls else None,average_win=sum(wins,Z)/len(wins) if wins else None,average_loss=sum(losses,Z)/len(losses) if losses else None,max_drawdown=maxdd,longest_underwater_hours=longest,unrecovered_hours_at_end=len(eq)-1-peak_i if eq[-1]<peak else 0,max_completed_recovery_hours=max(recoveries,default=None),max_consecutive_losses=maxloss,worst_day=min(dr),worst_trade=min(pnls,default=None),tail5_trades=sorted(pnls)[:5],holding_hours=total('holding_hours')+sum((D(run['end']-h['entry_t'])/H for h in run['open_positions'].values()),Z),holding_hours_closed=total('holding_hours'),holding_hours_open=sum((D(run['end']-h['entry_t'])/H for h in run['open_positions'].values()),Z),top5_share_gross_gains=sum(winners[:5],Z)/sum(wins,Z) if wins else None,pnl_without_top5_winners=sum(pnls,Z)-sum(winners[:5],Z),exposure_clusters=len(merged),cluster_intervals=merged,mean_exposure=sum((r['BTC_exposure']+r['ETH_exposure'] for r in curve),Z)/len(curve),max_exposure=max(r['BTC_exposure']+r['ETH_exposure'] for r in curve),price_pnl=total('price_pnl'),fees=total('fees'),slippage=total('slippage'),tick_rounding=total('tick_rounding'),dust_writeoff=total('dust_writeoff'),by_coin={c:sum((t['net_pnl'] for t in trades if t['coin']==c),Z) for c in COINS},extra_cost_capacity_usdt=max(Z,eq[-1]-CAP),break_even_extra_cost_bps_static=(eq[-1]-CAP)/turnover*10000 if turnover else None,break_even_note='Static allowance on observed turnover, not a reoptimized execution/fee-rate rerun; negative means no nonnegative allowance',daily_returns=dr,daily_utc_keys=list(daily))

def export(folder,result):
 folder=Path(folder);folder.mkdir(exist_ok=True,parents=True)
 dump(folder/'summary.json',{k:v for k,v in result.items() if k!='curve'})
 with gzip.open(folder/'equity.csv.gz','wt',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(result['curve'][0]));w.writeheader();w.writerows(result['curve'])
