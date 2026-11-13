"""Independent fill-to-balance arithmetic, not independent strategy replay."""
import hashlib
import json
import sqlite3
from decimal import Decimal
from pathlib import Path


def decimal(value):
    x=Decimal(str(value))
    if not x.is_finite():raise ValueError('NONFINITE')
    return x


def account_check(account):
    cash=Decimal('150');positions={'BTC-USDT':Decimal(0),'ETH-USDT':Decimal(0)}
    for fill in account['fills']:
        a=fill['asset'];q=decimal(fill['quantity']);n=decimal(fill['notional']);fee=decimal(fill['fee'])
        if a not in positions or q<=0 or n<=0 or fee<0:raise ValueError('INVALID_FILL')
        if fill['side']=='BUY':
            if fill['fee_currency']=='USDT':cash-=n+fee;positions[a]+=q
            elif fill['fee_currency']==a.split('-')[0]:cash-=n;positions[a]+=q-fee
            else:raise ValueError('UNSUPPORTED_FEE_CURRENCY')
        elif fill['side']=='SELL' and fill['fee_currency']=='USDT':
            cash+=n-fee;positions[a]-=q
        else:raise ValueError('UNSUPPORTED_FILL')
        if cash<0 or any(v<0 for v in positions.values()):raise ValueError('NEGATIVE_BALANCE')
    if cash!=decimal(account['cash']) or any(positions[a]!=decimal(account['positions'][a]) for a in positions):
        raise ValueError('BALANCE_MISMATCH')
    return {'fills':len(account['fills']),'cash':str(cash),
            'positions':{a:str(q) for a,q in positions.items()}}


def audit(path):
    con=sqlite3.connect(Path(path).resolve().as_uri()+'?mode=ro',uri=True)
    previous='';count=0;prior_fills={};summary={};slots=set()
    try:
        for slot,body,sha in con.execute('SELECT slot,body,sha256 FROM events ORDER BY seq'):
            event=json.loads(body)
            actual=hashlib.sha256(json.dumps(event,sort_keys=True,separators=(',',':')).encode()).hexdigest()
            if actual!=sha or event['previous']!=previous:raise ValueError('JOURNAL_INTEGRITY')
            if slot in slots:raise ValueError('DUPLICATE_WINDOW')
            slots.add(slot);previous=sha;count+=1
            for scenario,state in event['state']['scenarios'].items():
                arms={'strategy':state['account'],**{a:state['baselines'][a] for a in ('cash','buy_hold')}}
                for arm,account in arms.items():
                    key=scenario+'/'+arm;old=prior_fills.get(key,[])
                    if account['fills'][:len(old)]!=old:raise ValueError('FILL_HISTORY_REWRITTEN')
                    summary[key]=account_check(account);prior_fills[key]=account['fills']
        if count==0:raise ValueError('NO_OBSERVATIONS')
        return {'status':'FILL_BALANCE_RECONCILED','observations':count,'accounts':summary,
                'limits':'Checks stored fills and balances only. Does not verify prices, model edge, full replay, live execution, or profitability.'}
    finally:con.close()
