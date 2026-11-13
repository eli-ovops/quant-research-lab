from pathlib import Path
from decimal import Decimal as D,ROUND_FLOOR,ROUND_CEILING,getcontext
import json,datetime,hashlib
getcontext().prec=40
B=Path(__file__).resolve().parents[2]/'funding'; O=Path(__file__).resolve().parent
read=lambda f:json.loads((B/f).read_text())
def series(pat,idx):
 d={}
 for p in (B/'raw').glob(pat):
  if 'funding' in pat and not p.stem.split('_')[-1].isdigit():continue
  for r in json.loads(p.read_text())['data']:d[int(r[idx])]=r
 return d
def ms(s):return int(datetime.datetime.fromisoformat(s).replace(tzinfo=datetime.timezone.utc).timestamp()*1000)
def rnd(x,s,mode):return (x/s).to_integral_value(rounding=mode)*s
checks=[];dust=[]
for coin in ['BTC','ETH']:
 sp=read('raw/'+coin+'_spot_spec.txt')['data'][0];sw=read('raw/'+coin+'_swap_spec.txt')['data'][0]
 assert sp['baseCcy']==sw['ctValCcy']==coin and sw['ctType']=='linear' and sw['settleCcy']=='USDT'
 ss=series(coin+'_spot_1H_*.txt',0);ff=series(coin+'_swap_1H_*.txt',0);mm=series(coin+'_mark_1H_*.txt',0);rr=series(coin+'_funding_*.txt','fundingTime')
 for r in read('scenarios_all.json'):
  if r['coin']!=coin:continue
  t0=ms(r['start']);t1=ms(r['end']);mode=r['execution_mode']
  if mode=='delay_1h':t0+=3600000;t1+=3600000
  ix=(2,3,3,2) if mode=='adverse_hour' else (1,1,1,1)
  a,z,b,y=[D(v[i]) for v,i in zip([ss[t0],ss[t1],ff[t0],ff[t1]],ix)]
  f=D('.001')*r['fee_multiplier'];sf=f/2;sl=D(r['slippage_bps_per_leg_side'])/10000
  buy=a*(1+sl);sell=z*(1-sl);short=b*(1-sl);cover=y*(1+sl)
  unit=D(sw['ctVal'])*D(sw['ctMult']);lot=D(sw['lotSz']);step=D(sp['lotSz'])
  contracts=rnd(D(800)*(1-f)/buy/unit,lot,ROUND_FLOOR)
  while True:
   q=contracts*unit;g=rnd(q/(1-f),step,ROUND_CEILING)
   if g*buy<=800:break
   contracts-=lot
  net=g*(1-f);fund=sum((q*D(mm[t][1])*D(v['realizedRate']) for t,v in rr.items() if t0<t<t1),D(0))
  reserve=1200-g*buy;collateral=800-q*short*sf+fund+q*(short-cover)-q*cover*sf
  pnl=reserve+net*sell*(1-f)+collateral-2000
  assert reserve>=400 and q==D(r['hedged_base']) and g==D(r['gross_spot_base'])
  assert abs(pnl-D(r['net_pnl_proxy']))<D('1e-26')
  assert abs(fund-D(r['funding_proxy']))<D('1e-26')
  rem=net-rnd(net,step,ROUND_FLOOR)
  dust.append(float(rem*sell))
  checks.append({'coin':coin,'start':r['start'],'mode':mode,'fees':r['fee_multiplier'],'slip_bps':r['slippage_bps_per_leg_side'],'pnl':str(pnl),'cash_error':str(pnl-D(r['net_pnl_proxy'])),'off_lot_sell_base':str(rem)})
src=read('sources.json')
for s in src:assert hashlib.sha256(Path(s['path']).read_bytes()).hexdigest()==s['sha256']
seal=read('seal.json')
assert hashlib.sha256((B/'analyze.py').read_bytes()).hexdigest()==seal['analysis_sha256']
out={'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source_hashes':len(src),'independent_sizing_and_cash_checks':len(checks),'max_cash_error':max(abs(float(x['cash_error'])) for x in checks),'non_step_exit_quantity_cases':sum(D(x['off_lot_sell_base'])!=0 for x in checks),'max_dust_quote_impact':max(dust),'qualification':'B arithmetic consistent; exit net-base not rounded to lot, so executable ledger unproven. Conditional insufficient-evidence verdict preserved.','details':checks}
(O/'funding_checks.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n');print({k:v for k,v in out.items() if k!='details'})
