from pathlib import Path
import json
from orchestrator import *
from test_orchestrator import state,response,book,BASE
P=Path(__file__).resolve().parent
def main():
 runs=[]
 for fee in [5,10]:
  e=Experiment(fixture=True,fee_each_bps=fee)
  for i,candidate in enumerate(CANDIDATES):
   n=BASE+i*20000000000;s=state(i*10+1,n,candidate);id=e.submit(s,n+2000000);e.book(book(n+10000000,i*10+2));e.fixture_response(id,response(),n+100000000,api_cost_quote=.01);e.book(book(n+120000000,i*10+3));e.book(book(n+[REDACTED_PHONE],i*10+4,101))
  e.end();runs.append({'fee_each_bps':fee,'kind':'SYNTHETIC_NOT_MODEL_RUN','actual_api_calls':0,'ledger':e.ledger,'paper_proxy_cash':{str(k):str(v) for k,v in e.cash.items()},'complete_real_netvalue':False})
 (P/'dry_run_ledger_SYNTHETIC_NOT_MODEL_RUN.json').write_text(json.dumps(runs,indent=2)+'\n')
 print(json.dumps({'status':'OFFLINE_CONTRACT_DRYRUN_ONLY','fee_scenarios':2,'candidates':3,'arms':len(ARMS),'actualJevAPI':0,'no_real_latency_profit_or_forwardvalidation':True}))
if __name__=='__main__':main()
