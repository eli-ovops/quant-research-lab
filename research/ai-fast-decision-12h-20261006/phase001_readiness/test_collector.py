import unittest,json,tempfile
from pathlib import Path
from collector import stop_at,allowed,metadata,acquire
class T(unittest.TestCase):
 def test_hard_deadline(self):
  self.assertEqual(stop_at(100,200),200);self.assertEqual(stop_at(100,10000),2800);self.assertFalse(allowed(200,1,200,300,0,1,100));self.assertFalse(allowed(1,300,200,300,0,1,100))
 def test_bytecap(self):self.assertFalse(allowed(1,1,10,10,99,2,100))
 def test_noauth_channels_causalraw(self):
  raw=json.dumps({'arg':{'channel':'trades','instId':'BTC-USDT-SWAP'},'data':[{'ts':'10','sz':'2','count':'3','seqId':2}]});obj,c,a,ts=metadata(raw);self.assertEqual(ts,['10']);self.assertEqual(obj['data'][0]['count'],'3');self.assertNotIn('apiKey',obj)
 def test_duplicate_start(self):
  with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as d:
   p=Path(d)/'lock';acquire(p)
   with self.assertRaises(FileExistsError):acquire(p)
if __name__=='__main__':unittest.main()

