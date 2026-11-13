import unittest,random,math,json,copy,datetime
from pathlib import Path
from decimal import Decimal as D
import statistics_v2 as st,engine,independent,independent_metrics as im,fixtures
P=Path(__file__).resolve().parent
class StatisticsTests(unittest.TestCase):
 def test_synchronous_family_against_expanded_reference(self):
  x={str(i):[(math.sin(j/11)+.05*i)/100 for j in range(400)] for i in range(9)};a=st.simultaneous(x,{k:40 for k in x});rng=random.Random(2026092602);s=[];means={k:sum(v)/400*365 for k,v in x.items()}
  for _ in range(2000):
   indices=[]
   while len(indices)<400:
    i=rng.randrange(400);indices.extend((i+j)%400 for j in range(30))
   s.append(max(abs(sum(v[i] for i in indices[:400])/400*365-means[k]) for k,v in x.items()))
  self.assertAlmostEqual(a['common_half_width'],sorted(s)[1899],places=12)
  self.assertTrue(a['family_all_reliability_screens_pass'])
  b=st.simultaneous(x,{k:29 for k in x});self.assertFalse(b['family_all_reliability_screens_pass'])
 def test_year_rolling_half_open(self):
  proto=json.loads((P.parent/'protocol.json').read_text());count=0
  for period,(a,b) in proto['periods_UTC_half_open'].items():
   ms=lambda x:int(datetime.datetime.fromisoformat(x).timestamp()*1000);start,end=ms(a),ms(b);curve=[{'t':t,'valuation_equity':D(2000)+D(i)/100} for i,t in enumerate(range(start,end,st.H),1)]
   r=st.slices({'start':start,'end':end,'curve':curve},proto['rolling']['windows']);count+=len(r['rolling']);self.assertEqual(sum(y['net_change_usdt'] for y in r['yearly']),curve[-1]['valuation_equity']-2000)
   for w in r['rolling']:self.assertEqual(w['end']-w['start'],180*st.DAY);self.assertEqual(w['net_change_usdt'],D(4320)/100)
  self.assertEqual(count,23)
 def test_decision_all_required(self):
  results=[]
  for p in ['early','middle','latest']:
   for en in [24,48,72]:
    for ex in [4,8,12]:
     for c in ['baseline','fee2','slip20','delay1']:
      results.append(dict(period=p,entry=en,exit=ex,condition=c,mode='trend',metrics={'net_pnl':1,'max_drawdown':.1,'top5_share_gross_gains':.2,'pnl_without_top5_winners':1,'exposure_clusters':40},slices={'yearly':[{'net_change_usdt':1} for _ in range(3 if p=='early' else 2)]}))
  family={'candidates':{str(en)+'/'+str(ex):{'simultaneous95_lower':.01,'reliability_screen_pass':True} for en in [24,48,72] for ex in [4,8,12]}}
  self.assertTrue(all(x['exploratory_followup_candidate'] for x in st.decisions(results,family)))
  for r in results:
   if r['period']=='latest' and r['entry']==24 and r['exit']==4 and r['condition']=='fee2':r['metrics']['net_pnl']=-1
  self.assertFalse(st.decisions(results,family)[0]['exploratory_followup_candidate'])
 def test_all_supplemental_metrics(self):
  for cond in engine.CONDITIONS:
   f=fixtures.make(n=400);f['condition']=cond;a=engine.run(**f);b=independent.replay(f);im.assert_close(a['metrics'],im.compute(f,b))
if __name__=='__main__':unittest.main(verbosity=2)
