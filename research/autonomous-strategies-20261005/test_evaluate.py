import unittest
from evaluate import select,eligible
class GateTests(unittest.TestCase):
 def rows(self,ident,ret=.1,dd=.2,n=40,audit='PASS'):
  return [{'candidate':ident,'period':'validation','condition':c,'metrics':{'total_return':ret,'max_drawdown':dd,'closed_trades':n},'audit':{'status':audit}} for c in ['base','stress','delayed_stress']]
 def test_cost_delay_failure_cannot_be_hidden(self):
  r=self.rows('a');r[-1]['metrics']['total_return']=-.001
  self.assertFalse(eligible(r,30))
 def test_inadequate_sample_and_unknown_fail(self):
  self.assertFalse(eligible(self.rows('a',n=29),30));self.assertFalse(eligible(self.rows('a',audit='UNKNOWN'),30))
 def test_duplicate_cost_condition_rejected(self):
  r=self.rows("a")
  for x in r:x["condition"]="stress"
  self.assertFalse(eligible(r,30))
 def test_rank_and_no_multiple_family_winners(self):
  cs=[{'id':x,'family':'trend'} for x in ['a','b','c']]
  rs=self.rows('a')+self.rows('b',ret=.2)+self.rows('c',ret=.3,dd=.51)
  self.assertEqual(select(rs,cs),['b'])
 def test_development_does_not_select_winner(self):
  cs=[{'id':'a','family':'trend'}];rs=self.rows('a')
  for r in rs:r['period']='development'
  self.assertEqual(select(rs,cs),[])
if __name__=='__main__':unittest.main()
