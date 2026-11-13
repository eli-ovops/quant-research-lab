"""Deterministic offline scenario transitions. No model, network or scheduling."""
import copy
from decimal import Decimal as D
from paper_ledger import (ASSETS, initial, validate_book, validate_decision,
                          rebalance, executable_liquidation)
from paper_baselines import initial_baselines, step_baselines

SCENARIOS = {
    'base_quote':(10,5,'quote'), 'base_coin':(10,5,'base'),
    'stress_quote':(20,20,'quote'), 'stress_coin':(20,20,'base'),
}


def initial_experiment():
    return {'last_ms':-1,'slots':[], 'observations':[],
            'scenarios':{k:{'account':initial(),'baselines':initial_baselines(),
                            'risk_halted':False} for k in SCENARIOS}}


def step(state, decision, books, specs, now_ms, operating_cost_usdt=None):
    """One observed window. Missing prices yield UNKNOWN, with no backfilled entry.

    operating_cost_usdt is cumulative attributable cost, not incremental cost.
    None means unknown; it must never silently become zero business expense.
    Price-invalid windows consume the slot but retain inventory. Risk halt is sticky.
    """
    validate_decision(decision)
    if decision['slot'] in state['slots']:
        raise ValueError('DUPLICATE_WINDOW')
    if not state['last_ms'] < decision['committed_ms'] <= now_ms:
        raise ValueError('OUT_OF_ORDER_WINDOW')
    cost = None if operating_cost_usdt is None else D(str(operating_cost_usdt))
    if cost is not None and (not cost.is_finite() or cost<0):
        raise ValueError('INVALID_OPERATING_COST')
    out=copy.deepcopy(state)
    out['slots'].append(decision['slot']);out['last_ms']=now_ms
    observation={'slot':decision['slot'],'observed_ms':now_ms,'scenarios':{},
                 'operating_cost_usdt':None if cost is None else str(cost)}
    try:
        for a in ASSETS:
            validate_book(books[a],decision['committed_ms'],now_ms)
    except (ValueError,KeyError,TypeError) as e:
        for arm in out['scenarios'].values():
            arm['baselines']['entry_attempted']=True
        observation.update(status='INVALID_MARKET',reason=str(e),equity='UNKNOWN')
        out['observations'].append(observation)
        return out
    for name,(fee,buffer,currency) in SCENARIOS.items():
        arm=out['scenarios'][name]
        config=dict(fee_bps=fee,buffer_bps=buffer)
        try:
            before=executable_liquidation(arm['account'],books,specs,
                       decision['committed_ms'],now_ms,**config)
            if D(before['liquidatable_cash'])<=D('135'):
                arm['risk_halted']=True
            d=decision
            if arm['risk_halted']:
                d={**decision,'weights':{a:0 for a in ASSETS},
                   'rationale':'Sticky risk halt: attempt exit at current valid book'}
            arm['account']=rebalance(arm['account'],d,books,specs,now_ms,
                                    buy_fee_currency=currency,**config)
            value=executable_liquidation(arm['account'],books,specs,
                         decision['committed_ms'],now_ms,**config)
            # Post-execution breach also locks future risk. No claim of intraday stop.
            if D(value['liquidatable_cash'])<=D('135'):
                arm['risk_halted']=True
            trade_net=D(value['liquidatable_cash'])-150
            arm['baselines'],references=step_baselines(arm['baselines'],decision,
                         books,specs,now_ms,buy_fee_currency=currency,**config)
            observation['scenarios'][name]={
                'status':'VALUED','liquidation':value,'trade_net_usdt':str(trade_net),
                'business_net_usdt':'UNKNOWN' if cost is None else str(trade_net-cost),
                'risk_halted':arm['risk_halted'],'baselines':references,
                'buy_hold_comparison_valid':arm['baselines']['buy_hold_comparison_valid']}
        except (ValueError,KeyError,TypeError) as e:
            # Successful preceding operations remain; never roll back simulated fills
            # merely because later valuation or comparison failed.
            arm['baselines']['entry_attempted']=True
            observation['scenarios'][name]={'status':'INCOMPLETE',
                    'reason':str(e),'equity':'UNKNOWN','business_net_usdt':'UNKNOWN'}
    observation['status']='PROCESSED'
    out['observations'].append(observation)
    return out
