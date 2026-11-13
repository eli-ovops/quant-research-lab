from pathlib import Path
import json,csv,hashlib,importlib.util,datetime,difflib
from decimal import Decimal as D
import analyze as new
P=Path(__file__).resolve().parent;O=P.parent
spec=importlib.util.spec_from_file_location('original_c1_readonly',O/'analyze.py');old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
data,sp,audit=new.load();results=json.loads((P/'results_all.json').read_text());budgets={c:D(v) for c,v in results['benchmark_budgets'].items()};diff=[]
for r in results['scenarios']:
 name=r['variant'];en,ex=(15,7) if name=='short' else (30,15) if name=='long' else (20,10);fee=D('.002') if name=='fee2' else D('.003') if name=='severe' else D('.001');slip=D('.002') if name=='slip20' else D('.005') if name=='severe' else D('.0005')
 kwargs={'budgets':{c:D(800) for c in ['BTC','ETH']} if name=='hold' else budgets,'reserve':D(0)} if name in ['hold','exposure_hold'] else {}
 rr=old.simulate(data,sp,r['start'],r['end'],en,ex,fee,slip,1 if name=='delay1' else 0,**kwargs);m=old.metrics(rr);delta=r['net_pnl']-m['net_pnl'];assert abs(delta)<1e-8
 diff.append({'period':r['period'],'variant':name,'original_code_on_same_new_data':m['net_pnl'],'corrected_code':r['net_pnl'],'difference':delta,'reason':'No invalid-sale events in actual27 conditions; bug matters at rejection boundary'})
from test_analysis import make,SPEC
s={c:dict(SPEC[c],minSz='7.99') for c in ['BTC','ETH']};d,a,b=make(['100']*49+['140']);rr=old.simulate(d,s,a,b,budgets={'BTC':D(800),'ETH':D(800)});nr=new.simulate(d,s,a,b,budgets={'BTC':D(800),'ETH':D(800)})
boundary={'old_terminal_BTC_qty':str(rr['curve'][-1]['BTC_qty']),'new_terminal_BTC_qty':str(nr['curve'][-1]['BTC_qty']),'old_terminal_equity':str(rr['curve'][-1]['liquidation_equity_proxy']),'new_marked_equity':str(nr['curve'][-1]['valuation_equity']),'new_liquidatable_equity':nr['curve'][-1]['liquidation_equity_proxy'],'new_open_positions':len(nr['open_positions']),'correction':'Rejected shares retained; marked risk tracked; executable liquidation value unknown, not falsely flat'}
(P/'implementation_differences.json').write_text(json.dumps({'historical':diff,'synthetic_rejection':boundary},indent=2)+'\n')
(P/'implementation.diff').write_text(''.join(difflib.unified_diff((O/'analyze.py').read_text().splitlines(True),(P/'analyze.py').read_text().splitlines(True),fromfile='original/analyze.py',tofile='resume/analyze.py')))
curves=list(csv.DictReader((P/'equity_all.csv').open()));trades=list(csv.DictReader((P/'trades_all.csv').open()));yearly=[];clusters=[]
for r in results['scenarios']:
 subset=[x for x in curves if x['period']==r['period'] and x['variant']==r['variant']];prev=2000.
 for y in sorted({x['date'][:4] for x in subset}):
  yy=[x for x in subset if x['date'].startswith(y)];eqs=[prev]+[float(x['valuation_equity']) for x in yy];peak=prev;dd=0.
  for e in eqs:peak=max(peak,e);dd=max(dd,1-e/peak)
  yearly.append({'period':r['period'],'variant':r['variant'],'year':y,'days':len(yy),'start_equity':prev,'end_equity':eqs[-1],'marked_pnl':eqs[-1]-prev,'max_drawdown_within_year':dd,'note':'Within a separately reset period; do not sum as one continuous strategy'});prev=eqs[-1]
 if r['variant']=='main':
  ts=sorted([t for t in trades if t['period']==r['period'] and t['variant']=='main'],key=lambda x:x['entry_date']);groups=[]
  for t in ts:
   if not groups or t['entry_date']>groups[-1]['end']:groups.append({'start':t['entry_date'],'end':t['exit_date'],'trades':1})
   else:groups[-1]['end']=max(groups[-1]['end'],t['exit_date']);groups[-1]['trades']+=1
  clusters.append({'period':r['period'],'trades':len(ts),'overlapping_exposure_clusters':len(groups),'groups':groups,'not_independence_proof':True})
with (P/'yearly.csv').open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=list(yearly[0]));w.writeheader();w.writerows(yearly)
(P/'dependence_clusters.json').write_text(json.dumps(clusters,indent=2)+'\n')
# Raw-price hand-check candidates: first trade and worst holdout loss; no strategy rerun.
main=[t for t in trades if t['variant']=='main'];selected=[main[0],min([t for t in main if t['period']=='sealed_exploratory'],key=lambda t:D(t['net_pnl']))];manual=[]
for t in selected:
 c=t['coin'];en=new.ts(t['entry_date']);sig=new.ts(t['entry_signal']);ex=new.ts(t['exit_date']);rawin=data[c][en]['o'];rawout=data[c][ex]['c' if t['reason']=='scheduled_terminal' else 'o'];gross=D(t['gross_qty']);net=D(t['net_qty']);sold=D(t['sold_qty']);buyprice=D(t['entry_price']);sellprice=D(t['exit_price']);sellfee=(sold*sellprice*D('.001')/D('1e-8')).to_integral_value(rounding='ROUND_CEILING')*D('1e-8');cost=gross*buyprice;receipt=sold*sellprice-sellfee
 assert abs(receipt-cost-D(t['net_pnl']))<D('1e-18');manual.append({'period':t['period'],'coin':c,'entry_date':t['entry_date'],'exit_date':t['exit_date'],'signal_close':str(data[c][sig]['c']),'previous20_high':str(max(data[c][sig-j*new.DAY]['h'] for j in range(1,21))),'next_open':str(rawin),'exit_raw':str(rawout),'gross_buy_qty':str(gross),'net_after_buy_fee':str(net),'sell_lot_qty':str(sold),'buy_price_including_slip_tick':str(buyprice),'sell_price_including_slip_tick':str(sellprice),'cash_paid':str(cost),'cash_received':str(receipt),'net':str(receipt-cost),'identity':'gross*buyprice cash debit; floor(net,lot)*sellprice minus rounded sell fee credit'})
(P/'manual_trade_checks.json').write_text(json.dumps(manual,indent=2)+'\n')
for x in json.loads((P/'resume_record.json').read_text())['original_files']:assert hashlib.sha256(Path(x['path']).read_bytes()).hexdigest()==x['sha256']
seal=json.loads((P/'seal.json').read_text());assert hashlib.sha256((P/'analyze.py').read_bytes()).hexdigest()==seal['analysis_sha256'];assert hashlib.sha256((P/'benchmark_calibration.json').read_bytes()).hexdigest()==seal['benchmark_calibration_sha256']
print('old artifacts retained;27 unchanged historical PnLs; rejection counterexample',boundary);print('yearly rows',len(yearly));print('clusters',[(r['period'],r['overlapping_exposure_clusters']) for r in clusters])
