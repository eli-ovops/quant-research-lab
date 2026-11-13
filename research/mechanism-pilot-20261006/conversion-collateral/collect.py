from probe import *
from abi import *
COMET='0xc3d688B66703497DAA19211EEdff47f25384cdc3';WETH='0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2';RPC='https://ethereum-rpc.publicnode.com'
block=json.loads((P/'raw/eth_probe.body').read_text())['result']
functions=[('getReserves()',[]),('targetReserves()',[]),('getCollateralReserves(address)',[WETH]),('isBuyPaused()',[]),('getAssetInfoByAddress(address)',[WETH]),('quoteCollateral(address,uint256)',[WETH,100_000_000]),('baseTokenPriceFeed()',[])]
req=[{'jsonrpc':'2.0','id':i,'method':'eth_call','params':[{'to':COMET,'data':enc(sig,*args)},block]} for i,(sig,args) in enumerate(functions)]
r=fetch('comet_state',RPC,req);print('decoded',[(functions[x['id']][0],words(x['result']) if 'result'in x else x) for x in r or []])
e=json.loads((P/'selected_event.json').read_text());ms=sorted(e['markets'],key=lambda m:int(m['id']));ids=[json.loads(m['clobTokenIds'])[1 if i==0 else 0] for i,m in enumerate(ms)]
fetch('poly_books','https://clob.polymarket.com/books',[{'token_id':x} for x in ids])
fetch('poly_market','https://clob.polymarket.com/markets/'+ms[0]['conditionId'])
