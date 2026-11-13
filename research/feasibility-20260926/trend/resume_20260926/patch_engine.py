from pathlib import Path
import shutil
P=Path(__file__).resolve().parent;f=P/'analyze.py';s=f.read_text()
s=s.replace("P=Path(__file__).resolve().parent;DAY", "P=Path(__file__).resolve().parent;ORIGINAL=P.parent;DAY")
s=s.replace("(P/'raw'/f'{c}_spec.txt')", "(ORIGINAL/'raw'/f'{c}_spec.txt')")
s=s.replace("sorted((P/'raw').glob(c+'_daily_*.txt'))", "sorted((ORIGINAL/'raw').glob(c+'_daily_*.txt'))+sorted((P/'raw').glob(c+'_daily_*.txt'))")
a=s.index('def sell_quote(');b=s.index('\ndef simulate(',a)
s=s[:a]+'''def sell_quote(q,ref,spec,fee,slip,available_qty=None):
 sold=floor(q,D(spec['lotSz']))
 try:
  ref=D(ref)
  if not ref.is_finite() or ref<=0:return Z,Z,Z,Z,q
  px=floor(ref*(1-slip),D(spec['tickSz']))
 except (TypeError,ValueError,ArithmeticError):return Z,Z,Z,Z,q
 if sold<D(spec['minSz']) or sold>D(spec['maxMktSz']) or px<=0:return Z,px,Z,Z,q
 if spec.get('maxMktAmt') and sold*px>D(spec['maxMktAmt']):return Z,px,Z,Z,q
 if available_qty is not None and sold>D(available_qty):return Z,px,Z,Z,q
 cost=ceil(sold*px*fee,D('0.00000001'));return sold,px,cost,sold*px-cost,q-sold
''' +s[b:]
s=s.replace('reserve=D(400)):', 'reserve=D(400),execution_overrides=None):')
s=s.replace("caps=budgets or", "execution_overrides=execution_overrides or {}\n caps=budgets or")
s=s.replace("h=held.pop(c);q,px,feequote,received,rem=sell_quote(h['net'],ref,spec[c],fee,slip);cash+=received;dust[c]+=rem", """h=held[c];override=execution_overrides.get((date(t),c),{});salespec=dict(spec[c],**override.get('spec',{}));quote=override.get('quote',ref)
  q,px,feequote,received,rem=sell_quote(h['net'],quote,salespec,fee,slip,override.get('available_qty'))
  if q==0:
   rejections.append({'date':date(t),'coin':c,'reason':'exit_rejected_position_retained','budget':Z,'retained_base':h['net'],'signal_date':signal,'terminal':reason=='scheduled_terminal'})
   return False
  del held[c];cash+=received;dust[c]+=rem""")
s=s.replace("'days_held':(t-ts(h['date']))//DAY})", "'days_held':(t-ts(h['date']))//DAY})\n  return True")
s=s.replace("if side=='sell' and c in held:sell(c,t,data[c][t]['o'],'signal',sig);exited.add(c)", "if side=='sell' and c in held:\n    if sell(c,t,data[c][t]['o'],'signal',sig):exited.add(c)")
s=s.replace("eq=cash+sum((sell_quote(h['net'],data[c][t]['c'],spec[c],fee,slip)[3] for c,h in held.items()),Z)","""liquid=cash;valuation=cash;unliquidatable=False
  for c,h in held.items():
   override=execution_overrides.get((date(t),c),{});salespec=dict(spec[c],**override.get('spec',{}));quote=override.get('quote',data[c][t]['c'])
   sq=sell_quote(h['net'],quote,salespec,fee,slip,override.get('available_qty'))
   if sq[0]>0:liquid+=sq[3];valuation+=sq[3]
   else:unliquidatable=True;valuation+=h['net']*data[c][t]['c']
  eq=valuation""")
s=s.replace("'liquidation_equity_proxy':eq}", "'liquidation_equity_proxy':None if unliquidatable else liquid,'valuation_equity':eq,'exit_unresolved':unliquidatable,'active_positions':len(held)}")
s=s.replace("'pending_at_end':str(pending),'dust_base':dust}", "'pending_at_end':str(pending),'dust_base':dust,'open_positions':held,'all_trade_positions_closed':not held,'cash_realized_pnl':cash-capital}")
s=s.replace("float(r['liquidation_equity_proxy'])", "float(r['valuation_equity'])")
s=s.replace("'net_pnl':equities[-1]-2000", "'positions_unresolved':not run['all_trade_positions_closed'],'cash_realized_pnl':float(run['cash_realized_pnl']),'remaining_positions':run['open_positions'],'net_pnl':equities[-1]-2000")
s=s.replace("assert abs(sum((r['net_pnl'] for r in trades),Z)-(cash-capital))<D('1e-20')", "assert abs(sum((r['net_pnl'] for r in trades),Z)-sum((h['cost'] for h in held.values()),Z)-(cash-capital))<D('1e-20')")
f.write_text(s)
for n in ['protocol.json','protocol_freeze.json','sources.json']:shutil.copyfile(ORIGINAL/n,P/n) if False else shutil.copyfile(P.parent/n,P/n)
