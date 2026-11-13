"""Read-only reconciliation of all completed retained batch evidence."""
import pathlib,json,gzip,hashlib,math,statistics
R=pathlib.Path(__file__).resolve().parent
checks=[]
for b in sorted(R.glob('batch[1-9]')):
 if not (b/'results.json').exists():continue
 p=json.loads((b/'protocol.json').read_text());result=json.loads((b/'results.json').read_text());total=0
 assert all(hashlib.sha256(pathlib.Path(k).read_bytes()).hexdigest()==v for k,v in p['source_hashes'].items())
 for c in p['configs']:
  ledger=b/(c['id']+'.jsonl.gz');stats=result['results'][c['id']];returns=[];targets=zeros=0
  for line in gzip.open(ledger,'rt'):
   r=json.loads(line);m=r['metrics'];assert m['status'] in ('VALID','NO_TRADE')
   cash=500.;fees=funding=0.;base=contracts=0.
   for e in r['events']:
    cash+=e['cash_delta'];base+=e['base_delta'];contracts+=e['contract_delta']
    assert math.isclose(cash,e['cash_after'],abs_tol=1e-6)
    assert math.isclose(base,e['base_after'],abs_tol=1e-6)
    assert math.isclose(contracts,e['contracts_after'],abs_tol=1e-6)
    fees+=e.get('fee',0)
    if e['type']=='FUNDING':funding+=e['cash_delta']
   assert abs(base)<1e-6 and abs(contracts)<1e-6
   assert math.isclose(cash,m['final_equity'],abs_tol=1e-6)
   assert math.isclose(fees,m['fees'],abs_tol=1e-6) and math.isclose(funding,m['funding'],abs_tol=1e-6)
   assert math.isclose(sum(m['trade_pnls']),cash-500,abs_tol=1e-6)
   returns.append(m['return']);targets+=bool(m['target_hit']);zeros+=cash<=0
  assert len(returns)==stats['evaluated']==240
  assert targets==stats['targets'] and zeros==stats['zeros']
  assert abs(statistics.mean(returns)-stats['mean_return'])<1e-12
  total+=len(returns)
 assert total==result['independent_audits']
 checks.append({'batch':b.name,'configs':len(p['configs']),'accounts':total,'status':'PASS'})
out={'status':'PASS','batches':checks,'accounts':sum(x['accounts'] for x in checks),'configs':sum(x['configs'] for x in checks),'scope':'hashes, event cash/base/contracts, fees, funding, trade pnl, terminal account and aggregate counts; not independent real execution validation'}
(R/'reconciliation.json').write_text(json.dumps(out,indent=2));print(json.dumps(out))
