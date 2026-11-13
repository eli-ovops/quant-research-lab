import pathlib,json,time,urllib.request,hashlib
from abi import enc,words,kh
P=pathlib.Path(__file__).parent; RPC='https://ethereum-rpc.publicnode.com'; C='0xc3d688B66703497DAA19211EEdff47f25384cdc3'; W='0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2'; U='0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48'; Q='0x61fFE014bA17989E743c5F6cB21bF9697530B21e';END=26130865;START=END-216000;BLOCKS=[START+round(i*216000/11) for i in range(12)]
def rpc(name,requests):
 assert not (P/'raw'/f'{name}.json').exists(),'Do not overwrite receipts'
 assert len(list((P/'raw').glob('*.meta.json')))<19,'20 request budget reserve source request'
 meta={'url':RPC,'started_unix':time.time(),'request':requests,'submethods':len(requests) if isinstance(requests,list) else 1}
 try:
  req=urllib.request.Request(RPC,data=json.dumps(requests).encode(),headers={'Content-Type':'application/json'})
  with urllib.request.urlopen(req,timeout=35) as r:b=r.read(10000000);meta['http']=r.status
  (P/'raw'/f'{name}.json').write_bytes(b);meta.update(bytes=len(b),sha256=hashlib.sha256(b).hexdigest());result=json.loads(b)
 except Exception as e:meta['error']=repr(e);result=None
 meta['ended_unix']=time.time();(P/'raw'/f'{name}.meta.json').write_text(json.dumps(meta,indent=2));print(name,json.dumps({k:v for k,v in meta.items() if k!='request'}));return result
def call(id,b,sig,args=(),to=C):return {'jsonrpc':'2.0','id':id,'method':'eth_call','params':[{'to':to,'data':enc(sig,*args)},hex(b)]}
def header(id,b):return {'jsonrpc':'2.0','id':id,'method':'eth_getBlockByNumber','params':[hex(b),False]}
if __name__=='__main__':
 protocol={'frozen_unix':time.time(),'owner':'/root/conversion_collateral','routing_rule':'ROUTING-2026-09-30-v3','target':'astra medium','actual_model_effort_speed':'UNKNOWN','authorization':'Historical public read-only; local new directory; no wallet/signing/order/install/production/background','scope':'Fixed Ethereum USDC Comet/WETH/Uniswap v3 fee500;100 USDC trade;500 USDC capital cap','max_minutes':30,'max_public_request_operations':20,'RPC_submethods_separately_counted':True,'start_block_approx_30_days':START,'end_block':END,'blocks':BLOCKS,'selection':'12 uniformly spaced block numbers inclusive; frozen before historical calls. No pool/date/spread selection. Endpoint headers establish actual span; exact 30-day boundary is not assumed.','fields_each_sample':['block header','inventory WETH','reserves','targetReserves','isBuyPaused','100USDCquote'],'continuation':'All sufficient-inventory samples get fixed-path same-block and next-block quote/state. No full execution or gas claim without complete simulation. Optional all AbsorbCollateral(WETH) logs in bounded chunks, not success-selected.','success':'At least one historical sufficient-inventory state or precise bounded sampling/data limitation; never confuse 12 samples with continuous 30-day coverage.'}
 (P/'protocol.json').write_text(json.dumps(protocol,indent=2))
 b=END-7200;r=rpc('archive_probe',[header(0,b),call(1,b,'getCollateralReserves(address)',[W]),call(2,b,'getReserves()')]);print(json.dumps(r)[:800])
