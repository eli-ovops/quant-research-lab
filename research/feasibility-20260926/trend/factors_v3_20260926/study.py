from pathlib import Path
import json,datetime,hashlib,math,time
import numpy as np,pandas as pd
import core
P=core.P
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def dump(n,x):
 def enc(v):
  if isinstance(v,np.ndarray):return v.tolist()
  if isinstance(v,np.generic):return v.item()
  raise TypeError(type(v))
 (P/n).write_text(json.dumps(x,indent=2,default=enc,allow_nan=False))
def main():
 frozen=json.loads((P/'analysis_freeze.json').read_text())
 for n,h in frozen['files'].items():assert sha(P/n)==h,n
 assert not (P/'first_results_run.json').exists(),'Do not overwrite a prior attempt'
 proto=json.loads((P/'protocol.json').read_text());sources=json.loads((P/'source_manifest.json').read_text())
 for n,h in sources['input_files'].items():assert sha(P/n)==h
 dump('first_results_run.json',{'UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'protocol_sha256':sha(P/'protocol.json'),'first_historical_factor_and_label_computation':True})
 data={c:core.features(json.loads((P/(c+'_input.json')).read_text())) for c in ['BTC','ETH']}
 for c,d in data.items():d.to_csv(P/(c+'_features.csv.gz'),index=False,compression='gzip')
 fits={};quintiles=[];baselines=[];matches=[];states=[];eligibility=[];candidatekeys=[f+'__'+str(h) for f in core.FACTORS for h in [4,24]];reps=proto['primary_inference']['replicates'];bootstrap=np.zeros((reps,16));point=np.zeros(16);rng=np.random.default_rng(2026092603);done=0
 for fold in proto['folds']:
  days=pd.date_range(fold['eval_start'],fold['eval_end'],inclusive='left',tz='UTC');day0=core.ms(fold['eval_start'])//86400000;W=core.block_weights(len(days),reps,rng);assert np.all(W.sum(axis=1)==len(days))
  for coin,df in data.items():
   fit,valid,eligible=core.fit(df,fold);d=df.loc[valid].copy().reset_index(drop=True);fits[coin+'_'+fold['name']]=fit;rate=len(d)/int(eligible.sum());qby={f:np.digitize(d[f],fit['quintiles'][f])+1 for f in core.FACTORS};signal=d.copy()
   for f in core.FACTORS:signal[f+'_q']=qby[f]
   for f in core.STATES:signal[f+'_high']=(d[f]>=fit['state_medians'][f]).astype(int)
   for h in [4,24]:
    Y={cond:core.labels(df,h,cond).loc[valid].reset_index(drop=True) for cond in core.CONDS}
    for cond,lab in Y.items():
     assert np.isfinite(lab[['gross','net']]).all().all();assert (lab.exit_t<core.ms(fold['eval_end'])).all()
     for col in lab:signal[str(h)+'_'+cond+'_'+col]=lab[col]
     baselines.append(dict(coin=coin,fold=fold['name'],h=h,condition=cond,valid_rate=rate,**core.summary(lab.net),gross_mean=float(lab.gross.mean())))
    for f in core.FACTORS:
     q=qby[f];codes,high,ctrl,sup=core.match(d,q,fit);n=int(high.sum());matchedn=int(sup.sum());fraction=matchedn/n if n else 0;daysn=int(d.loc[high,'day'].nunique());key=f+'__'+str(h);ki=candidatekeys.index(key)
     gates={'valid_rate':rate>=.95,'q5_n':n>=200,'q5_days':daysn>=60,'matched_n':matchedn>=200,'matched_fraction':fraction>=.8,'calendar_blocks':len(days)//14>=8,'train_n':fit['n_train']>=6000,'unique_quintile_edges':len(np.unique(fit['quintiles'][f]))==4}
     eligibility.append(dict(factor=f,coin=coin,fold=fold['name'],h=h,eligible_hours=int(eligible.sum()),valid_hours=len(d),valid_rate=rate,q5_n=n,q5_days=daysn,matched_n=matchedn,matched_fraction=fraction,unmatched_fraction=1-fraction,gates=gates,pass_all=all(gates.values())))
     for cond,lab in Y.items():
      y=lab.net.to_numpy();gross=lab.gross.to_numpy();diff,cm=core.matched_values(y,codes,ctrl,sup)
      matches.append(dict(factor=f,coin=coin,fold=fold['name'],h=h,condition=cond,**core.summary(diff),q5_mean=float(y[high].mean()),matched_q5_mean=float(y[sup].mean()) if matchedn else None,matched_control_mean=float(cm[codes[sup]].mean()) if matchedn else None,matched_fraction=fraction,unmatched_fraction=1-fraction))
      for qi in range(1,6):
       mask=q==qi;stat=core.summary(y[mask]);quintiles.append(dict(factor=f,coin=coin,fold=fold['name'],h=h,condition=cond,quintile=qi,valid_rate=rate,**stat,gross_mean=float(gross[mask].mean()) if mask.any() else None,baseline_mean=float(y.mean()),baseline_delta=stat['mean']-float(y.mean()) if mask.any() else None,diagnostic_sufficiency='SUFFICIENT_COUNT' if mask.sum()>=100 else 'INSUFFICIENT'))
      for state in core.STATES:
       for level in [0,1]:
        co,hi,ct,su=core.match(d,q,fit,(state,level));dif,means=core.matched_values(y,co,ct,su);states.append(dict(factor=f,coin=coin,fold=fold['name'],h=h,condition=cond,state=state,level='high' if level else 'low',q5_n=int(hi.sum()),matched_fraction=float(su.sum()/hi.sum()) if hi.any() else None,q5_mean=float(y[hi].mean()) if hi.any() else None,matched_q5_mean=float(y[su].mean()) if su.any() else None,**core.summary(dif),status='DIAGNOSTIC_ONLY' if su.sum()>=100 else 'INSUFFICIENT'))
     y=Y['baseline'].net.to_numpy();dif,_=core.matched_values(y,codes,ctrl,sup);point[2*ki]+=float(y[high].mean())/6;point[2*ki+1]+=float(dif.mean())/6
     absolute,increment=core.bootstrap_cell(d,y,q,fit,W,day0);bootstrap[:,2*ki]+=absolute/6;bootstrap[:,2*ki+1]+=increment/6
     done+=1;dump('progress.json',{'coin_fold_factor_horizon_done':done,'total':48,'last':[coin,fold['name'],f,h]});print('DONE',done,coin,fold['name'],f,h,flush=True)
   signal.to_csv(P/(coin+'_'+fold['name']+'_signals_labels.csv.gz'),index=False,compression='gzip')
 for name,rows in [('quintiles',quintiles),('unconditional_baselines',baselines),('matched_controls',matches),('state_diagnostics',states),('eligibility',eligibility)]:pd.DataFrame(rows).to_csv(P/(name+'.csv'),index=False)
 dump('fitted_training_thresholds.json',fits);np.savez_compressed(P/'bootstrap_estimators.npz',estimators=bootstrap,point=point)
 joint=np.isfinite(bootstrap).all(axis=1);validn=int(joint.sum());ci_valid=validn>=9900
 if validn>1:
  sd=np.std(bootstrap[joint],axis=0,ddof=1);ci_valid=ci_valid and bool((sd>0).all())
 else:sd=np.full(16,np.nan)
 qcrit=None
 if ci_valid:
  mx=np.max(np.abs((bootstrap[joint]-point)/sd),axis=1);qcrit=float(np.sort(mx)[math.ceil(.95*validn)-1])
 intervals=[];decisions=[]
 for ki,key in enumerate(candidatekeys):
  f,h=key.split('__');h=int(h)
  ints=[]
  for offset,end in enumerate(['q5_net','matched_increment']):
   j=2*ki+offset;v=dict(factor=f,h=h,endpoint=end,point=float(point[j]),joint_valid_replicates=validn,bootstrap_sd=float(sd[j]) if np.isfinite(sd[j]) else None,simultaneous_lower=float(point[j]-qcrit*sd[j]) if ci_valid else None,simultaneous_upper=float(point[j]+qcrit*sd[j]) if ci_valid else None,status='EXPLORATORY_SIMULTANEOUS' if ci_valid else 'INSUFFICIENT_BOOTSTRAP_SUPPORT');intervals.append(v);ints.append(v)
  mm=[r for r in matches if r['factor']==f and r['h']==h];ee=[r for r in eligibility if r['factor']==f and r['h']==h];stress={c:float(np.mean([r['q5_mean'] for r in mm if r['condition']==c])) for c in core.CONDS};coincheck={};checks={}
  for coin in ['BTC','ETH']:
   cm=[r for r in mm if r['coin']==coin and r['condition']=='baseline'];both=sum(r['q5_mean']>0 and r['mean'] is not None and r['mean']>0 for r in cm);coincheck[coin]={'folds_both_positive':both,'pooled_q5_net':float(np.mean([r['q5_mean'] for r in cm])),'pooled_increment':float(np.mean([r['mean'] for r in cm]))};checks[coin+'_stage_consistency']=both>=2;checks[coin+'_pooled_positive']=coincheck[coin]['pooled_q5_net']>0 and coincheck[coin]['pooled_increment']>0
  checks.update(q5_net_positive=point[2*ki]>0,matched_increment_positive=point[2*ki+1]>0,all_stress_net_positive=all(stress[c]>0 for c in ['fee2','slip20','delay1']))
  enough=all(e['pass_all'] for e in ee) and ci_valid;bounds=ci_valid and all(v['simultaneous_lower']>0 for v in ints);passed=enough and bounds and all(checks.values());status='EXPLORATORY_CANDIDATE_ONLY' if passed else ('INSUFFICIENT_EVIDENCE' if not enough else ('FAIL_VISIBLE_REQUIREMENTS' if not all(checks.values()) else 'NO_POSITIVE_EVIDENCE'))
  decisions.append(dict(factor=f,h=h,status=status,passed=passed,primary_intervals=ints,minimum_evidence_pass=all(e['pass_all'] for e in ee),failed_minimum_cells=[{'coin':e['coin'],'fold':e['fold'],'failed':[k for k,v in e['gates'].items() if not v]} for e in ee if not e['pass_all']],visible_checks=checks,known_failures=[k for k,v in checks.items() if not v],simultaneous_both_lower_positive=bounds if ci_valid else None,coin_direction=coincheck,cost_sensitivity_pooled_q5=stress))
 dump('primary_inference.json',{'family_size':16,'block_days':14,'replicates':10000,'seed':2026092603,'joint_valid_replicates':validn,'critical_max_standardized':qcrit,'intervals':intervals,'conditional_on_training_thresholds':True,'matching_support_fixed_control_means_resampled':True});dump('decisions.json',decisions)
 print('COMPLETE ALL FIXED CELLS; no model outcome access yet',flush=True)
if __name__=='__main__':main()
