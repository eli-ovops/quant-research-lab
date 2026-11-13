from pathlib import Path
import json,hashlib
from fractions import Fraction
from orchestrator import Experiment,CANDIDATES,ARMS
from test_orchestrator import state,response,BASE
p=Path(__file__).resolve().parent
cases=[]
for costs in [(None,'.01'),('.02',None),('.01','.02')]:
 e=Experiment(True)
 for i,cost in enumerate(costs):
  at=BASE+i*20000000000;id=e.submit(state(i*100+1,at),at+2000000);e.fixture_response(id,response('WAIT'),at+100000000,api_cost_quote=cost)
 expected_cash=Fraction(500)-sum((Fraction(x) for x in costs if x is not None),Fraction(0));complete=all(x is not None for x in costs)
 assert e.cash[('FLOW_V1','JEV')]==expected_cash and e.cash_complete[('FLOW_V1','JEV')]==complete
 cases.append({'costs':costs,'cash':str(expected_cash),'complete':complete,'debits':len([r for r in e.ledger if r['status']=='FIXTURE_API_COST_DEBIT'])})
runs=json.loads((p/'dry_run_ledger_SYNTHETIC_NOT_MODEL_RUN.json').read_text());exits=0
for run in runs:
 expected={(c,a):Fraction(500) for c in CANDIDATES for a in ARMS}
 for r in run['ledger']:
  key=(r['candidate'],r['arm'])
  if r['status']=='FIXTURE_API_COST_DEBIT':expected[key]-=Fraction(r['api_cost_quote'])
  if r['status']=='PAPER_EXIT_FIXTURE_ONLY':
   assert Fraction(r['price_fee_delta'])==Fraction(r['gross'])-Fraction(r['fees']);expected[key]+=Fraction(r['price_fee_delta']);exits+=1
 for key,value in expected.items():assert value==Fraction(run['paper_proxy_cash'][str(key)])
inputs=json.loads((p/'input_sources.json').read_text());unchanged={n:hashlib.sha256(Path(v['source']).read_bytes()).hexdigest()==v['sha256'] for n,v in inputs.items()};assert all(unchanged.values())
assert hashlib.sha256((p/'orchestrator.py').read_bytes()).hexdigest()==inputs['orchestrator.py']['sha256']
(p/'audit.json').write_text(json.dumps({'status':'PASS_FINITE_FIXTURE_CASH_ARITHMETIC','cost_sequence_cases':cases,'dry_run_exits_checked':exits,'original_sources_unchanged':unchanged,'business_source_byte_parity':True,'independence':'different arithmetic from same execution Owner, not third party or full real replay','actual_Jev_calls':0},indent=2))
print('PASS',len(cases),exits)
