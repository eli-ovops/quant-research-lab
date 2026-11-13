import json,hashlib
from pathlib import Path
from datetime import datetime,timezone
R=Path(__file__).resolve().parent
OLD=R.parent/'independent-500-20261006'
Q=900000
P=json.loads((R/'protocol.json').read_text())
MAN={}
def ms(s):return int(datetime.fromisoformat(s.replace('Z','+00:00')).replace(tzinfo=timezone.utc).timestamp()*1000)
def check(p):
 b=p.read_bytes()
 if MAN:
  want=MAN[str(p.resolve())];assert len(b)==want['bytes'] and hashlib.sha256(b).hexdigest()==want['sha256'],'RAW_CHANGED:'+str(p)
 return json.loads(b)
def enable_seal():
 global MAN
 MAN={v['path']:v for v in json.loads((R/'data_manifest.json').read_text())['files']}
 for path in MAN:check(Path(path))
def load(coin,product):
 hold=coin in P['holdout_assets']
 assert not hold or (R/'selection.json').exists(),'HOLDOUT_BEFORE_SELECTION'
 base=R if hold else OLD;tag='SPOT' if product=='SPOT' else 'SWAP'
 rows=[]
 for p in sorted((base/'raw').glob(f'{coin}_{tag}_[0-9]*.json')):
  x=check(p)['response'];assert x['ok']
  rows.extend(v for v in x['data']['data'] if ms(P['raw_start'])<=int(v[0])<ms(P['end']))
 rows=[list(v) for v in dict.fromkeys(tuple(v) for v in rows)];rows.sort(key=lambda r:int(r[0]))
 spec=check(base/'raw'/f'{coin}_{tag}_spec.json')['data']['data'][0]
 assert spec['instId']==coin+'-USDT'+('-SWAP' if tag=='SWAP' else '')
 fund={}
 for p in sorted((base/'raw').glob(f'{coin}_fund_*.json')):
  for v in check(p)['data']['data']:fund[(v['fundingTime'],v['realizedRate'])]=v
 return rows,spec,list(fund.values())
def seal():
 previous=json.loads((OLD/'data_manifest.json').read_text());files=[]
 for v in previous['files']:
  p=OLD/v['file'];b=p.read_bytes();assert len(b)==v['bytes'] and hashlib.sha256(b).hexdigest()==v['sha256'],'PREVIOUS_RAW_CHANGED'
  files.append({'path':str(p.resolve()),'bytes':len(b),'sha256':v['sha256']})
 for p in sorted((R/'raw').glob('*.json')):
  b=p.read_bytes();files.append({'path':str(p.resolve()),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()})
 (R/'data_manifest.json').write_text(json.dumps({'created_utc':datetime.now(timezone.utc).isoformat(),'files':files,'warning':'Integrity only; newasset strategy evaluation forbidden before selection'},indent=2)+'\n')
if __name__=='__main__':seal();print('sealed')
