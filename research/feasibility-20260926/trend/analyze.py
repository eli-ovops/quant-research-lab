"""Frozen-rule, long-only, shared-cash daily OHLC diagnostic. No exchange orders."""
from pathlib import Path
from decimal import Decimal as D,ROUND_FLOOR,ROUND_CEILING,getcontext
import json,csv,datetime,hashlib,random,math,statistics,sys,platform
getcontext().prec=36
P=Path(__file__).resolve().parent;DAY=86400000;COINS=['BTC','ETH'];Z=D(0)
def enc(x):
 if isinstance(x,D):return str(x)
 raise TypeError(str(type(x)))
def save(n,x):(P/n).write_text(json.dumps(x,default=enc,ensure_ascii=False,indent=2)+'\n')
def csvsave(n,rows):
 if not rows:return
 with (P/n).open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def ts(s):return int(datetime.datetime.fromisoformat(s).replace(tzinfo=datetime.timezone.utc).timestamp()*1000)
def date(t):return datetime.datetime.fromtimestamp(t/1000,datetime.timezone.utc).date().isoformat()
def floor(x,s):return (x/s).to_integral_value(rounding=ROUND_FLOOR)*s
def ceil(x,s):return (x/s).to_integral_value(rounding=ROUND_CEILING)*s
def load():
 data={};spec={};aud={}
 for c in COINS:
  spec[c]=json.loads((P/'raw'/f'{c}_spec.txt').read_text())['data'][0]
  assert spec[c]['instType']=='SPOT' and spec[c]['baseCcy']==c and spec[c]['quoteCcy']=='USDT'
  d={};dup=0
  for f in sorted((P/'raw').glob(c+'_daily_*.txt')):
   rows=json.loads(f.read_text())['data'];assert all(int(a[0])>int(b[0]) for a,b in zip(rows,rows[1:]))
   for r in rows:
    t=int(r[0]);v=dict(zip(['o','h','l','c','vol'],map(D,r[1:6])));v['confirm']=r[-1]
    assert t%DAY==0 and v['confirm']=='1' and 0<v['l']<=min(v['o'],v['c'])<=max(v['o'],v['c'])<=v['h'] and v['vol']>=0
    if t in d:assert d[t]==v;dup+=1
    d[t]=v
  data[c]=d;aud[c]={'first':date(min(d)),'last':date(max(d)),'count':len(d),'duplicates':dup,'current_listTime':spec[c]['listTime'],'current_listTime_date':date(int(spec[c]['listTime'])),'bars_before_current_listTime':sum(t<int(spec[c]['listTime']) for t in d),'point_in_time_revision_archive':False}
 return data,spec,aud

def buy_size(budget,ref,spec,fee,slip):
 px=ceil(ref*(1+slip),D(spec['tickSz']));q=floor(budget/px,D(spec['lotSz']));fq=ceil(q*fee,D('0.00000001'))
 if q<D(spec['minSz']) or q>D(spec['maxMktSz']) or fq>=q:return None
 return px,q,fq

def sell_quote(q,ref,spec,fee,slip):
 sold=floor(q,D(spec['lotSz']));px=floor(ref*(1-slip),D(spec['tickSz']))
 if sold<D(spec['minSz']) or sold>D(spec['maxMktSz']) or px<=0:return Z,px,Z,Z,q
 cost=ceil(sold*px*fee,D('0.00000001'));return sold,px,cost,sold*px-cost,q-sold

def simulate(data,spec,start,end,entry=20,exit=10,fee=D('.001'),slip=D('.0005'),delay=0,budgets=None,capital=D(2000),reserve=D(400)):
 times=list(range(ts(start),ts(end)+DAY,DAY));warm=max(entry,exit,40)
 for c in COINS:
  assert all(t in data[c] for t in range(times[0]-warm*DAY,times[-1]+DAY,DAY)),('data_gap',c,start,end)
 cash=capital;held={};pending={};fills=[];trades=[];curve=[];rejections=[];dust={c:Z for c in COINS};tid=0
 caps=budgets or {c:D(800) for c in COINS};mode='hold' if budgets is not None else 'trend'
 def sell(c,t,ref,reason,signal):
  nonlocal cash
  h=held.pop(c);q,px,feequote,received,rem=sell_quote(h['net'],ref,spec[c],fee,slip);cash+=received;dust[c]+=rem
  price=h['net']*(ref-h['ref']);fees=h['fee_base']*h['px']+feequote
  slipcost=h['net']*(h['px']-h['ref'])+q*(ref-px);dustcost=rem*ref;pnl=received-h['cost']
  assert abs(pnl-(price-fees-slipcost-dustcost))<D('1e-20')
  fills.append({'date':date(t),'coin':c,'side':'sell','signal_date':signal,'reason':reason,'reference':ref,'price':px,'gross_qty':q,'base_fee':Z,'quote_fee':feequote,'inventory_change':-h['net'],'dust_added':rem,'cash_delta':received,'cash_after':cash,'trade_id':h['id']})
  trades.append({'trade_id':h['id'],'coin':c,'entry_date':h['date'],'exit_date':date(t),'entry_signal':h['signal'],'exit_signal':signal,'reason':reason,'gross_qty':h['gross'],'net_qty':h['net'],'sold_qty':q,'dust_qty':rem,'entry_reference':h['ref'],'exit_reference':ref,'entry_price':h['px'],'exit_price':px,'cost':h['cost'],'proceeds':received,'price_pnl':price,'fees':fees,'slippage_and_tick':slipcost,'dust_writeoff':dustcost,'net_pnl':pnl,'days_held':(t-ts(h['date']))//DAY})
 for i,t in enumerate(times):
  orders=[]
  if mode=='hold' and i==0:orders=[(c,'buy','scheduled_initial') for c in COINS]
  if mode=='trend':
   for c,(due,side,sig) in list(pending.items()):
    if due==t:orders.append((c,side,sig));del pending[c]
  exited=set()
  for c,side,sig in orders:
   if side=='sell' and c in held:sell(c,t,data[c][t]['o'],'signal',sig);exited.add(c)
  buyers=[(c,sig) for c,side,sig in orders if side=='buy' and c not in held and c not in exited]
  available=max(Z,cash-reserve);request=sum((caps[c] for c,_ in buyers),Z)
  allocations={c:min(caps[c],available*caps[c]/request) for c,_ in buyers} if request>0 else {}
  for c,sig in buyers:
   budget=allocations[c];s=buy_size(budget,data[c][t]['o'],spec[c],fee,slip)
   if s is None:rejections.append({'date':date(t),'coin':c,'reason':'size_or_fee_rejected','budget':budget});continue
   px,q,fq=s;cost=q*px;assert cost<=budget and cash-cost>=reserve-D('1e-20');cash-=cost;tid+=1
   held[c]={'id':tid,'date':date(t),'signal':sig,'ref':data[c][t]['o'],'px':px,'gross':q,'fee_base':fq,'net':q-fq,'cost':cost}
   fills.append({'date':date(t),'coin':c,'side':'buy','signal_date':sig,'reason':mode,'reference':data[c][t]['o'],'price':px,'gross_qty':q,'base_fee':fq,'quote_fee':Z,'inventory_change':q-fq,'dust_added':Z,'cash_delta':-cost,'cash_after':cash,'trade_id':tid})
  if i==len(times)-1:
   for c in list(held):sell(c,t,data[c][t]['c'],'scheduled_terminal','scheduled_terminal')
  values={c:held[c]['net']*data[c][t]['c'] if c in held else Z for c in COINS};raw_eq=cash+sum(values.values(),Z)
  eq=cash+sum((sell_quote(h['net'],data[c][t]['c'],spec[c],fee,slip)[3] for c,h in held.items()),Z)
  curve.append({'date':date(t),'cash':cash,'BTC_qty':held['BTC']['net'] if 'BTC' in held else Z,'ETH_qty':held['ETH']['net'] if 'ETH' in held else Z,'BTC_dust':dust['BTC'],'ETH_dust':dust['ETH'],'BTC_mark':data['BTC'][t]['c'],'ETH_mark':data['ETH'][t]['c'],'BTC_exposure':values['BTC']/raw_eq if raw_eq else Z,'ETH_exposure':values['ETH']/raw_eq if raw_eq else Z,'raw_equity':raw_eq,'liquidation_equity_proxy':eq})
  if mode=='trend':
   for c in COINS:
    if c in pending:continue
    r=data[c][t];side=None
    if c not in held and r['c']>max(data[c][t-j*DAY]['h'] for j in range(1,entry+1)):side='buy'
    if c in held and r['c']<min(data[c][t-j*DAY]['l'] for j in range(1,exit+1)):side='sell'
    if side:pending[c]=(t+(1+delay)*DAY,side,date(t))
 assert abs(sum((r['net_pnl'] for r in trades),Z)-(cash-capital))<D('1e-20')
 return {'fills':fills,'trades':trades,'curve':curve,'rejections':rejections,'pending_at_end':str(pending),'dust_base':dust}

def metrics(run):
 curve=run['curve'];equities=[2000.]+[float(r['liquidation_equity_proxy']) for r in curve];returns=[b/a-1 for a,b in zip(equities,equities[1:])];peak=equities[0];peak_i=0;dd=0.;duration=0;lossrun=0;maxrun=0
 for i,e in enumerate(equities):
  if e>=peak:peak=e;peak_i=i
  else:dd=max(dd,1-e/peak);duration=max(duration,i-peak_i)
 trades=run['trades'];pnls=[float(t['net_pnl']) for t in trades]
 for p in pnls:
  lossrun=lossrun+1 if p<0 else 0;maxrun=max(maxrun,lossrun)
 gains=sorted([x for x in pnls if x>0],reverse=True);sumg=sum(gains)
 return {'net_pnl':equities[-1]-2000,'return_full_2000':equities[-1]/2000-1,'trades':len(trades),'max_drawdown':dd,'longest_underwater_days':duration,'unrecovered_days_at_end':len(equities)-1-peak_i if equities[-1]<peak else 0,'worst_day':min(returns),'worst_trade_usdt':min(pnls,default=0),'max_consecutive_losing_trades_exit_order':maxrun,'max_holding_days':max([r['days_held'] for r in trades],default=0),'top3_share_gross_gains':sum(gains[:3])/sumg if sumg else None,'pnl_without_top3_winners':sum(pnls)-sum(gains[:3]),'annualized_daily_vol':statistics.stdev(returns)*math.sqrt(365) if len(returns)>1 else 0,'mean_exposure':sum(float(r['BTC_exposure']+r['ETH_exposure']) for r in curve)/len(curve),'max_exposure':max(float(r['BTC_exposure']+r['ETH_exposure']) for r in curve),'price_pnl':sum(float(r['price_pnl']) for r in trades),'fees':sum(float(r['fees']) for r in trades),'slippage_and_tick':sum(float(r['slippage_and_tick']) for r in trades),'dust_writeoff':sum(float(r['dust_writeoff']) for r in trades),'by_coin':{c:{'pnl':sum(float(r['net_pnl']) for r in trades if r['coin']==c),'trades':sum(r['coin']==c for r in trades)} for c in COINS},'overhead_scenarios':{str(a):equities[-1]-2000-a*len(curve)/365 for a in [0,60,240]},'stress_exit_haircut10_max_usdt':max(float(r['BTC_qty']*r['BTC_mark']+r['ETH_qty']*r['ETH_mark'])*.1 for r in curve),'stress_all_asset_USD_value20pct_loss_at_end':equities[-1]*.2,'venue_total_loss_upper_usdt':max(equities),'returns':returns}

def paired_ci(a,b):
 x=[i-j for i,j in zip(a,b)];rng=random.Random(20260926);n=len(x);samples=[]
 for _ in range(1000):
  picked=[]
  while len(picked)<n:
   st=rng.randrange(n);picked.extend(x[(st+j)%n] for j in range(30))
  samples.append(sum(picked[:n])/n*365)
 samples.sort();return {'annual_arithmetic_excess':sum(x)/n*365,'ci95':[samples[24],samples[974]],'block_days':30,'replicates':1000,'seed':20260926,'qualification':'paired circular-block descriptive interval, dependent regimes and model selection unknown; not confidence in executable future returns'}
def corr(x,y):
 mx=statistics.mean(x);my=statistics.mean(y);den=math.sqrt(sum((v-mx)**2 for v in x)*sum((v-my)**2 for v in y));return sum((a-mx)*(b-my) for a,b in zip(x,y))/den if den else None

def main():
 phase=sys.argv[1] if len(sys.argv)>1 else 'preseal';assert phase in ['preseal','all']
 proto=json.loads((P/'protocol.json').read_text());freeze=json.loads((P/'protocol_freeze.json').read_text());assert hashlib.sha256((P/'protocol.json').read_bytes()).hexdigest()==freeze['sha256']
 if phase=='all':assert hashlib.sha256(Path(__file__).read_bytes()).hexdigest()==json.loads((P/'seal.json').read_text())['analysis_sha256']
 for s in json.loads((P/'sources.json').read_text()):assert hashlib.sha256(Path(s['path']).read_bytes()).hexdigest()==s['sha256']
 data,spec,audit=load();save('data_audit.json',audit);allmetrics=[];fills=[];trades=[];curves=[];rejects=[];riskbudgets=None
 variants=[('main',20,10,D('.001'),D('.0005'),0),('short',15,7,D('.001'),D('.0005'),0),('long',30,15,D('.001'),D('.0005'),0),('fee2',20,10,D('.002'),D('.0005'),0),('slip20',20,10,D('.001'),D('.002'),0),('severe',20,10,D('.003'),D('.005'),0),('delay1',20,10,D('.001'),D('.0005'),1)]
 for period,(start,end) in proto['periods'].items():
  if phase=='preseal' and period=='sealed_exploratory':continue
  runs={};stats={}
  for name,en,ex,f,s,de in variants:
   run=simulate(data,spec,start,end,en,ex,f,s,de);runs[name]=run;stats[name]=metrics(run)
  if riskbudgets is None:
   riskbudgets={c:D(str(sum(float(r[c+'_exposure']) for r in runs['main']['curve'])/len(runs['main']['curve'])))*2000 for c in COINS}
   save('benchmark_calibration.json',{'based_only_on':'development main daily average gross marked weight','budgets':riskbudgets,'fixed_after_development':True,'limitation':'fixed initial capital allocation matches development average exposure; subsequent exposure and volatility can differ; not equal risk guarantee'})
  for name,budget in [('hold',{c:D(800) for c in COINS}),('exposure_hold',riskbudgets)]:
   run=simulate(data,spec,start,end,budgets=budget,reserve=Z);runs[name]=run;stats[name]=metrics(run)
  a=stats['main'];a['excess_vs_hold_usdt']=a['net_pnl']-stats['hold']['net_pnl'];a['excess_vs_exposure_hold_usdt']=a['net_pnl']-stats['exposure_hold']['net_pnl'];a['block_ci_vs_exposure_hold']=paired_ci(a['returns'],stats['exposure_hold']['returns']);a['block_ci_vs_cash']=paired_ci(a['returns'],[0.]*len(a['returns']))
  tslist=list(range(ts(start),ts(end)+DAY,DAY));daily={c:[float(data[c][t]['c']/data[c][t-DAY]['c']-1) for t in tslist] for c in COINS};a['BTC_ETH_return_correlation']=corr(daily['BTC'],daily['ETH'])
  for name,run in runs.items():
   m=stats[name];m.pop('returns');allmetrics.append(dict(period=period,variant=name,start=start,end=end,**m))
   for key,dest in [('fills',fills),('trades',trades),('curve',curves),('rejections',rejects)]:
    dest.extend(dict(period=period,variant=name,**r) for r in run[key])
 save('results_'+phase+'.json',{'phase':phase,'python':platform.python_version(),'verdict':'INSUFFICIENT_EVIDENCE','actual_orders':0,'genuinely_unseen_executable_trades':0,'scenarios':allmetrics,'data_audit':audit,'benchmark_budgets':riskbudgets});csvsave('fills_'+phase+'.csv',fills);csvsave('trades_'+phase+'.csv',trades);csvsave('equity_'+phase+'.csv',curves);save('rejections_'+phase+'.json',rejects)
 print(json.dumps({'phase':phase,'scenarios':len(allmetrics),'main':[m for m in allmetrics if m['variant']=='main']},default=enc,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
