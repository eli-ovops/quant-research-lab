"""Independent event-ledger and raw price-risk check of rejection fixtures."""
from pathlib import Path
from decimal import Decimal as D,ROUND_FLOOR,ROUND_CEILING
import json
from test_analysis import make,SPEC
from analyze import simulate
P=Path(__file__).resolve().parent

def audit(run,data,overrides):
 cash=D(2000);positions={'BTC':D(0),'ETH':D(0)};dust={'BTC':D(0),'ETH':D(0)};checks=0
 for day in run['curve']:
  for e in run['fills']:
   if e['date']!=day['date']:continue
   c=e['coin']
   if e['side']=='buy':
    cash-=e['gross_qty']*e['price'];positions[c]+=e['gross_qty']-e['base_fee']
   else:
    assert positions[c]>=e['gross_qty'];cash+=e['gross_qty']*e['price']-e['quote_fee'];dust[c]+=positions[c]-e['gross_qty'];positions[c]=D(0)
  assert cash==day['cash'];markvalue=cash;liq=cash;unresolved=False
  for c in ['BTC','ETH']:
   assert positions[c]==day[c+'_qty'] and dust[c]==day[c+'_dust'];q=positions[c]
   if not q:continue
   ov=overrides.get((day['date'],c),{});spec=dict(SPEC[c],**ov.get('spec',{}));rawmark=day[c+'_mark'];quote=ov.get('quote',rawmark);lot=D(spec['lotSz']);sell=(q/lot).to_integral_value(rounding=ROUND_FLOOR)*lot
   valid=sell>=D(spec['minSz']) and sell<=D(spec['maxMktSz']) and quote is not None
   if valid:
    quote=D(quote);valid=quote.is_finite() and quote>0
   px=(quote*D('.9995')/D(spec['tickSz'])).to_integral_value(rounding=ROUND_FLOOR)*D(spec['tickSz']) if valid else D(0)
   valid=valid and px>0 and (not spec.get('maxMktAmt') or sell*px<=D(spec['maxMktAmt'])) and ('available_qty' not in ov or sell<=D(ov['available_qty']))
   if valid:
    charge=(sell*px*D('.001')/D('1e-8')).to_integral_value(rounding=ROUND_CEILING)*D('1e-8');markvalue+=sell*px-charge;liq+=sell*px-charge
   else:markvalue+=q*rawmark;unresolved=True
  assert markvalue==day['valuation_equity'];assert (day['liquidation_equity_proxy'] is None) ==unresolved
  assert unresolved or liq==day['liquidation_equity_proxy'];checks+=1
 assert set(c for c,q in positions.items() if q)==set(run['open_positions'])
 return checks
out=[]
for case in ['later_sale','terminal','baseline']:
 d,a,b=make(['120','130','50','49','48']+['47']*45) if case=='later_sale' else make(['120']*49+['240'])
 ov={(('2020-01-04' if case=='later_sale' else b),c):{'available_qty':'0'} for c in ['BTC','ETH']}
 kw={'budgets':{'BTC':D(800),'ETH':D(800)}} if case=='baseline' else {}
 run=simulate(d,SPEC,a,b,execution_overrides=ov,**kw);out.append({'case':case,'independent_days':audit(run,d,ov),'open_positions':len(run['open_positions']),'result':'PASS'})
(P/'validation_rejected.json').write_text(json.dumps(out,indent=2)+'\n');print(out)
