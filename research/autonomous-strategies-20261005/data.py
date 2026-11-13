"""Read-only, hash-verified public dataset loader. Confirmation opt-in only."""
from pathlib import Path
import sys,json,hashlib,math,datetime
P=Path(__file__).resolve().parent;ROOT=P.parents[1];OLD=ROOT/'research/technical-patterns-20260930'
LEGACY=ROOT/'research/feasibility-20260926/trend/variants_20260926/admissible_periods_20260926'
sys.path.insert(0,str(LEGACY));import source_gate
sys.path.remove(str(LEGACY))
H=3600000

def ms(x):return int(datetime.datetime.fromisoformat(x.replace('Z','+00:00')).replace(tzinfo=datetime.timezone.utc).timestamp()*1000)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(p,x):Path(p).write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')

def validate(rows,start,end):
 d={};zeros=[]
 for r in rows:
  if len(r)!=9:raise ValueError('raw_fields')
  t=int(r[0])
  if not start<=t<end:continue
  v=list(map(float,r[1:8]));o,h,l,c=v[:4]
  if t%H or r[8]!='1' or not all(math.isfinite(x) for x in v) or not 0<l<=min(o,c)<=max(o,c)<=h or min(v[4:])<0:raise ValueError('invalid_raw')
  if v[4]==0:
   if t>=ms('2023-01-01'):raise ValueError('zero_volume_in_evaluation')
   zeros.append(t)
  if t in d and d[t]!=r:raise ValueError('conflicting_duplicate')
  d[t]=r
 want=set(range(start,end,H));missing=want-set(d)
 if missing:raise ValueError('missing_hours:'+str(len(missing)))
 return [d[t] for t in sorted(d)],sorted(set(zeros))

def load(confirmation=False):
 proto=json.loads((P/'protocol.json').read_text());raw,proof=source_gate.load()
 old_manifest=json.loads((OLD/'cross-asset-01/manifest.json').read_text());hashes={r['path']:r['sha256'] for r in old_manifest['files']}
 out={};specs={};manifest=[];gate={};start=ms('2022-12-10T08:00:00Z');end=ms('2026-10-01' if confirmation else '2026-07-01')
 for c in proto['assets']:
  if c in raw:rows=list(raw[c].values())
  else:
   rows=[]
   for f in sorted((OLD/'cross-asset-01/raw').glob(c+'_[0-9][0-9][0-9].json')):
    assert sha(f)==hashes[str(f.resolve())];manifest.append({'path':str(f),'sha256':sha(f)});rows+=json.loads(f.read_text())['data']['data']
  if confirmation:
   for f in sorted((P/'public_raw').glob(c+'_[0-9][0-9][0-9].json')):
    x=json.loads(f.read_text());r=x['response'];assert r['ok'] and x['request']['instId']==c+'-USDT';manifest.append({'path':str(f),'sha256':sha(f)})
    # New pages may overlap old June rows, which remain cross-checked by duplicate equality.
    rows+=r['data']['data']
  out[c],zeros=validate(rows,start,end);gate[c]={'hour_count':len(out[c]),'warmup_zero_hours':zeros,'trade_period_zero_hours':0}
  f=P/'public_raw'/f'{c}_spec.json';x=json.loads(f.read_text());assert x['ok'];sp=x['data']['data'][0]
  assert sp['instId']==c+'-USDT' and sp['instType']=='SPOT' and sp['quoteCcy']=='USDT';specs[c]=sp;manifest.append({'path':str(f),'sha256':sha(f)})
 return out,specs,{'reference_proof':proof,'files':manifest,'gate':gate,'confirmation_loaded':confirmation,'specs_historical_validity':'UNKNOWN_CURRENT_SNAPSHOT'}
if __name__=='__main__':
 d,sp,proof=load();dump(P/'development_input_gate.json',proof);print({c:len(v) for c,v in d.items()})
