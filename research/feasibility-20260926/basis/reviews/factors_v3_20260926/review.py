from pathlib import Path
import json, hashlib, datetime, warnings, ast
import numpy as np
import pandas as pd
P=Path('/Volumes/EXTERNAL/量化/research/feasibility-20260926/trend/factors_v3_20260926')
O=Path(__file__).resolve().parent
J=lambda p:json.loads(Path(p).read_text())
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
proto=J(P/'protocol.json');fits=J(P/'fitted_training_thresholds.json');F=list(proto['features']);S=list(proto['states']);H=3600000
res={'scope':'REVIEW_FACTOR_V3_ONLY','owner':'A','UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'method':'Independent raw array formulas; no C code imported or executed','tolerances':{'features_atol':1e-8,'features_rtol':1e-8,'tables_atol':2e-12,'bootstrap_atol':1e-12,'bootstrap_rtol':1e-10}}
checks={}; maxerr={}
def eq(a,b,name,atol=2e-12,rtol=1e-10):
 a=np.asarray(a,float);b=np.asarray(b,float);np.testing.assert_allclose(a,b,atol=atol,rtol=rtol,equal_nan=True,err_msg=name)
 z=np.abs(a-b);finite=z[np.isfinite(z)];maxerr[name]=float(finite.max()) if finite.size else 0
# Verify all frozen/package/source hashes; retain initial package inventory for end check.
manifest=J(P/'manifest.json');seal=J(P/'seal.json');assert sha(P/'manifest.json')==seal['manifest_sha256'];initial={r['path']:sha(P/r['path']) for r in manifest['files']}
assert all(initial[r['path']]==r['sha256'] and (P/r['path']).stat().st_size==r['bytes'] for r in manifest['files']);checks['package_files']=len(initial)
for name in ['analysis_freeze.json']:
 for n,h in J(P/name)['files'].items():assert sha(P/n)==h,(name,n)
src=J(P/'source_manifest.json')
for n,h in src['input_files'].items():assert sha(P/n)==h
for n,h in src['reused_gate'].items():assert sha(n)==h,n
assert sha(P/'protocol.json')==seal['protocol_sha256']==J(P/'protocol_freeze.json')['sha256'];assert sha(P/'analysis_freeze.json')==seal['analysis_freeze_sha256']
times=[J(P/'protocol_freeze.json')['UTC'],J(P/'analysis_freeze.json')['UTC'],J(P/'first_results_run.json')['UTC'],J(P/'first_model_result_access.json')['UTC']];assert times==sorted(times);res['recorded_chronology']=times;res['chronology_limit']='Hash-bound records and current files agree; local timestamps are not external tamper-proof attestation; reused history is exploratory.'
market=J(P.parent/'variants_20260926/full_history_20260926/market_sources.json');merged={'BTC':{},'ETH':{}};nsource=0
for r in market:
 for k,hk in [('path','sha256'),('normalized_path','normalized_sha256')]:assert sha(r[k])==r[hk];nsource+=1
 coin=r['id'].split('_')[0]
 for row in J(r['normalized_path'])['data']:
  t=int(row[0])
  if t in merged[coin]:assert merged[coin][t]==row
  merged[coin][t]=row
checks['raw_and_normalized_source_hashes']=nsource
raws={};features={};total_labels=0
for coin in ['BTC','ETH']:
 rows=J(P/(coin+'_input.json'));a=np.array(rows,float);raws[coin]=a
 assert len(a)==30648 and (np.diff(a[:,0])==H).all() and (a[:,8]==1).all()
 for r in rows:assert np.array_equal(np.array(merged[coin][int(r[0])],float),np.array(r,float))
 c=a[:,4];lr=np.r_[np.nan,np.log(c[1:]/c[:-1])];tr=np.maximum.reduce([a[:,2]-a[:,3],abs(a[:,2]-np.r_[c[0],c[:-1]]),abs(a[:,3]-np.r_[c[0],c[:-1]])]);d={k:np.full(len(a),np.nan) for k in F+S+['past_vol24','past_trend168']}
 delta=np.diff(c);gain=np.maximum(delta[:14],0).mean();loss=np.maximum(-delta[:14],0).mean()
 for i in range(14,len(a)):
  if i>14:gain=(13*gain+max(delta[i-1],0))/14;loss=(13*loss+max(-delta[i-1],0))/14
  if i<168:continue
  rr=lr[i-23:i+1];cc=c[i-23:i+1];v=np.std(rr);d['momentum24'][i]=sum(rr)/(v*np.sqrt(24));d['efficiency24'][i]=sum(rr)/sum(abs(rr));d['reversion24'][i]=-(c[i]-cc.mean())/cc.std();d['rsi14_negative'][i]=-.5 if gain==loss==0 else -gain/(gain+loss);d['atr_ratio'][i]=tr[i-13:i+1].mean()/tr[i-167:i+1].mean();d['quote_volume_ratio'][i]=a[i,7]/np.median(a[i-168:i,7]);d['past_vol24'][i]=v;d['past_trend168'][i]=np.log(c[i]/c[i-168])
 features[coin]=pd.DataFrame(d)
 saved=pd.read_csv(P/(coin+'_features.csv.gz'))
 for name in d:eq(d[name],saved[name],coin+'_'+name,1e-8,1e-8)
 print('RAW FEATURES PASS',coin,flush=True)
res['raw_feature_rows']=61296;res['feature_columns']=8
# Full descriptive table reconstruction using independently rebuilt raw features and labels.
records={k:[] for k in ['quintiles','unconditional_baselines','matched_controls','state_diagnostics','eligibility']};cellcache={};endpoint=np.zeros(16)
def stat(v):
 return dict(n=len(v),mean=float(np.mean(v)),median=float(np.median(v)),p05=float(np.quantile(v,.05)),positive_fraction=float(np.mean(v>0)))
def support(keys,high,eligible):
 idx={}
 for i,k in enumerate(keys):
  if eligible[i]:idx.setdefault(k,[]).append(i)
 sup=np.array([i for i in np.flatnonzero(high) if len(idx.get(keys[i],[]))>=5],int)
 return idx,sup
def matched(y,keys,high,ctrl):
 idx,sup=support(keys,high,ctrl);cm={k:float(np.mean(y[v])) for k,v in idx.items()};cv=np.array([cm[keys[i]] for i in sup]);v=y[sup]-cv
 return dict(**stat(v),q5_mean=float(y[high].mean()),matched_q5_mean=float(y[sup].mean()),matched_control_mean=float(cv.mean()),matched_fraction=len(sup)/sum(high),unmatched_fraction=1-len(sup)/sum(high)),idx,sup
for fold in proto['folds']:
 start=int(pd.Timestamp(fold['eval_start'],tz='UTC').timestamp()*1000);end=int(pd.Timestamp(fold['eval_end'],tz='UTC').timestamp()*1000)
 for coin,a in raws.items():
  fdf=features[coin];valid=np.isfinite(fdf).all(axis=1).to_numpy();train=(a[:,0]+26*H<start)&valid;ev=(a[:,0]>=start+26*H)&(a[:,0]+26*H<end);inds=np.flatnonzero(ev&valid);d=fdf.iloc[inds].reset_index(drop=True);sf=pd.read_csv(P/(coin+'_'+fold['name']+'_signals_labels.csv.gz'));ft=fits[coin+'_'+fold['name']]
  assert len(inds)==len(sf) and ft['n_train']==sum(train) and ft['train_last_t']==a[train,0][-1];eq(a[inds,0],sf.t,'event_times_'+coin+fold['name'],0,0)
  edges={f:np.quantile(fdf.loc[train,f],[.2,.4,.6,.8]) for f in F};med={s:np.median(fdf.loc[train,s]) for s in S};match_edges={s:np.quantile(fdf.loc[train,s],[1/3,2/3]) for s in ['past_vol24','past_trend168']}
  for f in F:eq(edges[f],ft['quintiles'][f],'train_edges_'+coin+fold['name']+f,1e-8,1e-8)
  for s in S:eq(med[s],ft['state_medians'][s],'state_median_'+coin+fold['name']+s,1e-8,1e-8)
  for s in match_edges:eq(match_edges[s],ft['match'][s],'match_edges_'+coin+fold['name']+s,1e-8,1e-8)
  dt=pd.to_datetime(a[inds,0],unit='ms',utc=True);days=(a[inds,0]//86400000).astype(int);keys=list(zip(dt.strftime('%Y-%m'),dt.hour//6,*[np.searchsorted(match_edges[x],d[x],side='right') for x in match_edges]));qby={f:np.searchsorted(edges[f],d[f],side='right')+1 for f in F}
  for f in F:assert np.array_equal(qby[f],sf[f+'_q'])
  for s in S:assert np.array_equal((d[s]>=med[s]).astype(int),sf[s+'_high'])
  for col in d:eq(d[col],sf[col],'event_feature_'+coin+fold['name']+col,1e-8,1e-8)
  for h in [4,24]:
   for cond,(fee,slip,delay) in proto['labels']['conditions'].items():
    ent=inds+1+delay;ex=ent+h;qty=(1-fee)/(a[ent,1]*(1+slip));y=qty*a[ex,1]*(1-slip)*(1-fee)-1;gross=a[ex,1]/a[ent,1]-1
    assert (a[ex,0]<end).all()
    for col,val in [('entry_t',a[ent,0]),('exit_t',a[ex,0]),('entry_open',a[ent,1]),('exit_open',a[ex,1]),('gross',gross),('net',y)]:eq(val,sf[f'{h}_{cond}_{col}'],f'label_{coin}_{fold["name"]}_{h}_{cond}_{col}',2e-14,2e-14)
    total_labels+=len(y);base=dict(coin=coin,fold=fold['name'],h=h,condition=cond);rate=len(inds)/sum(ev);records['unconditional_baselines'].append(dict(**base,**stat(y),valid_rate=rate,gross_mean=gross.mean()))
    for f in F:
     q=qby[f];hi=q==5;ct=q<5;r,idx,sup=matched(y,keys,hi,ct);records['matched_controls'].append(dict(**base,factor=f,**r))
     for qi in range(1,6):
      m=q==qi;z=stat(y[m]);records['quintiles'].append(dict(**base,factor=f,quintile=qi,**z,valid_rate=rate,gross_mean=gross[m].mean(),baseline_mean=y.mean(),baseline_delta=z['mean']-y.mean(),diagnostic_sufficiency='SUFFICIENT_COUNT' if sum(m)>=100 else 'INSUFFICIENT'))
     for s in S:
      for level in [0,1]:
       sm=(d[s].to_numpy()>=med[s])==bool(level);rr,_,ss=matched(y,keys,hi&sm,ct&sm);rr.pop('matched_control_mean');rr.pop('unmatched_fraction');records['state_diagnostics'].append(dict(**base,factor=f,state=s,level='high' if level else 'low',q5_n=int(sum(hi&sm)),**rr,status='DIAGNOSTIC_ONLY' if len(ss)>=100 else 'INSUFFICIENT'))
     if cond=='baseline':
      j=F.index(f)*4+[4,24].index(h)*2;endpoint[j]+=r['q5_mean']/6;endpoint[j+1]+=r['mean']/6
      cellcache[(fold['name'],coin,f,h)]=(keys,hi,ct,sup,y,days)
      nd=(end-start)//86400000;gates=dict(valid_rate=rate>=.95,q5_n=sum(hi)>=200,q5_days=len(set(days[hi]))>=60,matched_n=len(sup)>=200,matched_fraction=r['matched_fraction']>=.8,calendar_blocks=nd//14>=8,train_n=sum(train)>=6000,unique_quintile_edges=len(set(edges[f]))==4)
      records['eligibility'].append(dict(factor=f,coin=coin,fold=fold['name'],h=h,eligible_hours=sum(ev),valid_hours=len(inds),valid_rate=rate,q5_n=sum(hi),q5_days=len(set(days[hi])),matched_n=len(sup),matched_fraction=r['matched_fraction'],unmatched_fraction=r['unmatched_fraction'],pass_all=all(gates.values()),gates=str({k:bool(v) for k,v in gates.items()})))
  print('TABLES REBUILT',coin,fold['name'],flush=True)
keysby={'quintiles':['factor','coin','fold','h','condition','quintile'],'unconditional_baselines':['coin','fold','h','condition'],'matched_controls':['factor','coin','fold','h','condition'],'state_diagnostics':['factor','coin','fold','h','condition','state','level'],'eligibility':['factor','coin','fold','h']}
for name,rr in records.items():
 rebuilt=pd.DataFrame(rr).sort_values(keysby[name]).reset_index(drop=True);saved=pd.read_csv(P/(name+'.csv')).sort_values(keysby[name]).reset_index(drop=True);assert len(saved)==len(rebuilt) and not saved.duplicated(keysby[name]).any();assert set(saved)==set(rebuilt),(name,set(saved)^set(rebuilt))
 for col in saved:
  if col=='gates':assert all(ast.literal_eval(a)==ast.literal_eval(b) for a,b in zip(saved[col],rebuilt[col]))
  elif pd.api.types.is_numeric_dtype(saved[col]):eq(saved[col],rebuilt[col],name+'_'+col)
  else:assert list(saved[col])==list(rebuilt[col]),(name,col)
 rebuilt.to_csv(O/(name+'_recomputed.csv'),index=False);checks[name+'_rows_all_fields']=len(saved)
res['event_label_count']=total_labels
m=pd.DataFrame(records['matched_controls']);q=pd.DataFrame(records['quintiles']);st=pd.DataFrame(records['state_diagnostics']);base=m[m.condition=='baseline'];summary=[]
for f in F:
 for h in [4,24]:
  mm=m[(m.factor==f)&(m.h==h)];bb=mm[mm.condition=='baseline'];row=dict(factor=f,h=h,net_bp=bb.q5_mean.mean()*10000,increment_bp=bb['mean'].mean()*10000)
  for cond in ['fee2','slip20','delay1']:row[cond+'_bp']=mm[mm.condition==cond].q5_mean.mean()*10000
  for fold in proto['folds']:
   z=bb[bb.fold==fold['name']];row[fold['name']+'_net_bp']=z.q5_mean.mean()*10000;row[fold['name']+'_increment_bp']=z['mean'].mean()*10000
  summary.append(row)
pd.DataFrame(summary).to_csv(O/'candidate_summary.csv',index=False);res['candidate_summary']=summary
foldsummary=base.groupby(['factor','h','fold']).agg(q5_net=('q5_mean','mean'),matched_increment=('mean','mean')).reset_index();saved=pd.read_csv(P/'fold_direction_summary.csv');
for col in ['q5_net','matched_increment']:eq(foldsummary.sort_values(['factor','h','fold'])[col],saved.sort_values(['factor','h','fold'])[col],'fold_'+col)
for _,row in pd.read_csv(P/'state_increment_summary.csv').iterrows():
 g=st[(st.factor==row.factor)&(st.h==row.h)&(st.condition==row.condition)&(st.state==row.state)];hi=g[g.level=='high'];lo=g[g.level=='low'];vals=dict(high_q5_mean=hi.q5_mean.mean(),low_q5_mean=lo.q5_mean.mean(),high_matched_increment=hi['mean'].mean(),low_matched_increment=lo['mean'].mean(),high_minus_low_increment=hi['mean'].mean()-lo['mean'].mean(),high_matched_n=hi.n.sum(),low_matched_n=lo.n.sum(),all12_cells_n_ge100=bool((g.n>=100).all()),all12_support_ge80pct=bool((g.matched_fraction>=.8).all()))
 for k,v in vals.items():eq(v,row[k],'state_summary_'+k)
checks['state_summary_rows']=64;checks['fold_summary_rows']=24
# Independently regenerate all common resamples; group-by day arrays and non-BLAS einsum.
B=10000;rng=np.random.default_rng(2026092603);boot=np.zeros((B,16));bootcell=[];failures=[];draws={}
for fold in proto['folds']:
 nd=(pd.Timestamp(fold['eval_end'])-pd.Timestamp(fold['eval_start'])).days;day0=int(pd.Timestamp(fold['eval_start'],tz='UTC').timestamp())//86400;W=np.zeros((B,nd));nblocks=(nd+13)//14
 for rep in range(B):
  starts=rng.integers(nd,size=nblocks);picked=((starts[:,None]+np.arange(14)[None,:])%nd).ravel()[:nd];W[rep]=np.bincount(picked,minlength=nd)
  if rep==0:draws[fold['name']]={'starts':starts.tolist(),'day_counts':W[rep].astype(int).tolist()}
 assert (W.sum(axis=1)==nd).all()
 for coin in ['BTC','ETH']:
  for f in F:
   for h in [4,24]:
    keys,hi,ct,sup,y,days=cellcache[(fold['name'],coin,f,h)];day=days-day0;used=sorted(set(keys[i] for i in sup));index={k:i for i,k in enumerate(used)};g=len(used);hc=np.zeros((nd,g));hs=hc.copy();cc=hc.copy();cs=hc.copy()
    for i in sup:hc[day[i],index[keys[i]]]+=1;hs[day[i],index[keys[i]]]+=y[i]
    for i in np.flatnonzero(ct):
     if keys[i] in index:cc[day[i],index[keys[i]]]+=1;cs[day[i],index[keys[i]]]+=y[i]
    ah=np.bincount(day[hi],minlength=nd);ay=np.bincount(day[hi],weights=y[hi],minlength=nd);absval=np.einsum('ij,j->i',W,ay,optimize=False)/np.einsum('ij,j->i',W,ah,optimize=False)
    whc=np.einsum('ij,jk->ik',W,hc,optimize=False);whs=np.einsum('ij,jk->ik',W,hs,optimize=False);wcc=np.einsum('ij,jk->ik',W,cc,optimize=False);wcs=np.einsum('ij,jk->ik',W,cs,optimize=False)
    assert all(np.isfinite(x).all() for x in [whc,whs,wcc,wcs]);badcell=(whc>0)&(wcc==0);bad=badcell.any(axis=1)|(whc.sum(axis=1)==0);cm=np.divide(wcs,wcc,out=np.zeros_like(wcs),where=wcc>0);inc=(whs.sum(axis=1)-(whc*cm).sum(axis=1))/whc.sum(axis=1);inc[bad]=np.nan;j=F.index(f)*4+[4,24].index(h)*2;boot[:,j]+=absval/6;boot[:,j+1]+=inc/6
    bootcell.append(dict(fold=fold['name'],coin=coin,factor=f,h=h,invalid=int(sum(bad)),used_strata=g,max_weighted_count=float(max(whc.max(),wcc.max()))))
    if h==4 and badcell[0].any():
     k=int(np.flatnonzero(badcell[0])[0]);key=used[k];control=np.array([i for i in range(len(y)) if ct[i] and keys[i]==key]);target=np.array([i for i in sup if keys[i]==key]);failures.append(dict(fold=fold['name'],coin=coin,factor=f,stratum=[str(x) for x in key],original_control_n=len(control),original_q5_n=len(target),replicate0_control_weight=int(sum(W[0,day[control]])),replicate0_q5_weight=int(sum(W[0,day[target]])),control_days_and_weights=[[int(x+day0),int(W[0,x])] for x in sorted(set(day[control]))],q5_days_and_weights=[[int(x+day0),int(W[0,x])] for x in sorted(set(day[target]))]))
  print('BOOTSTRAP FULL PASS CALCULATED',coin,fold['name'],flush=True)
original=np.load(P/'bootstrap_estimators.npz');independent=np.load(P/'independent_bootstrap.npz')
eq(endpoint,original['point'],'point_all16');eq(boot,original['estimators'],'A_vs_original_bootstrap');eq(boot,independent['estimators'],'A_vs_C_nonBLAS_bootstrap');assert np.array_equal(np.isnan(boot),np.isnan(original['estimators'])) and np.array_equal(np.isnan(boot),np.isnan(independent['estimators']))
res['bootstrap']={'replicates':B,'endpoints':16,'joint_valid':int(np.isfinite(boot).all(axis=1).sum()),'finite_per_endpoint':np.isfinite(boot).sum(axis=0).tolist(),'all160000_values_and_nan_masks_match_both_C_artifacts':True,'cell_checks':bootcell,'replicate0_failure_witnesses':failures,'methodology_verdict':'Frozen exact matching plus calendar block resampling loses control support; method cannot supply required joint CI. This is inferential method failure, not proof of market inefficiency or profitability; no implementation deviation found.'}
(O/'replicate0_common_draw.json').write_text(json.dumps(draws,indent=2));np.savez_compressed(O/'A_bootstrap_recomputed.npz',estimators=boot,point=endpoint)
inf=J(P/'primary_inference.json');assert inf['joint_valid_replicates']==res['bootstrap']['joint_valid']==0
for j,v in enumerate(inf['intervals']):eq(v['point'],endpoint[j],'inference_point_'+str(j));assert v['simultaneous_lower'] is None and v['simultaneous_upper'] is None
for dec in J(P/'decisions.json'):
 f,h=dec['factor'],dec['h'];bb=base[(base.factor==f)&(base.h==h)];assert dec['passed'] is False and dec['status']=='INSUFFICIENT_EVIDENCE' and dec['minimum_evidence_pass'] is True
 for coin in ['BTC','ETH']:
  z=bb[bb.coin==coin];r=dec['coin_direction'][coin];eq(r['pooled_q5_net'],z.q5_mean.mean(),'coin_pooled');eq(r['pooled_increment'],z['mean'].mean(),'coin_increment');assert r['folds_both_positive']==sum((z.q5_mean>0)&(z['mean']>0))
 for cond,v in dec['cost_sensitivity_pooled_q5'].items():eq(v,m[(m.factor==f)&(m.h==h)&(m.condition==cond)].q5_mean.mean(),'decision_cost')
 assert bb.q5_mean.mean()<0
res['table_scope_summary']={'quintile_rows':len(q),'baseline_rows':48,'matched_rows':len(m),'state_rows':len(st),'state_rows_n_below100':int(sum(st.n<100)),'state_rows_support_below80pct':int(sum(st.matched_fraction<.8)),'quintile_rows_n_below100':int(sum(q.n<100)),'q5_n_range':[int(base.n.min()),int(base.n.max())],'matched_fraction_range':[float(base.matched_fraction.min()),float(base.matched_fraction.max())]}
assert all(sha(P/n)==h for n,h in initial.items());res['C_package_unchanged']=True;res['checks']=checks;res['maximum_absolute_errors']=maxerr;res['verdict']='PASS_DESCRIPTIVE_IMPLEMENTATION; FAIL_INFERENTIAL_METHOD; FAIL_VISIBLE_PROFITABILITY; STOP';res['warning_root_cause']='UNKNOWN; independent non-BLAS full replication agrees values and NaN locations, so warnings do not explain support failure.'
(O/'review.json').write_text(json.dumps(res,ensure_ascii=False,indent=2));print('A REVIEW COMPUTATION PASS',res['checks'],res['bootstrap']['finite_per_endpoint'],flush=True)
