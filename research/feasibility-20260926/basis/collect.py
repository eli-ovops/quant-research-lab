import urllib.request, urllib.parse, json, hashlib, time
from pathlib import Path
P=Path(__file__).resolve().parent
R=P/'raw'; R.mkdir(exist_ok=True)
S=[]
def fetch(name,url):
    t=time.time(); rec={'name':name,'url':url,'request_ms':round(t*1000),'authenticated':False}
    try:
        req=urllib.request.Request(url,headers={'User-Agent':'public-feasibility-research/1.0'})
        with urllib.request.urlopen(req,timeout=20) as r:
            b=r.read(); rec.update(http_status=r.status,headers=dict(r.headers))
        path=R/(name+'.txt');path.write_bytes(b)
        rec.update(path=str(path),sha256=hashlib.sha256(b).hexdigest(),bytes=len(b))
        try: data=json.loads(b)
        except Exception: data=None
    except Exception as e:
        rec['error']=str(e);data=None
    rec['received_ms']=round(time.time()*1000);rec['elapsed_ms']=rec['received_ms']-rec['request_ms'];S.append(rec)
    (P/'sources.json').write_text(json.dumps(S,indent=2,ensure_ascii=False))
    return data
def api(name,path,**q):return fetch(name,'https://www.okx.com/api/v5/'+path+'?'+urllib.parse.urlencode(q))
if __name__=='__main__':
    import sys
    phase=sys.argv[1]
    if (P/'sources.json').exists():S[:]=json.loads((P/'sources.json').read_text())
    if phase=='spec':
        api('time','public/time')
        for c in ['BTC','ETH']:
            api(c+'_futures','public/instruments',instType='FUTURES',uly=c+'-USDT')
            api(c+'_spot','public/instruments',instType='SPOT',instId=c+'-USDT')
            api(c+'_tiers','public/position-tiers',instType='FUTURES',tdMode='isolated',uly=c+'-USDT')
            api(c+'_delivery','public/delivery-exercise-history',instType='FUTURES',uly=c+'-USDT')
            api(c+'_settlement','public/settlement-history',instFamily=c+'-USDT')
    elif phase=='books':
        for c in ['BTC','ETH']:
            instruments=json.loads((R/(c+'_futures.txt')).read_text()).get('data',[])
            for i in instruments:
                if i['state']!='live' or i['ctType']!='linear' or i['settleCcy']!='USDT':continue
                name=i['instId'];api(name+'_spotbook','market/books',instId=c+'-USDT',sz=100)
                api(name+'_book','market/books',instId=name,sz=100)
                api(name+'_history','market/history-candles',instId=name,bar='1Dutc',limit=100)
    elif phase=='docs':
        for n,u in [('daily','https://www.okx.com/en-gb/help/expiry-futures-daily-settlement-mechanism'),('fees','https://www.okx.com/en-sg/help/trading-fee-rules-faq'),('futures_fees','https://www.okx.com/ua/help/how-to-calculate-the-contract-transaction-fee'),('api_docs','https://app.okx.com/docs-v5/en/'),('delivery_rule','https://www.okx.com/help/expiry-futures-introduction')]:fetch(n,u)
    print(json.dumps([{k:r[k] for k in ['name','http_status','error','bytes','elapsed_ms'] if k in r} for r in S],indent=2))
