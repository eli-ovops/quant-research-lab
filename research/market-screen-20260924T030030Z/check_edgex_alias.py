"""Public evidence-backed alias check; EDGE on OKX is EDGEX on Gate."""
import sys,json,gzip,time,hashlib
from pathlib import Path
from collections import Counter
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from screen_markets import Capture,depth_pair,dump
parent=Path(__file__).resolve().parent
out=parent/'alias-edgex-check';out.mkdir()
meta={}
with gzip.open(parent/'public-responses.jsonl.gz','rt') as f:
 for _ in range(3):
  r=json.loads(next(f));meta[r['url']]=r['response']
catalog=json.loads((parent/'catalog.json').read_text())
m=next(x for x in catalog if x['symbol']=='EDGEUSDT').copy()
m['gate_pair']=next(x for x in meta['https://api.gateio.ws/api/v4/spot/currency_pairs'] if x['id']=='EDGEX_USDT')
m['gate_currency']=next(x for x in meta['https://api.gateio.ws/api/v4/spot/currencies'] if x['currency']=='EDGEX')
m.update(gate_id='EDGEX_USDT',gate_name='edgeX',identity='CONTRACT_MATCH_PUBLIC_SOURCES',route_eligibility='BLOCKED_UNKNOWN')
assert m['gate_currency']['chains'][0]['addr'].lower()=='0xb0076de78dc50581770bba1d211ddc0ad4f2a241'
dump(out/'mapping.json',dict(market=m,official_sources=[
 'https://www.okx.com/en-us/help/okx-to-list-edge-edgex-for-spot-trading',
 'https://www.gate.com/zh/announcements/article/50464'],
 limitation='Matching public contract identity is not deposit/withdrawal availability or verified fees.',
 rejected_pair='OKX EDGE (edgeX) versus Gate EDGE (Definitive) are different assets'))
c=Capture(out,7890);rows=[]
try:
 with (out/'observations.jsonl').open('x') as log:
  for n in range(10):
   r=depth_pair(c,m,'alias_corrected_'+str(n+1));rows.append(r);log.write(json.dumps(r)+'\n');log.flush();time.sleep(2)
finally:
 c.close();raw=out/'public-responses.jsonl.gz'
 dump(out/'capture-manifest.json',dict(bytes=raw.stat().st_size,sha256=hashlib.sha256(raw.read_bytes()).hexdigest(),responses=c.seq))
dump(out/'summary.json',dict(quality_counts=dict(Counter(x['quality'] for x in rows)),
 valid_estimates=[dict(r,observed_ms=x['observed_ms']) for x in rows for r in x['results'] if r['status']=='ESTIMATE_ONLY' and r['scenario']=='higher_gate']))
print(json.dumps({'out':str(out),'quality':dict(Counter(x['quality'] for x in rows))}))
