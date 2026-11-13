import json,pathlib,datetime,collections,hashlib,statistics
P=pathlib.Path(__file__).resolve().parent
PROTOCOL=json.loads((P/'protocol.json').read_text())
END=1791244800000
START=END-30*86400000
ORDER=PROTOCOL['universe']
def utc(t):return datetime.datetime.fromtimestamp(t/1000,datetime.timezone.utc).isoformat()
def envelope(r):
    r=r.get('response',r)
    if 'error' in r:return {'ok':False,'error':r['error']}
    return r.get('structuredContent') or json.loads(next(x['text'] for x in r['content'] if x['type']=='text'))
def rows(file):
    d=envelope(json.loads((P/'raw'/file).read_text()))
    assert d['ok'],d
    return d['data']['data']
exist={x['symbol']:x['instrument'] for x in json.loads((P/'contract-existence.json').read_text())}
summary={};history={};eligible=[]
for b in ORDER:
    if not exist[b]:summary[b]={'status':'MISSING_CONTRACT','n':0};continue
    raw=rows(b+'_funding.json')
    unique={int(x['fundingTime']):x for x in raw}
    f=sorted([x for t,x in unique.items() if START<=t<END],key=lambda x:int(x['fundingTime']))
    history[b]=f
    intervals=[(int(y['fundingTime'])-int(x['fundingTime']))/3600000 for x,y in zip(f,f[1:])]
    changes=[{'at_utc':utc(int(f[i+1]['fundingTime'])),'previous_observed_hours':intervals[i-1],'new_observed_hours':intervals[i],'policy_change_verified':False} for i in range(1,len(intervals)) if intervals[i]!=intervals[i-1]]
    high=[x for x in f if abs(float(x['realizedRate']))>=.001]
    maxrow=max(f,key=lambda x:abs(float(x['realizedRate']))) if f else None
    summary[b]={'status':'DATA_OBSERVED','raw_n':len(raw),'n':len(f),'oldest_utc':utc(int(f[0]['fundingTime'])) if f else None,'newest_utc':utc(int(f[-1]['fundingTime'])) if f else None,'observed_span_days':(int(f[-1]['fundingTime'])-int(f[0]['fundingTime']))/86400000 if len(f)>1 else 0,'first_record_delay_from_start_hours':(int(f[0]['fundingTime'])-START)/3600000 if f else None,'thirty_day_coverage':'truncated_by_100_record_cap' if len(raw)==100 and f and int(f[0]['fundingTime'])>START+8*3600000 else 'bounded_page_covers_start_schedule_or_no_evidence_of_truncation','extreme_n':len(high),'max_abs_realized_bps':abs(float(maxrow['realizedRate']))*10000 if maxrow else None,'max_abs_event':maxrow,'signed_min_bps':min(float(x['realizedRate']) for x in f)*10000 if f else None,'signed_max_bps':max(float(x['realizedRate']) for x in f)*10000 if f else None,'observed_interval_counts_hours':dict(collections.Counter(intervals)),'observed_interval_changes':changes,'extreme_events':high,'policy_change_inference':'NOT_VERIFIED; adjacent actual interval differs from announced/default schedule'}
    if {int(x['fundingTime']) for x in f}==set(range(START,END,8*3600000)):
        summary[b]['thirty_day_coverage']='DATA_GRID_COMPLETE'
    for prev,nxt in zip(f,f[1:]):
        t=int(nxt['fundingTime']);tp=int(prev['fundingTime'])
        if abs(float(prev['realizedRate']))<.001:continue
        if tp>=t-30*60000:continue
        direction=-1 if float(prev['realizedRate'])>0 else 1
        eligible.append({'symbol':b,'prior_settlement_time':tp,'prior_settlement_utc':utc(tp),'prior_realized_bps':float(prev['realizedRate'])*10000,'next_actual_settlement_time':t,'next_actual_settlement_utc':utc(t),'direction':direction,'next_realized_bps_diagnostic_only':float(nxt['realizedRate'])*10000})
eligible.sort(key=lambda e:(e['next_actual_settlement_time'],ORDER.index(e['symbol'])))
selected=eligible[:6]
for i,e in enumerate(selected):
    e['id']=f'event_{i+1:02d}'
    b=e['symbol'];t=e['next_actual_settlement_time']
    candidate=[]
    for prev,nxt in zip(history[b],history[b][1:]):
        q=int(nxt['fundingTime'])
        if q>=t or q%86400000!=t%86400000 or abs(float(prev['realizedRate']))>=.001:continue
        candidate.append((q,prev,nxt))
    if candidate:
        q,prev,nxt=max(candidate,key=lambda x:x[0])
        e['control']={'next_actual_settlement_time':q,'utc':utc(q),'prior_realized_bps':float(prev['realizedRate'])*10000,'direction':e['direction'],'selection':'nearest earlier same UTC clock, non-high previous settled rate; direction matched to high event'}
    else:e['control']=None
total=sum(x['n'] for x in summary.values());nhigh=sum(x.get('extreme_n',0) for x in summary.values())
maximum=max(((x.get('max_abs_realized_bps') or -1,b,x.get('max_abs_event')) for b,x in summary.items()),key=lambda z:z[0])
result={'protocol':PROTOCOL,'contract_existence_current_only':{b:exist[b]['state'] if exist[b] else 'MISSING' for b in ORDER},'stage1':{'status':'OBSERVED_FIXED_UNIVERSE','total_settlements':total,'total_extreme_abs_ge10bps':nhigh,'global_max_abs_realized_bps':maximum[0],'global_max_symbol':maximum[1],'global_max_event':maximum[2],'per_symbol':summary,'eligible_prior_high_pairs':len(eligible),'next_settlement_selection_not_based_on_next_rate':True},'stage2':{'status':'NOT_STARTED' if selected else 'NO_PRIOR_HIGH_TRIGGER_IN_OBSERVED_SAMPLE','selected_by_frozen_rule':selected,'event_results':[],'account_pnl':'NOT_COMPUTED','cash_ownership':'UNKNOWN','known_schedule_archive':'UNKNOWN; actual next-settlement timestamp retrospectively available','causal_or_significance_claim':'NOT_MADE'}}
result['budget']={'explicit_public_calls':1+sum(bool(exist[b]) for b in ORDER)+sum(1 for f in (P/'raw').glob('event_*.json')),'authorized_explicit_public_calls':40,'internal_http_retries':'UNKNOWN','hard_limit_minutes':20}
result['stage1']['observed_interval_pairs']=sum(sum(s.get('observed_interval_counts_hours',{}).values()) for s in summary.values())
result['stage1']['observed_interval_change_count']=sum(len(s.get('observed_interval_changes',[])) for s in summary.values())
# Price results are optional; never condition selection on them.
for e in selected:
    r=e.copy();t=e['next_actual_settlement_time'];side=e['direction'];fn=e['id']+'_asset.json'
    if not (P/'raw'/fn).exists():continue
    def price(file,q):
        c={int(x[0]):x for x in rows(file)}
        needed=[q-31*60000,q-30*60000,q+30*60000]
        if any(z not in c for z in needed):return {'status':'MISSING_REQUIRED_PRICES','missing_utc':[utc(z) for z in needed if z not in c]}
        if c[q-31*60000][-1]!='1':return {'status':'ENTRY_PRECEDING_BAR_NOT_CLOSED'}
        ret=float(c[q+30*60000][1])/float(c[q-30*60000][1])-1
        return {'status':'PRICE_EVENT_ONLY','raw_candles':len(c),'entry_price_open':float(c[q-30*60000][1]),'entry_preceding_closed_close':float(c[q-31*60000][4]),'exit_price_open':float(c[q+30*60000][1]),'raw_asset_return_bps':ret*10000,'directional_gross_bps':ret*side*10000,'minus_cost_sensitivity_bps':{str(cost):ret*side*10000-cost for cost in [12,20,40]},'execution_fill_verified':False}
    r['price']=price(fn,t)
    if e['control'] and (P/'raw'/(e['id']+'_control.json')).exists():r['control_price']=price(e['id']+'_control.json',e['control']['next_actual_settlement_time'])
    else:r['control_price']={'status':'MISSING_CONTROL'}
    if (P/'raw'/(e['id']+'_btc.json')).exists():r['btc_price']=price(e['id']+'_btc.json',t)
    else:r['btc_price']={'status':'MISSING_BTC_COMPARISON'}
    if r['price']['status']=='PRICE_EVENT_ONLY' and r['control_price']['status']=='PRICE_EVENT_ONLY':r['high_minus_control_directional_bps']=r['price']['directional_gross_bps']-r['control_price']['directional_gross_bps']
    if r['price']['status']=='PRICE_EVENT_ONLY' and r['btc_price']['status']=='PRICE_EVENT_ONLY':r['asset_minus_btc_same_direction_bps']=r['price']['directional_gross_bps']-r['btc_price']['directional_gross_bps']
    result['stage2']['event_results'].append(r)
if result['stage2']['event_results']:result['stage2']['status']='PRICE_EVENTS_ONLY_NOT_ACCOUNT_BACKTEST'
valid=[e['price']['directional_gross_bps'] for e in result['stage2']['event_results'] if e['price']['status']=='PRICE_EVENT_ONLY']
result['stage2']['summary']={'valid_price_events':len(valid),'mean_directional_gross_bps':statistics.mean(valid) if valid else None,'mean_minus_cost_bps':{str(cost):statistics.mean(valid)-cost for cost in [12,20,40]} if valid else None,'sample_sufficient_for_significance':False}
(P/'selection.json').write_text(json.dumps(selected,indent=2)+'\n')
(P/'results.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'stage1_n':total,'high_n':nhigh,'max_bps':maximum[:2],'per_symbol':{b:{k:x.get(k) for k in ['n','extreme_n','max_abs_realized_bps','observed_interval_counts_hours','thirty_day_coverage']} for b,x in summary.items()},'selected':selected,'stage2_summary':result['stage2']['summary']},indent=2))
