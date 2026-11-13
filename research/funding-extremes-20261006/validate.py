import json,pathlib,hashlib,math,urllib.parse,datetime
P=pathlib.Path(__file__).resolve().parent
OLD=P.parent/'mechanism-pilot-20261006'/'funding-flow'
END=1791244800000;START=END-30*86400000
def env(r):
    r=r.get('response',r)
    return r.get('structuredContent') or json.loads(next(x['text'] for x in r['content'] if x['type']=='text'))
v={'validation':'PASS','checks':{},'public_requests':[],'old_artifacts_unchanged':{}}
source=[]
instruments=json.loads((P/'raw'/'instruments.json').read_text());ie=env(instruments)
assert ie['ok']
v['public_requests'].append({'file':'raw/instruments.json','tool':'market_get_instruments','arguments':{'instType':'SWAP'},'server_request_time_utc':ie['data']['requestTime']})
for b in json.loads((P/'protocol.json').read_text())['universe']:
    file=P/'raw'/(b+'_funding.json');raw=json.loads(file.read_text());e=env(raw);assert e['ok'];data=e['data']['data']
    assert len(data)<=100
    timestamps=[int(x['fundingTime']) for x in data]
    assert len(timestamps)==len(set(timestamps))
    assert all(x['instId']==b+'-USDT-SWAP' for x in data)
    assert all(math.isfinite(float(x['realizedRate'])) and math.isfinite(float(x['fundingRate'])) for x in data)
    filtered=[t for t in timestamps if START<=t<END]
    assert set(filtered)==set(range(START,END,8*3600000))
    v['checks'][b]={'raw_rows':len(data),'main_unique_rows':len(filtered),'grid':'DATA_GRID_COMPLETE','grid_interval_hours':8,'main_expected_rows':90,'first_ms':min(filtered),'last_ms':max(filtered),'duplicate_rows':0,'conflicting_duplicates':0,'instId_correct':True,'rates_finite':True,'raw_sha256':hashlib.sha256(file.read_bytes()).hexdigest()}
    v['public_requests'].append({'file':str(file.relative_to(P)),'tool':raw['tool'],'arguments':raw['arguments'],'server_request_time_utc':e['data']['requestTime'],'outer_requested_at_utc_semantics':'completion/save timestamp; not request start','outer_saved_time_utc':raw['requested_at_utc']})
for file in sorted((P/'raw').glob('*.json')):
    e=env(json.loads(file.read_text()))
    if file.name=='instruments.json':url='https://www.okx.com/api/v5/public/instruments?instType=SWAP'
    else:
        a=json.loads(file.read_text())['arguments'];url='https://www.okx.com/api/v5/public/funding-rate-history?'+urllib.parse.urlencode({k:val for k,val in a.items() if k!='history'})
    source.append({'file':str(file.relative_to(P)),'source_url':url,'server_request_time_utc':e['data']['requestTime'],'bytes':file.stat().st_size,'sha256':hashlib.sha256(file.read_bytes()).hexdigest()})
oldhash=json.loads((OLD/'artifact-hashes.json').read_text())
for f,expected in oldhash.items():
    got=hashlib.sha256((OLD/f).read_bytes()).hexdigest();assert got==expected
    v['old_artifacts_unchanged'][f]={'sha256':got,'matches_sealed_manifest':True}
assert len(v['public_requests'])==11
v['explicit_public_requests']=11;v['internal_http_retries']='UNKNOWN'
v['data_count']=900;v['no_strategy_or_account_profitability_acceptance']=True
(P/'sources.json').write_text(json.dumps(source,indent=2)+'\n')
(P/'requests.json').write_text(json.dumps(v['public_requests'],indent=2)+'\n')
(P/'validation.json').write_text(json.dumps(v,indent=2)+'\n')
print('PASS: 10 x 90 main unique timestamps; complete 8h grid; finite rates and correct instId; no duplicate/conflict; raw hashes recorded; sealed old artifacts unchanged; 11 public requests.')
