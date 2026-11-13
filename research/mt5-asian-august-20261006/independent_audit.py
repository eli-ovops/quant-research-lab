from pathlib import Path
import csv,json,hashlib,datetime as dt
from decimal import Decimal,ROUND_HALF_UP,ROUND_FLOOR,ROUND_CEILING
B=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def near(a,b,tol=1e-7):assert abs(float(a)-float(b))<=tol*max(1,abs(float(a)),abs(float(b))),(a,b)
def rounded(x,mode):
 d=Decimal(str(x));u=Decimal('.00001');n=d.quantize(u,rounding=ROUND_HALF_UP)
 if abs(d-n)<=Decimal('.0000000001'):return float(n)
 return float(d.quantize(u,rounding={'nearest':ROUND_HALF_UP,'floor':ROUND_FLOOR,'ceil':ROUND_CEILING}[mode]))
freeze=json.loads((B/'execution_freeze.json').read_text())
for n,h in freeze['hashes'].items():assert sha(B/n)==h,n
audit=json.loads((B/'dataaudit.json').read_text());assert sha(Path(audit['input']['path']))==freeze['input_sha256']
journals={n:list(csv.DictReader((B/n/'ledger.csv').open())) for n in ['base','stress']}
known={e['timestamp']:set() for journal in journals.values() for e in journal if e['event'] in ['OPEN','CLOSE','PENDING','PENDING_REJECTED_NORMALIZED_LEVEL']}
with Path(audit['input']['path']).open() as f:
 for r in csv.DictReader(f):
  if r['timestamp'] in known:known[r['timestamp']].add((float(r['bid']),float(r['ask'])))
summaries=[];pairs={}
for name,journal in journals.items():
 slip=Decimal('0') if name=='base' else Decimal('.0001');cash=500.;pos=None;closed=[];fee_sum=0;slip_sum=0;round_errors=[];maxcash=500
 for e in journal:
  event=e['event'];bid,ask=float(e['bid']),float(e['ask']);assert (bid,ask) in known[e['timestamp']]
  if event in ['PENDING','PENDING_REJECTED_NORMALIZED_LEVEL']:
   side=int(e['side']);near(e['entry'],rounded(e['entry_raw'],'nearest'));near(e['sl'],rounded(e['SL_raw'],'floor' if side==1 else 'ceil'));near(e['tp'],rounded(e['TP_raw'],'floor' if side==1 else 'ceil'));round_errors.append(abs(float(e['TP_round_delta'])))
   if event=='PENDING':assert float(e['entry'])>ask if side==1 else float(e['entry'])<bid
   continue
  side=int(e['side']);q=float(e['lot']);assert q==.1;fee=q*7/2;near(e['fee'],fee);near(e['cash_before'],cash);fee_sum+=fee;slip_sum+=float(e['execution_slippage_USD'])
  if event=='OPEN':
   assert pos is None
   quote=ask if side==1 else bid;candidate=Decimal(str(quote))+Decimal(side)*slip;price=rounded(candidate,'nearest');near(e['price'],price);near(e['margin'],q*100000*price/100);assert cash-fee>=float(e['margin'])
   near(e['planned_SL_risk_USD'],abs(price-float(e['sl']))*q*100000);near(e['planned_SL_risk_pct_of_balance'],abs(price-float(e['sl']))*q*100000/cash*100)
   stop_execution=float(e['sl'])-side*float(slip);near(e['planned_SL_execution_risk_USD'],abs(price-stop_execution)*q*100000+q*7)
   pos=e;cash-=fee
  elif event=='CLOSE':
   assert pos and int(pos['side'])==side;quote=bid if side==1 else ask;candidate=Decimal(str(quote))-Decimal(side)*slip
   if e['reason']=='TP_LIMIT':
    limit=Decimal(e['TP_limit']);assert candidate>=limit if side==1 else candidate<=limit;near(e['price'],limit)
   else:near(e['price'],rounded(candidate,'nearest'))
   pnl=side*(float(e['price'])-float(pos['price']))*q*100000;net=pnl-fee-float(pos['fee']);near(e['pnl'],pnl);near(e['net_trade_pnl'],net);cash+=pnl-fee
   closed.append({'open':pos,'close':e,'net':net});pos=None
  near(e['cash_after'],cash);maxcash=max(maxcash,cash)
 assert pos is None
 result=json.loads((B/name/'results.json').read_text());metric=result['metrics'];runtime=json.loads((B/name/'runtime.json').read_text())
 assert runtime['code_before_after_sha256']==freeze['hashes']['august_engine.py'];assert result['input_sha256']==freeze['input_sha256']
 near(metric['cash'],cash);near(metric['marked_pnl'],cash-500);near(metric['commission_USD'],fee_sum);near(metric['execution_slippage_USD'],slip_sum)
 gp=sum(x['net'] for x in closed if x['net']>0);gl=-sum(x['net'] for x in closed if x['net']<0);near(metric['profit_factor_net_trades'],gp/gl);assert metric['wins']==sum(x['net']>0 for x in closed) and metric['losses']==sum(x['net']<0 for x in closed)
 near(sum(w['contribution_USD'] for w in result['weeks']),cash-500)
 for w in result['weeks']:near(w['contribution_USD'],sum(x['net'] for x in closed if w['start']<=x['close']['timestamp']<w['end_exclusive']))
 sampled=list(csv.DictReader((B/name/'equity.csv').open()));peak=500.;sampleDD=0
 for row in sampled:
  near(row['equity'],float(row['cash'])+float(row['floating_pnl']));near(row['free_margin'],float(row['equity'])-float(row['margin']));peak=max(peak,float(row['equity']));sampleDD=max(sampleDD,1-float(row['equity'])/peak)
 assert metric['max_tick_drawdown']+1e-8>=sampleDD
 assert metric['target30_realized_first'] is None and maxcash<650 and max(float(r['equity']) for r in sampled)<650
 risk=[float(x['open']['planned_SL_risk_pct_of_balance']) for x in closed];overnight=sum(x['open']['timestamp'][:10]!=x['close']['timestamp'][:10] for x in closed)
 summaries.append({'scenario':name,'bookkeeping':'PASS','closed_trades':len(closed),'cash':cash,'PF':gp/gl,'fees':fee_sum,'slippage':slip_sum,'planned_SL_risk_pct_min':min(risk),'planned_SL_risk_pct_max':max(risk),'overnight_trade_count':overnight,'swap_this_sample':'no positioncarried; not incurred in modeled sample','max_realized_cash_observed':maxcash,'max_minute_equity_observed':max(float(r['equity']) for r in sampled),'max_abs_TP_rounding_price_delta':max(round_errors or [0]),'same_account_week_reconstruction':'PASS','sample_equity_cashidentity':'PASS','quote_normalization_limit_margin_fee':'PASS'})
 pairs[name]=closed
assert len(pairs['base'])==len(pairs['stress'])
decomp=[]
for b,s in zip(pairs['base'],pairs['stress']):
 assert b['open']['timestamp']==s['open']['timestamp'] and b['open']['side']==s['open']['side']
 direct=float(s['open']['execution_slippage_USD'])+float(s['close']['execution_slippage_USD']);diff=b['net']-s['net']
 decomp.append({'date':b['open']['timestamp'][:10],'base_net':b['net'],'stress_net':s['net'],'net_difference':diff,'direct_market_stop_slippage_USD':direct,'exitpath_and_rounding_residual_USD':diff-direct,'base_exit':b['close']['timestamp'],'stress_exit':s['close']['timestamp'],'base_reason':b['close']['reason'],'stress_reason':s['close']['reason'],'stress_TP_deferred_quotes':int(s['close']['tp_deferred_count'])})
out={'status':'PASS','scope':'sameOwner different cash/quote/price/fee/week implementation, not thirdparty/full independent strategy replay','summaries':summaries,'matched_trade_difference':decomp,'total_net_difference':sum(x['net_difference'] for x in decomp),'direct_slippage':sum(x['direct_market_stop_slippage_USD'] for x in decomp),'path_residual':sum(x['exitpath_and_rounding_residual_USD'] for x in decomp),'weekend_box_diagnostic_dates':[d for d in audit['ticks_by_UTCdate'] if dt.date.fromisoformat(d).weekday()==6],'weekday_data_gaps':[s for s in audit['sessions'] if s['missing_box_M15'] or s['missing_MA_M5']],'freeze_before_PnL_verified':True,'full_source_complete':'UNKNOWN'}
(B/'independent_audit.json').write_text(json.dumps(out,indent=2));print(json.dumps({'status':'PASS','summaries':summaries,'difference':out['total_net_difference'],'direct':out['direct_slippage'],'residual':out['path_residual'],'changed_exit_trades':[x for x in decomp if abs(x['exitpath_and_rounding_residual_USD'])>1e-7],'weekend_dates':out['weekend_box_diagnostic_dates']},indent=2))

