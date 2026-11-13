from pathlib import Path
import json,unittest,copy
from fractions import Fraction as F
from frozen_pressure_rules import PressureRules as Old
from pressure_rules_rolling import PressureRules as New
REG=json.loads((Path(__file__).parent/'instruments.json').read_text())
DOMAIN='SYNTHETIC_TEST_DOMAIN';START=1000000000000
def book(price):
 return {'asks':[[str(price+.01+i*.01),'50'] for i in range(5)],'bids':[[str(price-.01-i*.01),'50'] for i in range(5)]}
def row(ordinal,dt,channel,data,conn='TEST'):
 return {'local_ordinal':ordinal,'os_shared_ns':START+dt,'receive_wall_ns':START+dt,'run_id':'SYNTHETIC','connectionId':conn,'clock_domain_id':DOMAIN,'boot_identity':'TEST','instId':'SUI-USDT-SWAP','channel':channel,'raw':json.dumps({'arg':{'instId':'SUI-USDT-SWAP','channel':channel},'data':data})}
def trade(id,px='100',sz='1000',side='sell'):
 return {'tradeId':id,'px':px,'sz':sz,'side':side,'ts':'1','count':'1'}
def verify(sequence,cut=None):
 a=Old(REG,DOMAIN,cut);b=New(REG,DOMAIN,cut)
 for r in sequence:
  x=a.ingest(r);y=b.ingest(r);assert x==y,(r,x,y)
  s=a.states['SUI-USDT-SWAP'];t=b.states['SUI-USDT-SWAP'];n=r['os_shared_ns'];one=[v for v in s['flow'] if v[0]>n-1000000000]
  assert sum((v[1] for v in s['flow']),F(0))==t['cached_total10'] and sum((v[2] for v in s['flow']),F(0))==t['cached_net10']
  assert sum((v[1] for v in one),F(0))==t['cached_total1'] and sum((v[2] for v in one),F(0))==t['cached_net1']
 return a,b
def qualified_sequence():
 return [row(1,0,'books5',[book(100)]),row(2,0,'trades',[trade('first')]),row(3,5000000000,'trades',[trade('prior')]),row(4,9000000000,'books5',[book(100)]),row(5,9990000000,'trades',[trade('fresh','98.9')]),row(6,10000000000,'books5',[book(98.9)]),row(7,10050000000,'books5',[book(98.9)])]
class Tests(unittest.TestCase):
 def test_leftbound_sameclock(self):
  verify([row(1,0,'trades',[trade('a'),trade('b',side='buy')]),row(2,0,'trades',[trade('c')]),row(3,1000000000,'books5',[book(100)]),row(4,10000000000,'books5',[book(100)])])
 def test_actualqualification_andcooldown(self):
  a,b=verify(qualified_sequence());self.assertEqual(a.cool,b.cool);self.assertTrue(a.cool);self.assertTrue(any('WAIT_RULE35_COOLDOWN' in k for k in a.counters))
 def test_pre_cut_no_cool(self):
  a,b=verify(qualified_sequence(),START+10050000000);self.assertEqual(len(a.cool),1);self.assertEqual(a.cool,b.cool)
 def test_duplicate_no_refresh(self):
  a,b=verify([row(1,0,'trades',[trade('a')]),row(2,1000000000,'trades',[trade('a')]),row(3,2000000000,'books5',[book(100)])]);self.assertEqual(b.states['SUI-USDT-SWAP']['lasttrade_ns'],START);self.assertEqual(b.states['SUI-USDT-SWAP']['cached_total1'],0)
 def test_conflict_unknown(self):
  a,b=verify([row(1,0,'trades',[trade('a')]),row(2,100,'trades',[trade('a',px='99')])]);self.assertTrue(b.states['SUI-USDT-SWAP']['conflict'])
 def test_reference_cold_and_no_new_volume(self):
  verify([row(1,0,'books5',[book(100)]),row(2,0,'trades',[trade('x')]),row(3,11000000000,'books5',[book(98)])])
 def test_connection_refusal_rewarm(self):
  for cls in [Old,New]:
   obj=cls(REG,DOMAIN);obj.ingest(row(1,0,'trades',[trade('a')]))
   with self.assertRaises(ValueError):obj.ingest(row(2,1,'trades',[trade('b')],conn='OTHER'))
   fresh=cls(REG,DOMAIN);r=fresh.ingest(row(1,0,'trades',[trade('b')],conn='OTHER'));self.assertEqual(r['rejectreason'],'WAIT_TRADE_WARMUP10');self.assertFalse(fresh.cool)
 def test_no_direct_later_candidate(self):
  obj=New(REG,DOMAIN);r=row(1,0,'trades',[trade('a')]);obj.ingest(r)
  with self.assertRaises(RuntimeError):obj.candidate('SUI-USDT-SWAP',row(2,2000000000,'books5',[book(99)]))
 def test_other_asset_does_not_advance_sui_cache(self):
  a=Old(REG,DOMAIN);b=New(REG,DOMAIN);r=row(1,0,'trades',[trade('a')]);self.assertEqual(a.ingest(r),b.ingest(r));other=row(2,2000000000,'books5',[book(100)]);other['instId']='ETH-USDT-SWAP';other['raw']=json.dumps({'arg':{'instId':'ETH-USDT-SWAP','channel':'books5'},'data':[book(100)]});self.assertEqual(a.ingest(other),b.ingest(other));self.assertEqual(b.states['SUI-USDT-SWAP']['cached_total1'],100000);r=row(3,2000000000,'books5',[book(100)]);self.assertEqual(a.ingest(r),b.ingest(r));self.assertEqual(b.states['SUI-USDT-SWAP']['cached_total1'],0)
 def test_btc_eth_sui_interleaved_per_asset_exact(self):
  a=Old(REG,DOMAIN);b=New(REG,DOMAIN)
  sequence=[('BTC-USDT-SWAP',0),('ETH-USDT-SWAP',0),('SUI-USDT-SWAP',0),('BTC-USDT-SWAP',1000000000),('ETH-USDT-SWAP',5000000000),('BTC-USDT-SWAP',10000000000),('ETH-USDT-SWAP',[REDACTED_PHONE]),('SUI-USDT-SWAP',[REDACTED_PHONE])]
  for ordinal,(asset,dt) in enumerate(sequence,1):
   r=row(ordinal,dt,'trades',[trade(asset+str(ordinal))]);r['instId']=asset;r['raw']=json.dumps({'arg':{'instId':asset,'channel':'trades'},'data':[trade(asset+str(ordinal))]});self.assertEqual(a.ingest(r),b.ingest(r))
   for aa in ['BTC-USDT-SWAP','ETH-USDT-SWAP','SUI-USDT-SWAP']:
    old=a.states[aa];new=b.states[aa];self.assertEqual(sum((x[1] for x in old['flow']),F(0)),new['cached_total10']);self.assertEqual(sum((x[2] for x in old['flow']),F(0)),new['cached_net10'])
    if aa==asset:
     one=[x for x in old['flow'] if x[0]>r['os_shared_ns']-1000000000];self.assertEqual(sum((x[1] for x in one),F(0)),new['cached_total1']);self.assertEqual(sum((x[2] for x in one),F(0)),new['cached_net1'])
if __name__=='__main__':unittest.main()
