from probe import *
from abi import *
C='0xc3d688B66703497DAA19211EEdff47f25384cdc3';W='0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2';U='0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48';Q='0x61fFE014bA17989E743c5F6cB21bF9697530B21e';RPC='https://ethereum-rpc.publicnode.com'
b=json.loads((P/'raw/eth_probe.body').read_text())['result'];s={x['id']:words(x['result']) for x in json.loads((P/'raw/comet_state.body').read_text())}
feed='0x'+hex(s[4][2])[2:].zfill(40);bf='0x'+hex(s[6][0])[2:].zfill(40)
cs=[(C,'getPrice(address)',[feed]),(C,'getPrice(address)',[bf]),(Q,'quoteExactInputSingle((address,address,uint256,uint24,uint160))',[W,U,s[5][0],500,0]),(feed,'latestRoundData()',[])]
req=[{'jsonrpc':'2.0','id':i,'method':'eth_call','params':[{'to':to,'data':enc(sig,*args)},b]} for i,(to,sig,args) in enumerate(cs)]+[{'jsonrpc':'2.0','id':4,'method':'eth_getBlockByNumber','params':[b,False]}]
fetch('comet_dex_oracle',RPC,req)
e=json.loads((P/'selected_event.json').read_text());a='0xd91E80cF2E7be2e162c6513ceD06f1dD0dA35296';ms=sorted(e['markets'],key=lambda x:int(x['id']));mid=ms[0]['negRiskMarketID']
cs=[('col()',[]),('getMarketData(bytes32)',[mid])]+[('getPositionId(bytes32,bool)',[m['questionID'],0 if i==0 else 1]) for i,m in enumerate(ms)]
req=[{'jsonrpc':'2.0','id':i,'method':'eth_call','params':[{'to':a,'data':enc(sig,*args)},'latest']} for i,(sig,args) in enumerate(cs)]
fetch('poly_adapter','https://polygon-bor-rpc.publicnode.com',req)
