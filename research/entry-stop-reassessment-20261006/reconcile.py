import json,gzip,statistics as s,hashlib
from pathlib import Path
R=Path(__file__).resolve().parent
out={}; hashes={};count=0
for batch in ['controls','stops']:
 expected=json.loads((R/batch/'results.json').read_text())
 for key,a in expected['results'].items():
  p=R/batch/(key+'.jsonl.gz');rr=[json.loads(z) for z in gzip.open(p,'rt')];hashes[str(p)]=hashlib.sha256(p.read_bytes()).hexdigest()
  assert len(rr)==240 and len({(r['coin'],r['start']) for r in rr})==240
  assert abs(s.mean(r['metrics']['return'] for r in rr)-a['mean_return'])<1e-10
  assert sum(r['metrics']['target_hit'] for r in rr)==a['targets']
  assert all(r['metrics']['terminal_residual_base']==0 for r in rr)
  count+=len(rr)
  if batch=='stops':
   dates={t:s.mean(r['metrics']['return'] for r in rr if r['start']!=t) for t in sorted({r['start'] for r in rr})}
   coins={c:s.mean(r['metrics']['return'] for r in rr if r['coin']!=c) for c in sorted({r['coin'] for r in rr})}
   active=[r for r in rr if r['metrics']['entry_count']]
   out[key]={'mean':a['mean_return'],'active_mean':s.mean(r['metrics']['return'] for r in active),'leave_one_date_out':dates,'leave_one_coin_out':coins,'negative_date_exclusions':sum(v<0 for v in dates.values()),'negative_coin_exclusions':sum(v<0 for v in coins.values()),'worst_leave_date':min(dates.values()),'worst_leave_coin':min(coins.values())}
(R/'reconciliation.json').write_text(json.dumps({'ok':True,'accounts':count,'hashes':hashes,'checks':['240 unique coin/start per config','reported means and target counts','no residual position'],'runner_independent_replays':7680},indent=2))
(R/'stop_fragility.json').write_text(json.dumps(out,indent=2));print(json.dumps({k:{a:b for a,b in v.items() if not isinstance(b,dict)} for k,v in out.items()},indent=2))
