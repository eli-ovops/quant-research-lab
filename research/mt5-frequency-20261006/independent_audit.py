from pathlib import Path
import csv,json,hashlib,datetime as dt
from decimal import Decimal,ROUND_FLOOR,ROUND_HALF_UP
B=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def near(a,b,tol=1e-7):assert abs(float(a)-float(b))<=tol*max(1,abs(float(a)),abs(float(b))),(a,b)
def millis(s):return int(dt.datetime.fromisoformat(s).timestamp()*1000)
def round5(v):
 d=Decimal(str(v));u=Decimal('.00001');n=d.quantize(u,rounding=ROUND_HALF_UP)
 return float(n)
freeze=json.loads((B/'execution_freeze.json').read_text())
for n,h in freeze['hashes'].items():assert sha(B/n)==h,n
proto=json.loads((B/'protocol.json').read_text());assert sha(Path(proto['input_readonly']['path']))==freeze['input_sha256']
folders=[('cap'+str(c)+'_'+n,c,n) for c in [1,5,15] for n in ['base','stress']]
all_events={name:list(csv.DictReader((B/name/'ledger.csv').open())) for name,cap,cost in folders}
known={e['timestamp']:set() for events in all_events.values() for e in events if e['event'] in ['OPEN','CLOSE','PENDING']}
with Path(proto['input_readonly']['path']).open() as f:
 for row in csv.DictReader(f):
  if row['timestamp'] in known:known[row['timestamp']].add((float(row['bid']),float(row['ask'])))
out=[];trademap={}
for name,cap,cost in folders:
 events=all_events[name];result=json.loads((B/name/'results.json').read_text());cash=500.;position=None;daily_count={};daily_lock=set();closed=[];fees=0.;slips=0.;lastclose={};pending=None
 for e in events:
  time=dt.datetime.fromisoformat(e['timestamp']);day=e['timestamp'][:10];t=millis(e['timestamp'])
  if e['event']=='DAY_LOCK':daily_lock.add(day);assert float(e['equity'])<=float(e['day_start'])*.95+1e-8;continue
  if e['event']=='CANCEL_PENDING':pending=None;continue
  if e['event']=='REJECT':continue
  bid,ask=float(e['bid']),float(e['ask']);assert (bid,ask) in known[e['timestamp']]
  if e['event']=='PENDING':
   assert position is None and pending is None and day not in daily_lock and 3<=time.hour<13
   side=int(e['side']);assert float(e['entry'])>ask if side==1 else float(e['entry'])<bid
   if day in lastclose:assert t>=(lastclose[day]//300000+1)*300000
   if e['reentry']=='True':assert t>=int(e['eligible_after'])
   pending=e;continue
  side=int(e['side']);lot=float(e['lot']);fee=lot*3.5;near(e['fee'],fee);near(e['cash_before'],cash);fees+=fee;slips+=float(e['slip_USD'])
  if e['event']=='OPEN':
   assert position is None and pending and day not in daily_lock and 3<=time.hour<13
   entry=round5((ask if side==1 else bid)+side*(.0001 if cost=='stress' else 0));near(e['entry'],entry);SL=round5(float(e['sl'])-side*(.0001 if cost=='stress' else 0));unit=abs(Decimal(str(entry))-Decimal(str(SL)))*Decimal(100000)+Decimal(7);budget=Decimal(str(cash))*.01 if False else Decimal(str(cash))*Decimal('.01')
   expected=float(min(Decimal(100),(budget/unit/Decimal('.01')).to_integral_value(rounding=ROUND_FLOOR)*Decimal('.01')));near(lot,expected);assert lot>=.01
   near(e['risk_budget'],budget);near(e['risk_perlot'],unit);near(e['planned_risk'],lot*float(unit));assert float(e['planned_risk'])<=float(budget)+1e-8
   margin=lot*100000*entry/100;near(e['margin'],margin);assert cash-fee>=margin;cash-=fee
   daily_count[day]=daily_count.get(day,0)+1;assert daily_count[day]<=cap;assert int(e['day_OPEN_count'])==daily_count[day]
   position=e;pending=None
  elif e['event']=='CLOSE':
   assert position and side==int(position['side']);quote=bid if side==1 else ask;candidate=Decimal(str(quote))-Decimal(side)*Decimal('.0001' if cost=='stress' else '0')
   if e['reason']=='TP':assert candidate>=Decimal(e['TP_limit']) if side==1 else candidate<=Decimal(e['TP_limit']);near(e['price'],e['TP_limit'])
   else:near(e['price'],round5(candidate))
   pnl=side*(float(e['price'])-float(position['entry']))*lot*100000;net=pnl-fee-float(position['fee']);near(e['pnl'],pnl);near(e['net_trade_pnl'],net);cash+=pnl-fee
   closed.append({'key':(day,daily_count[day]),'open':position,'close':e,'net':net});position=None;lastclose[day]=t
  near(e['cash_after'],cash)
 assert position is None and pending is None
 near(result['final'],cash);near(result['net'],cash-500);near(result['commission'],fees);near(result['slip'],slips);assert result['trades']==sum(daily_count.values())==len(closed);assert result['day_max']==max(daily_count.values())
 gp=sum(x['net'] for x in closed if x['net']>0);gl=-sum(x['net'] for x in closed if x['net']<0);near(result['PF_net'],gp/gl);assert all(v<=cap for v in daily_count.values())
 daily=list(csv.DictReader((B/name/'daily.csv').open()));weekday=[d for d in daily if dt.date.fromisoformat(d['day']).weekday()<5];assert len(weekday)==20
 near(sum(float(d['contribution']) for d in daily),cash-500)
 for d in daily:assert int(d['OPEN_count'])==daily_count.get(d['day'],0)
 eq=list(csv.DictReader((B/name/'equity.csv').open()))
 for r in eq:near(r['equity'],float(r['cash'])+float(r['floating']));near(r['free_margin'],float(r['equity'])-float(r['margin']))
 first=[e for e in events if e['event']=='PENDING' and e['day_OPEN_count']=='0']
 out.append({'config':name,'status':'PASS','cap_limit':cap,'cost':cost,'first_proposal_count':len(first),'trades':len(closed),'cash':cash,'fees':fees,'slip':slips,'largest_plannedrisk_pct':result['plannedrisk_pct_max'],'quote_fee_risklot_margin_cap_cooldown_daylock_window_equity':'PASS','ledger_sha256':sha(B/name/'ledger.csv'),'daily_sha256':sha(B/name/'daily.csv')})
 trademap[name]={x['key']:x for x in closed}
paired=[]
for cost in ['base','stress']:
 ref=trademap['cap1_'+cost];high=trademap['cap5_'+cost];common=set(ref)&set(high);extra=set(high)-set(ref);shared_delta=sum(high[k]['net']-ref[k]['net'] for k in common);extra_net=sum(high[k]['net'] for k in extra);total=sum(x['net'] for x in high.values())-sum(x['net'] for x in ref.values())
 near(total,shared_delta+extra_net)
 pairs=[]
 for k in sorted(common):
  r,h=ref[k],high[k];pairs.append({'day':k[0],'dayordinal':k[1],'lot_cap1':float(r['open']['lot']),'lot_cap5':float(h['open']['lot']),'net_cap1':r['net'],'net_cap5':h['net'],'shared_net_delta':h['net']-r['net'],'entry_times_same':r['open']['timestamp']==h['open']['timestamp'],'fees_cap1':float(r['open']['fee'])+float(r['close']['fee']),'fees_cap5':float(h['open']['fee'])+float(h['close']['fee'])})
 def strip(rows):return [{k:v for k,v in row.items() if k not in ['cap','cost']} for row in rows]
 five=strip(all_events['cap5_'+cost]);fifteen=strip(all_events['cap15_'+cost]);assert five==fifteen
 normalized=hashlib.sha256(json.dumps(five,sort_keys=True).encode()).hexdigest()
 paired.append({'cost':cost,'total_cap5_minus_cap1_net':total,'extra_trade_count':len(extra),'extra_trade_net':extra_net,'shared_trade_sizing_net_delta':shared_delta,'shared_pair_rows':pairs,'shared_lot_different_count':sum(p['lot_cap1']!=p['lot_cap5'] for p in pairs),'extra_fee':sum(float(high[k]['open']['fee'])+float(high[k]['close']['fee']) for k in extra),'shared_fee_delta':sum(p['fees_cap5']-p['fees_cap1'] for p in pairs),'cap5_cap15_all_events_equal_ignoring_tags':True,'normalized_ledger_sha256':normalized,'equity5_15_identical':sha(B/('cap5_'+cost)/'equity.csv')==sha(B/('cap15_'+cost)/'equity.csv')})
result={'status':'PASS','scope':'sameOwner different bookkeeping/quote/riskcap implementation, notthirdparty/fullstrategyreplay','six_config_audit':out,'paired_frequency_at_same_cost':paired,'first_signal_reference':'signal_equivalence.json firstnormal20 signals matched beforePnL','no_network':True,'native_and_sourcecompleteness':'UNKNOWN'}
(B/'independent_audit.json').write_text(json.dumps(result,indent=2));print(json.dumps({'status':'PASS','six':out,'paired':[{k:v for k,v in p.items() if k!='shared_pair_rows'} for p in paired]},indent=2))

