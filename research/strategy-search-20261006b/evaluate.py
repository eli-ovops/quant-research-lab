"""Frozen search on previously seen assets, followed by sealed asset holdout."""
import json,gzip,hashlib,time,statistics,random,collections
from pathlib import Path
from datetime import datetime,timezone
import data,engine,audit
R=Path(__file__).resolve().parent;P=json.loads((R/'protocol.json').read_text());H=3600000
DEADLINE=data.ms(P['deadline_utc'])
def dump(name,x):(R/name).write_text(json.dumps(x,indent=2,allow_nan=False)+'\n')
def schedule(fold,h):
 a,b=map(data.ms,P['folds'][fold]);return range(a,b-h*H+1,h*H)
def aggregate(rows):
 valid=[r for r in rows if r['metrics']['final_equity'] is not None];m=[r['metrics'] for r in valid];v=[x['return'] for x in m];n=len(v)
 return {'scheduled':len(rows),'evaluated':n,'invalid':len(rows)-n,'targets':sum(x['target_hit'] is True for x in m),'losses':sum(x<0 for x in v),'zeros':sum(x['final_equity']<=0 for x in m),'no_trade':sum(x.get('entry_count',0)==0 for x in m),'trades':sum(x.get('trade_count',0) for x in m),'mean_return':statistics.mean(v) if n else None,'median_return':statistics.median(v) if n else None,'worst_return':min(v) if n else None,'p05_return':sorted(v)[int((n-1)*.05)] if n else None,'total_final':sum(x['final_equity'] for x in m),'mean_fees':statistics.mean(x['fees'] for x in m) if n else None,'mean_funding':statistics.mean(x['funding'] for x in m) if n else None,'max_drawdown':max((x['max_drawdown'] for x in m),default=None)}
def bootstrap(pairs):
 g=collections.defaultdict(list)
 for r,c in pairs:
  if r['metrics']['return'] is not None and c['metrics']['return'] is not None:g[r['start']].append((r['metrics']['return'],r['metrics']['return']-c['metrics']['return']))
 means=[(statistics.mean(v[0] for v in vs),statistics.mean(v[1] for v in vs)) for vs in g.values()]
 if not means:return {'date_clusters':0,'mean_ci90':[None,None],'paired_ci90':[None,None]}
 rng=random.Random(50020261006);out=[[],[]]
 for _ in range(2000):
  sample=rng.choices(means,k=len(means))
  for j in (0,1):out[j].append(statistics.mean(v[j] for v in sample))
 return {'date_clusters':len(means),'mean_ci90':[sorted(out[0])[100],sorted(out[0])[1899]],'paired_ci90':[sorted(out[1])[100],sorted(out[1])[1899]],'warning':'date-cluster intervals; not simultaneous across selected candidates and not independent market regimes'}
def main():
 assert len(P['configs'])==360
 assert not (R/'selection.json').exists(),'Refuse overwrite prior selection'
 data.enable_seal();names=['protocol.json','engine.py','audit.py','data.py','evaluate.py','data_manifest.json']
 hashes={f:hashlib.sha256((R/f).read_bytes()).hexdigest() for f in names};dump('execution_seal.json',{'at':datetime.now(timezone.utc).isoformat(),'sha256':hashes})
 (R/'ledgers').mkdir(exist_ok=True)
 datasets={};sigmaps={};controls={};screen=[];audit_count=0;metrics_count=0
 rules=list({c['rule']['id']:c['rule'] for c in P['configs']}.values())
 def dataset(coin,product):
  key=(coin,product)
  if key not in datasets:
   rows,spec,fund=data.load(coin,product)
   ep=engine.prepare_rows(rows);ap=audit.prepare_rows(rows)
   independent=audit.prepare_signals(rows,rules)
   for rule in rules:
    sm=engine.prepare_signals(ep,rule)
    signal_check=audit.compare_signals(sm,independent[rule['id']]);assert signal_check['ok'],str(signal_check)
    sigmaps[key+(rule['id'],)]=sm
   datasets[key]=(ep,ap,spec,fund)
  return key,datasets[key]
 def run(c,phase):
  nonlocal audit_count,metrics_count
  assets=P['screen_assets'] if phase=='screen' else P['holdout_assets'];rs=[];cs=[];pairs=[]
  with gzip.open(R/'ledgers'/f'{phase}_{c["id"]}.jsonl.gz','wt') as f:
   for coin in assets:
    key,(ep,ap,spec,fund)=dataset(coin,c['product']);signals=sigmaps[key+(c['rule']['id'],)]
    for fold in range(3):
     for start in schedule(fold,c['horizon_hours']):
      if time.time()*1000>=DEADLINE:raise RuntimeError('AUTHORIZED_DEADLINE')
      end=start+c['horizon_hours']*H
      out=engine.simulate(ep,spec,fund,c,start,end,signals)
      chk=audit.verify(ap,spec,fund,c,start,end,signals,out)
      assert chk['ok'],str(chk)
      audit_count+=1;metrics_count+=1
      record={'config':c['id'],'coin':coin,'fold':fold,'start':start,'end':end,'phase':phase,**out}
      f.write(json.dumps(record,separators=(',',':'),allow_nan=False)+'\n')
      rec={k:v for k,v in record.items() if k not in ('events','equity')};rs.append(rec)
      ck=(phase,c['rule']['family'],c['product'],c['leverage'],c['horizon_hours'],c['cost'],coin,start)
      if ck not in controls:
       co=engine.simulate(ep,spec,fund,c,start,end,signals,control=True)
       chk=audit.verify(ap,spec,fund,c,start,end,signals,co,control=True);assert chk['ok'],str(chk)
       audit_count+=1;controls[ck]={'metrics':co['metrics']}
       with gzip.open(R/'ledgers'/'controls.jsonl.gz','at') as cf:cf.write(json.dumps({'key':list(ck),**co},separators=(',',':'),allow_nan=False)+'\n')
      cs.append(controls[ck]);pairs.append((rec,controls[ck]))
  diffs=[a['metrics']['return']-b['metrics']['return'] for a,b in pairs if a['metrics']['return'] is not None and b['metrics']['return'] is not None]
  summary={'config':c,'phase':phase,'strategy':aggregate(rs),'control':aggregate(cs),'paired_mean':statistics.mean(diffs) if diffs else None,'folds':[aggregate([v for v in rs if v['fold']==i]) for i in range(3)],'by_coin':{coin:aggregate([v for v in rs if v['coin']==coin]) for coin in assets}}
  if phase=='holdout':summary['uncertainty']=bootstrap(pairs)
  dump(f'{phase}_{c["id"]}.json',summary)
  print(json.dumps({'finished':phase+'_'+c['id'],'accounts':summary['strategy']['evaluated'],'trades':summary['strategy']['trades'],'targets':summary['strategy']['targets'],'audited':audit_count}),flush=True)
  return summary
 for c in P['configs']:screen.append(run(c,'screen'))
 chosen=[]
 for product in ('SPOT','CONDITIONAL_SWAP'):
  for horizon in (24,168):
   eligible=[]
   for r in screen:
    c=r['config'];s=r['strategy'];folds=r['folds']
    if c['product']!=product or c['horizon_hours']!=horizon or c['cost']!='stress':continue
    if s['invalid']==0 and s['trades']>=30 and s['targets']>=3 and s['mean_return']>0 and sum(f['mean_return']>0 for f in folds)>=2 and r['paired_mean']>0:eligible.append(r)
   eligible.sort(key=lambda r:(-min(f['mean_return'] for f in r['folds']),-r['paired_mean'],r['config']['id']))
   if eligible:chosen.append(eligible[0]['config'])
 dump('selection.json',{'saved_utc':datetime.now(timezone.utc).isoformat(),'selected':chosen,'screen_hashes':{r['config']['id']:hashlib.sha256((R/f'screen_{r["config"]["id"]}.json').read_bytes()).hexdigest() for r in screen},'holdout_strategy_evaluation_before_selection':False})
 final=[]
 for c in chosen:
  r=run(c,'holdout');s=r['strategy'];u=r['uncertainty']
  r['paper_eligible']=bool(s['invalid']==0 and s['trades']>=30 and s['targets']>=3 and s['mean_return']>0 and sum(f['mean_return']>0 for f in r['folds'])>=2 and r['paired_mean']>0 and u['mean_ci90'][0]>0 and u['paired_ci90'][0]>0)
  r['actual_profitability']='UNKNOWN';final.append(r)
 assert time.time()*1000<DEADLINE,'AUTHORIZED_DEADLINE'
 for f,h in hashes.items():assert hashlib.sha256((R/f).read_bytes()).hexdigest()==h,'CODE_CHANGED:'+f
 data.enable_seal()
 dump('results.json',{'completed_utc':datetime.now(timezone.utc).isoformat(),'configs':360,'strategy_accounts':metrics_count,'audited_episodes':audit_count,'screen':screen,'holdout':final,'selected':chosen})
 dump('status.json',{'status':'COMPLETED','strategy_accounts':metrics_count,'audited_episodes':audit_count,'selected':len(chosen),'paper_eligible':sum(r['paper_eligible'] for r in final)})
if __name__=='__main__':
 try:main()
 except Exception as e:dump('status.json',{'status':'FAILED_CLOSED','error':str(e),'at':datetime.now(timezone.utc).isoformat()});raise
