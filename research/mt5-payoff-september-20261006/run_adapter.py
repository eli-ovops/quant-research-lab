from pathlib import Path
import json,hashlib,datetime as dt
from regime_engine import Arm,Factors,ms,load_ticks,writecsv
B=Path(__file__).resolve().parent;UTC=dt.timezone.utc
def create_accounts():return [Arm(a,c) for a in ['A','C'] for c in ['base','stress']]
def period_rows(ticks,start,end):
 for t,bid,ask in ticks:
  if t<end:yield (t,bid,ask,t>=start)
def main():
 proto=json.loads((B/'protocol.json').read_text());freeze=json.loads((B/'execution_freeze.json').read_text())
 for n,h in freeze['hashes'].items():assert hashlib.sha256((B/n).read_bytes()).hexdigest()==h,n
 audit=json.loads((B/'dataaudit.json').read_text());data=Path(audit['input']['path']);assert hashlib.sha256(data.read_bytes()).hexdigest()==audit['input']['sha256']
 start=ms(proto['period_UTC'][0]);end=ms(proto['period_UTC'][1]);market=Factors();accounts=create_accounts();count=0
 for t,bid,ask,inwindow in period_rows(load_ticks(data,'utc'),start,end):
  ctx,stats=market.ingest(t,bid,ask)
  if not inwindow:continue
  count+=1
  for a in accounts:a.step_factor(ctx,stats)
 results=[]
 for a in accounts:
  a.finish_day();r=a.arm_result(count);r['day_average_10weekdays']=r['trades']/10;r['continuous_account_two_weeks_noreset']=True;folder=B/(a.arm+'_'+a.cost);assert not folder.exists();folder.mkdir();writecsv(folder/'ledger.csv',a.events);writecsv(folder/'equity.csv',a.equity);writecsv(folder/'daily.csv',a.daily);(folder/'diagnostics.json').write_text(json.dumps(a.diagnostics,indent=2));(folder/'results.json').write_text(json.dumps(r,indent=2));results.append(r)
 for n,h in freeze['hashes'].items():assert hashlib.sha256((B/n).read_bytes()).hexdigest()==h,n
 (B/'run_results.json').write_text(json.dumps({'four':results,'trade_source_hashes':proto['source_hashes'],'adapter_sha256':freeze['hashes']['run_adapter.py'],'input_sha256':audit['input']['sha256'],'actual_model':'UNKNOWN','network':0,'finished_utc':dt.datetime.now(UTC).isoformat()},indent=2));print(json.dumps(results,indent=2))
if __name__=='__main__':main()

