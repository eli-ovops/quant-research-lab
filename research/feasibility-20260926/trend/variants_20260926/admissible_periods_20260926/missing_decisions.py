"""Frozen candidate gates with explicit missing early evidence; no reduced gate."""
from decimal import Decimal as D
import math

def conjunction(values):
 return False if False in values else (None if None in values else True)
def label(x):return 'UNKNOWN' if x is None else ('PASS' if x else 'FAIL')
def decide(rows,family):
 index={(r['period'],r['entry'],r['exit'],r['condition']):r for r in rows if r['mode']=='trend'};grid=[(a,b) for a in [24,48,72] for b in [4,8,12]]
 def metric(p,k,c,field):
  r=index[(p,*k,c)];return None if r['status']!='COMPUTED_VALIDATED' else r['metrics'][field]
 def positive(p,k,c):
  v=metric(p,k,c,'net_pnl');return None if v is None else D(v)>0
 profitable={k:conjunction([positive(p,k,c) for p,c in [('early','baseline'),('middle','baseline')]+[('latest',s) for s in ['baseline','fee2','slip20','delay1']]]) for k in grid};out=[]
 for k in grid:
  en,ex=k;neighbors=[q for q in grid if abs([24,48,72].index(q[0])-[24,48,72].index(en))+abs([4,8,12].index(q[1])-[4,8,12].index(ex))==1];need=max(2,math.ceil(len(neighbors)/2));yes=sum(profitable[n] is True for n in neighbors);unknown=sum(profitable[n] is None for n in neighbors);neighbor=True if yes>=need else (False if yes+unknown<need else None)
  maxdds=[metric(p,k,c,'max_drawdown') for p,c in [('early','baseline'),('middle','baseline')]+[('latest',c) for c in ['baseline','fee2','slip20','delay1']]];risk=conjunction([None if v is None else D(v)<=D('.4') for v in maxdds]);latest=index[('latest',en,ex,'baseline')]['metrics'];ci=family['candidates'][str(en)+'/'+str(ex)]
  years=[y for p in ['early','middle','latest'] for y in index[(p,en,ex,'baseline')]['slices']['yearly']];assert len(years)==7;missing_years=sum(y['net_change_usdt'] is None for y in years);positive_years=sum(y['net_change_usdt'] is not None and D(y['net_change_usdt'])>0 for y in years)
  gates={'early_baseline_positive':positive('early',k,'baseline'),'middle_baseline_positive':positive('middle',k,'baseline'),'latest_all4_positive':conjunction([positive('latest',k,c) for c in ['baseline','fee2','slip20','delay1']]),'neighbor_support':neighbor,'baseline_and_latest_stress_DD_le40pct':risk,'top5_share_le40pct':latest['top5_share_gross_gains'] is not None and D(latest['top5_share_gross_gains'])<=D('.4'),'net_excluding_top5_positive':D(latest['pnl_without_top5_winners'])>0,'at_least5of7_positive_calendar_slices':None if missing_years else positive_years>=5,'at_least30_latest_clusters':latest['exposure_clusters']>=30,'simultaneous_cash_lower_positive':ci['simultaneous95_lower']>0,'reliability_screen':ci['reliability_screen_pass']}
  out.append({'entry':en,'exit':ex,'primary':k==(24,4),'checks':{key:label(v) for key,v in gates.items()},'known_required_failures':[key for key,v in gates.items() if v is False],'unknown_required_checks':[key for key,v in gates.items() if v is None],'visible_requirements_status':'FAIL' if False in gates.values() else 'NO_OBSERVED_FAILURE','full_research_evidence':'INSUFFICIENT_EVIDENCE','full_candidate_pass':None,'exploratory_followup_candidate':None,'neighbors':neighbors,'required_neighbor_support':need,'known_support':yes,'unknown_neighbor_support':unknown,'positive_observed_calendar_slices':positive_years,'missing_calendar_slices':missing_years,'true_feasibility':'INSUFFICIENT_EVIDENCE'})
 return out
