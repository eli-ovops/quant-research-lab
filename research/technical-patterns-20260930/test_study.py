import unittest,copy,math
import study
class Checks(unittest.TestCase):
 def rows(self):
  rows=[]
  for i in range(1200):
   p=100+10*math.sin(i/22)+.01*i
   rows.append([str(i*study.H),str(p),str(p+1),str(p-1),str(p+.2),'1','1','1','1'])
  return rows
 def test_future_invariance(self):
  rows=self.rows();a=study.features(rows);cut=800*study.H
  for r in rows:
   if int(r[0])>=cut:
    for j in range(1,5):r[j]=str(float(r[j])*2)
  b=study.features(rows)
  self.assertEqual([x for x in a if x['t']<cut],[x for x in b if x['t']<cut])
 def test_band_signals_independent_formula(self):
  bars=study.features(self.rows());c=[b['c'] for b in bars]
  def lower(i):
   v=c[i-19:i+1];m=sum(v)/20
   return m-2*math.sqrt(sum((x-m)**2 for x in v)/20)
  for i in range(130,len(bars)):
   self.assertEqual(bars[i]['signals']['bollinger'],c[i-1]<lower(i-1) and c[i]>=lower(i))
 def test_flat_cost_roundtrip(self):
  self.assertLess(study.net(0),-29)
  self.assertAlmostEqual(study.net(0),(((1-.0005)*(.999**2)/(1+.0005))-1)*10000)
 def test_four_hour_aggregation(self):
  r=self.rows();b=study.features(r)[0]
  self.assertEqual(b['o'],float(r[0][1]));self.assertEqual(b['c'],float(r[3][4]))
  self.assertEqual(b['h'],max(float(x[2]) for x in r[:4]))
if __name__=='__main__':unittest.main()
