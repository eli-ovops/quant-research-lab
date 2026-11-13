"""Frozen V2 diagnostics. Deterministic; no parameter optimization."""
import random,math,datetime
from decimal import Decimal as D
H=3600000;DAY=24*H

def slices(run,windows):
 curve=run['curve'];lookup={r['t']:r['valuation_equity'] for r in curve};start,end=run['start'],run['end']
 def measure(a,b):
  prior=D(2000) if a==start else lookup[a-H];final=lookup[b-H];v=[prior]+[lookup[t] for t in range(a,b,H)];peak=prior;dd=D(0)
  for x in v:peak=max(peak,x);dd=max(dd,1-x/peak)
  return {'start':a,'end':b,'begin_equity':prior,'end_equity':final,'net_change_usdt':final-prior,'return':final/prior-1,'max_drawdown_with_local_peak':dd,'holding_reset':False}
 ms=lambda s:int(datetime.datetime.fromisoformat(s).timestamp()*1000)
 rolling=[measure(ms(w['start_inclusive']),ms(w['end_exclusive'])) for w in windows if start<=ms(w['start_inclusive']) and ms(w['end_exclusive'])<=end]
 years=[];year=datetime.datetime.fromtimestamp(start/1000,datetime.timezone.utc).year
 while True:
  y0=int(datetime.datetime(year,1,1,tzinfo=datetime.timezone.utc).timestamp()*1000);y1=int(datetime.datetime(year+1,1,1,tzinfo=datetime.timezone.utc).timestamp()*1000)
  if y0>=end:break
  item=measure(max(start,y0),min(end,y1));item.update(year=year,partial_year=(max(start,y0)!=y0 or min(end,y1)!=y1));years.append(item);year+=1
 return {'yearly':years,'rolling':rolling}

def simultaneous(returns,clusters,reps=2000,seed=2026092602,block=30):
 keys=sorted(returns);n=len(returns[keys[0]]);assert len(keys)==9 and all(len(returns[k])==n for k in keys) and n>0
 x={k:list(map(float,returns[k])) for k in keys};means={k:sum(x[k])/n*365 for k in keys};full,rem=divmod(n,block)
 sums={k:[sum(x[k][(i+j)%n] for j in range(block)) for i in range(n)] for k in keys};tails={k:[sum(x[k][(i+j)%n] for j in range(rem)) for i in range(n)] for k in keys}
 rng=random.Random(seed);deviations=[]
 for _ in range(reps):
  starts=[rng.randrange(n) for j in range(full+(rem>0))];scores=[]
  for k in keys:
   total=sum(sums[k][st] for st in starts[:full])+(tails[k][starts[-1]] if rem else 0);scores.append(abs(total/n*365-means[k]))
  deviations.append(max(scores))
 q=sorted(deviations)[math.ceil(.95*reps)-1];out={}
 for k in keys:out[k]={'annual_arithmetic_excess_vs_cash':means[k],'simultaneous95_lower':means[k]-q,'simultaneous95_upper':means[k]+q,'reliability_screen_pass':n>=365 and clusters[k]>=30,'days':n,'clusters':clusters[k]}
 return {'method':'Circular blocks; common draws across nine candidates;95%max absolute centered annual arithmetic mean deviation; nearest-rank quantile','block_days':block,'replicates':reps,'seed':seed,'common_half_width':q,'family_size':9,'family_all_reliability_screens_pass':all(v['reliability_screen_pass'] for v in out.values()),'candidates':out,'limitation':'Exploratory reused history; bootstrap does not remove prior family selection or regime dependence. Nominal cash0 is not opportunity cost.'}

def decisions(results,family):
 index={(r['period'],r['entry'],r['exit'],r['condition']):r for r in results if r['mode']=='trend'};keys=[(en,ex) for en in (24,48,72) for ex in (4,8,12)]
 profitability={key:all(D(str(index[(p,*key,c)]['metrics']['net_pnl']))>0 for p,c in [('early','baseline'),('middle','baseline')]+[('latest',s) for s in ('baseline','fee2','slip20','delay1')]) for key in keys};out=[]
 for en,ex in keys:
  en_i=[24,48,72].index(en);ex_i=[4,8,12].index(ex);neighbors=[(a,b) for a,b in keys if abs([24,48,72].index(a)-en_i)+abs([4,8,12].index(b)-ex_i)==1];needed=max(2,math.ceil(len(neighbors)/2));supported=sum(profitability[k] for k in neighbors)
  baseline=[index[(p,en,ex,'baseline')] for p in ['early','middle','latest']];latest=[index[('latest',en,ex,c)] for c in ('baseline','fee2','slip20','delay1')];main=baseline[-1]['metrics'];years=[s for r in baseline for s in r['slices']['yearly']];positive_years=sum(D(str(s['net_change_usdt']))>0 for s in years);assert len(years)==7
  checks={'earlier_and_all_latest_positive':profitability[(en,ex)],'neighbor_support':supported>=needed,'baseline_and_latest_stress_DD_le40pct':all(D(str(r['metrics']['max_drawdown']))<=D('.4') for r in baseline+latest),'top5_share_le40pct':main['top5_share_gross_gains'] is not None and D(str(main['top5_share_gross_gains']))<=D('.4'),'net_excluding_top5_positive':D(str(main['pnl_without_top5_winners']))>0,'at_least5_positive_calendar_slices':positive_years>=5,'at_least30_latest_clusters':main['exposure_clusters']>=30,'simultaneous_cash_lower_positive':family['candidates'][str(en)+'/'+str(ex)]['simultaneous95_lower']>0,'reliability_pass':family['candidates'][str(en)+'/'+str(ex)]['reliability_screen_pass']}
  out.append({'entry':en,'exit':ex,'primary':(en,ex)==(24,4),'neighbors':neighbors,'support':supported,'required':needed,'positive_year_slices':positive_years,'checks':checks,'exploratory_followup_candidate':all(checks.values()),'true_feasibility':'INSUFFICIENT_EVIDENCE'})
 return out
