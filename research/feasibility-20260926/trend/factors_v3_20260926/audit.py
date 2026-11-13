from pathlib import Path
import numpy as np,pandas as pd,json,hashlib,datetime,math
P=Path(__file__).resolve().parent;H=3600000
(P/'first_model_result_access.json').write_text(json.dumps({'UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'all_cells_completed':True,'warnings_under_investigation':True}))
proto=json.loads((P/'protocol.json').read_text());fits=json.loads((P/'fitted_training_thresholds.json').read_text());fa=list(proto['features']);candidates=[f+'__'+str(h) for f in fa for h in [4,24]];rng=np.random.default_rng(2026092603);B=10000;out=np.zeros((B,16));samplechecks=[];finitechecks=[]
for fold in proto['folds']:
 nd=(pd.Timestamp(fold['eval_end'])-pd.Timestamp(fold['eval_start'])).days;day0=int(pd.Timestamp(fold['eval_start'],tz='UTC').timestamp())//86400;W=np.zeros((B,nd));k,rem=divmod(nd,14)
 for rep in range(B):
  starts=rng.integers(0,nd,k+(rem>0))
  for j,st in enumerate(starts):
   for off in range(14 if j<k else rem):W[rep,(st+off)%nd]+=1
 for coin in ['BTC','ETH']:
  sig=pd.read_csv(P/(coin+'_'+fold['name']+'_signals_labels.csv.gz'));fit=fits[coin+'_'+fold['name']];raw=json.loads((P/(coin+'_input.json')).read_text());lookup={int(r[0]):i for i,r in enumerate(raw)};cl=np.array([float(r[4]) for r in raw]);ts=sig.t.to_numpy(dtype=np.int64);days=sig.day.to_numpy(dtype=int)-day0
  # Deterministic boundary/interior samples for all scores, both states, and8labels; directly from input arrays.
  for si in sorted(set([0,1,len(sig)//4,len(sig)//2,3*len(sig)//4,len(sig)-2,len(sig)-1])):
   i=lookup[int(ts[si])];ret=np.diff(np.log(cl[i-24:i+1]));mom=sum(ret)/(np.std(ret)*np.sqrt(24));eff=sum(ret)/sum(abs(x) for x in ret);rev=-(cl[i]-np.mean(cl[i-23:i+1]))/np.std(cl[i-23:i+1]);gain=np.mean(np.maximum(np.diff(cl[:15]),0));loss=np.mean(np.maximum(-np.diff(cl[:15]),0))
   for j in range(15,i+1):gain=(13*gain+max(cl[j]-cl[j-1],0))/14;loss=(13*loss+max(cl[j-1]-cl[j],0))/14
   rsi=-.5 if gain==loss==0 else -gain/(gain+loss)
   tr=[max(float(raw[j][2])-float(raw[j][3]),abs(float(raw[j][2])-cl[j-1]),abs(float(raw[j][3])-cl[j-1])) for j in range(i-167,i+1)];atr=np.mean(tr[-14:])/np.mean(tr);volume=float(raw[i][7])/np.median([float(r[7]) for r in raw[i-168:i]])
   for name,v in zip(fa+['atr_ratio','quote_volume_ratio'],[mom,eff,rev,rsi,atr,volume]):np.testing.assert_allclose(sig.iloc[si][name],v,rtol=1e-8,atol=1e-8)
   for h in [4,24]:
    for cond,(fee,slip,delay) in proto['labels']['conditions'].items():
     entry=float(raw[i+1+delay][1]);exit=float(raw[i+1+delay+h][1]);qty=(1-fee)/((1+slip)*entry);net=qty*exit*(1-slip)*(1-fee)-1;np.testing.assert_allclose(sig.iloc[si][str(h)+'_'+cond+'_net'],net,atol=2e-14,rtol=2e-14);assert int(sig.iloc[si][str(h)+'_'+cond+'_exit_t'])==int(raw[i+1+delay+h][0])
   samplechecks.append({'coin':coin,'fold':fold['name'],'bar_t':int(ts[si]),'scores_states_labels':'PASS'})
  #Independent matching keys, no core import. Full10000 bootstrap draws via einsum, no BLAS/matmul.
  key=list(zip(sig.month,sig.hourbucket,np.searchsorted(fit['match']['past_vol24'],sig.past_vol24,side='right'),np.searchsorted(fit['match']['past_trend168'],sig.past_trend168,side='right')));unique={v:j for j,v in enumerate(sorted(set(key)))};codes=np.array([unique[v] for v in key]);ng=len(unique)
  for f in fa:
   q=np.searchsorted(fit['quintiles'][f],sig[f],side='right')+1;assert np.array_equal(q,sig[f+'_q']);high=q==5;ctrl=q<5;ct=np.bincount(codes[ctrl],minlength=ng);sup=high&(ct[codes]>=5);used=sorted(set(codes[sup]));mapping={v:j for j,v in enumerate(used)};g=len(used)
   for h in [4,24]:
    y=sig[str(h)+'_baseline_net'].to_numpy();ac=np.bincount(days[high],minlength=nd);ass=np.bincount(days[high],weights=y[high],minlength=nd);absolute=np.einsum('ij,j->i',W,ass,optimize=False)/np.einsum('ij,j->i',W,ac,optimize=False)
    hc=np.zeros((nd,g));hs=np.zeros((nd,g));cc=np.zeros((nd,g));cs=np.zeros((nd,g))
    for i in range(len(sig)):
     group=mapping.get(codes[i])
     if group is None:continue
     if sup[i]:hc[days[i],group]+=1;hs[days[i],group]+=y[i]
     elif ctrl[i]:cc[days[i],group]+=1;cs[days[i],group]+=y[i]
    rhc=np.einsum('ij,jk->ik',W,hc,optimize=False);rhs=np.einsum('ij,jk->ik',W,hs,optimize=False);rcc=np.einsum('ij,jk->ik',W,cc,optimize=False);rcs=np.einsum('ij,jk->ik',W,cs,optimize=False)
    assert np.isfinite(rhc).all() and np.isfinite(rhs).all() and np.isfinite(rcc).all() and np.isfinite(rcs).all();assert np.max(rhc)<=nd*24 and np.max(rcc)<=nd*24
    means=np.divide(rcs,rcc,out=np.zeros_like(rcs),where=rcc>0);diff=(rhs.sum(axis=1)-(rhc*means).sum(axis=1))/rhc.sum(axis=1);bad=np.any((rhc>0)&(rcc==0),axis=1)|(rhc.sum(axis=1)==0);diff[bad]=np.nan;j=candidates.index(f+'__'+str(h));out[:,2*j]+=absolute/6;out[:,2*j+1]+=diff/6
    finitechecks.append({'coin':coin,'fold':fold['name'],'factor':f,'h':h,'all_weighted_inputs_finite':True,'matching_unavailable_reps':int(bad.sum())})
  print('AUDITED',coin,fold['name'],flush=True)
a=np.load(P/'bootstrap_estimators.npz');np.testing.assert_allclose(out,a['estimators'],rtol=1e-10,atol=1e-12,equal_nan=True);np.savez_compressed(P/'independent_bootstrap.npz',estimators=out)
result={'UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'pass':True,'direct_raw_samples':samplechecks,'full_bootstrap_replicates':10000,'full_estimator_values':160000,'comparison_tolerance':'atol1e-12 rtol1e-10, NaN locations exact','bootstrap_cell_checks':finitechecks,'warning_resolution':'Original numpy matmul emitted runtime warnings; independent full nonBLAS einsum recomputation uses finite bounded inputs and agrees all10000x16 estimator values incl NaN locations. Warning not treated as success alone; no result selection or parameter change. Underlying numerical-library warning cause UNKNOWN.','scope':'42 raw timestamps:4scores+2states+8labels; fullbootstrap16x10000. A external review pending.'};(P/'independent_audit.json').write_text(json.dumps(result,indent=2));print('AUDIT PASS')
