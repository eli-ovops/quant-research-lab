from pathlib import Path
from decimal import Decimal as D
import json,hashlib,gzip,csv,itertools
P=Path(__file__).resolve().parents[2]/'trend'/'variants_20260926'/'resume_implementation_20260926';O=P.parent;OUT=Path(__file__).resolve().parent
read=lambda n:json.loads((P/n).read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
counts={}
for name,base,rows in [('new_manifest',P,read('manifest.json')['files']),('new_sources',P,read('sources.json')),('old_manifest',O,json.loads((O/'manifest.json').read_text())['files']),('old_sources',O,json.loads((O/'sources.json').read_text()))]:
 for r in rows:
  f=Path(r['path']);f=f if f.is_absolute() else base/f;assert sha(f)==r['sha256']
 counts[name]=len(rows)
assert sha(P/'manifest.json')==read('seal.json')['manifest_sha256'];assert sha(O/'protocol.json')==read('seal.json')['original_protocol_sha256']
cache={c:{} for c in ['BTC','ETH']}
for r in json.loads((O/'reuse_hourly_sources.json').read_text()):
 for b in json.loads(Path(r['path']).read_text())['data']:cache[r['coin']][b[0]]=b
probes=[];data={c:dict(v) for c,v in cache.items()}
for i,a in enumerate(read('probe_attempts.json'),1):
 envelope=read(f'raw/probe{i}_result.json');obj=envelope.get('structuredContent') or json.loads(envelope['content'][0]['text']);assert obj['ok'];rr=obj['data']['data'];assert obj['data']['endpoint']=='GET /api/v5/market/history-candles'
 args=a['args'];c=args['instId'].split('-')[0];assert args['bar']=='1H' and args['limit']==12
 assert sorted(int(r[0]) for r in rr)==list(range(int(args['before'])+1,int(args['after']),3600000))
 assert rr==read(f'raw/probe{i}_normalized.json')['data']
 overlap=0
 for r in rr:
  assert len(r)==9 and r[-1]=='1';v=list(map(D,r[1:8]));assert all(x.is_finite() for x in v);assert 0<v[2]<=min(v[0],v[3])<=max(v[0],v[3])<=v[1] and min(v[4:])>0
  if r[0] in cache[c]:assert r==cache[c][r[0]];overlap+=1
  data[c][r[0]]=r
 assert overlap==(12 if i in [1,3] else 0)
 probes.append({'probe':i,'coin':c,'rows':len(rr),'exact_overlap':overlap})
start=1577548800000;end=1782864000000;coverage={c:len([t for t in v if start<=int(t)<end]) for c,v in data.items()};assert coverage=={'BTC':122,'ETH':122}
cases=read('synthetic/fixed_cases.json');assert len(cases)==40 and all(x['pass'] for x in cases)
assert {(x['entry'],x['exit'],x['condition']) for x in cases if x.get('mode')!='hold'}==set(itertools.product([24,48,72],[4,8,12],['baseline','fee2','slip20','delay1']))
s=read('synthetic/example/summary.json');cash=D(2000);inv={'BTC':D(0),'ETH':D(0)};dust=inv.copy()
for f in s['fills']:
 q=D(f['qty']);px=D(f['price']);c=f['coin']
 if f['side']=='buy':cash-=q*px;inv[c]+=q-D(f['base_fee'])
 else:cash+=q*px-D(f['quote_fee']);inv[c]-=q;dust[c]+=D(f['dust_added'])
 assert cash==D(f['cash_after'])
assert cash==D(s['metrics']['final_cash'])
for c in inv:assert inv[c]==D(s['dust'][c])+D(s['open_positions'].get(c,{}).get('net','0'))
h=read('historical_results.json');assert all(r['net_pnl'] is None for r in h['principal_scenarios']+h['auxiliary_hold'])
out={'hash_counts':counts,'seal_hashes_match':True,'probes':probes,'hours_per_coin':coverage,'missing_each':57032-122,'synthetic_configs':40,'synthetic_states_recorded':sum(x['curve_rows'] for x in cases),'example_cash_inventory_recomputed':True,'example_fills':len(s['fills']),'historical_pnl_all_null':True,'no_engine_or_tests_executed':True,'C_files_unchanged':True}
(OUT/'trend_variants_v2_implementation.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
