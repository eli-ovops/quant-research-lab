import unittest,json
from pathlib import Path
B=Path(__file__).resolve().parent
class T(unittest.TestCase):
 def test_registration_and_units(self):
  p=json.loads((B/'protocol.json').read_text());s={x['instId']:x for x in json.loads((B/'instruments.json').read_text())};self.assertEqual(len(p['assets']),6);self.assertEqual(set(p['assets']),set(s));self.assertEqual(s['SUI-USDT-SWAP']['lotSz'],'1');self.assertEqual(s['DOGE-USDT-SWAP']['ctVal'],'1000');self.assertEqual(json.loads((B/'asset_registry.json').read_text())['LEAD_only'],['ETH-USDT-SWAP','SOL-USDT-SWAP'])
 def test_bounded_singlejob_existing_clock_TLS(self):
  c=(B/'collector.py').read_text();self.assertIn('startwall+2700',c);self.assertIn('logicalmax=240000000',c);self.assertIn('230000000',c);self.assertIn('240000000-sum',c);self.assertIn('2147483648',c);self.assertIn('ssl.CERT_REQUIRED',c);self.assertIn("'check_hostname':True",c);self.assertIn("'automatic_reconnects':0",c);self.assertIn("os.O_CREAT|os.O_EXCL",c);self.assertIn("job005_after_job004_terminal/collector_final.json",c);self.assertIn('os_shared_ns',c)
if __name__=='__main__':unittest.main()
