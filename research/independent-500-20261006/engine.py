"""Frozen 500-USDT independent-account episode research. No network or orders.

Events expose cash and base/contract changes for independent replay. SWAP is
linear contract accounting with explicit realized funding, not scaled spot PnL.
OHLC maintenance breach and terminal liquidation remain research proxies.
"""
import hashlib
import json
import math
from decimal import Decimal, ROUND_FLOOR, ROUND_CEILING
from statistics import mean, pstdev

QUARTER = 900_000
HOUR = 3_600_000
INITIAL = 500.0
TARGET = 650.0
STOP = 250.0
WARMUP = 120
COSTS = {'SPOT': {'base': (.001, .0005), 'stress': (.002, .001)},
         'CONDITIONAL_SWAP': {'base': (.0005, .0005), 'stress': (.001, .001)}}


def rounded(value, increment, upward=False):
    step = Decimal(str(increment))
    if not step.is_finite() or step <= 0:
        raise ValueError('invalid_increment')
    n = (Decimal(str(value)) / step).to_integral_value(
        rounding=ROUND_CEILING if upward else ROUND_FLOOR)
    return float(n * step)


def adverse_price(reference, side, slip, tick):
    adjusted = Decimal(str(reference)) * (1 + Decimal(str(slip)) if side == 'buy' else 1 - Decimal(str(slip)))
    return rounded(adjusted, tick, side == 'buy')


def prepare_rows(rows):
    """Snapshot and validate once per instrument; reuse across episode calls."""
    indexed, invalid = _indexed(rows)
    return {'kind':'prepared_15m','indexed':indexed,'invalid':invalid}


def _indexed(rows):
    if isinstance(rows, dict) and rows.get('kind') == 'prepared_15m':
        return rows['indexed'], rows['invalid']
    indexed, invalid = {}, set()
    for r in rows:
        try:
            t = int(r[0])
            valid = len(r) == 9 and str(r[8]) == '1' and t % QUARTER == 0
            values = list(map(float, r[1:8]))
            o,h,l,c,v = values[:5]
            valid = valid and all(math.isfinite(x) for x in values)
            valid = valid and 0 < l <= min(o,c) <= max(o,c) <= h and v > 0 and min(values[5:]) >= 0
            if t in indexed and indexed[t] != list(r):
                valid = False
            indexed[t] = list(r)
            if not valid:
                invalid.add(t)
        except (ValueError, TypeError, IndexError):
            # Unlocatable malformed rows make the dataset unsafe, not silently
            # ignored. Sentinel is recognized by both signal and episode gates.
            invalid.add(None)
    return indexed, invalid


def _hourly(rows):
    indexed, invalid = _indexed(rows)
    if None in invalid:
        return []
    if not indexed:
        return []
    bars = []
    for t in range(min(indexed)//HOUR*HOUR, max(indexed)//HOUR*HOUR+HOUR, HOUR):
        keys = [t+k*QUARTER for k in range(4)]
        if any(k not in indexed or k in invalid for k in keys):
            bars.append({'t':t+HOUR, 'valid':False})
            continue
        rs = [indexed[k] for k in keys]
        bars.append({'t':t+HOUR, 'valid':True, 'o':float(rs[0][1]),
                     'h':max(float(r[2]) for r in rs), 'l':min(float(r[3]) for r in rs),
                     'c':float(rs[-1][4])})
    return bars


def _rsi(closes, n):
    differences = [b-a for a,b in zip(closes[-n-1:], closes[-n:])]
    gains = mean(max(d,0) for d in differences)
    losses = mean(max(-d,0) for d in differences)
    return 100.0 if losses == 0 and gains > 0 else 50.0 if gains == losses == 0 else 100-100/(1+gains/losses)


def _band(closes, n, z):
    v = closes[-n:]
    mu, sigma = mean(v), pstdev(v)
    return mu-z*sigma, mu+z*sigma


def prepare_signals(rows, rule):
    """Directions at available UTC hourly closing boundaries; no future input.

    At least 120 contiguous valid closed hours include the signal hour. EMA seeds
    at first close of each valid segment and recursively uses every subsequent
    close. Missing/zero bars reset the feature segment, never carry forward.
    """
    result, segment, closes = {}, [], []
    fast = slow = previous_fast = previous_slow = None
    family = rule['family']
    for bar in _hourly(rows):
        if not bar['valid']:
            segment, closes = [], []
            fast = slow = previous_fast = previous_slow = None
            continue
        segment.append(bar)
        closes.append(bar['c'])
        if family == 'ema':
            previous_fast, previous_slow = fast, slow
            fast = closes[-1] if fast is None else fast + 2/(rule['fast']+1)*(closes[-1]-fast)
            slow = closes[-1] if slow is None else slow + 2/(rule['slow']+1)*(closes[-1]-slow)
        if len(segment) < WARMUP:
            continue
        current, previous = closes[-1], closes[-2]
        direction = 0
        n = rule.get('n')
        if family == 'donchian':
            window = segment[-n-1:-1]
            old_window = segment[-n-2:-2]
            direction = 1 if current > max(b['h'] for b in window) and previous <= max(b['h'] for b in old_window) else -1 if current < min(b['l'] for b in window) and previous >= min(b['l'] for b in old_window) else 0
        elif family == 'ema':
            direction = 1 if previous_fast <= previous_slow and fast > slow else -1 if previous_fast >= previous_slow and fast < slow else 0
        elif family == 'momentum':
            momentum = current/closes[-n-1]-1
            old_momentum = previous/closes[-n-2]-1
            threshold = rule['threshold']
            direction = 1 if old_momentum <= threshold < momentum else -1 if old_momentum >= -threshold > momentum else 0
        elif family == 'boll':
            lo,hi = _band(closes,n,rule['z'])
            old_lo,old_hi = _band(closes[:-1],n,rule['z'])
            direction = 1 if previous < old_lo and current >= lo else -1 if previous > old_hi and current <= hi else 0
        elif family == 'rsi':
            rsi,old = _rsi(closes,n),_rsi(closes[:-1],n)
            direction = 1 if old <= rule['low'] < rsi else -1 if old >= rule['high'] > rsi else 0
        elif family == 'atr_break':
            prior = segment[-rule['atr_n']-1:-1]
            previous_closes = closes[-rule['atr_n']-2:-2]
            tr = [max(b['h']-b['l'], abs(b['h']-p), abs(b['l']-p)) for b,p in zip(prior,previous_closes)]
            offset = rule['atr_multiple']*mean(tr)
            window = segment[-n-1:-1]
            direction = 1 if current > max(b['h'] for b in window)+offset else -1 if current < min(b['l'] for b in window)-offset else 0
        else:
            raise ValueError('unknown_rule_family')
        if direction:
            result[bar['t']] = direction
    return result


def control_choice(spec, config, start):
    """Rule-independent canonical SHA256 control; no Python salted hash."""
    coin = spec.get('baseCcy') or spec.get('ctValCcy') or spec.get('instId','UNKNOWN').split('-')[0]
    material = [50020261006,config['product'],config['leverage'],config['horizon_hours'],config['cost'],coin,int(start)]
    encoded = json.dumps(material, separators=(',',':'), ensure_ascii=True).encode()
    digest = hashlib.sha256(encoded).digest()
    hour = int.from_bytes(digest[:8],'big') % (config['horizon_hours']//2)
    direction = 1 if config['product']=='SPOT' or digest[-1]&1 else -1
    return start+hour*HOUR, direction, hashlib.sha256(encoded).hexdigest()


def simulate(rows, spec, funding, config, start, end, signals, control=False):
    """One independent 500 account, at most one entry; return JSON-safe dict.

    Required data is the full [start-120H,end) 15m window. Funding coverage
    requires bracketing observations at/before start and at/after end and no
    gap >8H. No trades/data fetches. Successful return status is model evidence.
    """
    product = config['product']
    derivative = product == 'CONDITIONAL_SWAP'
    if product not in COSTS:
        raise ValueError('unknown_product')
    fee,slip = COSTS[product][config['cost']]
    events,equity = [],[]
    true_unknown = 'UNKNOWN' if derivative else 'NOT_APPLICABLE'
    def invalid(reason,status='DATA_INVALID'):
        return {'metrics': {'status':status,'target_hit':None,'final_equity':None,'return':None,
                            'max_drawdown':None,'fees':None,'funding':None,'exit_reason':reason,
                            'true_target':true_unknown,'true_liquidation':true_unknown,
                            'real_execution_validation':'UNKNOWN','initial':INITIAL},
                'events':[],'equity':[]}
    indexed,bad = _indexed(rows)
    if start%HOUR or end%QUARTER or end<=start or end-start!=config['horizon_hours']*HOUR:
        return invalid('invalid_episode_bounds')
    needed = range(start-WARMUP*HOUR,end,QUARTER)
    if None in bad or any(t not in indexed or t in bad for t in needed):
        return invalid('missing_zero_unconfirmed_or_invalid_candle')
    try:
        for name in ('tickSz','lotSz','minSz'):
            if not math.isfinite(float(spec[name])) or float(spec[name])<=0:
                return invalid('invalid_'+name,'SPEC_INVALID')
        if derivative and (spec['instType']!='SWAP' or spec['ctType']!='linear' or
                           spec['settleCcy']!='USDT' or not math.isfinite(float(spec['ctVal'])) or float(spec['ctVal'])<=0):
            return invalid('nonlinear_or_missing_swap_spec','SPEC_INVALID')
        if not derivative and spec.get('instType','SPOT')!='SPOT':
            return invalid('nonspot_spec','SPEC_INVALID')
    except (ValueError,TypeError,KeyError):
        return invalid('missing_spec','SPEC_INVALID')
    funding_rates = {}
    if derivative:
        try:
            for item in funding:
                t=int(item['fundingTime'])
                if not start-8*HOUR<=t<=end+8*HOUR:
                    continue
                rate=float(item['realizedRate'])
                if t%QUARTER or not math.isfinite(rate):
                    return invalid('invalid_funding')
                if t in funding_rates and funding_rates[t]!=rate:
                    return invalid('conflicting_funding')
                funding_rates[t]=rate
            times=sorted(funding_rates)
            left=max(t for t in times if t<=start)
            right=min(t for t in times if t>=end)
            covered=[t for t in times if left<=t<=right]
            if any(b-a>8*HOUR for a,b in zip(covered,covered[1:])):
                return invalid('funding_gap')
        except (ValueError,TypeError,KeyError):
            return invalid('missing_funding_coverage')
    balance=INITIAL
    base_qty=contracts=0.0
    direction=0
    entry_price=None
    attempted=False
    done=False
    pending_exit=None
    fees=funding_total=0.0
    exit_reason='NO_SIGNAL'
    peak=INITIAL
    max_drawdown=0.0
    seed=None
    if control:
        entry_t,entry_direction,seed=control_choice(spec,config,start)
        effective_signals={entry_t:entry_direction}
    else:
        effective_signals=signals

    def event(t,kind,cash_delta=0.0,base_delta=0.0,contract_delta=0.0,**extra):
        events.append(dict(timestamp=t,type=kind,cash_delta=cash_delta,
                           base_delta=base_delta,contract_delta=contract_delta,
                           cash_after=balance,base_after=direction*base_qty,
                           contracts_after=direction*contracts,**extra))

    def net_value(reference):
        if not base_qty:
            return balance
        side='sell' if direction>0 else 'buy'
        px=adverse_price(reference,side,slip,spec['tickSz'])
        if derivative:
            return balance+direction*base_qty*(px-entry_price)-base_qty*px*fee
        return balance+base_qty*px*(1-fee)

    def close_position(t,reference,reason,terminal=False):
        nonlocal balance,base_qty,contracts,direction,done,fees,exit_reason
        old_base,old_contracts,old_direction=base_qty,contracts,direction
        px=adverse_price(reference,'sell' if direction>0 else 'buy',slip,spec['tickSz'])
        charge=base_qty*px*fee
        if derivative:
            delta=direction*base_qty*(px-entry_price)-charge
            pnl=direction*base_qty*(px-entry_price)
            residual=0.0
        else:
            sold=rounded(base_qty,spec['lotSz'])
            # Untradeable fee dust is explicitly valued at terminal liquidation
            # proxy; it is never promoted to an executable exchange lot.
            if sold<float(spec['minSz']):sold=0.0
            residual=base_qty-sold
            charge=sold*px*fee
            delta=sold*px*(1-fee)
            pnl=None
        balance+=delta
        fees+=charge
        base_qty=0.0 if derivative else residual
        contracts=0.0
        direction=0 if derivative or not residual else 1
        done=True
        exit_reason=reason
        event(t,'EXIT',delta,-old_direction*(old_base-base_qty),-old_direction*old_contracts,
              price=px,reference_price=float(reference),fee=charge,realized_pnl=pnl,
              reason=reason,terminal_proxy=terminal,residual_base=base_qty)

    def apply_funding(t,reference,terminal=False):
        nonlocal balance,funding_total
        if derivative and base_qty and t in funding_rates:
            rate=funding_rates[t]
            delta=-direction*base_qty*reference*rate
            balance+=delta
            funding_total+=delta
            event(t,'FUNDING',delta,rate=rate,reference_price=reference,
                  notional_proxy=base_qty*reference,terminal_price_proxy=terminal)

    def maintenance_breach(t,reference,phase):
        nonlocal balance,base_qty,contracts,direction,done,exit_reason
        if not derivative or not base_qty or done:
            return False
        collateral=balance+direction*base_qty*(reference-entry_price)
        threshold=base_qty*reference*(.02+.002)
        if collateral>threshold:
            return False
        old_base,old_contracts,old_direction=base_qty,contracts,direction
        delta=-balance
        balance=0.0;base_qty=contracts=0.0;direction=0;done=True
        exit_reason='MAINTENANCE_PROXY_BREACH'
        event(t,'MAINTENANCE_PROXY_BREACH',delta,-old_direction*old_base,-old_direction*old_contracts,
              adverse_price=reference,modeled_collateral=collateral,maintenance_threshold=threshold,
              model_equity=0.0,true_liquidation='UNKNOWN',realized_pnl=None,phase=phase)
        return True

    for t in range(start,end,QUARTER):
        r=indexed[t]
        o,h,l,c=map(float,r[1:5])
        # Existing position owns funding before any gap check/queued exit.
        apply_funding(t,o)
        maintenance_breach(t,o,'OPEN_BEFORE_EXIT')
        if pending_exit and not done and base_qty:
            close_position(t,o,pending_exit)
            pending_exit=None
        if not attempted and not done and t in effective_signals:
            sign=int(effective_signals[t])
            if sign not in (-1,1):
                raise ValueError('invalid_direction')
            if sign==1 or derivative:
                attempted=True
                direction=sign
                px=adverse_price(o,'buy' if sign>0 else 'sell',slip,spec['tickSz'])
                budget=INITIAL*.95
                if derivative:
                    ct_val=float(spec['ctVal'])
                    contracts=rounded(budget/(ct_val*px*(1/config['leverage']+fee)),spec['lotSz'])
                    base_qty=contracts*ct_val
                    quantity=contracts
                else:
                    quantity=rounded(budget/px,spec['lotSz'])
                    base_qty=quantity*(1-fee)
                if quantity<=0 or quantity<float(spec['minSz']):
                    base_qty=contracts=0.0;direction=0;done=True;exit_reason='MIN_SIZE_REJECTED'
                    event(t,'REJECTED',reason=exit_reason,budget=budget)
                else:
                    entry_price=px
                    charge=quantity*px*fee if not derivative else base_qty*px*fee
                    fees+=charge
                    delta=-quantity*px if not derivative else -charge
                    balance+=delta
                    event(t,'ENTRY',delta,direction*base_qty,direction*contracts,
                          price=px,reference_price=o,fee=charge,fee_asset=quantity*fee if not derivative else 0.0,
                          budget=budget,margin=base_qty*px/config['leverage'] if derivative else 0.0,
                          direction=direction,signal_timestamp=t,quantity=quantity)
        if derivative and base_qty and not done:
            maintenance_breach(t+QUARTER,l if direction>0 else h,'INTRABAR_ADVERSE')
        value=net_value(c)
        peak=max(peak,value)
        max_drawdown=max(max_drawdown,1-value/peak)
        equity.append(dict(timestamp=t+QUARTER,cash=balance,base=direction*base_qty,
                           contracts=direction*contracts,equity=value,exit_cost_included=True))
        if base_qty and not done and pending_exit is None:
            if value>=TARGET:
                pending_exit='TARGET_CLOSE_SIGNAL'
            elif value<=STOP:
                pending_exit='STOP_CLOSE_SIGNAL'
    if base_qty and not done:
        terminal_reference=float(indexed[end-QUARTER][4])
        apply_funding(end,terminal_reference,terminal=True)
        maintenance_breach(end,terminal_reference,'TERMINAL_AFTER_FUNDING')
    if base_qty and not done:
        # end is not a tradable candle; use last closed candle close, explicitly.
        close_position(end,float(indexed[end-QUARTER][4]),'HORIZON_TERMINAL',terminal=True)
    final=net_value(float(indexed[end-QUARTER][4]))
    if equity:
        equity[-1].update(cash=balance,base=direction*base_qty,contracts=direction*contracts,equity=final)
    peak=max(peak,final)
    max_drawdown=max(max_drawdown,1-final/peak)
    status='ORDER_REJECTED' if exit_reason=='MIN_SIZE_REJECTED' else 'NO_TRADE' if not attempted else 'VALID'
    return {'metrics':dict(status=status,target_hit=final>=TARGET,final_equity=final,
                           **{'return':final/INITIAL-1},max_drawdown=max_drawdown,fees=fees,
                           funding=funding_total,exit_reason=exit_reason,initial=INITIAL,
                           true_target=true_unknown,true_liquidation=true_unknown,
                           real_execution_validation='UNKNOWN',control_seed=seed,
                           terminal_residual_base=base_qty,current_specs_historical_validity='UNKNOWN'),
            'events':events,'equity':equity}
