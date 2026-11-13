"""Capture PUBLIC metadata and independent REST depth. UNKNOWN never grants eligibility."""
import argparse
import json
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import requests
from evidence import atomic_json

REQUIRED = ['same_asset_and_unit','source_withdraw_enabled','destination_deposit_enabled',
            'same_network_and_contract','memo_and_minimums','account_fees_and_fee_currency',
            'order_rules','inventory_and_rebalance_cost','failure_cost']


def eligible(route):
    return all(isinstance(route.get(k),dict) and route[k].get('status')=='VERIFIED'
               and route[k].get('evidence') and route[k].get('checked_ms') for k in REQUIRED)


def public_get(url, port):
    start = time.time()*1000
    try:
        r = requests.get(url,proxies={'https':f'http://127.0.0.1:{port}'} if port else {},timeout=15)
        r.raise_for_status()
        data = r.json()
        if isinstance(data,dict) and 'code' in data and data['code']!='0':
            raise ValueError('public API rejected')
        return dict(url=url,requested_ms=start,received_ms=time.time()*1000,response=data)
    except Exception as exc:
        return dict(url=url,requested_ms=start,received_ms=time.time()*1000,error=type(exc).__name__)


def capture(port=7890):
    urls = {}
    for base in ['LSK','G']:
        urls[base+'_okx_instrument'] = 'https://www.okx.com/api/v5/public/instruments?instType=SPOT&instId='+base+'-USDT'
        urls[base+'_gate_currency'] = 'https://api.gateio.ws/api/v4/spot/currencies/'+base
        urls[base+'_gate_pair'] = 'https://api.gateio.ws/api/v4/spot/currency_pairs/'+base+'_USDT'
        urls[base+'_okx_depth'] = 'https://www.okx.com/api/v5/market/books?instId='+base+'-USDT&sz=100'
        urls[base+'_gate_depth'] = 'https://api.gateio.ws/api/v4/spot/order_book?currency_pair='+base+'_USDT&limit=100&with_id=true'
    with ThreadPoolExecutor(max_workers=5) as pool:
        futures = {key:pool.submit(public_get,url,port) for key,url in urls.items()}
        return {key:f.result() for key,f in futures.items()}


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parent/'monitor')
    parser.add_argument('--proxy-port',type=int,default=7890)
    args=parser.parse_args()
    data=capture(args.proxy_port)
    now=time.time()*1000
    path=args.root/('public-check-%d.json'%now)
    atomic_json(path,data)
    routes=[]
    for base in ['LSK','G']:
        gate=data[base+'_gate_currency'].get('response',{})
        networks=gate.get('chains') or [{'name':'UNKNOWN'}]
        for network in networks:
            name=network.get('name') or network.get('chain') or 'UNKNOWN'
            for source,destination in [('okx','gate'),('gate','okx')]:
                route=dict(symbol=base+'USDT',source=source,destination=destination,
                           gate_reported_network=name,okx_network='UNKNOWN',gate_public_metadata=network,
                           eligibility='BLOCKED_UNKNOWN',source_snapshot=str(path))
                for field in REQUIRED:
                    route[field]={'status':'UNKNOWN','evidence':None,'checked_ms':None}
                # Public status is a timestamped clue, never proof of the user's usable route.
                routes.append(route)
    atomic_json(args.root/'qualification.json',dict(updated_ms=now,routes=routes,
        executable=False,simulation_enabled=False,public_snapshot=str(path),
        note='Public metadata does not establish account permissions, OKX network mapping, real fees or inventory.'))
    print(json.dumps({'snapshot':str(path),'errors':{k:v['error'] for k,v in data.items() if 'error'in v},
                      'gate_currencies':{b:data[b+'_gate_currency'].get('response') for b in ['LSK','G']},
                      'routes':len(routes),'eligible':sum(eligible(r) for r in routes)},ensure_ascii=False))


if __name__=='__main__':main()
