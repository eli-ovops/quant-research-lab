"""Bounded public-only collector. Saved responses immutable; no auth/config reads."""
from pathlib import Path
import urllib.request, urllib.parse, json, time, hashlib, sys, datetime
from html.parser import HTMLParser
P=Path(__file__).resolve().parent
RAW=P/'raw';RAW.mkdir(exist_ok=True)
class Text(HTMLParser):
    def __init__(self): super().__init__();self.parts=[];self.skip=0
    def handle_starttag(self,tag,attrs):
        if tag in ('script','style'):self.skip+=1
    def handle_endtag(self,tag):
        if tag in ('script','style'):self.skip=max(0,self.skip-1)
    def handle_data(self,s):
        if not self.skip and s.strip():self.parts.append(s.strip())
def fetch(name,url):
    target=RAW/(name+'.txt')
    if target.exists():return target.read_text()
    sp=P/'sources.json';sources=json.loads(sp.read_text()) if sp.exists() else []
    entry={'name':name,'url':url,'request_ms':time.time_ns()//1000000,'authenticated':False}
    try:
        req=urllib.request.Request(url,headers={'User-Agent':'bounded-public-research/1.0','Accept':'application/json,text/html'})
        with urllib.request.urlopen(req,timeout=25) as r:
            body=r.read(12_000_000);entry['http_status']=r.status
            entry['headers']={k:v for k,v in r.headers.items() if k.lower() in ['date','content-type','content-length','cache-control','age']}
        target.write_bytes(body)
        entry.update(path=str(target),sha256=hashlib.sha256(body).hexdigest(),bytes=len(body))
        text=body.decode('utf-8')
        if '<html' in text[:500].lower() or '<!doctype' in text[:100].lower():
            parser=Text();parser.feed(text);(RAW/(name+'_readable.txt')).write_text('\n'.join(parser.parts))
    except Exception as e:
        entry['error']=type(e).__name__+': '+str(e);text=None
    entry['received_ms']=time.time_ns()//1000000
    entry['elapsed_ms']=entry['received_ms']-entry['request_ms']
    sources.append(entry);sp.write_text(json.dumps(sources,ensure_ascii=False,indent=2)+'\n')
    print(name,entry.get('http_status',entry.get('error')),entry.get('bytes',''),flush=True)
    return text
def api(name,path,**params):
    text=fetch(name,'https://www.okx.com/api/v5/'+path+'?'+urllib.parse.urlencode(params))
    if text is None:return None
    obj=json.loads(text)
    if obj.get('code')!='0':print('API_ERROR',name,obj,flush=True);return None
    return obj['data']
def initial():
    api('time','public/time')
    for c in ['BTC','ETH']:
        for typ,suffix in [('SPOT',''),('SWAP','-SWAP')]:
            inst=c+'-USDT'+suffix
            api(c+'_'+typ.lower()+'_spec','public/instruments',instType=typ,instId=inst)
            api(c+'_'+typ.lower()+'_book','market/books',instId=inst,sz=100)
        api(c+'_funding_current','public/funding-rate',instId=c+'-USDT-SWAP')
        api(c+'_funding_0','public/funding-rate-history',instId=c+'-USDT-SWAP',limit=100)
        api(c+'_tiers','public/position-tiers',instType='SWAP',tdMode='isolated',instFamily=c+'-USDT')
    docs={
        'funding_mechanism':'https://www.okx.com/en-eu/help/perps-funding-fee-mechanism',
        'funding_faq':'https://www.okx.com/en-sg/help/funding-fees-for-perpetual-contracts-faq',
        'fee_rules':'https://www.okx.com/en-sg/help/trading-fee-rules-faq',
        'fees':'https://www.okx.com/fees',
        'api_docs':'https://www.okx.com/docs-v5/en/',
    }
    for name,url in docs.items():fetch(name,url)
def stamp(x):return int(datetime.datetime.fromisoformat(x).replace(tzinfo=datetime.timezone.utc).timestamp()*1000)
def history():
    start=stamp('2026-06-28');end=stamp('2026-09-26')
    for c in ['BTC','ETH']:
        # One probe into desired one-year coverage. Do not silently imply 3 months is enough.
        api(c+'_funding_older_probe','public/funding-rate-history',instId=c+'-USDT-SWAP',after=stamp('2026-06-01'),limit=100)
        first=json.loads((RAW/(c+'_funding_0.txt')).read_text())['data']
        cursor=min(int(x['fundingTime']) for x in first)
        for page in range(1,40):
            rows=api(c+'_funding_'+str(page),'public/funding-rate-history',instId=c+'-USDT-SWAP',after=cursor,limit=100)
            if not rows:break
            nxt=min(int(x['fundingTime']) for x in rows)
            if nxt>=cursor:raise RuntimeError('Funding cursor did not decrease')
            cursor=nxt
            if cursor<start:break
        for kind in ['spot','swap','mark']:
            endpoint='market/history-mark-price-candles' if kind=='mark' else 'market/history-candles'
            inst=c+'-USDT'+('' if kind=='spot' else '-SWAP')
            cursor=end+3600001 # include exit bar and one-hour delayed exit as separate stress
            for page in range(40):
                rows=api(c+'_'+kind+'_1H_'+str(page),endpoint,instId=inst,bar='1H',after=cursor,limit=100)
                if not rows:break
                nxt=min(int(x[0]) for x in rows)
                if nxt>=cursor:raise RuntimeError('Candle cursor did not decrease')
                cursor=nxt
                if cursor<=start:break
    for name,url in {
        'formula_change_2025':'https://www.okx.com/en-us/help/okx-to-change-the-funding-rate-formula-for-perpetual-futures',
        'formula_change_2026':'https://www.okx.com/en-eu/help/important-update-revision-of-the-funding-rate-formula-for-okx-perpetual',
        'liquidation':'https://www.okx.com/en-au/help/forced-liquidation-faq',
        'isolated_margin':'https://www.okx.com/en-au/help/vii-introduction-to-the-isolated-mode-of-single-multi-currency-portfolio-margin',
    }.items():fetch(name,url)
if __name__=='__main__':
    if len(sys.argv)>1 and sys.argv[1]=='history':history()
    else:initial()
