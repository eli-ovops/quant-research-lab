from pathlib import Path
from decimal import Decimal as D,ROUND_FLOOR,ROUND_CEILING,getcontext
from collections import defaultdict
import json,csv,datetime,hashlib
getcontext().prec=40
O=Path(__file__).resolve().parent;B=O.parents[1]/'funding';F=B/'f1'
def rd(p):return json.loads(p.read_text())
def series(c,kind):
 out={}
 for p in (B/'raw').glob(c+'_'+kind+'_*.txt'):
  if kind=='funding' and not p.stem.rsplit('_',1)[-1].isdigit():continue
  for r in rd(p)['data']:out[int(r['fundingTime'] if kind=='funding' else r[0])]=r
 return out
def ts(s):return int(datetime.datetime.fromisoformat(s).replace(tzinfo=datetime.timezone.utc).timestamp()*1000)
def floor(x,s):return (x/s).to_integral_value(rounding=ROUND_FLOOR)*s
def ceil(x,s):return (x/s).to_integral_value(rounding=ROUND_CEILING)*s
def eq(a,b):assert abs(D(a)-b)<D('1e-25'),(a,b)
def key(r):return (r['coin'],r.get('start',r.get('block')),int(r['fee_multiplier']),int(r['slippage_bps_per_leg_side']),r['execution_mode'])
original=rd(F/'change_ledger.json')['original_files']
for r in original:assert hashlib.sha256((B/r['path']).read_bytes()).hexdigest()==r['sha256']
manifest=rd(F/'manifest_f1.json')['files']
for r in manifest:assert hashlib.sha256(Path(r['path']).read_bytes()).hexdigest()==r['sha256']
curves=defaultdict(list)
for r in csv.DictReader((F/'equity_curves_all.csv').open()):curves[key(r)].append(r)
old={key(r):r for r in rd(B/'scenarios_all.json')};new={key(r):r for r in rd(F/'scenarios_all.json')};assert old.keys()==new.keys() and len(new)==108
checks=[];hourcount=0;maxdelta=D(0);signchanges=0
for c in ['BTC','ETH']:
 sp=rd(B/'raw'/(c+'_spot_spec.txt'))['data'][0];sw=rd(B/'raw'/(c+'_swap_spec.txt'))['data'][0];lot=D(sp['lotSz']);unit=D(sw['ctVal'])*D(sw['ctMult']);clot=D(sw['lotSz'])
 spot=series(c,'spot_1H');fut=series(c,'swap_1H');mark=series(c,'mark_1H');rates=series(c,'funding')
 for k,r in new.items():
  if k[0]!=c:continue
  delay=3600000 if k[4]=='delay_1h' else 0;t0=ts(r['start'])+delay;t1=ts(r['end'])+delay;fee=D('.001')*k[2];swapfee=fee/2;sl=D(k[3])/10000
  ix=(2,3,3,2) if k[4]=='adverse_hour' else (1,1,1,1)
  a,z,b,y=[D(row[i]) for row,i in zip([spot[t0],spot[t1],fut[t0],fut[t1]],ix)];buy=a*(1+sl);sell=z*(1-sl);short=b*(1-sl);cover=y*(1+sl)
  contracts=floor(800*(1-fee)/buy/unit,clot)
  while True:
   q=contracts*unit;gross=ceil(q/(1-fee),lot)
   if gross*buy<=800:break
   contracts-=clot
  net=gross*(1-fee);sold=floor(net,lot);remain=net-sold
  assert D(sp['minSz'])<=sold<=D(sp['maxMktSz'])
  assert not sp.get('maxMktAmt') or sold*sell<=D(sp['maxMktAmt'])
  free=1200-gross*buy;fund=sum((q*D(mark[t][1])*D(v['realizedRate']) for t,v in rates.items() if t0<t<t1),D(0));proceeds=sold*sell*(1-fee)
  terminal=free+proceeds+800-q*short*swapfee+fund+q*(short-cover)-q*cover*swapfee
  for field,v in [('contracts',contracts),('gross_spot_base',gross),('net_spot_base',net),('sold_spot_base',sold),('remaining_spot_base',remain),('remaining_spot_realizable_value',D(0)),('cash_end',terminal),('net_pnl_proxy',terminal-2000),('spot_sell_fee',sold*sell*fee),('spot_hold_same_cash_allocation_pnl_proxy',proceeds-gross*buy)]:eq(r[field],v)
  assert not r['all_inventory_flat'] and remain>0 and sold%lot==0
  delta=terminal-2000-D(old[k]['net_pnl_proxy']);eq(delta,-remain*sell*(1-fee));maxdelta=max(maxdelta,abs(delta));signchanges+=((terminal>2000)!=(D(old[k]['net_pnl_proxy'])>0))
  seq=sorted(curves[k],key=lambda x:x['time']);assert len(seq)==721;peak=D(2000);peakts=t0;under=None;dd=D(0);recovered=0;first=None;last=D(2000);worst=D(0);daily={};fundcum=D(0)
  for rr in seq:
   t=ts(rr['time'])
   if t0<t<t1 and t in rates:fundcum+=q*D(mark[t][1])*D(rates[t]['realizedRate'])
   sx=D(spot[t][4])*(1-sl);fx=D(fut[t][4])*(1+sl)
   if t==t1:sx=sell;fx=cover
   hcash=sold*sx*(1-fee);equity=free+hcash+800-q*short*swapfee+fundcum+q*(short-fx)-q*fx*swapfee
   for field,v in [('equity_proxy',equity),('hypothetical_sold_base',sold),('retained_base',remain),('retained_realizable_value',D(0)),('spot_sale_cash',hcash),('spot_sale_fee',sold*sx*fee)]:eq(rr[field],v)
   worst=min(worst,equity-last);last=equity;daily[t//86400000]=equity
   if equity>=peak:
    if under is not None:recovered=max(recovered,(t-under)/3600000)
    peak=equity;peakts=t;under=None
   else:
    if under is None:under=peakts
    dd=max(dd,peak-equity)
   if first is None and equity>=2000:first=(t-t0)/86400000
   hourcount+=1
  ds=[];prev=D(2000)
  for t,v in sorted(daily.items()):ds.append(v-prev);prev=v
  for field,v in [('drawdown_usdt_hourly_proxy',dd),('worst_hour_proxy',worst),('worst_daily_change_proxy',min(ds))]:eq(r[field],v)
  assert r['max_completed_recovery_hours']==recovered and r['unrecovered_hours_at_exit']==((t1-under)/3600000 if under is not None else None) and r['net_cost_recovery_days_hourly_proxy']==first
  checks.append({'key':list(k),'cash':str(terminal),'remaining_base':str(remain),'net_delta':str(delta),'cash_inventory_metrics':'PASS'})
overlays=0
for r in csv.DictReader((F/'overheads_all.csv').open()):
 k=(r['coin'],r['start'],int(r['fee_multiplier']),int(r['slippage_bps']),r['mode']);eq(r['net_after_costs_proxy'],D(new[k]['net_pnl_proxy'])-D(r['operating_cost_30d'])-D(2000)*D(r['cash_opportunity_apr'])*30/365);overlays+=1
out={'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'reviewer':'C','original_hashes':len(original),'F1_manifest_hashes':len(manifest),'independent_terminal_cash_inventory':len(checks),'independent_hourly_valuations':hourcount,'independent_path_metrics':len(checks),'independent_cost_overlays':overlays,'sign_changes':signchanges,'max_pnl_reduction':str(maxdelta),'result':'PASS_F1_CONDITIONAL_ACCOUNTING_ONLY','details':checks}
(O/'funding_f1_checks.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:v for k,v in out.items() if k!='details'}))
