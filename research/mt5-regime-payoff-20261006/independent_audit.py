from pathlib import Path
import csv,json,hashlib,datetime as dt
from decimal import Decimal,ROUND_FLOOR,ROUND_HALF_UP
B=Path(__file__).resolve().parent;UTC=dt.timezone.utc;M5=300000
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def near(a,b):assert abs(float(a)-float(b))<1e-7*max(1,abs(float(a)),abs(float(b))),(a,b)
def round5(x,mode='nearest'):
 d=Decimal(str(x));u=Decimal('.00001');n=d.quantize(u,rounding=ROUND_HALF_UP)
 if abs(d-n)<Decimal('.0000000001'):return float(n)
 return float(d.quantize(u,rounding=ROUND_HALF_UP if mode=='nearest' else __import__('decimal').ROUND_FLOOR if mode=='floor' else __import__('decimal').ROUND_CEILING))
freeze=json.loads((B/'execution_freeze.json').read_text())
for n,h in freeze['hashes'].items():assert sha(B/n)==h,n
proto=json.loads((B/'protocol.json').read_text());inputp=Path(proto['input']['path']);assert sha(inputp)==freeze['input_sha256']
names=[a+'_'+c for a in ['A','B','C','D'] for c in ['base','stress']];events={n:list(csv.DictReader((B/n/'ledger.csv').open())) for n in names}
known={e['timestamp']:set() for es in events.values() for e in es if e['event'] in ['PENDING','OPEN','CLOSE','FILTER_CHECK']}
bars={}
with inputp.open() as f:
 for r in csv.DictReader(f):
  t=int(dt.datetime.fromisoformat(r['timestamp']).timestamp()*1000);bid=float(r['bid']);ask=float(r['ask']);k=t//M5*M5
  if k not in bars:bars[k]=[bid,bid,bid,bid]
  else:v=bars[k];v[1]=max(v[1],bid);v[2]=min(v[2],bid);v[3]=bid
  if r['timestamp'] in known:known[r['timestamp']].add((bid,ask))
def closed(k):
 keys=list(range(k-61*M5,k,M5))
 if not all(x in bars for x in keys):return None
 closes=[bars[x][3] for x in keys];net=closes[-1]-closes[0];den=sum(abs(b-a) for a,b in zip(closes,closes[1:]));tr=[]
 for x in range(k-14*M5,k,M5):v=bars[x];prev=bars[x-M5][3];tr.append(max(v[1]-v[2],abs(v[1]-prev),abs(v[2]-prev)))
 return (abs(net)/den if den else 0,sum(tr)/14,1 if net>0 else -1 if net<0 else 0)
outputs=[];baseline={};trades={}
for name in names:
 cash=500.;pos=None;pending=None;countday={};closedtrades=[];feeSum=0.;filterchecks=0
 for e in events[name]:
  event=e['event'];t=int(dt.datetime.fromisoformat(e['timestamp']).timestamp()*1000);day=e['timestamp'][:10];hour=dt.datetime.fromisoformat(e['timestamp']).hour
  if event in ['REJECT','DAY_LOCK']:continue
  if event in ['CANCEL_PENDING','FILTER_CANCEL']:pending=None;continue
  if event in ['PENDING','OPEN','CLOSE','FILTER_CHECK']:
   bid,ask=float(e['bid']),float(e['ask']);assert (bid,ask) in known[e['timestamp']]
  if event=='FILTER_CHECK':
   k=t//M5*M5;stats=closed(k);assert int(e['closed_completed_at'])<=t and int(e['latest_closed_start'])<t
   if stats:
    ER,ATR,direction=stats;near(e['ER_before'],ER);near(e['ATR_before'],ATR);assert int(e['closed_direction'])==direction;passed=ER>=.35 and ATR>=(ask-bid)*10 and direction==int(e['side'])
   else:passed=False
   assert (e['passed']=='True')==passed;filterchecks+=1;continue
  if event=='PENDING':
   assert pos is None and pending is None and 3<=hour<13;side=int(e['side']);assert float(e['entry'])>ask if side==1 else float(e['entry'])<bid;pending=e;continue
  lot=float(e['lot']);side=int(e['side']);fee=lot*3.5;near(e['fee'],fee);near(e['cash_before'],cash);feeSum+=fee;slip=Decimal('.0001' if name.endswith('stress') else '0')
  if event=='OPEN':
   assert pos is None and pending and countday.get(day,0)==0 and 3<=hour<13
   entry=round5(Decimal(str(ask if side==1 else bid))+Decimal(side)*slip);near(e['entry'],entry);SL=round5(Decimal(e['sl'])-Decimal(side)*slip);unit=abs(Decimal(str(entry))-Decimal(str(SL)))*100000+7;budget=Decimal(str(cash))*Decimal('.01');qty=float((budget/unit/Decimal('.01')).to_integral_value(rounding=ROUND_FLOOR)*Decimal('.01'));near(lot,qty);near(e['planned_risk'],lot*float(unit));assert float(e['planned_risk'])<=float(budget)+1e-8
   near(e['margin'],lot*100000*entry/100);assert cash-fee>=float(e['margin']);cash-=fee;countday[day]=1
   if name[0] in ['C','D']:
    target=Decimal(str(entry))+Decimal(side)*5*abs(Decimal(str(entry))-Decimal(e['sl']));near(e['tp'],round5(target,'floor' if side==1 else 'ceil'));assert int(e['position_expiry'])==t//86400000*86400000+21*3600000
   pos=e;pending=None
  elif event=='CLOSE':
   assert pos;quote=bid if side==1 else ask;candidate=Decimal(str(quote))-Decimal(side)*slip
   if e['reason']=='TP':assert candidate>=Decimal(e['TP_limit']) if side==1 else candidate<=Decimal(e['TP_limit']);near(e['price'],e['TP_limit'])
   else:near(e['price'],round5(candidate))
   if e['reason'].startswith('TIME'):assert t>=int(e['exit_deadline']);near(e['exit_delay_seconds'],(t-int(e['exit_deadline']))/1000)
   pnl=side*(float(e['price'])-float(pos['entry']))*lot*100000;net=pnl-fee-float(pos['fee']);near(e['net_trade_pnl'],net);near(e['netR'],net/float(pos['planned_risk']));cash+=pnl-fee;closedtrades.append({'open':pos,'close':e,'net':net});pos=None
  near(e['cash_after'],cash)
 assert pos is None and pending is None
 r=json.loads((B/name/'results.json').read_text());near(r['net'],cash-500);near(r['final'],cash);near(r['commission'],feeSum);assert r['trades']==len(closedtrades);assert all(v<=1 for v in countday.values())
 if closedtrades:
  gp=sum(x['net'] for x in closedtrades if x['net']>0);gl=-sum(x['net'] for x in closedtrades if x['net']<0);near(r['PF_net'],gp/gl)
 else:assert r['PF_net'] is None and cash==500
 for e in csv.DictReader((B/name/'equity.csv').open()):near(e['equity'],float(e['cash'])+float(e['floating']));near(e['free_margin'],float(e['equity'])-float(e['margin']))
 if name.startswith('A'):
  old=Path('/Volumes/EXTERNAL/量化/research/mt5-frequency-20261006')/('cap1_'+name.split('_')[1]);oldrows=list(csv.DictReader((old/'ledger.csv').open()));assert len(oldrows)==len(events[name])
  for o,n in zip(oldrows,events[name]):
   for key,value in o.items():assert n[key]==value,(key,value,n[key])
  assert sha(old/'equity.csv')==sha(B/name/'equity.csv');baseline[name]='EXACT_CORE_LEDGER_AND_EQUITY_EQUIVALENT'
 trades[name]=closedtrades;outputs.append({'config':name,'status':'PASS','cash':cash,'trades':len(closedtrades),'fee':feeSum,'closed_factor_checks':filterchecks,'quote_risklot_margin_cap_window_cost_and_cash':'PASS','A_baseline':baseline.get(name),'ledger_sha256':sha(B/name/'ledger.csv')})
describe={}
for name in ['A_base','A_stress']:
 proposals=[e for e in events[name] if e['event']=='PENDING'];mapday={x['open']['timestamp'][:10]:x for x in trades[name]};groups={}
 for p in proposals:
  g='missing61' if not p['ER_before'] else 'ER_ge035' if float(p['ER_before'])>=.35 else 'ER_lt035';v=groups.setdefault(g,{'candidates':0,'traded':0,'no_fill':0,'net':0.});v['candidates']+=1;x=mapday.get(p['timestamp'][:10])
  if x:v['traded']+=1;v['net']+=x['net']
  else:v['no_fill']+=1
 describe[name]=groups
filter_marginals={}
for name in ['B_base','B_stress','D_base','D_stress']:
 checks=[e for e in events[name] if e['event']=='FILTER_CHECK'];proposal=[e for e in checks if e['stage']=='proposal'];complete=[e for e in proposal if e['ER_before']]
 filter_marginals[name]={'proposal_checks':len(proposal),'complete':len(complete),'ER_independent_pass':sum(float(e['ER_before'])>=.35 for e in complete),'ATRspread_independent_pass':sum(float(e['ATR_before'])>=float(e['spread'])*10 for e in complete),'direction_independent_pass':sum(int(e['closed_direction'])==int(e['side']) for e in complete),'combined_proposal_pass':sum(e['passed']=='True' for e in proposal),'trigger_checks':sum(e['stage']=='trigger' for e in checks),'trigger_pass':sum(e['stage']=='trigger' and e['passed']=='True' for e in checks)}
sens={}
for name in ['C_base','C_stress']:
 closed=trades[name];maximum=max(x['net'] for x in closed);weeks=[]
 for s,e in [('2026-08-03','2026-08-08'),('2026-08-10','2026-08-15'),('2026-08-17','2026-08-22'),('2026-08-24','2026-08-29')]:weeks.append({'start':s,'end_exclusive':e,'net':sum(x['net'] for x in closed if s<=x['close']['timestamp'][:10]<e)})
 sens[name]={'max_netwinner':maximum,'net_without_maxwinner':sum(x['net'] for x in closed)-maximum,'descriptive_fragility_not_new_acceptance_gate':True,'weeks_same_account':weeks}
result={'status':'PASS','scope':'sameOwner different factor/cash/risk bookkeeping; notthirdparty/fullindependentstrategyreplay','configs':outputs,'A_exact_equivalence':baseline,'original_candidate_ER_groups_descriptive':describe,'filter_marginals':filter_marginals,'tail_concentration_descriptive':sens,'full_source_complete':'UNKNOWN'}
(B/'independent_audit.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))

