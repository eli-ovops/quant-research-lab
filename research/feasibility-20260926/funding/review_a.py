"""Independent read-only review of A; writes only B/reviews. Standard library."""
from pathlib import Path
from decimal import Decimal as D
import json, hashlib, datetime
P = Path(__file__).resolve().parent
A = P.parent / 'basis'
def raw(name):
    obj = json.loads((A/'raw'/f'{name}.txt').read_text())
    assert obj['code'] == '0'
    return obj['data']
def main():
    src = json.loads((A/'sources.json').read_text())
    hashes = []
    for s in src:
        if 'path' in s:
            actual = hashlib.sha256(Path(s['path']).read_bytes()).hexdigest()
            assert actual == s['sha256']
            hashes.append({'path': s['path'], 'sha256':actual})
    universe = raw('all_futures')
    relevant = [x for x in universe if x['instId'].split('-')[0] in ['BTC','ETH']]
    # Independent filter uses base prefix and explicit type, not A's instFamily filter.
    matches = [x for x in relevant if x['instType']=='FUTURES' and x['ctType']=='linear'
               and x['settleCcy']=='USDT' and x['state']=='live' and x['ruleType']=='normal']
    assert not matches
    assert all(raw(c+s)==[] for c in ['BTC','ETH'] for s in ['_futures','_family'])
    audits=[]
    for c in ['BTC','ETH']:
        delivery=raw(c+'_delivery')[0]
        dd=next(x for x in delivery['details'] if x['insId']==c+'-USDT-260626')
        rows=sorted((int(e['ts']),D(v['settlePx'])) for e in raw(c+'_settlement') for v in e['details'] if v['instId']==dd['insId'])
        assert datetime.datetime.fromtimestamp(int(delivery['ts'])/1000,datetime.timezone.utc).isoformat()=='2026-06-26T08:00:00+00:00'
        points=[p for t,p in rows]+[D(dd['px'])]
        credit=D(0);basis=points[0]
        for next_basis in points[1:]:
            credit += basis-next_basis
            basis=next_basis
        direct=points[0]-D(dd['px'])
        assert credit==direct
        audits.append({'coin':c,'instId':dd['insId'],'delivery_price':dd['px'],'per_base_unit_difference':str(credit),'points':len(points),'not_trade_profit':True})
    # Independent cash postings and terminal equity for a deliberately non-flat basis.
    capital=D(2000);q=D('.01');spot0=D(60000);spot1=D(66000);future0=D(60300);future1=D(66200)
    spotfee=D('.001');futfee=D('.0005');gross=q/(1-spotfee)
    postings=[-gross*spot0,-q*future0*futfee,q*spot1,-q*spot1*spotfee,q*(future0-future1),-q*future1*futfee]
    pnl=sum(postings,D(0))
    direct=q*((future0-spot0)-(future1-spot1))-(gross-q)*spot0-q*spot1*spotfee-q*(future0+future1)*futfee
    assert abs(pnl-direct)<D('1e-22')
    annual_claim=json.loads((A/'results.json').read_text())
    assert annual_claim['pnl_USDT'] is None and annual_claim['return_on_2000'] is None
    assert annual_claim['independent_trade_events']==annual_claim['heldout_completed_trades']==0
    ann=(A/'raw'/'discontinuation_readable.txt').read_text()
    excerpt=ann[ann.find('Published on'):]
    out={'checked_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source_hashes_checked':len(hashes),'hashes':hashes,'universe':len(universe),'btc_eth':len(relevant),'independent_eligible_count':len(matches),'settlement_recalculations':audits,'independent_synthetic_cash_pnl':str(pnl),'full_capital_return_synthetic':str(pnl/capital),'announcement_excerpt':excerpt[:6500],'verdict':'PASS_LIMITED_CURRENT_PRODUCT_REJECTION; HISTORICAL_PROFITABILITY_INSUFFICIENT','caveats':['Synthetic cash postings are not actual execution','A eligibility helper omits instType check but raw universe is FUTURES; independent explicit-type filter gives identical zero','No actual historical account ledger; arithmetic identity only']}
    (P/'reviews').mkdir(exist_ok=True)
    (P/'reviews'/'basis_checks.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:v for k,v in out.items() if k not in ['hashes','announcement_excerpt']},ensure_ascii=False,indent=2))
    print(excerpt[:3000])
if __name__=='__main__':main()
