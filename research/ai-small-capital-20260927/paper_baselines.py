"""Offline reference arms; no scheduler, model call, or exchange execution."""
import copy
from paper_ledger import ASSETS, initial, rebalance, executable_liquidation


def initial_baselines():
    return {'cash':initial(), 'buy_hold':initial(), 'entry_attempted':False,
            'buy_hold_comparison_valid':False}


def step_baselines(state, committed_decision, books, specs, now_ms,
                   fee_bps=10, buffer_bps=5, buy_fee_currency='quote'):
    """Buy-hold attempts entry once; failures stay recorded and are never backfilled.

    50% cap applies at entry. Later drift is retained by definition of buy-hold;
    this comparator is not risk-matched after entry. Caller persists each step.
    Whole-step validation failure leaves input unchanged.
    """
    out=copy.deepcopy(state)
    if not out['entry_attempted']:
        d={**committed_decision,'weights':{a:'.25' for a in ASSETS},
           'rationale':'Predefined once-only buy-hold benchmark'}
        out['buy_hold']=rebalance(out['buy_hold'],d,books,specs,now_ms,
                                  fee_bps,buffer_bps,buy_fee_currency)
        out['entry_attempted']=True
        out['buy_hold_comparison_valid'] = (
            len(out['buy_hold']['fills']) == 2 and
            all(x['result']=='PAPER_FILLED' for x in out['buy_hold']['attempts']))
    values={}
    for arm in ('cash','buy_hold'):
        values[arm]=executable_liquidation(out[arm],books,specs,
                        committed_decision['committed_ms'],now_ms,fee_bps,buffer_bps)
    return out,values
