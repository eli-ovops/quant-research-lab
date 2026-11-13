"""Frozen screening then selection then confirmation. No strategy tuning."""
import json,hashlib,gzip,time,statistics,sys
from pathlib import Path
from datetime import datetime,timezone
import engine,audit,data
R=Path(__file__).resolve().parent
P=json.loads((R/'protocol.json').read_text())
H=3600000
DEADLINE=data.ms(P['limits']['deadline_utc'])

def dump(name,x):
    (R/name).write_text(json.dumps(x,indent=2,allow_nan=False)+'\n')

def starts(period,h):
    a,b=map(data.ms,P['periods'][period]);return range(a,b-h*H+1,h*H)

def aggregate(items):
    valid=[x for x in items if x['metrics']['final_equity'] is not None]
    vals=[x['metrics']['return'] for x in valid]
    n=len(valid);nall=len(items)
    return dict(scheduled=nall,evaluated=n,invalid=nall-n,targets=sum(x['metrics']['target_hit'] for x in valid),target_rate=sum(x['metrics']['target_hit'] for x in valid)/n if n else None,losses=sum(v<0 for v in vals),zeros=sum(x['metrics']['final_equity']<=0 for x in valid),no_trade=sum(x['metrics']['status']=='NO_TRADE' for x in valid),mean_return=statistics.mean(vals) if n else None,median_return=statistics.median(vals) if n else None,worst_return=min(vals) if n else None,p05_return=sorted(vals)[int((n-1)*.05)] if n else None,total_initial=n*500,total_final=sum(x['metrics']['final_equity'] for x in valid),mean_fees=statistics.mean(x['metrics']['fees'] for x in valid) if n else None,mean_funding=statistics.mean(x['metrics']['funding'] for x in valid) if n else None,max_episode_drawdown=max((x['metrics']['max_drawdown'] for x in valid),default=None))

def main():
    assert len(P['configs'])==120
    data.enable_seal()
    assert not (R/'selection.json').exists(),'Refuse silently overwriting a prior selection'
    hashes={f:hashlib.sha256((R/f).read_bytes()).hexdigest() for f in ('protocol.json','engine.py','audit.py','data.py','evaluate.py','data_manifest.json')}
    dump('execution_seal.json',dict(created_utc=datetime.now(timezone.utc).isoformat(),sha256=hashes))
    (R/'ledgers').mkdir(exist_ok=True)
    datasets={};maps={};control_cache={};summaries={};allmetrics=[];audit_count=0
    rules=list({x['rule']['id']:x['rule'] for x in P['configs']}.values())
    def get_data(coin,product,period):
        # Confirmation prices loaded into the evaluator only after selection was saved.
        cutoff=data.ms(P['periods']['confirmation'][1] if period=='confirmation' else P['periods']['validation'][1])
        key=(coin,product,cutoff)
        if key not in datasets:
            rows,spec,fund=data.load(coin,product,cutoff)
            independent=audit.prepare_signals(rows,rules)
            for rule in rules:
                sig=engine.prepare_signals(rows,rule)
                assert sig==independent[rule['id']],f'SIGNAL_AUDIT:{key}:{rule["id"]}'
                maps[key+(rule['id'],)]=sig
            datasets[key]=(engine.prepare_rows(rows),audit.prepare_rows(rows),spec,fund)
        return key,datasets[key]
    def run_config(c,period):
        nonlocal audit_count
        records=[];controls=[]
        name=f'{period}_{c["id"]}'
        with gzip.open(R/'ledgers'/f'{name}.jsonl.gz','wt') as log:
            for coin in P['assets']:
                key,(rows,auditrows,spec,fund)=get_data(coin,c['product'],period)
                sig=maps[key+(c['rule']['id'],)]
                for start in starts(period,c['horizon_hours']):
                    if time.time()*1000>=DEADLINE:raise RuntimeError('AUTHORIZED_DEADLINE_REACHED')
                    end=start+c['horizon_hours']*H
                    out=engine.simulate(rows,spec,fund,c,start,end,sig)
                    checked=audit.verify(auditrows,spec,fund,c,start,end,sig,out,control=False)
                    assert checked['ok'],f'LEDGER_AUDIT:{name}:{coin}:{start}:{checked}'
                    audit_count+=1
                    rec={'config':c['id'],'period':period,'coin':coin,'start':start,'end':end,**out}
                    log.write(json.dumps(rec,separators=(',',':'),allow_nan=False)+'\n')
                    minimal={k:v for k,v in rec.items() if k not in ('events','equity')};records.append(minimal);allmetrics.append(minimal)
                    ck=(period,coin,c['product'],c['leverage'],c['horizon_hours'],c['cost'],start)
                    if ck not in control_cache:
                        co=engine.simulate(rows,spec,fund,c,start,end,sig,control=True)
                        ca=audit.verify(auditrows,spec,fund,c,start,end,sig,co,control=True)
                        assert ca['ok'],f'CONTROL_AUDIT:{ck}:{ca}'
                        audit_count+=1
                        cr={'key':list(ck),'metrics':co['metrics']};control_cache[ck]=cr
                        with gzip.open(R/'ledgers'/'controls.jsonl.gz','at') as cl:cl.write(json.dumps({'key':list(ck),**co},separators=(',',':'),allow_nan=False)+'\n')
                    controls.append(control_cache[ck])
        a=aggregate(records);b=aggregate(controls)
        # Missing either side excluded only from paired statistic, always visible in aggregate denominators.
        pairs=[(x['metrics'],y['metrics']) for x,y in zip(records,controls) if x['metrics']['target_hit'] is not None and y['metrics']['target_hit'] is not None]
        improvement=statistics.mean(int(x['target_hit'])-int(y['target_hit']) for x,y in pairs) if pairs else None
        result={'config':c,'period':period,'strategy':a,'control':b,'paired_count':len(pairs),'paired_target_improvement':improvement,'by_coin':{coin:aggregate([x for x in records if x['coin']==coin]) for coin in P['assets']}}
        summaries[(period,c['id'])]=result
        dump(f'{name}.json',result)
        print(json.dumps({'finished':name,'evaluated':a['evaluated'],'targets':a['targets'],'audited':audit_count}),flush=True)
        return result
    for period in ('development','validation'):
        for c in P['configs']:run_config(c,period)
    selected=[]
    for product in ('SPOT','CONDITIONAL_SWAP'):
        for horizon in (24,168):
            candidates=[]
            for c in P['configs']:
                if c['product']!=product or c['horizon_hours']!=horizon:continue
                r=summaries[('validation',c['id'])];s=r['strategy']
                if s['evaluated']>=30 and s['invalid']==0 and s['targets']>=3 and s['mean_return']>0:candidates.append(r)
            candidates.sort(key=lambda r:(-r['paired_target_improvement'],-r['strategy']['mean_return'],r['config']['id']))
            if candidates:selected.append(candidates[0]['config'])
    dump('selection.json',{'saved_utc':datetime.now(timezone.utc).isoformat(),'selected':selected,'validation_input_sha256':{c['id']:hashlib.sha256((R/f'validation_{c["id"]}.json').read_bytes()).hexdigest() for c in P['configs']},'no_confirmation_evaluation_before_this_file':True})
    confirmed=[]
    for c in selected:
        result=run_config(c,'confirmation');s=result['strategy'];v=summaries[('validation',c['id'])]
        result['research_repeatability_candidate']=bool(s['evaluated']>=30 and s['invalid']==0 and s['targets']>=3 and s['mean_return']>0 and result['paired_target_improvement']>0 and v['paired_target_improvement']>0)
        result['actual_viability']='UNKNOWN'
        confirmed.append(result)
    with gzip.open(R/'episode_metrics.jsonl.gz','wt') as f:
        for x in allmetrics:f.write(json.dumps(x,separators=(',',':'),allow_nan=False)+'\n')
    assert time.time()*1000<DEADLINE,'AUTHORIZED_DEADLINE_REACHED'
    for f,h in hashes.items():assert hashlib.sha256((R/f).read_bytes()).hexdigest()==h,'EXECUTION_FILE_CHANGED:'+f
    data.enable_seal()
    dump('results.json',{'completed_utc':datetime.now(timezone.utc).isoformat(),'configs':120,'effective_assets':15,'audited_episodes':audit_count,'selection':selected,'confirmation':confirmed,'screening':[summaries[(p,c['id'])] for p in ('development','validation') for c in P['configs']]})
    dump('status.json',{'status':'COMPLETED','audited':audit_count,'selected':len(selected),'completed_utc':datetime.now(timezone.utc).isoformat()})
if __name__=='__main__':
    try:main()
    except Exception as e:
        dump('status.json',{'status':'FAILED_CLOSED','error':str(e),'at':datetime.now(timezone.utc).isoformat()});raise
