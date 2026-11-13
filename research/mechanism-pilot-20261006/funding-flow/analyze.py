import json, pathlib, hashlib, statistics, datetime, collections, re
P = pathlib.Path(__file__).resolve().parent
RAW = P/'raw'
START, END, BAR = 1790985600000, 1791244800000, 900000
COST = 12/10000
def utc(t): return datetime.datetime.fromtimestamp(t/1000,datetime.timezone.utc).isoformat()
def tool_rows(name):
    r=json.loads((RAW/(name+'.json')).read_text())
    envelope=r.get('structuredContent') or json.loads(next(c['text'] for c in r['content'] if c['type']=='text'))
    assert envelope['ok'], name
    return envelope['data']['data']
def stats(xs):
    return {'n':len(xs),'mean_bps':statistics.mean(xs)*10000 if xs else None,'median_bps':statistics.median(xs)*10000 if xs else None,'positive_count':sum(x>0 for x in xs),'minimum_bps':min(xs)*10000 if xs else None,'maximum_bps':max(xs)*10000 if xs else None}
symbols={}
for b in ['btc','eth']:
    raw_c=tool_rows(b+'_candles')+tool_rows(b+'_boundary')
    c={int(x[0]):x for x in raw_c}
    main={t:v for t,v in c.items() if START<=t<END}
    expected=set(range(START,END,BAR))
    assert set(main)==expected and all(x[-1]=='1' for x in main.values())
    funding=sorted(tool_rows(b+'_funding'),key=lambda x:int(x['fundingTime']))
    oi={}
    for f in sorted(RAW.glob(b+'_oi_?.json')):
        response=json.loads(f.read_text());assert response['code']=='0'
        oi.update({int(x[0]):x for x in response['data']})
    assert len(oi)==289
    events=[]
    for f in funding:
        t=int(f['fundingTime'])
        if not START<=t<END or not all(q in c for q in [t-BAR,t,t+BAR]): continue
        rate=float(f['realizedRate']);sgn=1 if rate>0 else -1 if rate<0 else 0
        pre=float(c[t-BAR][4])/float(c[t-BAR][1])-1
        post=float(c[t+BAR][4])/float(c[t][1])-1
        events.append({'utc':utc(t),'ts':t,'realized_rate':rate,'realized_bps':rate*10000,'pre15_return_bps':pre*10000,'post30_return_bps':post*10000,'pre_opposite_funding_sign_bps':-sgn*pre*10000,'post_same_funding_sign_bps':sgn*post*10000,'funding_cash_abs_for_500_notional':abs(rate)*500,'signal_visibility':'ex_post only'})
    intervals=[(int(y['fundingTime'])-int(x['fundingTime']))/3600000 for x,y in zip(funding,funding[1:])]
    changes=[{'utc':utc(int(funding[i+1]['fundingTime'])),'previous_hours':intervals[i-1],'new_hours':intervals[i]} for i in range(1,len(intervals)) if intervals[i]!=intervals[i-1]]
    current=tool_rows(b+'_current')[0]
    proxy=[];price_only=[];last_exit=-1;account=500;drawdown=0;peak=500
    for t,x in sorted(main.items()):
        ret=float(x[4])/float(x[1])-1
        if ret>-.01:continue
        entry=t+BAR;exit_t=entry+2*BAR
        delta=float(oi[t+BAR][1])/float(oi[t][1])-1 if t in oi and t+BAR in oi else None
        e={'signal_candle_start_utc':utc(t),'price_return_bps':ret*10000,'oi_contract_delta_bps':delta*10000 if delta is not None else None,'true_liquidation_verified':False,'entry_utc':utc(entry),'exit_utc':utc(exit_t)}
        if entry not in c or exit_t not in c:
            e['outcome']='window incomplete';price_only.append(e);continue
        gross=float(c[exit_t][1])/float(c[entry][1])-1
        held_funding=sum(float(f['realizedRate']) for f in funding if entry<int(f['fundingTime'])<=exit_t)
        net=gross-COST-held_funding
        e.update({'gross_bps':gross*10000,'roundtrip_cost_bps':12,'held_funding_bps':held_funding*10000,'net_bps':net*10000,'funding_boundary_caveat':'entry at settlement timestamp is ambiguous; this diagnostic excludes entry-stamp funding and is not accepted execution'})
        price_only.append(e)
        if delta is not None and delta<=-.02:
            e=e.copy();e['overlap_skipped']=entry<last_exit
            if not e['overlap_skipped']:
                pnl=account*net;account+=pnl;peak=max(peak,account);drawdown=max(drawdown,(peak-account)/peak);last_exit=exit_t
                e.update({'account_pnl_usdt':pnl,'account_equity_usdt':account})
            proxy.append(e)
    symbols[b.upper()]={'instrument':b.upper()+'-USDT-SWAP','data':{'main_confirmed_candles':len(main),'boundary_unique_extra_candles':len(c)-len(main),'missing_main_candles':0,'historical_funding_records':len(funding),'oi_unique_records':len(oi),'oi_main_aligned_timestamps':len(set(main)&set(oi))},'settlement':{'events':events,'pre_opposite_sign':stats([e['pre_opposite_funding_sign_bps']/10000 for e in events]),'post_same_sign':stats([e['post_same_funding_sign_bps']/10000 for e in events]),'mean_abs_realized_funding_bps':statistics.mean(abs(e['realized_bps']) for e in events),'maximum_single_funding_cash_500':max(e['funding_cash_abs_for_500_notional'] for e in events)},'interval':{'interval_counts_hours':dict(collections.Counter(intervals)),'changes':changes,'first_settlement_utc':utc(int(funding[0]['fundingTime'])),'last_settlement_utc':utc(int(funding[-1]['fundingTime'])),'min_funding_bps':min(float(f['realizedRate']) for f in funding)*10000,'max_funding_bps':max(float(f['realizedRate']) for f in funding)*10000,'current_snapshot_cap_bps':float(current['maxFundingRate'])*10000,'current_snapshot_floor_bps':float(current['minFundingRate'])*10000,'historical_caps_verified':False},'liquidation_proxy':{'worst_price_15m_return_bps':min(float(x[4])/float(x[1])-1 for x in main.values())*10000,'price_only_stress_events':price_only,'price_and_oi_proxy_events':proxy,'proxy_outcome_statistics':stats([e['net_bps']/10000 for e in proxy if 'net_bps' in e]),'account':{'initial_usdt':500,'ending_usdt':account,'max_drawdown_pct':drawdown*100,'executed_simulated_events':sum('account_pnl_usdt' in e for e in proxy),'acceptance':'diagnostic hypothetical, no live execution; zero triggers does not validate mechanism'}}}
all_events=[e for s in symbols.values() for e in s['settlement']['events']]
total_proxy=sum(len(s['liquidation_proxy']['price_and_oi_proxy_events']) for s in symbols.values())
result={'generated_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'sample':{'start_utc':utc(START),'end_utc_exclusive':utc(END),'symbols':symbols},'mechanisms':{'funding_settlement_impact':{'status':'EVENT_DESCRIPTION_ONLY','real_data_n':{'candles':576,'funding_records':200,'complete_settlement_events':len(all_events)},'actually_computed':'15m before and 30m after return grouped using realized historical funding sign; cash size per event for constant 500U notional','pooled_pre_opposite_funding_sign':stats([e['pre_opposite_funding_sign_bps']/10000 for e in all_events]),'pooled_post_same_funding_sign':stats([e['post_same_funding_sign_bps']/10000 for e in all_events]),'not_done':['point-in-time prediction archive','causal controls or significance','tradable settlement-entry strategy/account replay','sub-minute settlement impact']},'funding_cap_interval_switch':{'status':'NO_SWITCH_IN_FROZEN_SAMPLE','real_data_n':{'settlements':200,'intervals':198,'observed_changes':sum(len(s['interval']['changes']) for s in symbols.values())},'actually_computed':'adjacent fundingTime differences and interval changes on each fixed symbol; min/max historical realized rate','not_done':['historical cap/floor verification','historical per-instrument change announcement timestamps','conditional cap-trigger return backtest'],'official_rule_effective_utc':'2026-04-14','normalization':'8/N divider normalizes per-period rate; shorter interval does not imply 8x funding cash'},'liquidation_reversal_liquidity':{'status':'PROXY_ONLY_NO_TRUE_LIQUIDATION_HISTORY','real_data_n':{'candles':576,'oi_snapshots':578,'true_liquidation_events':0,'stress_proxy_events':total_proxy,'price_only_events':sum(len(s['liquidation_proxy']['price_only_stress_events']) for s in symbols.values())},'actually_computed':'15m drawdown <=-1% plus contemporaneous OI contracts drop <=-2%, next-bar hypothetical long and 30m exit if triggered; fixed cost 12bps and realized funding','not_done':['actual liquidation labels/completeness','maker queue probability','historical book/trade execution simulation','actual limit fills','live account/trade']}}}
result['mechanisms']['funding_settlement_impact']['arithmetic_cost_sensitivity_only']={'pre_mean_gross_bps':result['mechanisms']['funding_settlement_impact']['pooled_pre_opposite_funding_sign']['mean_bps'],'pre_mean_minus12bps':result['mechanisms']['funding_settlement_impact']['pooled_pre_opposite_funding_sign']['mean_bps']-12,'post_mean_gross_bps':result['mechanisms']['funding_settlement_impact']['pooled_post_same_funding_sign']['mean_bps'],'post_mean_minus12bps':result['mechanisms']['funding_settlement_impact']['pooled_post_same_funding_sign']['mean_bps']-12,'not_a_trade_backtest':True,'funding_cash_included':False}
result['mechanisms']['liquidation_reversal_liquidity']['real_data_n']['true_liquidation_events']=None
result['mechanisms']['liquidation_reversal_liquidity']['true_liquidation_event_count_status']='UNKNOWN; no actual liquidation labels collected'
result['budget']={'explicit_public_market_requests':14,'official_docs_direct_curl_requests':2,'jina_requests':1,'web_search_open_find_operations':10,'total_explicit_public_operations':27,'cli_attempts_without_supported_market_data':2,'internal_tool_http_retries_or_cli_update_checks':'UNKNOWN','maximum_authorized_explicit_public_operations':40}
(P/'results.json').write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n')
urls={'frequency_official.html':'https://www.okx.com/en-eu/help/okx-to-enable-automatic-updates-for-funding-fee-settlement-period','frequency_official.txt':'https://r.jina.ai/https://www.okx.com/en-eu/help/okx-to-enable-automatic-updates-for-funding-fee-settlement-period','api_docs.html':'https://www.okx.com/docs-v5/en/'}
oi_requests=json.loads((RAW/'oi_requests.json').read_text())
urls.update({r['file']:r['url'] for r in oi_requests})
sources=[]
for f in sorted(RAW.iterdir()):
    if not f.is_file():continue
    url=urls.get(f.name)
    if f.suffix=='.json' and f.stem.endswith(('funding','current','candles','boundary')):
        symbol=f.stem.split('_')[0].upper()+'-USDT-SWAP'
        endpoint='/api/v5/public/funding-rate-history' if f.stem.endswith('funding') else '/api/v5/public/funding-rate' if f.stem.endswith('current') else '/api/v5/market/history-candles'
        url='https://www.okx.com'+endpoint+'?instId='+symbol
    sources.append({'file':str(f.relative_to(P)),'source_url':url,'sha256':hashlib.sha256(f.read_bytes()).hexdigest(),'bytes':f.stat().st_size})
(P/'sources.json').write_text(json.dumps(sources,indent=2)+'\n')
print(json.dumps({'mechanisms':result['mechanisms'],'per_symbol_counts':{b:{'n_settlement':len(s['settlement']['events']),'price_only':len(s['liquidation_proxy']['price_only_stress_events']),'proxy':len(s['liquidation_proxy']['price_and_oi_proxy_events'])} for b,s in symbols.items()}},indent=2))
