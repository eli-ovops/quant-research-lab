"""Supplementary metrics from second implementation events/raw, no main engine imports."""
from decimal import Decimal as D
H=3600000;Z=D(0)
def compute(case,replay):
 data={c:{int(r[0]):list(map(D,r[1:8])) for r in rr} for c,rr in case['raw'].items()};slip=D('.002') if case['condition']=='slip20' else D('.0005');positions={};trades=[];spans=[]
 for t,c,side,q,px,bf,qf,cash in replay['fills']:
  if side=='buy':positions[c]={'q':q,'net':q-bf,'px':px,'ref':data[c][t][0],'bf':bf,'cost':q*px,'t':t}
  else:
   h=positions.pop(c);ref=data[c][t-H][3] if t==case['end'] else data[c][t][0];rem=h['net']-q;net=q*px-qf-h['cost'];spans.append((h['t'],t))
   trades.append({'coin':c,'net_pnl':net,'holding_hours':D(t-h['t'])/H,'price_pnl':h['net']*(ref-h['ref']),'fees':h['bf']*h['px']+qf,'slippage':slip*(h['net']*h['ref']+q*ref),'tick_rounding':h['net']*(h['px']-h['ref']*(1+slip))+q*(ref*(1-slip)-px),'dust_writeoff':rem*ref})
 curves=replay['curve'];vals=[D(2000)]+[x['valuation_equity'] for x in curves];top=D(2000);top_i=0;under=False;maxdd=Z;duration=0;recoveries=[]
 for i,v in enumerate(vals):
  if v>=top:
   if under:recoveries.append(i-top_i)
   top=v;top_i=i;under=False
  else:under=True;maxdd=max(maxdd,(top-v)/top);duration=max(duration,i-top_i)
 daily={}
 for r in curves:daily[r['t']//(24*H)]=r['valuation_equity']
 dr=[];previous=D(2000)
 for v in daily.values():dr.append((v-previous)/previous);previous=v
 pnls=[t['net_pnl'] for t in trades];gains=sorted([x for x in pnls if x>0],reverse=True);losses=[x for x in pnls if x<0];run=0;losing=0
 for x in pnls:run=(run+1) if x<0 else 0;losing=max(run,losing)
 for h in positions.values():spans.append((h['t'],case['end']))
 merged=[]
 for a,b in sorted(spans):
  if merged and a<merged[-1][1]:merged[-1][1]=max(b,merged[-1][1])
  else:merged.append([a,b])
 exposure=[]
 for r in curves:
  held=sum(r[c+'_qty']*data[c][r['t']][3] for c in ('BTC','ETH'));exposure.append(held/r['raw_equity'] if r['raw_equity'] else Z)
 turn=sum(q*p for _,_,_,q,p,_,_,_ in replay['fills']);count=len(pnls);last=curves[-1];total=lambda k:sum((r[k] for r in trades),Z);holding_open=sum((D(case['end']-h['t'])/H for h in positions.values()),Z)
 return dict(final_equity=vals[-1],net_pnl=vals[-1]-2000,return_full_2000=(vals[-1]-2000)/2000,final_cash=last['cash'],unresolved_positions=len(positions),liquidation_equity_proxy=last['liquidation_equity_proxy'],fills=len(replay['fills']),closed_trades=count,rejections=len(replay['rejections']),turnover_usdt=turn,turnover_multiple=turn/2000,win_rate=D(len(gains))/count if count else None,average_win=sum(gains,Z)/len(gains) if gains else None,average_loss=sum(losses,Z)/len(losses) if losses else None,max_drawdown=maxdd,longest_underwater_hours=duration,unrecovered_hours_at_end=len(vals)-1-top_i if vals[-1]<top else 0,max_completed_recovery_hours=max(recoveries,default=None),max_consecutive_losses=losing,worst_day=min(dr),worst_trade=min(pnls,default=None),tail5_trades=sorted(pnls)[:5],holding_hours=total('holding_hours')+holding_open,holding_hours_closed=total('holding_hours'),holding_hours_open=holding_open,top5_share_gross_gains=sum(gains[:5],Z)/sum(gains,Z) if gains else None,pnl_without_top5_winners=sum(pnls,Z)-sum(gains[:5],Z),exposure_clusters=len(merged),cluster_intervals=merged,mean_exposure=sum(exposure,Z)/len(exposure),max_exposure=max(exposure),price_pnl=total('price_pnl'),fees=total('fees'),slippage=total('slippage'),tick_rounding=total('tick_rounding'),dust_writeoff=total('dust_writeoff'),by_coin={c:sum((tr['net_pnl'] for tr in trades if tr['coin']==c),Z) for c in ('BTC','ETH')},extra_cost_capacity_usdt=max(Z,vals[-1]-2000),break_even_extra_cost_bps_static=(vals[-1]-2000)/turn*10000 if turn else None,daily_returns=dr,daily_utc_keys=list(daily))

def assert_close(a,b,path=''):
 if isinstance(b,dict):
  for k,v in b.items():assert_close(a[k],v,path+'/'+k)
 elif isinstance(b,(list,tuple)):
  assert len(a)==len(b),path
  for i,(x,y) in enumerate(zip(a,b)):assert_close(x,y,path+'/'+str(i))
 elif isinstance(b,D):assert abs(D(a)-b)<D('1e-22'),(path,a,b)
 else:assert a==b,(path,a,b)
