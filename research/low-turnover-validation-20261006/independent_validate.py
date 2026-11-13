"""Independent ledger auditor: does not import replay implementation or data loader."""
import csv,json,pathlib,datetime,hashlib,math
B=pathlib.Path(__file__).resolve().parent
DAY=86400000
def millis(s):
 d=datetime.datetime.fromisoformat(s)
 if d.tzinfo is None:d=d.replace(tzinfo=datetime.timezone.utc)
 return int(d.timestamp()*1000)
def near(a,b,tol=1e-7):assert abs(float(a)-float(b))<=tol*max(1,abs(float(a)),abs(float(b))),(a,b)
def h(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def run():
 p=json.loads((B/'protocol.json').read_text());f=json.loads((B/'freeze.json').read_text());assert h(B/'protocol.json')==f['protocol_sha256'] and h(B/'dataaudit.json')==f['dataaudit_sha256']
 raw={'BTC':{},'ETH':{}}
 for item in p['source_files']:
  file=pathlib.Path(item['path']);assert h(file)==item['sha256'];asset=file.name.split('_')[0]
  for row in json.loads(file.read_text())['data']:
   t=int(row[0]);assert t%DAY==0 and row[-1]=='1'
   if t in raw[asset]:assert raw[asset][t]==row
   raw[asset][t]=row
 result=json.loads((B/'results.json').read_text());receipts=[]
 for sc in result['scenarios']:
  ledger=list(csv.DictReader((B/sc['ledger_file']).open()));days=list(csv.DictReader((B/sc['equity_file']).open()))
  cash=500.;q={'BTC':0.,'ETH':0.};cursor=0;fee=p['costs'][sc['cost']]['fee_bps_each_side']/10000;slip=p['costs'][sc['cost']]['slip_bps_each_side']/10000
  fees=slips=turnover=0.;peak=prev=500.;drawdown=0.;worst=1.;exposure=0.;active=0;weights_checks=0
  for d in days:
   t=millis(d['bar_timestamp']);assert t==millis(sc['start'])+days.index(d)*DAY
   group=[]
   while cursor<len(ledger) and millis(ledger[cursor]['timestamp'])<t+DAY:
    l=ledger[cursor];at=millis(l['timestamp']);assert at>=t;c=l['asset'];qty=float(l['quantity']);side=1 if l['side']=='BUY' else -1
    near(l['cash_before'],cash);near(l['quantity_before'],q[c]);assert qty>0
    if l['reason']=='terminal_liquidation':
     assert at==millis(sc['end_exclusive'])-1 and t==millis(sc['end_exclusive'])-DAY and side==-1
     near(qty,q[c]);ref=float(raw[c][t][4])
    else:
     assert at==t;ref=float(raw[c][t][1])
     if l['reason']=='weekly_rebalance':
      assert datetime.datetime.fromtimestamp(t/1000,datetime.timezone.utc).weekday()==0
      latest=millis(l['signal_latest_bar']);old=millis(l['signal_old_bar'])
      assert latest==t-DAY and old==t-91*DAY and latest-old==90*DAY and latest+DAY<=at
      if side==1:assert float(raw[c][latest][4])>float(raw[c][old][4])
      group.append(l)
     else:assert sc['mode']=='hold' and at==millis(sc['start'])
    px=ref*(1+side*slip);fvalue=qty*px*fee;svalue=qty*abs(px-ref)
    near(l['reference_price'],ref);near(l['execution_price'],px);near(l['execution_notional'],qty*px);near(l['fee_USDT'],fvalue);near(l['slippage_USDT'],svalue)
    cash-=side*qty*px+fvalue;q[c]+=side*qty;near(l['cash_after'],cash);near(l['quantity_after'],q[c]);assert cash>=-1e-7 and q[c]>=-1e-12
    fees+=fvalue;slips+=svalue;turnover+=qty*ref/500;cursor+=1
   if group:
    # No final liquidation on same day as group in this dataset; weights posttrade at daily open.
    assert not any(x['reason']=='terminal_liquidation' and millis(x['timestamp'])>=t for x in ledger[max(0,cursor-len(group)):cursor])
    seen_buy=False
    for l in group:
     if l['side']=='BUY':seen_buy=True
     if l['side']=='SELL':assert not seen_buy
    navopen=cash+sum(q[c]*float(raw[c][t][1]) for c in q)
    for c in q:
     on=float(raw[c][t-DAY][4])>float(raw[c][t-91*DAY][4]);near(q[c]*float(raw[c][t][1]),navopen*.5 if on else 0)
    weights_checks+=1
   vals={c:q[c]*float(raw[c][t][4]) for c in q};eq=cash+sum(vals.values())
   near(d['cash'],cash);near(d['BTC_qty'],q['BTC']);near(d['ETH_qty'],q['ETH']);near(d['BTC_value'],vals['BTC']);near(d['ETH_value'],vals['ETH']);near(d['equity'],eq)
   peak=max(peak,eq);drawdown=max(drawdown,1-eq/peak);worst=min(worst,eq/prev-1);prev=eq
   ex=sum(vals.values())/eq;near(d['exposure'],ex);exposure+=ex;active+=ex>1e-12
  assert cursor==len(ledger) and all(abs(v)<1e-10 for v in q.values())
  near(sc['final_equity_USDT'],cash);near(sc['net_return'],cash/500-1);near(sc['net_pnl_USDT'],cash-500);near(sc['max_drawdown'],drawdown);near(sc['worst_day_return'],worst);near(sc['fees_USDT'],fees);near(sc['slippage_USDT'],slips);near(sc['turnover_two_sided_initial_capital'],turnover);near(sc['mean_daily_close_market_exposure'],exposure/len(days));near(sc['active_days_fraction'],active/len(days));assert sc['individual_trade_legs']==len(ledger)
  if drawdown==0:assert sc['return_drawdown_ratio'] is None
  else:near(sc['return_drawdown_ratio'],(cash/500-1)/drawdown)
  assert len(days)==(millis(sc['end_exclusive'])-millis(sc['start']))//DAY
  receipts.append({'period':sc['period'],'cost':sc['cost'],'mode':sc['mode'],'checked_fill_legs':len(ledger),'checked_days':len(days),'weekly_weight_checks':weights_checks,'equity_cash_quantity_fees_slippage_alignment_boundaries':'PASS'})
 out={'independent_from_engine':True,'all_pass':True,'scenarios':receipts,'protocol_sha256':h(B/'protocol.json'),'results_sha256':h(B/'results.json'),'validator_sha256':h(pathlib.Path(__file__)),'network_calls':0}
 (B/'independent_validation.json').write_text(json.dumps(out,indent=2));print('PASS:',len(receipts),'scenarios; cash/holdings/fees/slip/weights/causal timing/period boundaries')
if __name__=='__main__':run()
