from pathlib import Path
import json,csv,statistics,math,random
P=Path(__file__).resolve().parent
rs=json.loads((P/'results_all.json').read_text())['scenarios'];equity=list(csv.DictReader((P/'equity_all.csv').open()));trades=list(csv.DictReader((P/'trades_all.csv').open()));checks=[]
def equal(a,b):assert abs(float(a)-b)<1e-9,(a,b)
for r in rs:
 cc=[x for x in equity if x['period']==r['period'] and x['variant']==r['variant']];tt=[x for x in trades if x['period']==r['period'] and x['variant']==r['variant']];e=[2000]+[float(x['valuation_equity']) for x in cc];changes=[e[i]/e[i-1]-1 for i in range(1,len(e))]
 peak=2000;peakat=0;maxdd=0;duration=0
 for i,v in enumerate(e):
  if v>=peak:peak=v;peakat=i
  maxdd=max(maxdd,1-v/peak);duration=max(duration,i-peakat)
 equal(r['max_drawdown'],maxdd);assert r['longest_underwater_days']==duration;equal(r['worst_day'],min(changes));equal(r['annualized_daily_vol'],statistics.stdev(changes)*math.sqrt(365));equal(r['net_pnl'],e[-1]-2000)
 p=[float(x['net_pnl']) for x in tt];winners=sorted([v for v in p if v>0],reverse=True);equal(r['pnl_without_top3_winners'],sum(p)-sum(winners[:3]))
 if winners:equal(r['top3_share_gross_gains'],sum(winners[:3])/sum(winners))
 seq=0;worst=0
 for v in p:seq=seq+1 if v<0 else 0;worst=max(worst,seq)
 assert worst==r['max_consecutive_losing_trades_exit_order'];assert r['max_holding_days']==max([int(x['days_held']) for x in tt],default=0)
 equal(sum(float(x['price_pnl'])-float(x['fees'])-float(x['slippage_and_tick'])-float(x['dust_writeoff']) for x in tt),r['net_pnl'])
 checks.append({'period':r['period'],'variant':r['variant'],'metric_check':'PASS'})
(P/'metrics_validation.json').write_text(json.dumps({'scenarios':checks,'scope':'Net/daily risk/drawdown/duration/volatility/trade concentration/loss streak/holding/decomposition independently recomputed from audited events'},indent=2)+'\n')
print('27 metric sets PASS')
