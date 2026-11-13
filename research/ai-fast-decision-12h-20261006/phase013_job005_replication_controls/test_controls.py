import unittest,hashlib
from controls import own_momentum,grid_candidates,direction,SEED
def book(t,mid,ordinal):return {'time':t,'mid':mid,'ordinal':ordinal,'conn':'c','clock_domain_id':'d','wall_ms':100000+t}
def event():return {'asof_ms':1000,'asof_ordinal':3,'connectionId':'c','clock_domain_id':'d','impulse_bps':101}
class T(unittest.TestCase):
 def test_1second_not_book_500ms(self):
  s={'books':[book(0,100,1),book(500,99,2),book(1000,100,3)],'times':[0,500,1000]};x=own_momentum(event(),s);self.assertEqual(x['direction'],0);self.assertEqual(x['status'],'WAIT_TRUE_ZERO');self.assertEqual(x['own_reference_ordinal'],1)
 def test_missingref_not_zero_and_futureordinal_excluded(self):
  s={'books':[book(500,99,1),book(1000,100,3)],'times':[500,1000]};self.assertIsNone(own_momentum(event(),s)['direction']);s={'books':[book(0,100,1),book(1000,100,3),book(1000,200,4)],'times':[0,1000,1000]};self.assertEqual(own_momentum(event(),s)['direction'],0)
 def test_seed_only_run_asset_grid(self):
  expected=1 if hashlib.sha256((SEED+'r'+'A'+'4').encode()).digest()[0]%2==0 else -1;self.assertEqual(direction('r','A',4),expected);self.assertEqual(direction('r','A',4),direction('r','A',4))
 def test_grid_first_strictafter_and_ttl(self):
  books=[book(1000,100,1),book(1100,100,2),book(36500,100,3)];events,rejected=grid_candidates({'A':{'books':books,'times':[1000,1100,36500]}},'r',0,37000);self.assertEqual(events[0]['asof_ordinal'],2);self.assertEqual(events[0]['grid_index'],0);self.assertEqual(rejected[0]['status'],'EXPIRED_GRID_BOOK')
if __name__=='__main__':unittest.main()
