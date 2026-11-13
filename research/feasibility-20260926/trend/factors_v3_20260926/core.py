from pathlib import Path
import json,numpy as np,pandas as pd
P=Path(__file__).resolve().parent;H=3600000
FACTORS=['momentum24','efficiency24','reversion24','rsi14_negative'];STATES=['atr_ratio','quote_volume_ratio'];CONDS={'baseline':(.001,.0005,0),'fee2':(.002,.0005,0),'slip20':(.001,.002,0),'delay1':(.001,.0005,1)}
def ms(s):return int(pd.Timestamp(s,tz='UTC').timestamp()*1000)
def features(rows):
 a=np.asarray(rows,dtype=float);d=pd.DataFrame(a[:,:8],columns=['t','open','high','low','close','base_volume','volCcy','quote_volume']);c=d.close;r=np.log(c/c.shift(1));vol=r.rolling(24).std(ddof=0)
 d['momentum24']=r.rolling(24).sum()/(vol*np.sqrt(24));d['efficiency24']=r.rolling(24).sum()/r.abs().rolling(24).sum();d['reversion24']=-(c-c.rolling(24).mean())/c.rolling(24).std(ddof=0)
 diff=c.diff().to_numpy();gain=np.maximum(diff,0);loss=np.maximum(-diff,0);rsi=np.full(len(c),np.nan)
 if len(c)>14:
  ag=np.mean(gain[1:15]);al=np.mean(loss[1:15])
  for i in range(14,len(c)):
   if i>14:ag=(13*ag+gain[i])/14;al=(13*al+loss[i])/14
   rsi[i]=50 if ag==al==0 else (100 if al==0 else 100-100/(1+ag/al))
 d['rsi14_negative']=-rsi/100
 tr=pd.concat([d.high-d.low,(d.high-c.shift(1)).abs(),(d.low-c.shift(1)).abs()],axis=1).max(axis=1);d['atr_ratio']=tr.rolling(14).mean()/tr.rolling(168).mean();d['quote_volume_ratio']=d.quote_volume/d.quote_volume.shift(1).rolling(168).median();d['past_vol24']=vol;d['past_trend168']=np.log(c/c.shift(168))
 fs=FACTORS+STATES+['past_vol24','past_trend168'];d[fs]=d[fs].replace([np.inf,-np.inf],np.nan);d.loc[:167,fs]=np.nan
 dt=pd.to_datetime(d.t,unit='ms',utc=True);d['month']=dt.dt.strftime('%Y-%m');d['hourbucket']=dt.dt.hour//6;d['day']=d.t.astype('int64')//86400000;return d

def labels(d,h,cond):
 fee,slip,delay=CONDS[cond];entry=d.open.shift(-(1+delay));exit=d.open.shift(-(1+delay+h));gross=exit/entry-1;net=(1+gross)*(1-slip)/(1+slip)*(1-fee)**2-1
 return pd.DataFrame({'entry_t':d.t+(1+delay)*H,'exit_t':d.t+(1+delay+h)*H,'entry_open':entry,'exit_open':exit,'gross':gross,'net':net})
def masks(d,fold):
 a,b=ms(fold['eval_start']),ms(fold['eval_end']);tr=(d.t>=ms(fold['train_start']))&(d.t+26*H<a);ev=(d.t>=a+26*H)&(d.t+26*H<b);return tr,ev

def fit(d,fold):
 tr,ev=masks(d,fold);cols=FACTORS+STATES+['past_vol24','past_trend168'];valid=np.isfinite(d[cols]).all(axis=1);train=d.loc[tr&valid];q={f:np.quantile(train[f],[.2,.4,.6,.8],method='linear') for f in FACTORS};match={f:np.quantile(train[f],[1/3,2/3],method='linear') for f in ['past_vol24','past_trend168']};med={f:float(train[f].median()) for f in STATES}
 return {'quintiles':q,'match':match,'state_medians':med,'n_train':len(train),'train_last_t':int(train.t.max())},ev&valid,ev

def groups(d,fit):
 out=d[['month','hourbucket']].copy()
 for f,edges in fit['match'].items():out[f]=np.digitize(d[f],edges)
 return pd.MultiIndex.from_frame(out)

def match(d,q,fit,state=None):
 keys=groups(d,fit)
 if state is not None:
  f,level=state;ok=(d[f]>=fit['state_medians'][f]).to_numpy()==bool(level)
 else:ok=np.ones(len(d),dtype=bool)
 codes,_=pd.factorize(keys);high=(q==5)&ok;ctrl=(q<5)&ok;cnt=np.bincount(codes[ctrl],minlength=codes.max()+1);supported=high&(cnt[codes]>=5)
 return codes,high,ctrl,supported

def summary(y):
 a=np.asarray(y,float);a=a[np.isfinite(a)];return {'n':len(a),'mean':float(a.mean()) if len(a) else None,'median':float(np.median(a)) if len(a) else None,'p05':float(np.quantile(a,.05)) if len(a) else None,'positive_fraction':float(np.mean(a>0)) if len(a) else None}

def matched_values(y,codes,ctrl,supported):
 n=codes.max()+1;cnt=np.bincount(codes[ctrl],minlength=n);sums=np.bincount(codes[ctrl],weights=y[ctrl],minlength=n);means=np.divide(sums,cnt,out=np.full(n,np.nan),where=cnt>0);return y[supported]-means[codes[supported]],means

def block_weights(n,reps,rng,block=14):
 w=np.zeros((reps,n));full,rem=divmod(n,block)
 for i in range(reps):
  st=rng.integers(0,n,full+(rem>0));idx=np.concatenate([(s+np.arange(block if j<full else rem))%n for j,s in enumerate(st)]);w[i]=np.bincount(idx,minlength=n)
 return w

def bootstrap_cell(d,y,q,fit,W,day0):
 codes,high,ctrl,supported=match(d,q,fit);day=d.day.to_numpy(dtype=int)-day0;n=W.shape[1];ng=codes.max()+1
 counts=np.bincount(day[high],minlength=n);sums=np.bincount(day[high],weights=y[high],minlength=n);absolute=(W@sums)/(W@counts)
 # Limit to strata with supported Q5; omit unused controls. Recompute within-stratum control means for each draw.
 used=np.unique(codes[supported]);remap=np.full(ng,-1);remap[used]=np.arange(len(used));ctrl=ctrl&(remap[codes]>=0);g=len(used)
 def mat(mask,values):
  z=np.zeros((n,g));np.add.at(z,(day[mask],remap[codes[mask]]),values if np.isscalar(values) else values[mask]);return z
 hc=W@mat(supported,1);hs=W@mat(supported,y);cc=W@mat(ctrl,1);cs=W@mat(ctrl,y)
 with np.errstate(invalid='ignore',divide='ignore'):
  cm=np.divide(cs,cc,out=np.zeros_like(cs),where=cc>0);diff=(hs.sum(axis=1)-(hc*cm).sum(axis=1))/hc.sum(axis=1)
 invalid=np.any((hc>0)&(cc==0),axis=1)|(hc.sum(axis=1)==0);diff[invalid]=np.nan
 return absolute,diff
