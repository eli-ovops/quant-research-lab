import json,gzip,hashlib,math
from pathlib import Path
from fractions import Fraction as F
from collections import deque
P=Path(__file__).resolve().parent;B=P.parent
def qentry(levels,unit,step,minlot):
 remaining=F(500)/(1+F(5,10000));qty=F(0)
 for px,q in levels:
  px=F(px);q=F(q);take=min(q,remaining/(px*unit));qty+=take;remaining-=take*px*unit
  if remaining==0:break
 if remaining>0:return None
 qty=(qty//step)*step
 return qty if qty>=minlot else None
def cost(levels,qty,unit):
 total=F(0);left=qty
 for px,q in levels:
  take=min(left,F(q));total+=take*F(px)*unit;left-=take
  if left==0:return total/qty/unit
 return None
def main():
 rs=[json.loads(x) for x in (P/'asof_diagnostics.jsonl').read_text().splitlines()];result=json.loads((P/'results.json').read_text());spec={x['instId']:x for x in json.loads((B/'phase025_public_input_latency_probe/instruments.json').read_text())};targets={}
 for a in spec:
  subset=[r for r in rs if r['asset']==a]
  for index in [0,len(subset)//2,len(subset)-1]:targets[subset[index]['ordinal']]=subset[index]
 state={a:{'books':deque(),'trades':deque(),'seen':set()} for a in spec};proof=[]
 with gzip.open(B/'phase025_public_input_latency_probe/raw/ws_messages.jsonl.gz','rt') as stream:
  for line in stream:
   row=json.loads(line);a=row['instId'];now=row['os_shared_ns']
   if a not in state:continue
   s=state[a];unit=F(spec[a]['ctVal'])*F(spec[a]['ctMult']);raw=json.loads(row['raw'])
   for d in raw.get('data',[]):
    if row['channel']=='books5':s['books'].append((now,[(F(z[0]),F(z[1])) for z in d['asks']],[(F(z[0]),F(z[1])) for z in d['bids']]))
    elif row['channel']=='trades':
     key=(d.get('tradeId'),d.get('source'))
     if key not in s['seen']:
      s['seen'].add(key);amt=F(d['px'])*F(d['sz'])*unit;s['trades'].append((now,amt,amt*(1 if d['side']=='buy' else -1)))
   while s['trades'] and s['trades'][0][0]<=now-10000000000:s['trades'].popleft()
   while len(s['books'])>1 and s['books'][1][0]<=now-10250000000:s['books'].popleft()
   if row['local_ordinal'] not in targets:continue
   r=targets[row['local_ordinal']];m=r['metrics'];total=sum((z[1] for z in s['trades']),F(0));net=sum((z[2] for z in s['trades']),F(0));one=[z for z in s['trades'] if z[0]>now-1000000000];t1=sum((z[1] for z in one),F(0));prior=total-t1
   checks={'total10_received':total,'total1_received':t1,'prior9_received':prior}
   cur=s['books'][-1] if s['books'] else None;refs=[z for z in s['books'] if z[0]<=now-10000000000];ref=refs[-1] if refs else None
   if cur and ref and now-cur[0]<=250000000 and now-10000000000-ref[0]<=250000000:checks['abs_impulse10_bps']=abs(((cur[1][0][0]+cur[2][0][0])/(ref[1][0][0]+ref[2][0][0])-1)*10000)
   if cur and now-cur[0]<=250000000:
    values=[]
    for sign,entry,exit in [(1,cur[1],cur[2]),(-1,cur[2],cur[1])]:
     qty=qentry(entry,unit,F(spec[a]['lotSz']),F(spec[a]['minSz']))
     if qty is None:continue
     E=cost(entry,qty,unit);X=cost(exit,qty,unit)
     if E is None or X is None:continue
     fee=F(5,10000);values.append((E*(1+fee)/(X*(1-fee))-1)*10000 if sign==1 else (1-E*(1-fee)/(X*(1+fee)))*10000)
    if len(values)==2:checks['required_plus5_bps']=max(values)+5
   for k,v in checks.items():assert m[k] is not None and math.isclose(m[k],float(v),rel_tol=1e-12,abs_tol=1e-10),(a,k)
   proof.append({'asset':a,'ordinal':row['local_ordinal'],'exact_recomputed':{k:str(v) for k,v in checks.items()},'PASS':True})
 assert len(proof)==27
 originalorder=['identity_known','warm10','current_fresh','ref10_fresh','ref1_fresh','both_capacity','flow10_positive','nested_consistent','imb10_ge08','aligned10','past_cost_room','dominant_depth','total1_positive','unique_trade_fresh','prior9_positive']
 funnel={}
 for a in spec:
  data=[r for r in rs if r['asset']==a];g=result['groups'][a];assert len(data)==g['samples']
  for key,stats in g['single_gate'].items():assert stats['available']+stats['missing']==len(data) and stats['pass']<=stats['available']
  survivors=data;funnel[a]={}
  for key in originalorder:
   count=len(survivors);survivors=[r for r in survivors if r['gates'][key] is True];funnel[a][key]={'enter':count,'survive':len(survivors)}
  for branch in ['continuation','decay']:funnel[a][branch]={'survive':sum(r['gates'][branch] is True for r in survivors)}
 assert sum(g['samples'] for g in result['groups'].values())==len(rs)
 (P/'original_rule_funnel.json').write_text(json.dumps({'clarification':'candidate computes capacity before pressure_choice flow gates; coverage declared pedagogic funnel retained separately; no strategy income/cooldown','groups':funnel},indent=2)+'\n')
 (P/'audit.json').write_text(json.dumps({'status':'PASS_FINITE_MATH_COUNTS','samples':proof,'sample_count':27,'all_group_denominators_checked':True,'not_full_independent_strategy_replay':True,'future_quotes_checked':False,'income_calculation':False},indent=2)+'\n')
 print('PASS 27 independent Fraction asof cases + counts')
if __name__=='__main__':main()
