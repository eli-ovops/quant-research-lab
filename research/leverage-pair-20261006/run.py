import sys,json,gzip,hashlib,time,statistics,collections
from pathlib import Path
from datetime import datetime,timezone,timedelta
R=Path(__file__).resolve().parent;OLD=R.parent/'aggressive-500-20261006';sys.path.insert(0,str(OLD))
import engine,audit,data,evaluate
P=json.loads((OLD/'protocol.json').read_text())
def dump(n,x):(R/n).write_text(json.dumps(x,indent=2,allow_nan=False)+'\n')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 assert not (R/'results.json').exists()
 begin=datetime.now(timezone.utc);deadline=time.time()+1800
 configs=[]
 for h in (24,168):configs.append(next(c for c in P['configs'] if c['id']==f'trend_1_L10_H{h}_stress'))
 sources=[OLD/v for v in ('engine.py','audit.py','data.py','protocol.json','data_manifest.json','evaluate.py')]+[OLD/'ledgers'/f'holdout_trend_1_L20_H{h}_stress.jsonl.gz' for h in (24,168)]
 seal={str(p):sha(p) for p in sources};dump('protocol.json',{'started_utc':begin.isoformat(),'deadline_utc':(begin+timedelta(minutes=30)).isoformat(),'configs':configs,'comparison':'fixed20x ledgers reused, new10x same rules/assets/dates; POST_HOC not blind test','assets':P['holdout_assets'],'old_sources_sha256':seal,'owner':'root','new_network_calls':0,'no_tuning':True,'retention':'all files are audit evidence'})
 data.enable_seal();datasets={};counts=0;results=[]
 for c in configs:
  h=c['horizon_hours'];oldrows=[json.loads(s) for s in gzip.open(OLD/'ledgers'/f'holdout_trend_1_L20_H{h}_stress.jsonl.gz','rt')];oldmap={(r['coin'],r['start']):r for r in oldrows};newrows=[]
  with gzip.open(R/f'ledger10_h{h}.jsonl.gz','wt') as f:
   for coin in P['holdout_assets']:
    if coin not in datasets:
     raw,spec,fund=data.load(coin,'CONDITIONAL_SWAP');ep=engine.prepare_rows(raw);ap=audit.prepare_rows(raw);sig=engine.prepare_signals(ep,c['rule']);ind=audit.prepare_signals(raw,[c['rule']]);assert audit.compare_signals(sig,ind[c['rule']['id']])['ok'];datasets[coin]=(ep,ap,spec,fund,sig)
    ep,ap,spec,fund,sig=datasets[coin]
    for fold in range(3):
     for start in evaluate.schedule(fold,h):
      assert time.time()<deadline
      end=start+h*3600000;out=engine.simulate(ep,spec,fund,c,start,end,sig);assert audit.verify(ap,spec,fund,c,start,end,sig,out)['ok'];counts+=1
      row={'coin':coin,'start':start,'end':end,'fold':fold,**out};assert (coin,start) in oldmap;newrows.append(row);f.write(json.dumps(row,separators=(',',':'))+'\n')
  assert len(newrows)==len(oldrows)
  def stats(rr):
   s=evaluate.aggregate(rr);s['loss50_count']=sum(r['metrics']['return']<=-.5 for r in rr);return s
  pairs=[(r,oldmap[r['coin'],r['start']]) for r in newrows]
  transitions=collections.Counter(('target' if a['metrics']['target_hit'] else 'zero' if a['metrics']['final_equity']==0 else 'other','target' if b['metrics']['target_hit'] else 'zero' if b['metrics']['final_equity']==0 else 'other') for a,b in pairs)
  results.append({'hours':h,'10x':stats(newrows),'20x':stats(oldrows),'paired_transition_10_to_20':{a+'->'+b:n for (a,b),n in transitions.items()},'mean_return_difference_10_minus_20':statistics.mean(a['metrics']['return']-b['metrics']['return'] for a,b in pairs),'by_coin':{coin:{'10x':stats([r for r in newrows if r['coin']==coin]),'20x':stats([r for r in oldrows if r['coin']==coin])} for coin in P['holdout_assets']}})
  print(json.dumps({'hours':h,'new10_accounts':len(newrows),'audited':counts}),flush=True)
 assert all(sha(Path(p))==s for p,s in seal.items());data.enable_seal();dump('results.json',{'status':'COMPLETED','new_independent_audits':counts,'reused20_windows':counts,'results':results,'real_profitability':'UNKNOWN','new_out_of_sample':False})
if __name__=='__main__':main()
