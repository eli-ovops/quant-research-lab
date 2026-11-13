from pathlib import Path
import json,copy,itertools
import analyze,source_gate,missing_decisions
P=Path(__file__).resolve().parent
proto=json.loads((P.parent/'protocol.json').read_text())
rows=analyze.blocked_rows(proto)
assert len(rows)==40 and sum(r['mode']=='trend' for r in rows)==36
assert all(len(r['slices']['yearly'])==3 and len(r['slices']['rolling'])==11 and all(v is None for v in r['metrics'].values()) for r in rows)
assert all('return' in y and y['return'] is None for r in rows for y in r['slices']['yearly'])
for period in ['middle','latest']:
 for en,ex,c in itertools.product([24,48,72],[4,8,12],['baseline','fee2','slip20','delay1']):
  rows.append(dict(period=period,entry=en,exit=ex,condition=c,mode='trend',status='COMPUTED_VALIDATED',metrics=dict(net_pnl=10,max_drawdown=.1,top5_share_gross_gains=.2,pnl_without_top5_winners=5,exposure_clusters=40),slices={'yearly':[{'net_change_usdt':1},{'net_change_usdt':1}]}))
family={'candidates':{str(a)+'/'+str(b):dict(simultaneous95_lower=.1,reliability_screen_pass=True) for a,b in itertools.product([24,48,72],[4,8,12])}}
d=missing_decisions.decide(rows,family)
assert len(d)==9 and all(x['full_candidate_pass'] is None and x['missing_calendar_slices']==3 and x['positive_observed_calendar_slices']==4 and x['checks']['at_least5of7_positive_calendar_slices']=='UNKNOWN' and x['checks']['neighbor_support']=='UNKNOWN' and not x['known_required_failures'] for x in d)
next(r for r in rows if (r['period'],r['entry'],r['exit'],r['condition'])==('latest',24,4,'fee2'))['metrics']['net_pnl']=-1
d=missing_decisions.decide(rows,family);assert d[0]['checks']['latest_all4_positive']=='FAIL' and d[0]['full_candidate_pass'] is None
try:source_gate.for_period({},'early');raise AssertionError('early admitted')
except ValueError as e:assert 'period_not_admitted' in str(e)
raw,proof=source_gate.load();gates={}
for period in ['middle','latest']:
 selected,start,end,checks=source_gate.for_period(raw,period);gates[period]=checks
broken={k:dict(v) for k,v in raw.items()};del broken['BTC'][start-80*3600000]
try:source_gate.for_period(broken,'latest');raise AssertionError('missing warmup admitted')
except ValueError as e:assert 'missing_warmup' in str(e)
broken={k:dict(v) for k,v in raw.items()};t=start-80*3600000;broken['BTC'][t]=list(broken['BTC'][t]);broken['BTC'][t][5]='0'
try:source_gate.for_period(broken,'latest');raise RuntimeError('zero admitted')
except AssertionError:pass
(P/'pre_pnl_tests.json').write_text(json.dumps({'pass':True,'tests':['40 null placeholders and original slice schema','9 candidates and unchanged7year denominator','all positive visible cannot pass full gate','known negative stress remains FAIL','early admission rejected','both actual admitted input periods exact gate','missing warmup rejected','zero volume rejected'],'source':proof,'gates':gates,'historical_PnL_runs':0},indent=2))
print('PASS targeted missing-data/admission tests; historicalPnL=0')
