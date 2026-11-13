from pathlib import Path
from decimal import Decimal as D
import json,datetime,hashlib,csv,gzip,itertools,time
import engine,independent,independent_metrics as im,statistics_v2 as st,source_gate,missing_decisions
P=Path(__file__).resolve().parent;OLD=P.parent;H=3600000
sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
def save(n,x):engine.dump(P/n,x)
def blocked_rows(proto):
 rows=[];s,e=proto['periods_UTC_half_open']['early'];start,end=source_gate.ms(s),source_gate.ms(e);fields=json.loads((P/'output_schema.json').read_text())['metric_fields']
 yearly=[dict(year=y,partial_year=False,start=source_gate.ms(str(y)+'-01-01T00:00:00+00:00'),end=source_gate.ms(str(y+1)+'-01-01T00:00:00+00:00'),begin_equity=None,end_equity=None,net_change_usdt=None,**{'return':None},max_drawdown_with_local_peak=None,status='NOT_EVALUATED') for y in [2020,2021,2022]]
 rolling=[dict(start=source_gate.ms(w['start_inclusive']),end=source_gate.ms(w['end_exclusive']),begin_equity=None,end_equity=None,net_change_usdt=None,**{'return':None},max_drawdown_with_local_peak=None,status='NOT_EVALUATED') for w in proto['rolling']['windows'] if w['period']=='early']
 for en,ex,c,mode in [(a,b,c,'trend') for a,b,c in itertools.product([24,48,72],[4,8,12],engine.CONDITIONS)]+[(24,4,c,'hold') for c in engine.CONDITIONS]:
  ident='early_'+mode+'_'+str(en)+'_'+str(ex)+'_'+c;rows.append(dict(id=ident,period='early',entry=en,exit=ex,condition=c,mode=mode,status='NOT_EVALUATED_DATA_GATE_FAILED',reason='Original early period contains12zero hours per coin and price/volume discrepancies; no substitution or reduced window',metrics={k:None for k in fields},slices={'yearly':yearly,'rolling':rolling}))
 return rows

def main():
 freeze=json.loads((P/'analysis_freeze.json').read_text())
 for n,h in freeze['files'].items():assert sha(P/n)==h,n
 assert sha(OLD/'protocol.json')==freeze['protocol_sha256'];source_gate.authority()
 assert not(P/'first_real_PnL_run.json').exists(),'preserve original run and use explicit revision if needed'
 proto=json.loads((OLD/'protocol.json').read_text());raw,sourceproof=source_gate.load();cache={};gates={}
 for period in ['middle','latest']:
  selected,start,end,checks=source_gate.for_period(raw,period);cache[period]=(selected,start,end);gates[period]=checks
 save('input_gate.json',{'source':sourceproof,'periods':gates,'early':'NOT_ADMITTED','pass_for_admitted':True})
 spec={c:json.loads((OLD.parent/'raw'/(c+'_spec.txt')).read_text())['data'][0] for c in engine.COINS}
 results=blocked_rows(proto);audit=[];family_series={};clusters={};done=0;start_clock=time.time()
 save('first_real_PnL_run.json',{'UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'classification':'EXPLORATORY_REUSED_HISTORY','admitted':'72trend+8hold;early36+4null','all_original_candidates_retained':True})
 for period in ['middle','latest']:
  selected,start,end=cache[period]
  choices=[(en,ex,cond,'trend') for en,ex,cond in itertools.product([24,48,72],[4,8,12],engine.CONDITIONS)]+[(24,4,cond,'hold') for cond in engine.CONDITIONS]
  for en,ex,cond,mode in choices:
   ident=period+'_'+mode+'_'+str(en)+'_'+str(ex)+'_'+cond;case=dict(raw=selected,spec=spec,start=start,end=end,entry=en,exit=ex,condition=cond,mode=mode,synthetic=False)
   a=engine.run(**case);b=independent.replay(case)
   fills=[(f['t'],f['coin'],f['side'],f['qty'],f['price'],f['base_fee'],f['quote_fee'],f['cash_after']) for f in a['fills']];im.assert_close(fills,b['fills'],'fills')
   assert [(s['signal'],s['due'],s['coin'],s['side']) for s in a['signals']]==b['signals']
   assert [(r['t'],r['coin'],r['side'],r['phase']) for r in a['rejections']]==b['rejections']
   assert [(x['due'],x['coin'],x['side'],x['signal']) for x in a['cancellations'] if x['reason']=='period_end_pending_cancelled']==b['pending']
   assert len(a['curve'])==len(b['curve'])
   for x,y in zip(a['curve'],b['curve']):im.assert_close({k:x[k] for k in y},y,'curve')
   second=im.compute(case,b);im.assert_close(a['metrics'],second,'metrics')
   sc=st.slices(a,proto['rolling']['windows']);entry=dict(id=ident,period=period,entry=en,exit=ex,condition=cond,mode=mode,status='COMPUTED_VALIDATED',metrics=a['metrics'],slices=sc)
   if period=='latest' and mode=='trend' and cond=='baseline':family_series[str(en)+'/'+str(ex)]=a['metrics']['daily_returns'];clusters[str(en)+'/'+str(ex)]=a['metrics']['exposure_clusters']
   engine.export(P/'runs'/ident,a);engine.dump(P/'runs'/ident/'independent_metrics.json',second)
   with gzip.open(P/'runs'/ident/'independent_curve.json.gz','wt') as f:json.dump(b['curve'],f,default=engine.enc)
   engine.dump(P/'runs'/ident/'independent_events.json',{k:v for k,v in b.items() if k!='curve'})
   entry['metrics']={k:v for k,v in entry['metrics'].items() if k not in ['daily_returns','daily_utc_keys','cluster_intervals']};results.append(entry);done+=1
   audit.append({'id':ident,'pass':True,'fills':len(fills),'signals':len(a['signals']),'rejections':len(a['rejections']),'pending_cancelled':len(a['cancellations']),'hourly_states':len(a['curve']),'independent_metric_fields':len(second),'scope':'raw-secondimplementation signals/fills/rejections/pending/cash/inventory/equity and supplementary metrics'})
   save('progress.json',{'computed_and_independently_validated':done,'admitted':80,'planned':120,'last':ident,'elapsed_s':time.time()-start_clock});print('VALIDATED',done,ident,flush=True)
  holds={r['condition']:r for r in results if r['period']==period and r['mode']=='hold'}
  for r in results:
   if r['period']==period:r['metrics']['excess_vs_cash_usdt']=r['metrics']['net_pnl'];r['metrics']['excess_vs_same_condition_hold_usdt']=r['metrics']['net_pnl']-holds[r['condition']]['metrics']['net_pnl']
 family=st.simultaneous(family_series,clusters);decision=missing_decisions.decide(results,family)
 save('results_all.json',{'classification':'EXPLORATORY_REUSED_HISTORY','true_feasibility':'INSUFFICIENT_EVIDENCE','principal_planned':108,'principal_computed':72,'hold_planned':12,'hold_computed':8,'scenarios':results});save('family_intervals.json',family);save('candidate_decisions.json',decision);save('independent_validation.json',{'all_admitted_passed':True,'not_evaluated_early':40,'scenarios':audit})
 rows=[dict(id=r['id'],period=r['period'],entry=r['entry'],exit=r['exit'],condition=r['condition'],mode=r['mode'],status=r['status'],**{k:v for k,v in r['metrics'].items() if not isinstance(v,(dict,list))}) for r in results];fields=list(dict.fromkeys(k for r in rows for k in r))
 with (P/'summary.csv').open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
 print('COMPLETE72+8;early36+4null',flush=True)
if __name__=='__main__':main()
