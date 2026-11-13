"""Local-only gate for the two originally independent admissible periods."""
from pathlib import Path
from decimal import Decimal as D
import json,hashlib,datetime
P=Path(__file__).resolve().parent;OLD=P.parent;DATA=OLD/'full_history_20260926';H=3600000
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
ms=lambda s:int(datetime.datetime.fromisoformat(s).timestamp()*1000)
def authority():
 a=json.loads((P/'authority.json').read_text());assert sha(Path(a['task_file']))==a['sha256'];assert sha(OLD/'protocol.json')==a['original_protocol_sha256'];return a

def load():
 authority();seal=json.loads((DATA/'seal.json').read_text());assert sha(DATA/'manifest.json')==seal['manifest_sha256'];manifest=json.loads((DATA/'manifest.json').read_text());expected={r['path']:r['sha256'] for r in manifest['files']};src=json.loads((DATA/'market_sources.json').read_text());raw={c:{} for c in ['BTC','ETH']};count=0
 assert sha(DATA/'market_sources.json')==expected['market_sources.json']
 for r in src:
  f=Path(r['path']);n=Path(r['normalized_path']);assert sha(f)==r['sha256']==expected[str(f.relative_to(DATA))];assert sha(n)==r['normalized_sha256']==expected[str(n.relative_to(DATA))]
  env=json.loads(f.read_text());obj=env.get('structuredContent') or json.loads(env['content'][0]['text']);rows=json.loads(n.read_text())['data'];assert obj['ok'] and rows==obj['data']['data'];c=r['id'].split('_')[0]
  for row in rows:
   t=int(row[0]);assert t not in raw[c] or raw[c][t]==row;raw[c][t]=row
  count+=2
 return raw,{'verified_market_files':count,'original_full_history_manifest':seal['manifest_sha256'],'no_new_requests':True}

def for_period(raw,period):
 a=authority()
 if period not in a['allowed_periods']:raise ValueError('period_not_admitted:'+period)
 proto=json.loads((OLD/'protocol.json').read_text());s,e=proto['periods_UTC_half_open'][period];start,end=ms(s),ms(e);lo=start-80*H;out={};checks=[]
 for c in ['BTC','ETH']:
  wanted=list(range(lo,end,H));d=raw[c]
  if any(t not in d for t in wanted):raise ValueError('missing_warmup_or_period')
  rr=[d[t] for t in wanted]
  for r in rr:
   if len(r)!=9 or r[-1]!='1':raise ValueError('fields_or_confirmation')
   v=list(map(D,r[1:8]));assert all(x.is_finite() for x in v) and 0<v[2]<=min(v[0],v[3])<=max(v[0],v[3])<=v[1] and v[4]>0 and min(v[5:])>=0
  daily={int(r[0]):r for f in list((OLD.parent/'raw').glob(c+'_daily_*.txt'))+list((OLD.parent/'resume_20260926'/'raw').glob(c+'_daily_*.txt')) for r in json.loads(f.read_text())['data']};days=0
  for t in range(((lo+24*H-1)//(24*H))*(24*H),end,24*H):
   rows=[d[t+i*H] for i in range(24)];v=[D(rows[0][1]),max(D(r[2]) for r in rows),min(D(r[3]) for r in rows),D(rows[-1][4])]+[sum(D(r[j]) for r in rows) for j in [5,6,7]]
   if t not in daily or v!=list(map(D,daily[t][1:8])):raise ValueError('daily_price_or_volume_difference')
   days+=1
  out[c]=rr;checks.append({'coin':c,'hours_including80_warmup':len(rr),'full_days_exact_OHLC_and_volume':days,'pass':True})
 return out,start,end,checks
