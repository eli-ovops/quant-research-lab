from pathlib import Path
from collections import Counter,defaultdict
from bisect import bisect_right
from decimal import Decimal
import json,gzip,hashlib,math,subprocess
import frozen_suite as suite
import frozen_execution_v12 as execution
B=Path(__file__).resolve().parent
def positive(v):
 try:d=Decimal(str(v));return d.is_finite() and d>0 and math.isfinite(float(d)) and float(d)>0
 except Exception:return False
def guard_row(r,identity,last_ordinal,last_shared,allowed_assets):
 bad=[]
 if not isinstance(r,dict):return ['row_not_object']
 required={'local_ordinal','os_shared_ns','receive_wall_ns','receive_wall_ms','connectionId','clock_domain_id','boot_identity','run_id','channel','instId','raw'}
 if not required.issubset(r):return ['required_outer_fields_missing']
 wall=r['receive_wall_ms']
 if isinstance(wall,bool) or not isinstance(wall,(int,float)) or not math.isfinite(wall):bad.append('invalid_wall_ms')
 elif isinstance(r['receive_wall_ns'],int) and abs(wall-r['receive_wall_ns']/1e6)>.001:bad.append('wall_ms_ns_mismatch')
 for key in ['local_ordinal','os_shared_ns','receive_wall_ns']:
  if isinstance(r.get(key),bool) or not isinstance(r.get(key),int) or not 0<=r[key]<2**63:bad.append('missing_clock_or_ordinal')
 if r.get('local_ordinal')!=last_ordinal+1:bad.append('ordinal_not_contiguous')
 if not isinstance(r.get('os_shared_ns'),int) or r['os_shared_ns']<last_shared:bad.append('shared_clock_backstep')
 for key in ['run_id','clock_domain_id','boot_identity']:
  if r.get(key)!=identity.get(key):bad.append('identity_'+key)
 try:o=json.loads(r['raw'])
 except Exception:
  if r.get('raw')=='pong' and r.get('channel') is None:return bad
  return bad+['unknown_raw_literal']
 if not isinstance(o,dict):return bad+['raw_not_object']
 arg=o.get('arg',{});records=o.get('data',[])
 if not isinstance(arg,dict) or not isinstance(records,list):return bad+['arg_or_records_shape']
 if r.get('channel')!=arg.get('channel') or r.get('instId')!=arg.get('instId'):bad.append('raw_arg_outer_mismatch')
 if o.get('connId') is not None and o['connId']!=r.get('connectionId'):bad.append('raw_connection_mismatch')
 if records:
  if not r.get('connectionId'):bad.append('missing_connection')
  if r.get('instId') not in allowed_assets or r.get('channel') not in ['books5','trades']:bad.append('unknown_data_channel_asset')
  for d in records:
   if not isinstance(d,dict):bad.append('record_not_object');continue
   if d.get('instId') is not None and d['instId']!=r.get('instId'):bad.append('record_asset_mismatch')
   if r.get('channel')=='books5':
    for side in ['asks','bids']:
     lv=d.get(side,[])
     if not isinstance(lv,list):bad.append('book_levels_not_list');continue
     if not lv:bad.append('empty_book')
     for x in lv:
      if not isinstance(x,(list,tuple)) or len(x)<2 or not positive(x[0]) or not positive(x[1]):bad.append('nonpositive_nonfinite_book')
    try:
     if Decimal(d['bids'][0][0])>=Decimal(d['asks'][0][0]):bad.append('crossed_book')
    except Exception:bad.append('malformed_book')
   elif r.get('channel')=='trades':
    if not positive(d.get('px')) or not positive(d.get('sz')):bad.append('nonpositive_nonfinite_trade')
    if d.get('side') not in ['buy','sell'] or d.get('tradeId') is None:bad.append('trade_fields')
 return list(set(bad))
def mature_source(directory,assets,expected_domain=None):
 directory=Path(directory);final_path=directory/'collector_final.json'
 if not final_path.exists():return None,{'status':'NOT_MATURE_LIVE_OR_UNKNOWN','result':None}
 try:final=json.loads(final_path.read_text());identity=json.loads((directory/'collector_identity.json').read_text())
 except Exception:return None,{'status':'MATURITY_RECEIPT_UNREADABLE','result':None}
 if not isinstance(final,dict) or not isinstance(identity,dict):return None,{'status':'MATURITY_RECEIPT_SHAPE','result':None}
 required=['pid','job_id','run_id','clock_domain_id','boot_identity','source_sha256']
 if any(k not in identity or k not in final for k in required):return None,{'status':'MATURITY_RECEIPT_FIELDS_MISSING','result':None}
 if any(final[k]!=identity[k] for k in required):return None,{'status':'MATURITY_RECEIPT_IDENTITY_MISMATCH','result':None}
 if expected_domain is not None and identity['clock_domain_id']!=expected_domain:return None,{'status':'MATURITY_CLOCK_DOMAIN_MISMATCH','result':None}
 if any(isinstance(final.get(k),bool) or not isinstance(final.get(k),int) or final[k]<0 for k in ['messages','logical_JSONL_bytes','gzip_file_bytes']) or not isinstance(identity['pid'],int) or identity['pid']<=0:return None,{'status':'MATURITY_COUNT_OR_PID_SHAPE','result':None}
 try:ps=subprocess.run(['ps','-p',str(identity['pid']),'-o','pid=,command='],capture_output=True,text=True)
 except Exception:return None,{'status':'PS_EXECUTION_UNKNOWN','result':None}
 if ps.returncode not in (0,1) or ps.stderr.strip() or (ps.returncode==0 and not ps.stdout.strip()):return None,{'status':'PS_QUERY_UNKNOWN','result':None}
 if final['status']!='STOPPED' or ps.stdout.strip():return None,{'status':'NOT_TERMINAL','result':None}
 file=directory/'raw/ws_messages.jsonl.gz'
 if final['messages']==0 or not file.exists():return None,{'status':'NO_CAPTURED_DATA','result':None,'terminal_error':final.get('error')}
 segments=[];current=[];scope=None;invalid=[];lastord=0;lastshared=-1;logical=0;sha=hashlib.sha256();rows=0
 with gzip.open(file,'rb') as inp:
  for line in inp:
   logical+=len(line);sha.update(line);rows+=1
   if logical>240000000:raise ValueError('LOGICAL_INPUT_CAP')
   try:r=json.loads(line)
   except Exception:r=None
   bad=guard_row(r,identity,lastord,lastshared,assets)
   if isinstance(r,dict):
    ordinal=r.get('local_ordinal');clock=r.get('os_shared_ns')
    if isinstance(ordinal,int) and not isinstance(ordinal,bool) and lastord<ordinal<2**63:lastord=ordinal
    if isinstance(clock,int) and not isinstance(clock,bool) and lastshared<=clock<2**63:lastshared=clock
   newscope=(r.get('run_id'),r.get('connectionId'),r.get('clock_domain_id')) if isinstance(r,dict) else None
   if bad:
    invalid.append({'row':rows,'ordinal':r.get('local_ordinal') if isinstance(r,dict) else None,'reasons':bad})
    if current:segments.append(current);current=[]
    scope=None;continue
   if scope!=newscope:
    if current:segments.append(current)
    current=[];scope=newscope
   current.append(r)
 if current:segments.append(current)
 if rows!=final['messages'] or logical!=final['logical_JSONL_bytes']:raise ValueError('FINAL_COUNTS_MISMATCH')
 return segments,{'status':'CLOSED_CONDITIONAL_SOURCE' if not invalid else 'CLOSED_SOURCE_WITH_REJECTED_ROWS_NOT_COMPLETE','rows':rows,'logical_bytes':logical,'logical_sha256':sha.hexdigest(),'gzip_sha256':hashlib.sha256(file.read_bytes()).hexdigest(),'segments':len(segments),'invalid_rows':invalid,'terminal_error':final.get('error'),'CRC_EOF_pass':True,'identity':identity,'full_market_completeness':'UNKNOWN'}
def controls_and_matches(rows,specs,domain,targets):
 f=suite.Features(specs,domain);first={};byord={r['local_ordinal']:r for r in rows}
 for r in rows:
  v=f.ingest(r)
  if v is None:continue
  a,now,_,d,c=v
  if a not in ['ETH-USDT-SWAP','SOL-USDT-SWAP']:continue
  own=f.feature(a,now,1000,c,d);lead=f.feature('BTC-USDT-SWAP',now,1000,c,d)
  if not own or not lead or abs(own['impulse_bps'])>1 or suite.leader_predicate(lead,own):continue
  sign=1 if own['impulse_bps']>0 else -1 if own['impulse_bps']<0 else 0;key=(a,r['receive_wall_ns']//1000000000,sign);first.setdefault(key,{'control_id':r['local_ordinal'],'asset':a,'asof_ms':now,'asof_ordinal':r['local_ordinal'],'connectionId':c,'direction':sign,'received_wall_ns':r['receive_wall_ns'],'clock_domain_id':d})
 return select_matches(first,targets,byord)
def select_matches(first,targets,byord):
 matches=[]
 for e in targets:
  if e['family']!='BTC_TRANSMISSION':continue
  sign=e['self_momentum_baseline_direction'];key=(e['asset'],byord[e['asof_ordinal']]['receive_wall_ns']//1000000000,sign);ctrl=first.get(key)
  if ctrl and not(ctrl['asof_ordinal']<e['asof_ordinal'] and ctrl['asof_ms']<e['asof_ms']):ctrl=None
  matches.append({'target_event_id':e['event_id'],'asset':e['asset'],'target_asof_ms':e['asof_ms'],'control':ctrl,'match_status':'MATCHED_DETERMINISTIC_NEIGHBOR' if ctrl else 'UNMATCHED','not_random_or_independent_counterfactual':True})
 counts=Counter(m['control']['control_id'] for m in matches if m['control'])
 for m in matches:m['control_reuse_count']=counts.get(m['control']['control_id'],0) if m['control'] else 0
 return matches
def evaluate(segments,specs,freeze,cohort):
 all_events=[];all_out=[];all_matches=[];nextid=1
 for segid,rows in enumerate(segments):
  events,states,counters=suite.run_signals(rows,specs,freeze['clock_domain_id'])
  for e in events:e['event_id']=nextid;nextid+=1;e['segment_id']=segid;e['cohort']=cohort
  matches=controls_and_matches(rows,specs,freeze['clock_domain_id'],events);out=execution.outcomes(events,states,specs);emap={e['event_id']:e for e in events}
  for r in out:
   r.update(family=emap[r['event_id']]['family'],segment_id=segid,cohort=cohort,economic_financing_net='UNKNOWN')
   if r['status']=='observed':r['break_even_fee_each_side_bps']=r['gross_price_delta_USDT']/(r['entry_notional_USDT']+r['exit_notional_USDT'])*10000
  for m in matches:
   target=emap[m['target_event_id']];ctrl=m['control'];m['control_outcomes']=None;m['self_momentum_same_asof']=None
   for kind,event in [('control_outcomes',ctrl),('self_momentum_same_asof',{**target,'direction':target['self_momentum_baseline_direction']})]:
    if event is None:continue
    if event['direction']==0:m[kind]=[{'status':'WAIT_ZERO_OWN_MOMENTUM','price_fee_delta_USDT':0,'not_unmatched_imputation':True}];continue
    derived={**event,'event_id':target['event_id']};rr=[r for r in execution.outcomes([derived],states,specs) if r['action']=='FOLLOW' and r['delay_ms']==0 and r['hold_seconds']==15];m[kind]=rr
   if ctrl:
    tt=[r for r in out if r['event_id']==target['event_id'] and r['action']=='FOLLOW' and r['delay_ms']==0 and r['hold_seconds']==15];over=[]
    for a in tt:
     for b in m['control_outcomes']:
      if a['status']=='observed' and b['status']=='observed' and a['fee_each_side_bps']==b['fee_each_side_bps']:over.append({'fee_bps':a['fee_each_side_bps'],'holding_overlap_ms':max(0,min(a['exit_received_ms'],b['exit_received_ms'])-max(a['entry_received_ms'],b['entry_received_ms'])),'control_entry_after_leader_asof':b['entry_received_ms']>=target['asof_ms']})
    m['holding_window_overlap']=over;m['control_window_may_cover_later_leader_event']=True
  all_events+=events;all_out+=out;all_matches+=matches
 return all_events,all_out,all_matches
def main():
 proto=json.loads((B/'protocol.json').read_text());original=json.loads((B/'original_suite_freeze.json').read_text());freeze=json.loads((B/'execution_freeze.json').read_text())
 for n,h in freeze['hashes'].items():assert hashlib.sha256((B/n).read_bytes()).hexdigest()==h
 specs={x['instId']:x for x in json.loads((B/'instruments.json').read_text())};segments,source=mature_source(proto['dev_source'],specs,original['clock_domain_id']);assert segments is not None
 if source['invalid_rows']:events,out,matches=[],[],[];source['evaluation_rejected_due_to_invalid_source']=True
 else:events,out,matches=evaluate(segments,specs,original,'JOB002_PRE007_FREEZE_DEVELOPMENT');futuresegments,fr=mature_source(proto['future_source_binding']['directory'],specs,original['clock_domain_id']);future_result=None
 if futuresegments is not None and not fr.get('invalid_rows'):
  binding={**original,'capture_run_id':proto['future_source_binding']['authorized_run_id']};eligible=[e for rows in futuresegments for e in rows if suite.forward_eligible(e,binding)];future_result={'status':'MATURE_AVAILABLE_NOT_EVALUATED_THIS_PREPARATION','eligible_rows':len(eligible),'not_strategy_pass':True}
 (B/'dev_events.json').write_text(json.dumps(events,indent=2));(B/'dev_event_deltas.json').write_text(json.dumps(out,indent=2));(B/'dev_matched_controls.json').write_text(json.dumps(matches,indent=2));(B/'source_guard_receipt.json').write_text(json.dumps(source,indent=2));(B/'future_source_receipt.json').write_text(json.dumps(fr,indent=2));(B/'results.json').write_text(json.dumps({'status':'EVALUATOR_PREPARED_DEV_ONLY','development_event_counts':dict(Counter(e['family'] for e in events)),'development_segments':len(segments),'matched':sum(m['control'] is not None for m in matches),'unmatched':sum(m['control'] is None for m in matches),'future_result':future_result,'FLOW_BOOK_random_control':'NOT_IMPLEMENTED','AI_results':None,'actual_model_calls':0,'not_account_PnL':True},indent=2));print({'dev_events':len(events),'segments':len(segments),'matches':len(matches),'future_result':future_result})
if __name__=='__main__':main()

