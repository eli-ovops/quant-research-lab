import json,urllib.request,time,hashlib,pathlib,sys
P=pathlib.Path(__file__).parent

def fetch(name,url,data=None):
    t=time.time(); req=urllib.request.Request(url, data=None if data is None else json.dumps(data).encode(),headers={'User-Agent':'mechanism-research/1.0','Content-Type':'application/json'})
    meta={'url':url,'request':data,'started_unix':t}
    try:
        with urllib.request.urlopen(req,timeout=18) as r: b=r.read(5000000); meta['status']=r.status
        (P/'raw'/f'{name}.body').write_bytes(b); meta.update(bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
    except Exception as e: b=b'';meta['error']=repr(e)
    meta['ended_unix']=time.time();(P/'raw'/f'{name}.meta.json').write_text(json.dumps(meta,indent=2));print(name,json.dumps(meta))
    try:return json.loads(b)
    except:return None
if __name__=='__main__':
    fetch('gamma_probe','https://gamma-api.polymarket.com/events?active=true&closed=false&limit=100&order=id&ascending=true')
    fetch('eth_probe','https://ethereum-rpc.publicnode.com',{'jsonrpc':'2.0','id':1,'method':'eth_blockNumber','params':[]})
