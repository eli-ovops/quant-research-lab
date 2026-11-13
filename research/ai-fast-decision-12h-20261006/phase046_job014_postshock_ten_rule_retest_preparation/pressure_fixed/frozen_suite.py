from pathlib import Path
from bisect import bisect_right
from collections import deque
from decimal import Decimal
import json,hashlib
import frozen_execution_v12 as execution
B=Path(__file__).resolve().parent
FAMILIES=('FLOW_IMPULSE','BOOK_STATE','BTC_TRANSMISSION')
def clock_view(row,expected_shared_domain=None,allow_legacy=True):
 if 'os_shared_ns' in row:
  if not isinstance(row['os_shared_ns'],int) or not row.get('clock_domain_id') or row['clock_domain_id']!=expected_shared_domain:return None
  return row['os_shared_ns']/1e6,'OS_SHARED',row['clock_domain_id']
 if allow_legacy and row.get('connection_local_id') and isinstance(row.get('monotonic_ns'),int):return row['monotonic_ns']/1e6,'LEGACY_INTERNAL','legacy-process|'+row['connection_local_id']
 return None
def forward_eligible(row,freeze):
 return row.get('clock_domain_id')==freeze['clock_domain_id'] and isinstance(row.get('os_shared_ns'),int) and row['os_shared_ns']>=freeze['forward_cut_OS_shared_ns'] and row.get('run_id')==freeze['capture_run_id']
def impulse_ok(f):return bool(f and abs(f['flow_imbalance'])>=.8 and abs(f['impulse_bps'])>=3 and f['flow_imbalance']*f['impulse_bps']>0)
def book_predicate(f):
 if not f:return None
 current,ref=f['book'],f['reference']
 if min(len(current['asks']),len(current['bids']),len(ref['asks']),len(ref['bids']))<3:return None
 if [x[0] for x in current['asks'][:3]]!=[x[0] for x in ref['asks'][:3]] or [x[0] for x in current['bids'][:3]]!=[x[0] for x in ref['bids'][:3]]:return None
 unit=f['unit'];bid=sum(p*q*unit for p,q in current['bids'][:3]);ask=sum(p*q*unit for p,q in current['asks'][:3]);imb=float((bid-ask)/(bid+ask)) if bid+ask else 0;side=1 if imb>0 else -1 if imb<0 else 0
 nowopp=ask if side==1 else bid;refopp=sum(p*q*unit for p,q in (ref['asks'] if side==1 else ref['bids'])[:3]);ratio=float(nowopp/refopp) if refopp else None
 if abs(imb)<.8 or ratio is None or ratio>.5 or abs(f['flow_imbalance'])<.5 or f['flow_imbalance']*side<=0 or abs(f['impulse_bps'])>1:return None
 return {'direction':side,'top3_imbalance':imb,'opposing_depth_ratio':ratio,'visible_depth_decrease_not_cancel_or_intent':True}
def leader_predicate(leader,follower):
 if not impulse_ok(leader) or not follower or leader['connectionId']!=follower['connectionId'] or leader['clock_domain_id']!=follower['clock_domain_id']:return None
 gap=leader['impulse_bps']-follower['impulse_bps']
 if abs(gap)<2 or gap*leader['impulse_bps']<=0 or abs(follower['impulse_bps'])>1:return None
 return {'direction':1 if gap>0 else -1,'leader':'BTC-USDT-SWAP','beta':1,'leader_impulse_bps':leader['impulse_bps'],'leader_flow_imbalance':leader['flow_imbalance'],'follower_impulse_bps':follower['impulse_bps'],'leader_gap_bps':gap,'self_momentum_baseline_direction':1 if follower['impulse_bps']>0 else -1 if follower['impulse_bps']<0 else 0,'not_arbitrage_or_true_lead':True}
class Features:
 def __init__(self,specs,expected_shared_domain=None):
  self.specs=specs;self.expected=expected_shared_domain;self.states={a:{'books':[],'times':[],'flow':deque(),'firsttrade':None,'latest':None,'conn':None,'domain':None,'seen_trades':{},'flow_unknown':False} for a in specs};self.last=None;self.counters={'invalid_clock':0,'invalid_book':0,'exact_trade_repeats':0,'trade_identity_conflicts':0,'missing_trade_id':0}
 def ingest(self,row):
  a=row['instId']
  if a not in self.states:return None
  view=clock_view(row,self.expected)
  if view is None:self.counters['invalid_clock']+=1;return None
  now,mode,domain=view
  if self.last and self.last[0]==domain and now<self.last[1]:self.counters['invalid_clock']+=1;return None
  self.last=(domain,now);s=self.states[a];conn=row['connectionId']
  if s['conn']!=conn or s['domain']!=domain:s.update(books=[],times=[],flow=deque(),firsttrade=None,latest=None,conn=conn,domain=domain,seen_trades={},flow_unknown=False)
  o=json.loads(row['raw']);records=o.get('data',[])
  if not records:return None
  unit=Decimal(self.specs[a]['ctVal'])*Decimal(self.specs[a]['ctMult'])
  if row['channel']=='books5':
   for d in records:
    valid=execution.valid_book(d)
    if valid is None:s['latest']=None;self.counters['invalid_book']+=1;continue
    asks,bids=valid;book={'time':now,'ordinal':row['local_ordinal'],'wall_ms':row['receive_wall_ms'],'conn':conn,'asks':asks,'bids':bids,'mid':float((asks[0][0]+bids[0][0])/2),'clock_domain_id':domain,'source_os_shared_ns':row.get('os_shared_ns')}
    s['books'].append(book);s['times'].append(now);s['latest']=book
  elif row['channel']=='trades':
   if s['firsttrade'] is None:s['firsttrade']=now
   for d in records:
    if d.get('tradeId') is None:self.counters['missing_trade_id']+=1;s['flow_unknown']=True;continue
    identity=(d['tradeId'],d.get('source'));signature=(d.get('px'),d.get('sz'),d.get('side'),d.get('ts'),d.get('count'))
    if identity in s['seen_trades']:
     if s['seen_trades'][identity]==signature:self.counters['exact_trade_repeats']+=1
     else:self.counters['trade_identity_conflicts']+=1;s['flow_unknown']=True
     continue
    s['seen_trades'][identity]=signature
    amount=Decimal(d['px'])*Decimal(d['sz'])*unit;s['flow'].append((now,float(amount)*(1 if d['side']=='buy' else -1),float(amount),row['local_ordinal']))
  else:return None
  return a,now,mode,domain,conn
 def feature(self,a,now,lookback_ms,conn,domain):
  s=self.states[a]
  if self.last and self.last[0]==domain and now<self.last[1]:return None
  if s['conn']!=conn or s['domain']!=domain or s['flow_unknown'] or s['firsttrade'] is None or s['firsttrade']>now-1000:return None
  while s['flow'] and s['flow'][0][0]<=now-1000:s['flow'].popleft()
  i=bisect_right(s['times'],now-lookback_ms)-1;book=s['latest']
  if i<0 or not book or not 0<=now-book['time']<=250 or now-lookback_ms-s['books'][i]['time']>250:return None
  ref=s['books'][i];total=sum(x[2] for x in s['flow']);net=sum(x[1] for x in s['flow']);imb=net/total if total else 0;imp=(book['mid']/ref['mid']-1)*10000
  return {'book':book,'reference':ref,'flow_imbalance':imb,'flow_total_USDT':total,'flow_net_USDT':net,'impulse_bps':imp,'quote_age_ms':now-book['time'],'unit':Decimal(self.specs[a]['ctVal'])*Decimal(self.specs[a]['ctMult']),'connectionId':conn,'clock_domain_id':domain}
def run_signals(rows,specs,expected_shared_domain=None):
 features=Features(specs,expected_shared_domain);events=[];cool={};reject={'cooldown':0};last_scope=None
 for row in rows:
  result=features.ingest(row)
  if result is None:continue
  a,now,mode,domain,conn=result
  if last_scope!=(domain,conn):cool={};last_scope=(domain,conn)
  one=features.feature(a,now,1000,conn,domain);half=features.feature(a,now,500,conn,domain);candidate=[]
  if impulse_ok(one):candidate.append(('FLOW_IMPULSE',one,{'direction':1 if one['flow_net_USDT']>0 else -1}))
  bp=book_predicate(half)
  if bp:candidate.append(('BOOK_STATE',half,bp))
  if a in ('ETH-USDT-SWAP','SOL-USDT-SWAP'):
   leader=features.feature('BTC-USDT-SWAP',now,1000,conn,domain);lp=leader_predicate(leader,one)
   if lp:candidate.append(('BTC_TRANSMISSION',one,lp))
  for family,f,extra in candidate:
   key=(family,a)
   if now-cool.get(key,-1e99)<35000:reject['cooldown']+=1;continue
   cool[key]=now;events.append({'event_id':len(events)+1,'family':family,'asset':a,'asof_ms':now,'asof_wall_ms':row['receive_wall_ms'],'asof_ordinal':row['local_ordinal'],'connectionId':conn,'clock_view':mode,'clock_domain_id':domain,'source_asof_shared_ns':row.get('os_shared_ns'),'source_receive_wall_ns':row.get('receive_wall_ns'),'impulse_bps':f['impulse_bps'],'imbalance':f['flow_imbalance'],'flow_total_USDT':f['flow_total_USDT'],'flow_net_USDT':f['flow_net_USDT'],'quote_age_ms':f['quote_age_ms'],'latest_book_ordinal':f['book']['ordinal'],'reference_book_ordinal':f['reference']['ordinal'],'reference_book_time':f['reference']['time'],'latest_book_time':f['book']['time'],'WAIT_event_delta':0,**extra})
 return events,features.states,{**features.counters,**reject}
def compact_state(e,states,specs,is_live=False,feature_completed_shared_ns=None):
 book=next(x for x in states[e['asset']]['books'] if x['ordinal']==e['latest_book_ordinal'])
 return {'state_version':'stateV2','question_version':'impulse_suite_action_v2','family':e['family'],'asset':e['asset'],'asof_ordinal':e['asof_ordinal'],'asof_receive_ms':e['asof_ms'],'clock_view':e['clock_view'],'clock_domain_id':e['clock_domain_id'],'source_asof_shared_ns':e['source_asof_shared_ns'],'source_latest_book_shared_ns':book['source_os_shared_ns'],'feature_completed_shared_ns':feature_completed_shared_ns,'is_live':is_live,'connectionId':e['connectionId'],'quote_age_ms':e['quote_age_ms'],'direction':e['direction'],'impulse_bps':e['impulse_bps'],'flow_imbalance':e['imbalance'],'top3_imbalance':e.get('top3_imbalance'),'opposing_depth_ratio':e.get('opposing_depth_ratio'),'leader_gap_bps':e.get('leader_gap_bps'),'leader_impulse_bps':e.get('leader_impulse_bps'),'self_momentum_baseline_direction':e.get('self_momentum_baseline_direction'),'asks_contracts':[[str(p),str(q)] for p,q in book['asks']],'bids_contracts':[[str(p),str(q)] for p,q in book['bids']],'contract_spec':specs[e['asset']],'fee_each_side_bps_assumptions':[5,10],'allowed_actions':['WAIT','FOLLOW','FADE'],'provider_adapter':'NOT_IMPLEMENTED','confidence_not_provided':True}
def live_input_gate(state,send_shared_ns,expected_domain):
 reasons=[]
 if not state.get('is_live'):reasons.append('HISTORICAL_BENCHMARK_ONLY')
 if state.get('clock_view')!='OS_SHARED' or state.get('clock_domain_id')!=expected_domain:reasons.append('CLOCK_NAMESPACE_MISMATCH')
 try:
  a,b,f=state['source_asof_shared_ns'],state['source_latest_book_shared_ns'],state['feature_completed_shared_ns']
  if any(isinstance(v,bool) or not isinstance(v,int) for v in [a,b,f,send_shared_ns]):raise ValueError()
  if not b<=a<=f<=send_shared_ns:reasons.append('INPUT_CAUSAL_ORDER')
  if not 0<=send_shared_ns-a<=250000000 or not 0<=send_shared_ns-b<=250000000:reasons.append('INPUT_TTL_EXPIRED')
 except (KeyError,TypeError,ValueError):reasons.append('SHARED_SOURCE_FIELDS_MISSING')
 return {'may_send_live_state':not reasons,'on_failure':'WAIT','reasons':reasons,'not_actual_provider_or_risk_validation':True}
def main():
 p=json.loads((B/'protocol.json').read_text());freeze=json.loads((B/'execution_freeze.json').read_text())
 for n,h in freeze['hashes'].items():assert hashlib.sha256((B/n).read_bytes()).hexdigest()==h
 source=Path(p['dev_source']['path']);blob=source.read_bytes();assert hashlib.sha256(blob).hexdigest()==p['dev_source']['sha256'];rows=[json.loads(x) for x in blob.splitlines()];specs={x['instId']:x for x in json.loads((B/'instruments.json').read_text())};events,states,counters=run_signals(rows,specs,freeze['clock_domain_id']);out=execution.outcomes(events,states,specs);mapping={e['event_id']:e for e in events}
 for r in out:r['family']=mapping[r['event_id']]['family'];r['cohort']='OLD001_DEVELOPMENT_NOT_FORWARD'
 (B/'dev_events.json').write_text(json.dumps(events,indent=2));(B/'dev_event_deltas.json').write_text(json.dumps(out,indent=2));(B/'dev_compact_states_v2.json').write_text(json.dumps([compact_state(e,states,specs) for e in events],indent=2));(B/'results.json').write_text(json.dumps({'status':'PREPARED_AND_DEVELOPMENT_ONLY','events':{f:sum(e['family']==f for e in events) for f in FAMILIES},'counters':counters,'observed_outcome_rows':sum(r['status']=='observed' for r in out),'censored_outcome_rows':sum(r['status']!='observed' for r in out),'future_cut':freeze['forward_cut_utc'],'006_evaluation':'NOT_RUN','model_calls':0,'not_account_PnL':True},indent=2));print({'events':{f:sum(e['family']==f for e in events) for f in FAMILIES},'outcome_rows':len(out)})
if __name__=='__main__':main()
