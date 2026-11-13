"""Different implementation cash/quote auditor, not an independent strategy replay."""
from pathlib import Path
import csv,json,hashlib,datetime,argparse
B=Path(__file__).resolve().parent
def near(a,b):assert abs(float(a)-float(b))<1e-7*max(1,abs(float(a)),abs(float(b))),(a,b)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def run(prefix,auditname,freezename):
 freeze=json.loads((B/freezename).read_text());assert sha(B/auditname)==freeze['sha256']
 audit=json.loads((B/auditname).read_text());assert sha(B/'raw/EURUSD_202609_provider_response.bin')==audit['source_zip_sha256']
 outputs=[]
 for commission in [0,7]:
  d=B/(prefix+str(commission));events=list(csv.DictReader((d/'ledger.csv').open()));daily=list(csv.DictReader((d/'equity.csv').open()));summary=json.loads((d/'results.json').read_text())
  runtime=json.loads((d/'runtime_receipt.json').read_text());assert runtime['source_sha256_before']==runtime['source_sha256_after'];assert runtime['input_sha256']==audit['input']['sha256']
  known={e['timestamp']:set() for e in events if e['event'] in ['OPEN','CLOSE']}
  with Path(audit['input']['path']).open() as f:
   for r in csv.DictReader(f):
    if r['timestamp'] in known:known[r['timestamp']].add((float(r['bid']),float(r['ask'])))
  cash=500.;position=None;closed=0;fees=0
  for e in events:
   t=datetime.datetime.fromisoformat(e['timestamp']);start=datetime.datetime.fromisoformat(audit['period_UTC'][0].replace('Z','+00:00'));end=datetime.datetime.fromisoformat(audit['period_UTC'][1].replace('Z','+00:00'));assert start<=t<end
   if e['event']=='PENDING':
    assert t.hour>=3 and t.hour<13;assert position is None
    assert float(e['entry'])>float(e['latest_price']) if int(e['side'])==1 else float(e['entry'])<float(e['latest_price'])
    continue
   bid=float(e['bid']);ask=float(e['ask']);assert (bid,ask) in known[e['timestamp']]
   near(e['cash_before'],cash);lot=float(e['lot']);assert lot==.1;fee=lot*commission/2;near(e['fee'],fee);fees+=fee;side=int(e['side'])
   if e['event']=='OPEN':
    assert position is None;px=ask if side==1 else bid;near(e['price'],px);margin=lot*100000*px/100;near(e['margin'],margin);assert cash-fee>=margin
    near(e['planned_SL_risk_USD'],abs(px-float(e['sl']))*lot*100000);near(e['planned_SL_risk_pct_of_balance'],abs(px-float(e['sl']))*lot*100000/cash*100)
    position={'side':side,'entry':px,'lot':lot,'sl':float(e['sl']),'tp':float(e['tp']),'margin':margin};cash-=fee
   else:
    assert position and side==position['side'];px=float(e['price'])
    if e['reason']=='TP_LIMIT':near(px,position['tp']);assert bid>=px if side==1 else ask<=px
    else:near(px,bid if side==1 else ask)
    if e['reason'].startswith('SL_GAP'):assert bid<=position['sl'] if side==1 else ask>=position['sl']
    if e['reason']=='SOURCE_TIME_EXIT':assert t.hour>=13
    pnl=side*(px-position['entry'])*lot*100000;near(e['pnl'],pnl);near(e['entry'],position['entry']);cash+=pnl-fee;position=None;closed+=1
   near(e['cash_after'],cash)
  near(summary['research_marked_metrics']['cash'],cash);near(summary['research_marked_metrics']['commission_USD'],fees);assert closed==summary['research_marked_metrics']['closed_trades'];assert position is None
  # Reconstruct sampled equity from actual fills; compare every saved minute.
  trade=[e for e in events if e['event'] in ['OPEN','CLOSE']];cursor=0;cash2=500.;q=None
  for r in daily:
   while cursor<len(trade) and trade[cursor]['timestamp']<=r['timestamp']:
    e=trade[cursor];cash2=float(e['cash_after']);q=e if e['event']=='OPEN' else None;cursor+=1
   near(r['cash'],cash2);near(r['equity'],float(r['cash'])+float(r['floating_pnl']));near(r['free_margin'],float(r['equity'])-float(r['margin']))
   if q:near(r['margin'],q['margin'])
   else:near(r['floating_pnl'],0);near(r['margin'],0)
  outputs.append({'commission_roundtrip_perlot':commission,'trade_count':closed,'fees_USD':fees,'cash':cash,'ledger_sha256':sha(d/'ledger.csv'),'results_sha256':sha(d/'results.json'),'quote_fee_cash_margin_risk_equity_checks':'PASS','sampled_equity_rows':len(daily)})
 result={'status':'PASS','audit_type':'sameOwner different bookkeeping implementation; not thirdparty or fullstrategy replay','real_data_audit_sha256':sha(B/auditname),'outputs':outputs,'full5day_coverage_pass':audit.get('all_five_sessions_data_pass',False),'full_week_PnL':None if not audit.get('all_five_sessions_data_pass',False) else 'conditional research metrics only'}
 (B/(prefix+'independent_audit.json')).write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--prefix',default='replay_fullscan_commission');p.add_argument('--audit',default='real_data_audit_fullscan.json');p.add_argument('--freeze',default='dataaudit_fullscan_freeze.json');a=p.parse_args();run(a.prefix,a.audit,a.freeze)
