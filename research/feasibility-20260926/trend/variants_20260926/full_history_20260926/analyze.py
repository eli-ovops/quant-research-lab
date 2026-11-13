"""Run exactly frozen108+12 only after the complete-data and code seals pass."""
from pathlib import Path
from decimal import Decimal as D
import json,datetime,hashlib,csv,gzip,itertools,time
import engine,independent,independent_metrics as im,statistics_v2 as st,data_gate
P=Path(__file__).resolve().parent;OLD=P.parent;H=3600000
sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
def save(n,x):engine.dump(P/n,x)
def main():
 freeze=json.loads((P/'analysis_freeze.json').read_text())
 for n,h in freeze['files'].items():assert sha(P/n)==h,n
 assert sha(OLD/'protocol.json')==freeze['protocol_sha256']
 raw,gate,differences,sources=data_gate.load();save('data_gate.json',gate);save('daily_differences.json',differences);save('market_sources.json',sources);assert gate['pass'],'full_data_gate_failed'
 ds={s['id']:s['sha256'] for s in sources};assert ds==json.loads((P/'data_freeze.json').read_text())['raw_sha256']
 proto=json.loads((OLD/'protocol.json').read_text());spec={c:json.loads((OLD.parent/'raw'/(c+'_spec.txt')).read_text())['data'][0] for c in engine.COINS}
 assert not (P/'results_all.json').exists(),'preserve previously opened results'
 save('first_real_PnL_run.json',{'UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'classification':'EXPLORATORY_REUSED_HISTORY','phase':'ALL_FIXED_SCENARIOS','plan':'108+12; no adaptive parameter choice'})
 results=[];audit=[];family_series={};clusters={};start_clock=time.time()
 for period,(s,e) in proto['periods_UTC_half_open'].items():
  start,end=data_gate.ms(s),data_gate.ms(e);selected={c:[r for r in rows if start-80*H<=int(r[0])<end] for c,rows in raw.items()}
  choices=[(en,ex,cond,'trend') for en,ex,cond in itertools.product([24,48,72],[4,8,12],engine.CONDITIONS)]+[(24,4,cond,'hold') for cond in engine.CONDITIONS]
  for en,ex,cond,mode in choices:
   ident=period+'_'+mode+'_'+str(en)+'_'+str(ex)+'_'+cond
   case=dict(raw=selected,spec=spec,start=start,end=end,entry=en,exit=ex,condition=cond,mode=mode,synthetic=False)
   a=engine.run(**case);b=independent.replay(case)
   fills=[(f['t'],f['coin'],f['side'],f['qty'],f['price'],f['base_fee'],f['quote_fee'],f['cash_after']) for f in a['fills']];im.assert_close(fills,b['fills'],'fills')
   assert [(s['signal'],s['due'],s['coin'],s['side']) for s in a['signals']]==b['signals']
   assert [(r['t'],r['coin'],r['side'],r['phase']) for r in a['rejections']]==b['rejections']
   assert [(x['due'],x['coin'],x['side'],x['signal']) for x in a['cancellations'] if x['reason']=='period_end_pending_cancelled']==b['pending']
   assert len(a['curve'])==len(b['curve'])
   for x,y in zip(a['curve'],b['curve']):im.assert_close({k:x[k] for k in y},y,'curve')
   independent_m=im.compute(case,b);im.assert_close(a['metrics'],independent_m,'metrics')
   slice_result=st.slices(a,proto['rolling']['windows']);entry=dict(id=ident,period=period,entry=en,exit=ex,condition=cond,mode=mode,metrics=a['metrics'],slices=slice_result)
   if period=='latest' and mode=='trend' and cond=='baseline':family_series[str(en)+'/'+str(ex)]=a['metrics']['daily_returns'];clusters[str(en)+'/'+str(ex)]=a['metrics']['exposure_clusters']
   engine.export(P/'runs'/ident,a);engine.dump(P/'runs'/ident/'independent_metrics.json',independent_m)
   with gzip.open(P/'runs'/ident/'independent_curve.json.gz','wt') as f:json.dump(b['curve'],f,default=engine.enc)
   engine.dump(P/'runs'/ident/'independent_events.json',{k:v for k,v in b.items() if k!='curve'})
   entry['metrics']={k:v for k,v in entry['metrics'].items() if k not in ['daily_returns','daily_utc_keys','cluster_intervals']};results.append(entry);audit.append({'id':ident,'pass':True,'fills':len(fills),'signals':len(a['signals']),'rejections':len(a['rejections']),'cancelled':len(a['cancellations']),'hourly_states':len(a['curve']),'independent_metric_fields':len(independent_m),'scope':'raw-derived second implementation; full fills/signals/rejections/end pending/cash/inventory/equity and supplementary metrics'})
   save('progress.json',{'completed':len(results),'planned':120,'last':ident,'elapsed_s':time.time()-start_clock})
   print('VALIDATED',len(results),ident,flush=True)
  holds={r['condition']:r for r in results if r['period']==period and r['mode']=='hold'}
  for r in results:
   if r['period']==period:r['metrics']['excess_vs_cash_usdt']=r['metrics']['net_pnl'];r['metrics']['excess_vs_same_condition_hold_usdt']=r['metrics']['net_pnl']-holds[r['condition']]['metrics']['net_pnl']
 family=st.simultaneous(family_series,clusters);decision=st.decisions(results,family)
 save('results_all.json',{'classification':'EXPLORATORY_REUSED_HISTORY','true_feasibility':'INSUFFICIENT_EVIDENCE','principal_count':108,'hold_count':12,'scenarios':results});save('family_intervals.json',family);save('candidate_decisions.json',decision);save('independent_validation.json',{'all_passed':True,'scenarios':audit})
 rows=[dict(id=r['id'],period=r['period'],entry=r['entry'],exit=r['exit'],condition=r['condition'],mode=r['mode'],**{k:v for k,v in r['metrics'].items() if not isinstance(v,(dict,list))}) for r in results]
 with (P/'summary.csv').open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
 print('COMPLETE',len(results),flush=True)
if __name__=='__main__':main()
