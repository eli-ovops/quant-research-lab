from pathlib import Path
import csv,json,hashlib,datetime as dt,ast
from decimal import Decimal,ROUND_HALF_UP,ROUND_FLOOR,ROUND_CEILING
B=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def near(a,b):assert abs(float(a)-float(b))<1e-7*max(1,abs(float(a)),abs(float(b))),(a,b)
def epoch(s):return int(dt.datetime.fromisoformat(s.replace('Z','+00:00')).timestamp()*1000)
def rnd(x,mode='nearest'):
 d=Decimal(str(x));n=d.quantize(Decimal('.00001'),rounding=ROUND_HALF_UP)
 if abs(d-n)<=Decimal('.0000000001'):return float(n)
 return float(d.quantize(Decimal('.00001'),rounding={'nearest':ROUND_HALF_UP,'floor':ROUND_FLOOR,'ceil':ROUND_CEILING}[mode]))
p=json.loads((B/'protocol.json').read_text());f=json.loads((B/'execution_freeze.json').read_text())
for n,h in f['hashes'].items():assert sha(B/n)==h
output=[];matched=[];M5=300000
for src in p['inputs']:
 assert sha(Path(src['path']))==src['sha256']
 names=[src['name']+'_'+a+'_'+c for a in ['C','E'] for c in ['base','stress']]
 events={n:list(csv.DictReader((B/n/'ledger.csv').open())) for n in names}
 wanted={e['timestamp']:set() for es in events.values() for e in es if e.get('bid')};closedbars={};bounds=set()
 for es in events.values():
  for e in es:
   if e['event']=='WATCH':
    for k in ast.literal_eval(e['starts']):closedbars[k]=None
   if e['event']=='CLOSE' and e['reason']=='TIME21':bounds.add(int(e['exit_deadline']))
   if e['event']=='OPEN' and e.get('confirmation_starts'):
    for k in ast.literal_eval(e['confirmation_starts']):closedbars[k]=None
    bounds.add(int(e['confirmation_boundary']))
 first={};times=[]
 with Path(src['path']).open() as inp:
  for row in csv.DictReader(inp):
   t=epoch(row['timestamp']);bid=float(row['bid']);ask=float(row['ask']);k=t//M5*M5
   if row['timestamp'] in wanted:wanted[row['timestamp']].add((bid,ask))
   if k in closedbars:closedbars[k]=(bid,ask,t)
   for boundary in bounds:
    if boundary not in first and t>=boundary:first[boundary]=t
 for name in names:
  cash=500.;pos=None;count={};trades={};fees=0.;confirms=0;watch=None;watchdays=set();cancel_checked=0
  for e in events[name]:
   event=e['event'];t=epoch(e['timestamp']);day=e['timestamp'][:10]
   if e.get('bid'):assert (float(e['bid']),float(e['ask'])) in wanted[e['timestamp']]
   if event=='WATCH':
    assert day not in watchdays and pos is None;watchdays.add(day);watch=e
   if event=='CANCEL_WATCH':
    assert watch and int(e['triggered'])==epoch(watch['timestamp'])
    if e['reason']=='close_back_inside':
     side=int(watch['side']);starts=ast.literal_eval(watch['starts']);done=[k for k in starts if t>=k+M5];assert done
     assert any(closedbars[k] and not (closedbars[k][0]>float(watch['edge']) if side==1 else closedbars[k][1]<float(watch['edge'])) for k in done)
    watch=None;cancel_checked+=1
   if event=='OPEN':
    assert pos is None and count.get(day,0)==0
    side=int(e['side']);lot=float(e['lot']);slip=Decimal('.0001' if name.endswith('stress') else '0')
    quote=float(e['ask'] if side==1 else e['bid']);entry=rnd(Decimal(str(quote))+Decimal(side)*slip);near(entry,e['entry'])
    exitSL=rnd(Decimal(e['sl'])-Decimal(side)*slip);unit=abs(Decimal(str(entry))-Decimal(str(exitSL)))*100000+7;budget=Decimal(str(cash))*Decimal('.01')
    lots=float(min(Decimal(100),(budget/unit/Decimal('.01')).to_integral_value(rounding=ROUND_FLOOR)*Decimal('.01')));near(lot,lots);assert lot>=.01
    near(e['planned_risk'],lot*float(unit));assert float(e['planned_risk'])<=float(budget)+1e-8
    near(e['margin'],lot*100000*entry/100);assert cash-lot*3.5>=float(e['margin'])
    target=Decimal(str(entry))+Decimal(side)*5*abs(Decimal(str(entry))-Decimal(e['sl']));near(e['tp'],rnd(target,'floor' if side==1 else 'ceil'))
    if '_E_' in name:
     assert watch
     starts=ast.literal_eval(e['confirmation_starts']);trigger=int(e['confirmation_trigger']);assert starts==[(trigger//M5+i)*M5 for i in [1,2,3]]
     boundary=starts[-1]+M5;assert t==first[boundary] and t<int(dt.datetime.fromisoformat(day).replace(tzinfo=dt.timezone.utc).timestamp()*1000)+13*3600000
     vals=[closedbars[k][0 if side==1 else 1] for k in starts];assert all(x>float(e['confirmation_edge']) if side==1 else x<float(e['confirmation_edge']) for x in vals)
     assert all(closedbars[k][2]<k+M5 for k in starts);near(vals[0],ast.literal_eval(e['confirmation_closes'])[0]);confirms+=1;watch=None
    near(e['cash_before'],cash);fee=lot*3.5;near(e['fee'],fee);cash-=fee;fees+=fee;near(e['cash_after'],cash);count[day]=1;pos=e
   elif event=='CLOSE':
    assert pos;side=int(e['side']);lot=float(e['lot']);slip=Decimal('.0001' if name.endswith('stress') else '0');quote=float(e['bid'] if side==1 else e['ask']);cand=Decimal(str(quote))-Decimal(side)*slip
    if e['reason']=='TP':assert cand>=Decimal(e['TP_limit']) if side==1 else cand<=Decimal(e['TP_limit']);near(e['price'],e['TP_limit'])
    else:near(e['price'],rnd(cand))
    if e['reason']=='TIME21':assert t==first[int(e['exit_deadline'])];near(e['exit_delay_seconds'],(t-int(e['exit_deadline']))/1000)
    pnl=side*(float(e['price'])-float(pos['entry']))*lot*100000;fee=lot*3.5;net=pnl-fee-float(pos['fee']);near(net,e['net_trade_pnl']);near(e['netR'],net/float(pos['planned_risk']));near(e['cash_before'],cash);cash+=pnl-fee;fees+=fee;near(e['cash_after'],cash)
    trades[day]={'net':net,'lot':lot,'entry':float(pos['entry']),'SLdistance':abs(float(pos['entry'])-float(pos['sl'])),'reason':e['reason']};pos=None
  assert pos is None
  r=json.loads((B/name/'results.json').read_text());near(r['final'],cash);near(r['commission'],fees);assert r['trades']==len(trades)
  near(sum(float(x['contribution']) for x in csv.DictReader((B/name/'daily.csv').open())),cash-500)
  for row in csv.DictReader((B/name/'equity.csv').open()):near(row['equity'],float(row['cash'])+float(row['floating']));near(row['free_margin'],float(row['equity'])-float(row['margin']))
  regression=None
  if '_C_' in name:
   ref=Path(src['reference'])/('C_'+name.split('_')[-1]);old=list(csv.DictReader((ref/'ledger.csv').open()));new=events[name];assert old==new,'C ledger mismatch '+name;assert sha(ref/'equity.csv')==sha(B/name/'equity.csv'),'C equity mismatch';regression='EXACT ledger/equity'
  output.append({'config':name,'status':'PASS','cash':cash,'fee':fees,'confirmation_original_quote_closedbar':confirms,'canceled_watch_closedbar_checked':cancel_checked,'C_regression':regression})
  events[name+'_trades']=trades
 for cost in ['base','stress']:
  C=events[src['name']+'_C_'+cost+'_trades'];E=events[src['name']+'_E_'+cost+'_trades'];es=events[src['name']+'_E_'+cost];rows=[]
  for day in sorted(set(C)|set(E)):
   cancels=[x['reason'] for x in es if x['event']=='CANCEL_WATCH' and x['timestamp'][:10]==day]
   rows.append({'day':day,'C':C.get(day),'E':E.get(day),'cancel_reasons':cancels,'EminusC':E.get(day,{}).get('net',0)-C.get(day,{}).get('net',0)})
  matched.append({'period':src['name'],'cost':cost,'days':rows,'delta':sum(x['EminusC'] for x in rows)})
result={'status':'PASS','scope':'sameOwner different implementation finite quote/closedbar/cash/risk/cost/limit audit not thirdparty full replay','eight':output,'matched_candidates':matched,'historical_swap_and_native':'UNKNOWN'}
(B/'independent_audit.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
