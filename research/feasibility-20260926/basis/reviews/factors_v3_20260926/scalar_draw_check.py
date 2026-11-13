from pathlib import Path
import json,math,hashlib
import numpy as np
import pandas as pd
O=Path(__file__).resolve().parent;P=O.parents[2]/'trend/factors_v3_20260926'
# O.parents[2] is research/feasibility-20260926.
r=json.loads((O/'review.json').read_text());draw=json.loads((O/'replicate0_common_draw.json').read_text());proto=json.loads((P/'protocol.json').read_text());fits=json.loads((P/'fitted_training_thresholds.json').read_text());F=list(proto['features']);out=[0.0]*16;cells=[]
for fold in proto['folds']:
 day0=int(pd.Timestamp(fold['eval_start'],tz='UTC').timestamp())//86400;w=draw[fold['name']]['day_counts']
 for coin in ['BTC','ETH']:
  d=pd.read_csv(P/(coin+'_'+fold['name']+'_signals_labels.csv.gz'));ft=fits[coin+'_'+fold['name']];wt=[w[int(x)-day0] for x in d.day];keys=list(zip(d.month,d.hourbucket,np.searchsorted(ft['match']['past_vol24'],d.past_vol24,side='right'),np.searchsorted(ft['match']['past_trend168'],d.past_trend168,side='right')))
  for f in F:
   hi=[int(i) for i in np.flatnonzero(d[f+'_q'].to_numpy()==5)];control={}
   for i,q in enumerate(d[f+'_q']):
    if q<5:control.setdefault(keys[i],[]).append(i)
   sup=[i for i in hi if len(control.get(keys[i],[]))>=5]
   for h in [4,24]:
    y=d[f'{h}_baseline_net'].tolist();absolute=math.fsum(wt[i]*y[i] for i in hi)/sum(wt[i] for i in hi);valid=True;numerator=[]
    for i in sup:
     if wt[i]==0:continue
     ctr=control[keys[i]];den=sum(wt[k] for k in ctr)
     if not den:valid=False;break
     cm=math.fsum(wt[k]*y[k] for k in ctr)/den;numerator.append(wt[i]*(y[i]-cm))
    inc=math.fsum(numerator)/sum(wt[i] for i in sup) if valid else float('nan');j=F.index(f)*4+[4,24].index(h)*2;out[j]+=absolute/6;out[j+1]+=inc/6;cells.append(dict(coin=coin,fold=fold['name'],factor=f,h=h,absolute=absolute,increment=inc if valid else None,valid=valid))
expected=np.load(O/'A_bootstrap_recomputed.npz')['estimators'][0];np.testing.assert_allclose(out,expected,atol=1e-12,rtol=1e-10,equal_nan=True)
C=json.loads((P/'independent_audit.json').read_text());lookup={(x['coin'],x['fold'],x['factor'],x['h']):x['matching_unavailable_reps'] for x in C['bootstrap_cell_checks']}
assert all(lookup[(x['coin'],x['fold'],x['factor'],x['h'])]==x['invalid'] for x in r['bootstrap']['cell_checks'])
r['bootstrap']['scalar_event_by_event_replicate0_all48cells_matches']=True;r['bootstrap']['C_reported_48cell_invalid_counts_match']=True
e=pd.read_csv(O/'eligibility_recomputed.csv');r['table_scope_summary']['matched_q5_n_range']=r['table_scope_summary'].pop('q5_n_range');r['table_scope_summary']['q5_n_range']=[int(e.q5_n.min()),int(e.q5_n.max())]
r['table_scope_summary']['valid_rate_range']=[float(e.valid_rate.min()),float(e.valid_rate.max())]
(O/'scalar_draw_check.json').write_text(json.dumps({'passed':True,'replicate':0,'shared_draws':'replicate0_common_draw.json','scalar48cells':cells,'all16_endpoints_match':True},indent=2))
(O/'review.json').write_text(json.dumps(r,ensure_ascii=False,indent=2));print('SCALAR FIRST JOINT DRAW PASS; all48 cell invalid-count totals match C; q5 count labels clarified.')
