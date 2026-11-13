import pathlib,json,hashlib,re,datetime,collections
P=pathlib.Path(__file__).resolve().parent
protocol=json.loads((P/'protocol.json').read_text())
reviewed=json.loads((P/'candidates-reviewed.json').read_text())
raws=sorted((P/'raw').glob('*.json'))
requests=[];sources=[];allurls=set();search_n=open_n=0
for f in raws:
    r=json.loads(f.read_text());a=r['arguments'];assert isinstance(r['response'],str)
    ns=len(a.get('search_query',[]));no=len(a.get('open',[]));search_n+=ns;open_n+=no
    urls=sorted(set(re.findall(r'\((https://www\.okx\.com[^)]+)\)',r['response'])))
    allurls.update(urls)
    sources.append({'file':str(f.relative_to(P)),'sha256':hashlib.sha256(f.read_bytes()).hexdigest(),'bytes':f.stat().st_size,'source_urls':urls,'capture_kind':'complete web tool response, not original HTTP HTML'})
    requests.append({'file':str(f.relative_to(P)),'tool':'web.run','arguments':a,'request_started_utc':r.get('request_started_utc'),'response_saved_utc':r.get('response_saved_utc',r.get('requested_at_utc')),'time_note':'search1 outer requested_at is save/completion time; start UNKNOWN','search_operations':ns,'open_operations':no})
eligible=[]
for x in reviewed:
    assert x['url'] in allurls, x['url']
    if x['eligible']:
        assert x['kind']=='coin_interval_change'
        assert x['effective_utc'] and '2026-09-06'<=x['effective_utc'][:10]<'2026-10-06'
        assert x['old_interval_hours'] is not None and x['new_interval_hours'] is not None
        eligible.append(x)
eligible.sort(key=lambda x:(x['effective_utc'],reviewed.index(x)))
selected=[]
for x in eligible[:3]:
    for coin in x['instIds'][:3]:
        if len(selected)>=6:break
        selected.append({'announcement_url':x['url'],'instId':coin,'effective_utc':x['effective_utc']})
assert search_n+open_n<=30
result={'protocol':protocol,'stageA':{'status':'NO_QUALIFYING_COIN_ADJUSTMENT_FOUND_IN_RETRIEVED_CORPUS','reviewed_entries':len(reviewed),'reviewed_category_counts':dict(collections.Counter(x['kind'] for x in reviewed)),'unique_official_urls_returned':len(allurls),'qualifying_announcements':len(eligible),'selected_contract_events':selected,'selection':[],'actual_announcements_in_date_range':'UNKNOWN; search not exhaustive','coverage':'14 bilingual targeted official queries and Chinese/Europe first trading-update page; indexed/cached/locale/category coverage incomplete','not_a_market_negative_result':True},'stageB':{'status':'NOT_STARTED_NO_ELIGIBLE_ANNOUNCEMENT','actual_funding_records':0,'observed_interval_switches':None,'abs_rate_ge10bps_count':None,'event_history_coverage':'NOT_TESTED'},'stageC':{'status':'NOT_STARTED_ANNOUNCEMENT_GATE_UNMET','actual_price_records':0,'price_events':[],'controls':[],'BTC_comparisons':[],'mean_gross_bps':None,'cost_sensitivity_bps':None,'funding_cash_ownership':'UNKNOWN','account_pnl':'NOT_COMPUTED','profitability_acceptance':'NOT_TESTED'},'budget':{'search_operations':search_n,'open_operations':open_n,'total_explicit_public_operations':search_n+open_n,'internal_requests':'UNKNOWN','max_public_operations':30,'max_minutes':20},'limits':['no outside dates/other exchanges','no new listings as cycle changes','no generic mechanism as individual event','no price reading before announcement selection','no installation/auth/account/orders/production/background/polling']}
(P/'results.json').write_text(json.dumps(result,indent=2)+'\n')
(P/'selection.json').write_text(json.dumps(selected,indent=2)+'\n')
(P/'sources.json').write_text(json.dumps(sources,indent=2)+'\n')
(P/'requests.json').write_text(json.dumps(requests,indent=2)+'\n')
sealed={}
for rel in ['funding-extremes-20261006','mechanism-pilot-20261006/funding-flow']:
    old=P.parent/rel;manifest=json.loads((old/'artifact-hashes.json').read_text())
    for file,expected in manifest.items():
        got=hashlib.sha256((old/file).read_bytes()).hexdigest();assert got==expected
    sealed[rel]={'files_verified':len(manifest),'unchanged':True}
validation={'evidence_integrity':'PASS','reviewed_source_urls_found_in_raw':True,'raw_response_hashes':{x['file']:x['sha256'] for x in sources},'public_operation_budget_pass':True,'old_artifacts':sealed,'business_gate':'announcement candidate gate unmet, strategy/account not tested','routing_actual':'UNKNOWN'}
(P/'validation.json').write_text(json.dumps(validation,indent=2)+'\n')
print(json.dumps({'reviewed':len(reviewed),'unique_official_urls':len(allurls),'qualifying':len(eligible),'selected':len(selected),'searches':search_n,'opens':open_n,'calls':search_n+open_n,'validation':validation['evidence_integrity'],'sealed':sealed},indent=2))
