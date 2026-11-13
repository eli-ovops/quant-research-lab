"""Independent Decimal ledger/signal audit; no import from strategy implementation."""
from pathlib import Path
from decimal import Decimal as Q,ROUND_FLOOR,ROUND_CEILING,getcontext
import json,csv,hashlib,datetime,sys
getcontext().prec=40
P=Path(__file__).resolve().parent;DAY=86400000;C=['BTC','ETH']
def ms(x):return int(datetime.datetime.fromisoformat(x).replace(tzinfo=datetime.timezone.utc).timestamp()*1000)
def loadcsv(n):return list(csv.DictReader((P/n).open()))
def down(x,s):return (x/s).to_integral_value(rounding=ROUND_FLOOR)*s
def up(x,s):return (x/s).to_integral_value(rounding=ROUND_CEILING)*s
phase=sys.argv[1] if len(sys.argv)>1 else 'all';out=json.loads((P/('results_'+phase+'.json')).read_text());sources=json.loads((P/'sources.json').read_text())
for s in sources:assert hashlib.sha256(Path(s['path']).read_bytes()).hexdigest()==s['sha256']
data={};sp={}
for c in C:
 sp[c]=json.loads((P/'raw'/(c+'_spec.txt')).read_text())['data'][0];data[c]={}
 for p in (P/'raw').glob(c+'_daily_*.txt'):
  for r in json.loads(p.read_text())['data']:data[c][int(r[0])]=r
fills=loadcsv('fills_'+phase+'.csv');curves=loadcsv('equity_'+phase+'.csv');trades=loadcsv('trades_'+phase+'.csv');summary=[]
for m in out['scenarios']:
 period,name=m['period'],m['variant'];ff=[r for r in fills if r['period']==period and r['variant']==name];cc=[r for r in curves if r['period']==period and r['variant']==name];tt=[r for r in trades if r['period']==period and r['variant']==name]
 fee=Q('.002') if name=='fee2' else Q('.003') if name=='severe' else Q('.001');sl=Q('.002') if name=='slip20' else Q('.005') if name=='severe' else Q('.0005');en,ex=(15,7) if name=='short' else (30,15) if name=='long' else (20,10);delay=2 if name=='delay1' else 1
 cash=Q(2000);pos={c:Q(0) for c in C};dust={c:Q(0) for c in C};maxerr=Q(0);checksignals=0;expected={};observed={};costs={};tradecash=[];max_participation=0.
 for row in cc:
  t=ms(row['date']);today=[r for r in ff if r['date']==row['date']]
  for f in today:
   c=f['coin'];buy=f['side']=='buy';tick=Q(sp[c]['tickSz']);lot=Q(sp[c]['lotSz']);q=Q(f['gross_qty']);assert q%lot==0
   ref=Q(data[c][t][4 if f['reason']=='scheduled_terminal' else 1]);assert ref==Q(f['reference'])
   px=up(ref*(1+sl),tick) if buy else down(ref*(1-sl),tick);assert px==Q(f['price']);bfee=up(q*fee,Q('1e-8')) if buy else Q(0);qfee=Q(0) if buy else up(q*px*fee,Q('1e-8'))
   assert bfee==Q(f['base_fee']) and qfee==Q(f['quote_fee'])
   if buy:
    assert pos[c]==0;cash-=q*px;pos[c]=q-bfee;costs[f['trade_id']]=q*px
   else:
    assert q==down(pos[c],lot);cash+=q*px-qfee;dust[c]+=pos[c]-q;pos[c]=0;tradecash.append(q*px-qfee-costs[f['trade_id']])
   assert abs(cash-Q(f['cash_after']))<Q('1e-20')
   assert cash>= (0 if name in ['hold','exposure_hold'] else 400)-Q('1e-20')
   vol=Q(data[c][t][5]);max_participation=max(max_participation,float(q/vol) if vol else float('inf'))
   if name not in ['hold','exposure_hold'] and f['reason']!='scheduled_terminal':
    s=ms(f['signal_date']);assert t-s==delay*DAY;cl=Q(data[c][s][4]);level=max(Q(data[c][s-j*DAY][2]) for j in range(1,en+1)) if buy else min(Q(data[c][s-j*DAY][3]) for j in range(1,ex+1));assert (cl>level if buy else cl<level);checksignals+=1;observed[(t,c)]=f['side']
  equity=cash
  for c in C:
   assert pos[c]==Q(row[c+'_qty']) and dust[c]==Q(row[c+'_dust']);q=down(pos[c],Q(sp[c]['lotSz']));px=down(Q(data[c][t][4])*(1-sl),Q(sp[c]['tickSz']))
   if q>=Q(sp[c]['minSz']):equity+=q*px-up(q*px*fee,Q('1e-8'))
  err=abs(equity-Q(row['liquidation_equity_proxy']));maxerr=max(maxerr,err);assert err<Q('1e-18')
  if name not in ['hold','exposure_hold']:
   for c in C:
    # Independent signal completeness from end-of-day inventory and raw windows.
    if any(coin==c and due>t for (due,coin) in expected):continue
    cl=Q(data[c][t][4]);side=None
    if pos[c]==0 and cl>max(Q(data[c][t-j*DAY][2]) for j in range(1,en+1)):side='buy'
    if pos[c]>0 and cl<min(Q(data[c][t-j*DAY][3]) for j in range(1,ex+1)):side='sell'
    if side and t+delay*DAY<=ms(m['end']):expected[(t+delay*DAY,c)]=side
 if name not in ['hold','exposure_hold']:assert expected==observed,(period,name,'missing or extra signals',len(expected),len(observed))
 assert abs(cash-2000-Q(str(m['net_pnl'])))<Q('1e-8')
 assert abs(sum(tradecash,Q(0))-(cash-2000))<Q('1e-18')
 assert len(tt)==len(tradecash)
 summary.append({'period':period,'variant':name,'fills':len(ff),'daily_equity_rows':len(cc),'signals_independently_checked':checksignals,'signal_completeness':True,'ending_cash_recomputed':str(cash),'max_daily_cash_identity_error':str(maxerr),'max_order_fraction_of_daily_volume':max_participation,'volume_is_not_depth_proof':True})
result={'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'phase':phase,'sources_hashes_checked':len(sources),'scenario_checks':summary,'max_cash_error':max(float(x['max_daily_cash_identity_error']) for x in summary),'actual_account_ledger':False,'execution_claim':'OHLC conditional arithmetic only'}
(P/('validation_'+phase+'.json')).write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps({'phase':phase,'scenarios':len(summary),'hashes':len(sources),'max_error':result['max_cash_error']}))
