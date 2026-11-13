"""Read-only C audit, does not import or run any C code or strategy."""
from pathlib import Path
from decimal import Decimal
import json,hashlib,datetime,csv
P=Path(__file__).resolve().parents[2]/'trend'
O=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
sources=json.loads((P/'sources.json').read_text());manifest=json.loads((P/'manifest.json').read_text());proto=json.loads((P/'protocol.json').read_text());freeze=json.loads((P/'protocol_freeze.json').read_text());seal=json.loads((P/'seal.json').read_text())
source_bad=[r['path'] for r in sources if sha(Path(r['path']))!=r['sha256']]
manifest_bad=[r['path'] for r in manifest['files'] if sha(Path(r['path']))!=r['sha256']]
assert not source_bad and not manifest_bad
assert sha(P/'protocol.json')==freeze['sha256']==seal['protocol_sha256']
assert sha(P/'analyze.py')==seal['analysis_sha256']
assert sha(P/'sources.json')==seal['data_sources_sha256']
day=86400000
def ts(s):return int(datetime.datetime.fromisoformat(s).replace(tzinfo=datetime.timezone.utc).timestamp()*1000)
def date(t):return datetime.datetime.fromtimestamp(t/1000,datetime.timezone.utc).date().isoformat()
assets={};miss={}
for c in ['BTC','ETH']:
 raw=[]
 for f in (P/'raw').glob(c+'_daily_*.txt'):
  d=json.loads(f.read_text());assert d['code']=='0';rs=d['data'];assert all(int(a[0])>int(b[0]) for a,b in zip(rs,rs[1:]));raw.extend(rs)
 stamps=[int(r[0]) for r in raw];st=sorted(stamps);assert len(stamps)==len(set(stamps));assert all(b-a==day for a,b in zip(st,st[1:]))
 for r in raw:
  _,op,hi,lo,cl,vol,*rest=r
  op,hi,lo,cl,vol=map(Decimal,[op,hi,lo,cl,vol]);assert 0<lo<=min(op,cl)<=max(op,cl)<=hi and vol>=0 and r[-1]=='1' and int(r[0])%day==0
 spec=json.loads((P/'raw'/f'{c}_spec.txt').read_text())['data'][0]
 assets[c]={'count':len(raw),'first':date(st[0]),'last':date(st[-1]),'pre_current_listTime':sum(t<int(spec['listTime']) for t in stamps),'internal_gaps':0,'duplicate':0}
 for name,(a,b) in proto['periods'].items():
  required=set(range(ts(a)-40*day,ts(b)+day,day));missing=sorted(required-set(stamps));miss.setdefault(name,{})[c]={'required':len(required),'missing':len(missing)}
cs={n:len(list(csv.DictReader((P/n).open()))) for n in ['fills_all.csv','trades_all.csv','equity_all.csv']};assert not any(cs.values())
res=json.loads((P/'results_all.json').read_text());assert res['completed_historical_scenarios']==0 and res['net_pnl'] is None
first_trend=min(r['request_utc'] for r in sources if '_daily_' in r['name'])
out={'checked_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source_hashes':len(sources),'manifest_hashes':len(manifest['files']),'mismatches':source_bad+manifest_bad,'protocol_hash_verified':True,'freeze_utc':freeze['at'],'first_trend_request_utc':first_trend,'freeze_precedes_trend_download':freeze['at']<first_trend,'assets':assets,'missing_recomputed':miss,'csv_data_rows':cs,'historical_strategy_rerun':False,'C_files_modified':False,'economic_verdict':'INSUFFICIENT_EVIDENCE supported','implementation_acceptance':'NOT_GRANTED; no valid historical trades'}
(O/'trend_checks.json').write_text(json.dumps(out,ensure_ascii=False,indent=2));print(json.dumps(out,indent=2))
