from bisect import bisect_right
import hashlib
SEED='FAST_AI_CONTROL_V1'
def direction(run,asset,index):return 1 if hashlib.sha256((SEED+run+asset+str(index)).encode()).digest()[0]%2==0 else -1
def own_momentum(event,state):
 books,times=state['books'],state['times'];now=event['asof_ms'];i=bisect_right(times,now)-1
 while i>=0 and books[i]['ordinal']>event['asof_ordinal']:i-=1
 j=bisect_right(times,now-1000)-1
 if i<0 or j<0:return {'status':'UNKNOWN_MISSING_REFERENCE','direction':None}
 current,ref=books[i],books[j]
 if current['conn']!=event['connectionId'] or ref['conn']!=event['connectionId'] or current.get('clock_domain_id')!=event['clock_domain_id'] or ref.get('clock_domain_id')!=event['clock_domain_id']:return {'status':'UNKNOWN_DOMAIN_OR_CONNECTION','direction':None}
 if not 0<=now-current['time']<=250 or not 0<=now-1000-ref['time']<=250:return {'status':'UNKNOWN_STALE_REFERENCE_OR_CURRENT','direction':None}
 impulse=(current['mid']/ref['mid']-1)*10000;sign=1 if impulse>0 else -1 if impulse<0 else 0
 return {'status':'WAIT_TRUE_ZERO' if sign==0 else 'DIRECTION_AVAILABLE','direction':sign,'own_received_1s_impulse_bps':impulse,'own_current_ordinal':current['ordinal'],'own_reference_ordinal':ref['ordinal']}
def grid_candidates(states,run,first_ms,last_ms):
 events=[];rejected=[];index=0;target=first_ms+1000
 while target<=last_ms:
  for asset,state in states.items():
   times,books=state['times'],state['books'];i=bisect_right(times,target)
   if i>=len(books):rejected.append({'asset':asset,'grid_index':index,'grid_target_ms':target,'status':'NO_GRID_BOOK'});continue
   book=books[i]
   if book['time']-target>250:rejected.append({'asset':asset,'grid_index':index,'grid_target_ms':target,'status':'EXPIRED_GRID_BOOK'});continue
   events.append({'event_id':len(events)+1,'asset':asset,'direction':direction(run,asset,index),'grid_index':index,'grid_target_ms':target,'asof_ms':book['time'],'asof_wall_ms':book['wall_ms'],'asof_ordinal':book['ordinal'],'connectionId':book['conn'],'clock_domain_id':book['clock_domain_id'],'baseline':'B_FIXED_TIMEGRID_SEEDED_DIRECTION','not_random_matched_trial':True})
  index+=1;target=first_ms+1000+index*35000
 return events,rejected
