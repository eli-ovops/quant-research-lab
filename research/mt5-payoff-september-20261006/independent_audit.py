from pathlib import Path
import csv,json,hashlib,datetime as dt
from decimal import Decimal,ROUND_FLOOR,ROUND_HALF_UP,ROUND_CEILING
B=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def near(a,b):assert abs(float(a)-float(b))<=1e-7*max(1,abs(float(a)),abs(float(b))),(a,b)
def round5(x,mode='nearest'):
 d=Decimal(str(x));u=Decimal('.00001');n=d.quantize(u,rounding=ROUND_HALF_UP)
 if abs(d-n)<=Decimal('.0000000001'):return float(n)
 return float(d.quantize(u,rounding=ROUND_HALF_UP if mode=='nearest' else ROUND_FLOOR if mode=='floor' else ROUND_CEILING))
freeze=json.loads((B/'execution_freeze.json').read_text());proto=json.loads((B/'protocol.json').read_text())
for n,h in freeze['hashes'].items():assert sha(B/n)==h,n
for n,h in proto['source_hashes'].items():assert sha(B/n)==h,n
inputp=Path(proto['input']['path']);assert sha(inputp)==freeze['data_sha256']
names=['A_base','A_stress','C_base','C_stress'];events={n:list(csv.DictReader((B/n/'ledger.csv').open())) for n in names};known={e['timestamp']:set() for es in events.values() for e in es if e['event'] in ['PENDING','OPEN','CLOSE']}
with inputp.open() as f:
 for r in csv.DictReader(f):
  if r['timestamp'] in known:known[r['timestamp']].add((float(r['bid']),float(r['ask'])))
outputs=[];trades={}
for name in names:
 cash=500.;pos=None;pending=None;dailycount={};closed=[];fees=0.
 for e in events[name]:
  event=e['event'];t=dt.datetime.fromisoformat(e['timestamp']);day=e['timestamp'][:10]
  if event in ['REJECT','DAY_LOCK']:continue
  if event in ['CANCEL_PENDING','FILTER_CANCEL']:pending=None;continue
  bid=float(e['bid']);ask=float(e['ask']);assert (bid,ask) in known[e['timestamp']]
  if event=='PENDING':assert pos is None and pending is None and 3<=t.hour<13;pending=e;continue
  side=int(e['side']);q=float(e['lot']);fee=q*3.5;near(e['fee'],fee);near(e['cash_before'],cash);fees+=fee;slip=Decimal('.0001' if name.endswith('stress') else '0')
  if event=='OPEN':
   assert pos is None and pending and dailycount.get(day,0)==0 and 3<=t.hour<13
   entry=round5(Decimal(str(ask if side==1 else bid))+Decimal(side)*slip);near(e['entry'],entry);SL=round5(Decimal(e['sl'])-Decimal(side)*slip);unit=abs(Decimal(str(entry))-Decimal(str(SL)))*100000+7;budget=Decimal(str(cash))*Decimal('.01');lot=float((budget/unit/Decimal('.01')).to_integral_value(rounding=ROUND_FLOOR)*Decimal('.01'));near(q,lot);assert q>=.01;near(e['risk_budget'],budget);near(e['planned_risk'],q*float(unit));assert float(e['planned_risk'])<=float(budget)+1e-8
   near(e['margin'],q*100000*entry/100);assert cash-fee>=float(e['margin']);cash-=fee;dailycount[day]=1
   if name.startswith('C'):
    target=Decimal(str(entry))+Decimal(side)*5*abs(Decimal(str(entry))-Decimal(e['sl']));near(e['tp'],round5(target,'floor' if side==1 else 'ceil'))
   pos=e;pending=None
  elif event=='CLOSE':
   assert pos;quote=bid if side==1 else ask;candidate=Decimal(str(quote))-Decimal(side)*slip
   if e['reason']=='TP':assert candidate>=Decimal(e['TP_limit']) if side==1 else candidate<=Decimal(e['TP_limit']);near(e['price'],e['TP_limit'])
   else:near(e['price'],round5(candidate))
   if e['reason'].startswith('TIME'):
    epoch=int(t.timestamp()*1000);assert epoch>=int(e['exit_deadline']);near(e['exit_delay_seconds'],(epoch-int(e['exit_deadline']))/1000);assert t.hour>= (21 if name.startswith('C') else 13)
   pnl=side*(float(e['price'])-float(pos['entry']))*q*100000;net=pnl-fee-float(pos['fee']);near(e['pnl'],pnl);near(e['net_trade_pnl'],net);near(e['netR'],net/float(pos['planned_risk']));cash+=pnl-fee;closed.append({'open':pos,'close':e,'net':net});pos=None
  near(e['cash_after'],cash)
 assert pos is None and pending is None
 r=json.loads((B/name/'results.json').read_text());near(r['final'],cash);near(r['net'],cash-500);near(r['commission'],fees);assert r['trades']==len(closed)
 gp=sum(x['net'] for x in closed if x['net']>0);gl=-sum(x['net'] for x in closed if x['net']<0);near(r['PF_net'],gp/gl);assert r['wins']==sum(x['net']>0 for x in closed)
 daily=list(csv.DictReader((B/name/'daily.csv').open()));near(sum(float(x['contribution']) for x in daily),cash-500)
 for d in daily:assert int(d['OPEN_count'])==dailycount.get(d['day'],0)
 for e in csv.DictReader((B/name/'equity.csv').open()):near(e['equity'],float(e['cash'])+float(e['floating']));near(e['free_margin'],float(e['equity'])-float(e['margin']))
 weeks=[]
 for start,end in [('2026-09-07','2026-09-12'),('2026-09-14','2026-09-19')]:weeks.append({'start':start,'end_exclusive':end,'net_contribution':sum(x['net'] for x in closed if start<=x['close']['timestamp'][:10]<end),'continuous_account':True})
 near(sum(w['net_contribution'] for w in weeks),cash-500)
 maxwin=max(x['net'] for x in closed);overnight=sum(x['open']['timestamp'][:10]!=x['close']['timestamp'][:10] for x in closed)
 outputs.append({'config':name,'status':'PASS','cash':cash,'trades':len(closed),'fees':fees,'weeks_sameaccount':weeks,'max_netwinner':maxwin,'net_without_maxwinner_descriptive':cash-500-maxwin,'overnightUTC':overnight,'risk_cost_limit_time_and_continuous_cash':'PASS','source_strategy_unchanged':True});trades[name]={x['open']['timestamp'][:10]:x for x in closed}
matched=[]
for cost in ['base','stress']:
 A=trades['A_'+cost];C=trades['C_'+cost];rows=[]
 for day in sorted(set(A)|set(C)):
  a,c=A.get(day),C.get(day)
  rows.append({'day':day,'A_net':a['net'] if a else None,'C_net':c['net'] if c else None,'delta_CminusA':c['net']-a['net'] if a and c else None,'A_reason':a['close']['reason'] if a else None,'C_reason':c['close']['reason'] if c else None,'A_exit':a['close']['timestamp'] if a else None,'C_exit':c['close']['timestamp'] if c else None,'A_lot':float(a['open']['lot']) if a else None,'C_lot':float(c['open']['lot']) if c else None,'entry_time_same':a['open']['timestamp']==c['open']['timestamp'] if a and c else False,'oldTP_to_newSL':bool(a and c and a['close']['reason']=='TP' and c['close']['reason']=='SL')})
 matched.append({'cost':cost,'rows':rows,'total_delta_CminusA':sum(x['delta_CminusA'] for x in rows if x['delta_CminusA'] is not None),'TP_to_SL_dates':[x['day'] for x in rows if x['oldTP_to_newSL']],'shared_lot_changes':sum(x['A_lot']!=x['C_lot'] for x in rows),'interpretation':'exitcombination pluscontinuous sizing, not singleTPcausal'})
out={'status':'PASS','scope':'sameOwner different cash/risk/quote/time audit, notthirdparty/fullstrategyreplay','four':outputs,'matched_same_date':matched,'trade_source_hashes':proto['source_hashes'],'adapter_hash':freeze['run_adapter_sha256'],'full_source_and_swap':'UNKNOWN'}
(B/'independent_audit.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))

