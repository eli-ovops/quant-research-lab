from pathlib import Path
from collections import Counter,defaultdict
from decimal import Decimal
import json,gzip,hashlib,subprocess
from pressure_rules_rolling import PressureRules
from frozen_summary import pressure_summaries
import frozen_execution_v12 as core
from source_metadata import terminal_metadata
B=Path(__file__).resolve().parent
def require_run(protocol):
 if protocol.get('mode')!='AUTHORIZED_CLOSED_REPLICATION':raise RuntimeError('PREPARE_ONLY_NO_RAW_REPLICATION_RUN')
def load_raw(protocol):
 directory=Path(protocol['source']);final=json.loads((directory/'collector_final.json').read_text());identity=json.loads((directory/'collector_identity.json').read_text());ps=subprocess.run(['ps','-p',str(identity['pid']),'-o','pid=,command='],capture_output=True,text=True)
 if final['status']!='STOPPED' or ps.returncode!=1 or ps.stdout.strip() or ps.stderr.strip() or identity['run_id']!=protocol['expected_run'] or identity['clock_domain_id']!=protocol['expected_domain']:raise ValueError('SOURCE_NOT_TERMINAL_OR_PS_UNKNOWN')
 rows=[];h=hashlib.sha256();logical=0;last=-1;frames=Counter();data=Counter()
 with gzip.open(directory/'raw/ws_messages.jsonl.gz','rb') as raw:
  for line in raw:
   h.update(line);logical+=len(line);r=json.loads(line)
   if any(not isinstance(r.get(k),int) or isinstance(r[k],bool) for k in ['local_ordinal','os_shared_ns','receive_wall_ns']) or r['local_ordinal']!=len(rows)+1 or r['os_shared_ns']<last or any(r[k]!=identity[k] for k in ['run_id','clock_domain_id','boot_identity']) or r['connectionId']!=final['connectionId']:raise ValueError('RAW_IDENTITY_TYPE_ORDER')
   last=r['os_shared_ns'];o=json.loads(r['raw']) if r['raw']!='pong' else {}
   if not isinstance(o,dict) or not isinstance(o.get('arg',{}),dict) or o.get('arg',{}).get('instId')!=r['instId'] or o.get('arg',{}).get('channel')!=r['channel']:raise ValueError('RAW_ARG')
   if r['channel']:frames[r['channel']+'|'+r['instId']]+=1
   if o.get('data'):data[r['channel']+'|'+r['instId']]+=1
   rows.append(r)
 if len(rows)!=final['messages'] or logical!=final['logical_JSONL_bytes'] or dict(frames)!=final['channel_counts'] or len(data)!=18 or h.hexdigest()!=protocol['source_raw_sha256']:raise ValueError('RAW_COUNTS_HASH_CHANNELS')
 return rows,{'status':'CLOSED_RAW_ONLY_SOURCE_CONDITIONAL','rows':len(rows),'logical_bytes':logical,'raw_sha256':h.hexdigest(),'CRC_EOF':True,'actual18data':dict(data),'error':final.get('error'),'telemetry':'NOT_APPLICABLE rawonly notfailure','full_market_completeness':'UNKNOWN','terminal_metadata':terminal_metadata(identity,final,rows[0]['os_shared_ns'],rows[-1]['os_shared_ns'])}
def main():
 p=json.loads((B/'protocol.json').read_text());require_run(p);f=json.loads((B/'execution_freeze.json').read_text())
 for n,h in f['hashes'].items():assert hashlib.sha256((B/n).read_bytes()).hexdigest()==h
 rows,receipt=load_raw(p);registry=json.loads((B/'instruments.json').read_text());rules=PressureRules(registry,p['rule_domain'],forward_cut_ns=p['rule_cut_OS_shared_ns']);events=[];states={a:{'books':[],'times':[]} for a in p['assets']};before=0
 for row in rows:
  before+=row['os_shared_ns']<p['rule_cut_OS_shared_ns'];result=rules.ingest(row)
  if result and result['qualified_rule']:events.append({'event_id':len(events)+1,'family':result['qualified_rule'],'direction':result['shock_direction'],'asof_ms':result['source_asof_shared_ns']/1e6,**result})
  if row['instId'] in states and row['channel']=='books5':
   for d in json.loads(row['raw']).get('data',[]):
    valid=core.valid_book(d)
    if valid:
     book={'time':row['os_shared_ns']/1e6,'ordinal':row['local_ordinal'],'conn':row['connectionId'],'asks':valid[0],'bids':valid[1]};states[row['instId']]['books'].append(book);states[row['instId']]['times'].append(book['time'])
 shadows=core.outcomes(events,states,{s['instId']:s for s in registry});emap={e['event_id']:e for e in events}
 for r in shadows:r['family']=emap[r['event_id']]['family'];r['registered_action']=emap[r['event_id']]['action']
 actual=[r for r in shadows if r['action']==r['registered_action']];aa,ss=pressure_summaries(actual,shadows,p['assets']);pairs=defaultdict(dict)
 for r in shadows:pairs[(r['event_id'],r['fee_each_side_bps'],r['delay_ms'],r['hold_seconds'])][r['action']]=r
 pairrows=[]
 for key,pair in pairs.items():
  a,b=pair['FOLLOW'],pair['FADE'];status='UNKNOWN_CENSORED';same=None
  if a['status']=='observed' and b['status']=='observed':same=Decimal(a['contracts'])==Decimal(b['contracts']);status='BOTH_OBSERVED_SAMEQTY' if same else 'BOTH_OBSERVED_QTY_MISMATCH_NOT_STRICTPAIR'
  pairrows.append({'event_id':key[0],'fee_each_side_bps':key[1],'delay_ms':key[2],'hold_seconds':key[3],'status':status,'sameqty':same,'FOLLOW_contracts':a.get('contracts'),'FADE_contracts':b.get('contracts'),'not_bestselection_or_model':True})
 def dump(n,x):(B/n).write_text(json.dumps(x,separators=(',',':')))
 for n,x in [('source_receipt.json',receipt),('pressure_events.json',events),('pressure_shadow_outcomes.json',shadows),('pressure_actual_branch_outcomes.json',actual),('pressure_actual_full_summary.json',aa),('pressure_shadow_full_summary.json',ss),('pressure_shadow_pair_receipts.json',pairrows),('pressure_reject_counters.json',dict(rules.counters))]:dump(n,x)
 dump('results.json',{'status':'CLOSED_FRESH_RAW_ONLY_PRESSURE_REPLICATION','source':receipt,'rulecut_original_OS':p['rule_cut_OS_shared_ns'],'precut_warmonly_rows':before,'events_by_rule_asset':{rule:{a:sum(e['family']==rule and e['asset']==a for e in events) for a in p['assets']} for rule in ['CONTINUATION_FOLLOW_V1','PRESSURE_DECAY_FADE_V1']},'events':len(events),'actualrows':len(actual),'shadowrows':len(shadows),'actualsummary540':len(aa),'shadowsummary1080':len(ss),'actual_AI':None,'provider':'NOT_IMPLEMENTED','telemetry':'notapplicable','no_source_return_sums_or_bestselection':True,'globalgoal':'ACTIVE'})
if __name__=='__main__':main()
