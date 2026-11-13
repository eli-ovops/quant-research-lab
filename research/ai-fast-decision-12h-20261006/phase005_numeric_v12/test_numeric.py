import unittest,json,ast
from pathlib import Path
from decimal import Decimal as D
from fractions import Fraction as F
import frozen_core as core
B=Path(__file__).resolve().parent
class T(unittest.TestCase):
 def test_actual_false_censor_both_cases(self):
  p=json.loads((B/'protocol.json').read_text());diag=json.loads((Path(p['old_results_readonly'])/'numeric_censor_diagnosis.json').read_text());spec={s['instId']:s for s in json.loads((B/'instruments.json').read_text())}
  self.assertEqual(len(diag['trace']),2)
  for t in diag['trace']:
   levels=[(D(s['price']),D(s['available'])) for s in t['steps']];unit=D(spec[t['asset']]['ctVal'])*D(spec[t['asset']]['ctMult']);q=core.size_capacity(levels,unit,D('.01'),D('.01'),D(t['fee_bps'])/10000);self.assertIsNotNone(q);self.assertEqual(q,D(t['quantity_floor_would_meet_min']))
 def test_true_depth_and_min_insufficient(self):
  self.assertIsNone(core.size_capacity([(D(100),D(1))],D(1),D('.01'),D('.01'),D(0)));self.assertIsNone(core.size_capacity([(D(100),D(100))],D(1),D('.01'),D(6),D(0)))
 def test_exact_grid_boundary_no_epsilon(self):
  self.assertEqual(core.size_capacity([(D(100),D(5))],D(1),D('.1'),D('.1'),D(0)),D(5))
  self.assertIsNone(core.size_capacity([(D(100),D('4.999999999999999999999999999'))],D(1),D('.1'),D('.1'),D(0)))
 def test_fee_cap_and_exit_same_quantity(self):
  lv=[(D(100),D(1)),(D(110),D(100))];q=core.size_capacity(lv,D(1),D('.01'),D('.01'),D('.0005'));n,_=core.depthfill(lv,q,D(1));self.assertLessEqual(F(n)*(1+F(D('.0005'))),F(500));exit_n,exit_px=core.depthfill([(D(90),D(100))],q,D(1));self.assertEqual(exit_n/q,D(90));self.assertNotEqual(q,core.size_capacity([(D(90),D(100))],D(1),D('.01'),D('.01'),D('.0005')))
 def test_only_sizing_function_changed(self):
  p=json.loads((B/'protocol.json').read_text());old=ast.parse((Path(p['old_results_readonly'])/'frozen_core.py').read_text());new=ast.parse((B/'frozen_core.py').read_text());defs=lambda t:{x.name:ast.dump(x,include_attributes=False) for x in t.body if isinstance(x,(ast.FunctionDef,ast.ClassDef))};a,b=defs(old),defs(new);self.assertEqual(set(a),set(b));self.assertEqual([k for k in a if a[k]!=b[k]],['size_capacity'])
if __name__=='__main__':unittest.main()

