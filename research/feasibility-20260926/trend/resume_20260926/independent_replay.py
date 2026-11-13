"""Independent full rule/size/state replay from raw bars. No analyze import."""
from pathlib import Path
from decimal import Decimal as N,ROUND_FLOOR,ROUND_CEILING,getcontext
import json,csv,datetime
getcontext().prec=40
P=Path(__file__).resolve().parent;O=P.parent;C=['BTC','ETH'];DAY=86400000;ZERO=N(0)
def date(x):return datetime.datetime.fromtimestamp(x/1000,datetime.timezone.utc).date().isoformat()
def ms(x):return int(datetime.datetime.fromisoformat(x).replace(tzinfo=datetime.timezone.utc).timestamp()*1000)
def snap(x,step,mode):return (x/step).to_integral_value(rounding=mode)*step
bars={};spec={}
for c in C:
 spec[c]=json.loads((O/'raw'/(c+'_spec.txt')).read_text())['data'][0];bars[c]={}
 for f in list((O/'raw').glob(c+'_daily_*.txt'))+list((P/'raw').glob(c+'_daily_*.txt')):
  for r in json.loads(f.read_text())['data']:bars[c][int(r[0])]=list(map(N,r[1:6]))
curves=list(csv.DictReader((P/'equity_all.csv').open()));fills=list(csv.DictReader((P/'fills_all.csv').open()));protocol=json.loads((P/'protocol.json').read_text());summaries=[];samples=[];calibration=None
for period,(start,end) in protocol['periods'].items():
 for name in ['main','short','long','fee2','slip20','severe','delay1','hold','exposure_hold']:
  fee=N('.002') if name=='fee2' else N('.003') if name=='severe' else N('.001');slip=N('.002') if name=='slip20' else N('.005') if name=='severe' else N('.0005');en,ex=(15,7) if name=='short' else (30,15) if name=='long' else (20,10);lag=2 if name=='delay1' else 1
  cash=N(2000);inventory={};queue={};dust={c:ZERO for c in C};ev=[];values=[];exposures={c:[] for c in C};hold=name in ['hold','exposure_hold'];budgets=calibration if name=='exposure_hold' else {c:N(800) for c in C};reserve=ZERO if hold else N(400)
  def exitone(c,t,reference,signal,reason):
   global cash
   q=inventory[c]['net'];sp=spec[c];sold=snap(q,N(sp['lotSz']),ROUND_FLOOR);px=snap(reference*(1-slip),N(sp['tickSz']),ROUND_FLOOR)
   if sold<N(sp['minSz']) or sold>N(sp['maxMktSz']) or px<=0 or (sp.get('maxMktAmt') and sold*px>N(sp['maxMktAmt'])):return False
   charge=snap(sold*px*fee,N('1e-8'),ROUND_CEILING);cash+=sold*px-charge;dust[c]+=q-sold;del inventory[c]
   ev.append((date(t),c,'sell',signal,reference,px,sold,ZERO,charge,cash));return True
  for t in range(ms(start),ms(end)+DAY,DAY):
   today=queue.pop(t,[])
   if hold and t==ms(start):today=[(c,'buy','scheduled_initial') for c in C]
   exited=set()
   for c,side,sig in today:
    if side=='sell' and c in inventory:
     if exitone(c,t,bars[c][t][0],sig,'signal'):exited.add(c)
   buylist=[(c,sig) for c,side,sig in today if side=='buy' and c not in inventory and c not in exited]
   total=sum((budgets[c] for c,sig in buylist),ZERO);free=max(ZERO,cash-reserve)
   for c,sig in buylist:
    sp=spec[c];budget=min(budgets[c],free*budgets[c]/total);ref=bars[c][t][0];price=snap(ref*(1+slip),N(sp['tickSz']),ROUND_CEILING);quantity=snap(budget/price,N(sp['lotSz']),ROUND_FLOOR);basecharge=snap(quantity*fee,N('1e-8'),ROUND_CEILING)
    if quantity<N(sp['minSz']) or quantity>N(sp['maxMktSz']) or quantity<=basecharge:continue
    cash-=quantity*price;inventory[c]={'net':quantity-basecharge};ev.append((date(t),c,'buy',sig,ref,price,quantity,basecharge,ZERO,cash))
   if t==ms(end):
    for c in list(inventory):exitone(c,t,bars[c][t][3],'scheduled_terminal','terminal')
   markeq=cash+sum((v['net']*bars[c][t][3] for c,v in inventory.items()),ZERO);value=cash
   for c in C:
    exposures[c].append(inventory[c]['net']*bars[c][t][3]/markeq if c in inventory else ZERO)
    if c in inventory:
     q=inventory[c]['net'];sold=snap(q,N(spec[c]['lotSz']),ROUND_FLOOR);px=snap(bars[c][t][3]*(1-slip),N(spec[c]['tickSz']),ROUND_FLOOR);value+=sold*px-snap(sold*px*fee,N('1e-8'),ROUND_CEILING)
   values.append((date(t),cash,{c:inventory[c]['net'] if c in inventory else ZERO for c in C},dict(dust),value))
   if not hold:
    for c in C:
     if any(any(x[0]==c for x in entries) for due,entries in queue.items() if due>t):continue
     action=None
     if c not in inventory and bars[c][t][3]>max(bars[c][t-j*DAY][1] for j in range(1,en+1)):action='buy'
     elif c in inventory and bars[c][t][3]<min(bars[c][t-j*DAY][2] for j in range(1,ex+1)):action='sell'
     if action:queue.setdefault(t+lag*DAY,[]).append((c,action,date(t)))
  expected=[r for r in fills if r['period']==period and r['variant']==name];assert len(ev)==len(expected)
  for a,r in zip(ev,expected):
   assert a[:4]==(r['date'],r['coin'],r['side'],r['signal_date'])
   for v,k in zip(a[4:],['reference','price','gross_qty','base_fee','quote_fee','cash_after']):assert abs(v-N(r[k]))<N('1e-18'),(period,name,k,v,r[k])
  cc=[r for r in curves if r['period']==period and r['variant']==name];assert len(cc)==len(values)
  for a,r in zip(values,cc):
   assert a[0]==r['date'] and abs(a[1]-N(r['cash']))<N('1e-18') and abs(a[4]-N(r['valuation_equity']))<N('1e-18')
   for c in C:assert a[2][c]==N(r[c+'_qty']) and a[3][c]==N(r[c+'_dust'])
  if name=='main' and period=='development':
   # Match the original protocol's implemented development mean float conversion;
   # additionally expose high-precision discrepancy without selecting allocations.
   calibration={c:N(str(sum(float(x) for x in exposures[c])/len(exposures[c])))*2000 for c in C}
  summaries.append({'period':period,'variant':name,'cash_end':str(cash),'fills_independently_generated':len(ev),'days':len(values),'unresolved_positions':len(inventory),'status':'PASS'})
  if name=='main':samples.extend({'period':period,'event':list(map(str,e))} for e in ev[:2]+ev[-2:])
out={'implementation':'independent from raw chronology,signals,position size and cash; no strategy imports','scenario_count':len(summaries),'scenarios':summaries,'independent_benchmark_budgets':calibration,'sample_first_last_events':samples};(P/'independent_replay.json').write_text(json.dumps(out,indent=2,default=str)+'\n');print('independent full raw replays',len(summaries),'all PASS')
