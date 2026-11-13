import unittest,numpy as np,pandas as pd,json
import core
class Tests(unittest.TestCase):
 def rows(self,n=400):
  c=100+np.arange(n)*.01+np.sin(np.arange(n)/5);return [[i*core.H,c[i],c[i]+1,c[i]-1,c[i],1,100+i,100+i,1] for i in range(n)]
 def test_feature_causality(self):
  r=self.rows();a=core.features(r);r2=[x[:] for x in r]
  for x in r2[251:]:x[1:5]=[v*2 for v in x[1:5]];x[7]*=5
  b=core.features(r2);np.testing.assert_allclose(a.loc[:250,core.FACTORS+core.STATES],b.loc[:250,core.FACTORS+core.STATES],equal_nan=True)
 def test_formulas_independent(self):
  r=self.rows();d=core.features(r);i=200;c=np.array([x[4] for x in r]);ret=[np.log(c[j]/c[j-1]) for j in range(i-23,i+1)]
  self.assertAlmostEqual(d.momentum24[i],sum(ret)/(np.std(ret)*np.sqrt(24)),10);self.assertAlmostEqual(d.efficiency24[i],sum(ret)/sum(abs(x) for x in ret),10);self.assertAlmostEqual(d.reversion24[i],-(c[i]-np.mean(c[i-23:i+1]))/np.std(c[i-23:i+1]),9)
  self.assertAlmostEqual(d.quote_volume_ratio[i],r[i][7]/np.median([x[7] for x in r[i-168:i]]),12)
  gain=loss=0
  for j in range(1,15):gain+=max(c[j]-c[j-1],0)/14;loss+=max(c[j-1]-c[j],0)/14
  for j in range(15,i+1):gain+=(max(c[j]-c[j-1],0)-gain)/14;loss+=(max(c[j-1]-c[j],0)-loss)/14
  self.assertAlmostEqual(d.rsi14_negative[i],-gain/(gain+loss),12)
 def test_labels_and_cost(self):
  d=core.features(self.rows())
  for h in [4,24]:
   for cond,(f,s,delay) in core.CONDS.items():
    a=core.labels(d,h,cond);i=200;buy=d.open[i+1+delay];sell=d.open[i+1+delay+h];qty=(1/(buy*(1+s)))*(1-f);proceeds=qty*sell*(1-s)*(1-f)
    self.assertEqual(a.exit_t[i]-a.entry_t[i],h*core.H);self.assertAlmostEqual(a.net[i],proceeds-1,14);self.assertAlmostEqual(a.gross[i],sell/buy-1,14)
 def test_warmup_zero(self):
  r=[[i*core.H,100,100,100,100,1,1,1,1] for i in range(300)];d=core.features(r);self.assertTrue(d.loc[:167,core.FACTORS+core.STATES].isna().all().all());self.assertTrue(d.momentum24.isna().all());self.assertEqual(d.rsi14_negative[200],-.5);self.assertTrue(d.atr_ratio.isna().all())
 def test_boundary_fit(self):
  p=json.loads((core.P/'protocol.json').read_text());f=p['folds'][0];t=np.arange(core.ms('2023-01-01'),core.ms('2025-01-01'),core.H);r=self.rows(len(t))
  for x,v in zip(r,t):x[0]=v
  d=core.features(r);a,ev,_=core.fit(d,f);tr,_=core.masks(d,f);self.assertTrue((d.loc[tr,'t']+26*core.H<core.ms(f['eval_start'])).all());self.assertTrue((d.loc[ev,'t']>=core.ms(f['eval_start'])+26*core.H).all());self.assertTrue((d.loc[ev,'t']+26*core.H<core.ms(f['eval_end'])).all())
  d2=d.copy();d2.loc[~tr,core.FACTORS]=999;b,_,_=core.fit(d2,f)
  for k in core.FACTORS:np.testing.assert_equal(a['quintiles'][k],b['quintiles'][k])
 def test_bootstrap_weights(self):
  w=core.block_weights(181,20,np.random.default_rng(1));self.assertTrue(np.all(w.sum(axis=1)==181));np.testing.assert_equal(w,core.block_weights(181,20,np.random.default_rng(1)))
 def test_matching_and_bootstrap(self):
  n=240;d=pd.DataFrame({'month':['2024-01']*n,'hourbucket':[0]*n,'past_vol24':[1]*n,'past_trend168':[0]*n,'day':np.arange(n)//24,'atr_ratio':[1]*n,'quote_volume_ratio':[1]*n});fit={'match':{'past_vol24':np.array([.5,2]),'past_trend168':np.array([-.5,.5])},'state_medians':{'atr_ratio':1,'quote_volume_ratio':1}};q=np.where(np.arange(n)%5==0,5,1);y=np.where(q==5,.02,.01);codes,high,ctrl,sup=core.match(d,q,fit)
  self.assertTrue(np.array_equal(high,sup));self.assertFalse(np.any(high&ctrl));diff,_=core.matched_values(y,codes,ctrl,sup);np.testing.assert_allclose(diff,.01)
  a,b=core.bootstrap_cell(d,y,q,fit,np.ones((3,10)),0);np.testing.assert_allclose(a,.02);np.testing.assert_allclose(b,.01)
 def test_insufficient_bootstrap_stratum(self):
  d=pd.DataFrame({'month':['2024-01']*6,'hourbucket':[0]*6,'past_vol24':[1]*6,'past_trend168':[0]*6,'day':[0,1,1,1,1,1]});fit={'match':{'past_vol24':np.array([.5,2]),'past_trend168':np.array([-.5,.5])}};q=np.array([5,1,1,1,1,1]);a,b=core.bootstrap_cell(d,np.ones(6),q,fit,np.array([[2.,0.]]),0);self.assertTrue(np.isnan(b[0]))
if __name__=='__main__':unittest.main()
