import sys,json,gzip,hashlib,statistics
from pathlib import Path
from bisect import bisect_right
from fractions import Fraction as F
from decimal import Decimal as D
BASE=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(BASE/'phase026_shock_pressure_transition_preparation'))
from pressure_rules import PressureRules,pressure_choice
from frozen_cost_shock import asof_required_move
CUT=29136966188000
class StateOnly(PressureRules):
 def candidate(self,*args):return None
def summary(values):
 v=sorted(values)
 return {'available':len(v),'min':v[0] if v else None,'median':statistics.median(v) if v else None,'p95':v[min(len(v)-1,int(len(v)*.95))] if v else None,'max':v[-1] if v else None}
def evaluate(a,row,engine):
 s=engine.states[a];now=row['os_shared_ns'];n={};g={}
 def metric(k,v):n[k]=None if v is None else float(v)
 def gate(k,v):g[k]=v
 book=s['books'][-1] if s['books'] else None
 refs=[]
 for secs in [10,1]:
  idx=bisect_right(s['times'],now-secs*1000000000)-1
  ref=s['books'][idx] if idx>=0 else None;refs.append(ref)
  gate('ref'+str(secs)+'_fresh',None if ref is None else 0<=now-secs*1000000000-ref['ns']<=250000000)
 ref10,ref1=refs
 gate('warm10',s['firsttrade_ns'] is not None and now-s['firsttrade_ns']>=10000000000)
 gate('current_fresh',None if book is None else 0<=now-book['ns']<=250000000)
 gate('identity_known',not s['conflict'])
 flow=[x for x in s['flow'] if x[0]>now-10000000000];one=[x for x in flow if x[0]>now-1000000000]
 total=sum((x[1] for x in flow),F(0));net=sum((x[2] for x in flow),F(0));t1=sum((x[1] for x in one),F(0));n1=sum((x[2] for x in one),F(0));prior=total-t1
 shock=1 if net>0 else -1 if net<0 else 0
 impulse=(book['mid']/ref10['mid']-1)*10000 if book and ref10 and g['current_fresh'] is True and g['ref10_fresh'] is True else None
 spec=engine.specs[a];unit=D(spec['ctVal'])*D(spec['ctMult']);proxy=asof_required_move(book,unit,D(spec['lotSz']),D(spec['minSz'])) if book and g['current_fresh'] is True else None
 required=proxy[0]+5 if proxy else None
 depth=sum((F(px)*F(q)*F(unit) for px,q in (ref10['asks'] if shock==1 else ref10['bids'])[:5]),F(0)) if ref10 and shock and g['ref10_fresh'] is True else None
 dominant=(total+shock*net)/2 if total>0 and shock else None
 age=now-s['lasttrade_ns'] if s['lasttrade_ns'] is not None else None
 metric('abs_impulse10_bps',abs(impulse) if impulse is not None else None);metric('required_plus5_bps',required);metric('past_cost_margin_bps',abs(impulse)-required if impulse is not None and required is not None else None)
 metric('dominant_reference_depth_ratio',dominant/depth if dominant is not None and depth and depth>0 else None)
 metric('imb10',net/total if total>0 else None);metric('unique_trade_age_ms',F(age,1000000) if age is not None else None);metric('rate_ratio',9*t1/prior if prior>0 else None);metric('imb1',n1/t1 if t1>0 else None)
 for k,v in [('total10_received',total),('total1_received',t1),('prior9_received',prior)]:metric(k,v)
 gate('flow10_positive',total>0);gate('nested_consistent',abs(net)<=total and abs(n1)<=t1 and t1<=total and abs(net-n1)<=prior)
 gate('imb10_ge08',None if total<=0 else abs(net)/total>=F(4,5));gate('aligned10',None if impulse is None or total<=0 else impulse*net>0)
 gate('both_capacity',None if g['current_fresh'] is not True else proxy is not None);gate('past_cost_room',None if impulse is None or required is None else abs(impulse)>=required)
 gate('dominant_depth',None if dominant is None or depth is None or depth<=0 else dominant>=depth)
 gate('unique_trade_fresh',None if age is None else 0<=age<=250000000);gate('total1_positive',t1>0);gate('prior9_positive',prior>0)
 gate('continuation',None if prior<=0 or t1<=0 or not shock else 9*t1/prior>=1 and abs(n1)/t1>=F(4,5) and n1*shock>0)
 gate('decay',None if prior<=0 or t1<=0 else 9*t1/prior<=F(1,4) and abs(n1)/t1<=F(1,5))
 return {'asset':a,'ordinal':row['local_ordinal'],'source_shared_ns':now,'metrics':n,'gates':g,'future_outcomes_used':False}
ORDER=['identity_known','warm10','current_fresh','ref10_fresh','ref1_fresh','flow10_positive','nested_consistent','imb10_ge08','aligned10','both_capacity','past_cost_room','dominant_depth','total1_positive','unique_trade_fresh','prior9_positive']
def main():
 p=Path(__file__).resolve().parent;proto=json.loads((p/'protocol.json').read_text());freeze=json.loads((p/'execution_freeze.json').read_text())
 for n,h in freeze['hashes'].items():assert hashlib.sha256((p/n).read_bytes()).hexdigest()==h
 assert hashlib.sha256((BASE/'phase026_shock_pressure_transition_preparation/pressure_rules.py').read_bytes()).hexdigest()==proto['rule_sha']
 src=BASE/'phase025_public_input_latency_probe';raw=src/'raw/ws_messages.jsonl.gz';tele=src/'local_processing_timing.jsonl'
 digest=hashlib.sha256()
 with gzip.open(raw,'rb') as stream:
  for line in stream:digest.update(line)
 assert digest.hexdigest()==proto['raw_sha']
 assert hashlib.sha256(tele.read_bytes()).hexdigest()==proto['telemetry_sha']
 selected={}
 for line in tele.open():
  r=json.loads(line)
  if r['source']['os_shared_ns']>=CUT:
   o=r['source']['local_ordinal'];assert o not in selected;selected[o]=r['asset']
 registry=json.loads((src/'instruments.json').read_text());engine=StateOnly(registry,proto['domain']);records=[];rawN=0
 with gzip.open(raw,'rt') as stream:
  for line in stream:
   r=json.loads(line);rawN+=1;engine.ingest(r)
   if r['local_ordinal'] in selected:
    a=selected[r['local_ordinal']];assert a==r['instId'];records.append(evaluate(a,r,engine))
 assert len(records)==len(selected)
 with (p/'asof_diagnostics.jsonl').open('w') as out:
  for r in records:out.write(json.dumps(r,separators=(',',':'))+'\n')
 groups={}
 for a in engine.specs:
  rs=[r for r in records if r['asset']==a];N=len(rs);metrics={};gates={};funnel={};active=rs
  for k in records[0]['metrics']:
   metrics[k]=summary([r['metrics'][k] for r in rs if r['metrics'][k] is not None]);metrics[k]['missing']=N-metrics[k]['available']
  for k in records[0]['gates']:
   avail=sum(r['gates'][k] is not None for r in rs);passed=sum(r['gates'][k] is True for r in rs);gates[k]={'available':avail,'missing':N-avail,'pass':passed,'pass_fraction_available':passed/avail if avail else None}
  for k in ORDER:
   before=len(active);active=[r for r in active if r['gates'][k] is True];funnel[k]={'enter':before,'survive':len(active),'removed_including_unknown':before-len(active)}
  funnel['continuation']={'survive':sum(r['gates']['continuation'] is True for r in active)};funnel['decay']={'survive':sum(r['gates']['decay'] is True for r in active)}
  groups[a]={'samples':N,'metrics':metrics,'single_gate':gates,'sequential_funnel':funnel}
 result={'status':'ASOF_PAST_PROXY_DIAGNOSTIC_ONLY','raw_rows':rawN,'selected_postcut_fixed_bucket_samples':len(records),'all_state_valid_and_invalid_included':True,'income_calculations':0,'AI_calls':0,'groups':groups,'source_hashes_verified':True,'rule_sha':proto['rule_sha'],'cooldown':'NOT_APPLIED independent asof support, not emitted strategy events','identity_unknown_flow_metrics_caveat':'conflict makes qualification unknown even when received numeric proxy can be described','globalgoal':'ACTIVE'}
 (p/'results.json').write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps({'samples':len(records),'raw':rawN,'groups':len(groups)}))
if __name__=='__main__':main()
