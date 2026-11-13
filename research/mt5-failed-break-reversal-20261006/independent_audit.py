from pathlib import Path
import csv,json,hashlib,datetime as dt
from decimal import Decimal,ROUND_HALF_UP,ROUND_FLOOR,ROUND_CEILING
B=Path(__file__).resolve().parent;M5=300000
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def ep(s):return int(dt.datetime.fromisoformat(s.replace('Z','+00:00')).timestamp()*1000)
def near(a,b):assert abs(float(a)-float(b))<1e-7*max(1,abs(float(a)),abs(float(b))),(a,b)
def rnd(x,mode='nearest'):
 d=Decimal(str(x));u=Decimal('.00001');n=d.quantize(u,rounding=ROUND_HALF_UP)
 if abs(d-n)<=Decimal('.0000000001'):return float(n)
 return float(d.quantize(u,rounding={'nearest':ROUND_HALF_UP,'floor':ROUND_FLOOR,'ceil':ROUND_CEILING}[mode]))
p=json.loads((B/'protocol.json').read_text());freeze=json.loads((B/'execution_freeze.json').read_text())
for n,h in freeze['hashes'].items():assert sha(B/n)==h
out=[];comparisons=[]
for src in p['inputs']:
 assert sha(Path(src['path']))==src['sha256'];es={cost:list(csv.DictReader((B/(src['name']+'_'+cost)/'ledger.csv').open())) for cost in ['base','stress']};known={e['timestamp']:set() for events in es.values() for e in events if e.get('bid')};bars={};bounds=set();targets=[]
 for cost,events in es.items():
  watch=None
  for e in events:
   if e['event']=='WATCH':watch=e
   if e['event']=='REVERSAL_DECISION':
    targets.append({'watch':watch,'decision':e,'cost':cost,'maxask':None,'minbid':None,'done':False});bounds.add(int(e['decision_bar'])+M5)
   if e['event']=='CLOSE' and e['reason']=='TIME21':bounds.add(int(e['exit_deadline']))
 first={}
 with Path(src['path']).open() as inp:
  for row in csv.DictReader(inp):
   t=ep(row['timestamp']);bid=float(row['bid']);ask=float(row['ask']);k=t//M5*M5;bars[k]=(bid,ask,t)
   if row['timestamp'] in known:known[row['timestamp']].add((bid,ask))
   for boundary in bounds:
    if boundary not in first and t>=boundary:first[boundary]=(t,bid,ask)
   for target in targets:
    if target['done']:continue
    w,e=target['watch'],target['decision'];start=ep(w['timestamp']);end=ep(e['timestamp'])
    if t<start or t>end:continue
    if target['maxask'] is None and (t!=start or (bid,ask)!=(float(w['bid']),float(w['ask']))):continue
    target['maxask']=max(target['maxask'] if target['maxask'] is not None else ask,ask);target['minbid']=min(target['minbid'] if target['minbid'] is not None else bid,bid)
    if t==end and (bid,ask)==(float(e['bid']),float(e['ask'])):target['done']=True
 for target in targets:
  w,e=target['watch'],target['decision'];assert target['done'];side0=int(w['original_side']);side=-side0;k=int(e['decision_bar']);trigger=ep(w['timestamp']);high=float(w['rawhigh']);low=float(w['rawlow'])
  for bar in range((trigger//M5+1)*M5,k+M5,M5):
   assert bar in bars;close=bars[bar][0 if side0==1 else 1];inside=low<close<high
   assert inside if bar==k else not inside
  assert (ep(e['timestamp']),float(e['bid']),float(e['ask']))==first[k+M5]
  near(e['maxask'],target['maxask']);near(e['minbid'],target['minbid'])
  slip=Decimal('.0001' if target['cost']=='stress' else '0');quote=Decimal(e['ask'] if side==1 else e['bid']);entry=rnd(quote+Decimal(side)*slip);sl=rnd(Decimal(str(target['minbid']))-Decimal('.0001'),'floor') if side==1 else rnd(Decimal(str(target['maxask']))+Decimal('.0001'),'ceil');tp=high if side==1 else low
  risk=abs(Decimal(str(entry))-Decimal(str(rnd(Decimal(str(sl))-Decimal(side)*slip))))*100000+7;gain=Decimal(side)*(Decimal(str(tp))-Decimal(str(entry)))*100000-7
  near(e['entry_estimate'],entry);near(e['sl'],sl);near(e['tp'],tp);near(e['netRR'],gain/risk)
 for cost,events in es.items():
  folder=B/(src['name']+'_'+cost);cash=500.;pos=None;fees=0.;count={};trades={};checks=0;decision=None
  for e in events:
   if e.get('bid'):assert (float(e['bid']),float(e['ask'])) in known[e['timestamp']]
   day=e['timestamp'][:10];t=ep(e['timestamp']);event=e['event']
   if event=='REVERSAL_DECISION':decision=e;checks+=1
   if event=='OPEN':
    assert decision and float(decision['netRR'])>=3 and pos is None and count.get(day,0)==0
    side=int(e['side']);lot=float(e['lot']);fee=lot*3.5;slip=Decimal('.0001' if cost=='stress' else '0');entry=rnd(Decimal(e['ask'] if side==1 else e['bid'])+Decimal(side)*slip);unit=abs(Decimal(str(entry))-Decimal(str(rnd(Decimal(e['sl'])-Decimal(side)*slip))))*100000+7;budget=Decimal(str(cash))*Decimal('.01');lots=float(min(Decimal(100),(budget/unit/Decimal('.01')).to_integral_value(rounding=ROUND_FLOOR)*Decimal('.01')))
    near(lot,lots);assert lot>=.01;near(e['entry'],entry);near(e['planned_risk'],lot*float(unit));assert float(e['planned_risk'])<=float(budget)+1e-8;near(e['margin'],lot*100000*entry/100);assert cash-fee>=float(e['margin']);near(e['tp'],decision['tp']);near(e['sl'],decision['sl']);assert float(e['tp'])<entry<float(e['sl']) if side==-1 else float(e['sl'])<entry<float(e['tp'])
    near(e['fee'],fee);near(e['cash_before'],cash);cash-=fee;fees+=fee;near(e['cash_after'],cash);pos=e;count[day]=1
   elif event=='CLOSE':
    assert pos;side=int(e['side']);lot=float(e['lot']);fee=lot*3.5;slip=Decimal('.0001' if cost=='stress' else '0');candidate=Decimal(e['bid'] if side==1 else e['ask'])-Decimal(side)*slip
    if e['reason']=='TP':assert candidate>=Decimal(e['TP_limit']) if side==1 else candidate<=Decimal(e['TP_limit']);near(e['price'],e['TP_limit'])
    else:near(e['price'],rnd(candidate))
    if e['reason']=='TIME21':assert (t,float(e['bid']),float(e['ask']))==first[int(e['exit_deadline'])]
    pnl=side*(float(e['price'])-float(pos['entry']))*lot*100000;net=pnl-fee-float(pos['fee']);near(e['net_trade_pnl'],net);near(e['netR'],net/float(pos['planned_risk']));near(e['cash_before'],cash);cash+=pnl-fee;fees+=fee;near(e['cash_after'],cash);trades[day]={'net':net,'lot':lot,'reason':e['reason']};pos=None
  assert pos is None;r=json.loads((folder/'results.json').read_text());near(r['final'],cash);near(r['commission'],fees);assert r['trades']==len(trades)
  near(sum(float(x['contribution']) for x in csv.DictReader((folder/'daily.csv').open())),cash-500)
  for row in csv.DictReader((folder/'equity.csv').open()):near(row['equity'],float(row['cash'])+float(row['floating']))
  out.append({'period':src['name'],'cost':cost,'status':'PASS','cash':cash,'fee':fees,'decision_quote_bar_extrema_RR_checked':checks,'trades':len(trades)})
  cref=list(csv.DictReader((Path(src['reference'])/('C_'+cost)/'ledger.csv').open()));cnets={e['timestamp'][:10]:float(e['net_trade_pnl']) for e in cref if e['event']=='CLOSE'};comparisons.append({'period':src['name'],'cost':cost,'F_trade_dates_only_not_signals_fromC':[{'date':d,'F':v,'C_net_same_date':cnets.get(d)} for d,v in trades.items()]})
result={'status':'PASS','scope':'sameOwner different finite quote/bar/extrema/RR/cash/risk/cost/time audit notthirdparty full replay','four':out,'same_date_descriptive':comparisons,'swap_native_sourcecompleteness':'UNKNOWN'}
(B/'independent_audit.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))

