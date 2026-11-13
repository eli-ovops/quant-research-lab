"""Public raw evidence loader; does not fill or repair price observations."""
import json,hashlib
from pathlib import Path
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parent
Q=900000

def ms(s):
    return int(datetime.fromisoformat(s.replace('Z','+00:00')).replace(tzinfo=timezone.utc).timestamp()*1000)

_MANIFEST=None
def checked_read(p):
    if _MANIFEST is not None:
        b=p.read_bytes();wanted=_MANIFEST[str(p.relative_to(ROOT))]
        assert len(b)==wanted["bytes"] and hashlib.sha256(b).hexdigest()==wanted["sha256"], "RAW_CHANGED:"+str(p)
        return b
    return p.read_bytes()

def enable_seal():
    global _MANIFEST
    _MANIFEST={r["file"]:r for r in json.loads((ROOT/"data_manifest.json").read_text())["files"]}
    for f in _MANIFEST:checked_read(ROOT/f)

def load(coin,product,cutoff):
    tag='SPOT' if product=='SPOT' else 'SWAP'
    rows=[]
    for p in sorted((ROOT/'raw').glob(f'{coin}_{tag}_[0-9]*.json')):
        x=json.loads(checked_read(p));r=x['response']
        assert r['ok'] is True
        rows.extend(v for v in r['data']['data'] if ms('2026-07-05T00:00:00Z')<=int(v[0])<cutoff)
    # Keep conflicting duplicates so the engine and auditor can reject them.
    seen={};out=[]
    for r in rows:
        key=tuple(r)
        if key not in seen:out.append(r);seen[key]=True
    out.sort(key=lambda r:int(r[0]))
    spec=json.loads(checked_read(ROOT/'raw'/f'{coin}_{tag}_spec.json'))['data']['data'][0]
    assert spec['instId']==coin+'-USDT'+('-SWAP' if tag=='SWAP' else '')
    fund={}
    for p in sorted((ROOT/'raw').glob(f'{coin}_fund_*.json')):
        for r in json.loads(checked_read(p))['data']['data']:
            # Endpoint bracketing funding is necessary; not price information.
            key=(r['fundingTime'],r['realizedRate']);fund[key]=r
    return out,spec,list(fund.values())

def seal():
    records=[]
    for p in sorted((ROOT/'raw').glob('*.json')):
        b=p.read_bytes();records.append({'file':str(p.relative_to(ROOT)),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()})
    p=json.loads((ROOT/'protocol.json').read_text());quality=[]
    for coin in p['assets']:
        for product in ('SPOT','CONDITIONAL_SWAP'):
            rows,_,_=load(coin,product,ms(p['end']));ts={int(r[0]) for r in rows}
            quality.append({'coin':coin,'product':product,'rows':len(rows),'unique_timestamps':len(ts),'missing':sum(t not in ts for t in range(ms(p['raw_start']),ms(p['end']),Q)),'zero_volume':sum(float(r[5])<=0 for r in rows),'unconfirmed':sum(r[-1]!='1' for r in rows)})
    x={'created_utc':datetime.now(timezone.utc).isoformat(),'files':records,'quality':quality,'warning':'Integrity seal only; no confirmation PnL computed.'}
    (ROOT/'data_manifest.json').write_text(json.dumps(x,indent=2)+'\n')
    return quality
if __name__=='__main__':print(json.dumps(seal()))
