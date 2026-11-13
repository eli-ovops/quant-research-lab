"""Deterministic, long-only pooled-cash SPOT research simulator (standard library).

No orders/network. Current instrument specifications are a historical proxy.
Intervals are [start_ms, end_ms); candles are open-timestamped. UTC 4H
signals become available at their closing boundary; execution uses that
boundary's hourly open plus delay_hours. Equity is estimated liquidation value.
"""
import math
from decimal import Decimal, ROUND_FLOOR, ROUND_CEILING
from statistics import mean, pstdev

HOUR = 3_600_000
FOUR = 4 * HOUR
WARMUP = 126


def _round(value, step, up=False):
    if not step or float(step) <= 0:
        return float(value)
    d, s = Decimal(str(value)), Decimal(str(step))
    return float((d / s).to_integral_value(rounding=ROUND_CEILING if up else ROUND_FLOOR) * s)


def _bars(rows):
    buckets = {}
    for row in rows:
        if len(row) >= 9 and str(row[8]) != '1':
            continue
        t = int(row[0])
        buckets.setdefault(t // FOUR * FOUR, []).append(row)
    out = []
    for t, group in sorted(buckets.items()):
        if len(group) != 4 or [int(r[0]) for r in group] != [t + k * HOUR for k in range(4)]:
            continue
        out.append({'t': t + FOUR, 'index': t // FOUR,
                    'o': float(group[0][1]), 'h': max(float(r[2]) for r in group),
                    'l': min(float(r[3]) for r in group), 'c': float(group[-1][4]),
                    'valid': all(float(r[5]) > 0 for r in group)})
    return out


def _lower(closes, n, z):
    values = closes[-n:]
    return mean(values) - z * pstdev(values)


def run(data, specs, candidate, condition, start_ms, end_ms, initial=2000):
    """Return {'metrics','equity','fills','trades','signals'}; all JSON-safe.

    Specs accept coin or COIN-USDT keys, with OKX tickSz/lotSz/minSz.
    Missing specs impose no rounding and are explicitly labelled UNKNOWN.
    Closed trades count completed strategy exits with positive executed sale,
    including terminal exits; lot-sized residual dust remains in the ledger.
    """
    if end_ms <= start_ms or initial <= 0:
        raise ValueError('positive interval and initial equity required')
    fee, slip = float(condition['fee']), float(condition['slip'])
    delay = int(condition.get('delay_hours', 0))
    if not 0 <= fee < 1 or not 0 <= slip < 1 or delay < 0:
        raise ValueError('invalid cost/delay')
    coins = sorted(data)
    rows = {c: {int(r[0]): r for r in data[c] if len(r) < 9 or str(r[8]) == '1'} for c in coins}
    series = {c: _bars(data[c]) for c in coins}
    lookup = {c: {b['t']: i for i, b in enumerate(series[c])} for c in coins}
    hours = sorted(set(t for rr in rows.values() for t in rr if start_ms <= t < end_ms))
    if not hours:
        raise ValueError('no candles in interval')
    family = candidate['family']
    if family not in ('trend', 'reversion', 'rotation', 'hold', 'cash'):
        raise ValueError('unknown family')
    cash = float(initial)
    pos = {c: 0.0 for c in coins}
    active = {c: False for c in coins}
    entered = {}
    basis = {c: 0.0 for c in coins}
    last_close = {}
    fills, trades, signals, equity = [], [], [], []
    pending = {}
    last_targets = {c: 0.0 for c in coins}
    baseline_sent = False
    rejected = 0
    total_fees = 0.0

    def spec(c):
        return (specs or {}).get(c, (specs or {}).get(c + '-USDT', {}))

    def price(c, reference, side):
        return _round(reference * (1 + slip if side == 'buy' else 1 - slip),
                      spec(c).get('tickSz'), side == 'buy')

    def mark(closes):
        values = {c: pos[c] * price(c, closes[c], 'sell') * (1 - fee)
                  for c in coins if c in closes}
        invested = sum(values.values())
        value = cash + invested
        return value, invested / value if value > 0 else 0.0

    def reject(c, side, t, st, why, reason):
        nonlocal rejected
        rejected += 1
        fills.append(dict(timestamp=t, signal_timestamp=st, coin=c, side=side,
                          status='rejected', rejection=why, reason=reason,
                          quantity=0.0, cash_delta=0.0, asset_delta=0.0,
                          cash_after=cash, asset_after=pos[c], forced_proxy=reason == 'terminal'))

    def execute(t, event, references, terminal=False):
        nonlocal cash, total_fees
        st, targets, reason = event
        value, _ = mark(references)
        # A target transition changes only affected coins. Existing allocations
        # are left untouched when their target weight is unchanged.
        changed = {c: w for c, w in targets.items() if terminal or w != last_targets[c]}
        wanted = {c: value * w for c, w in changed.items()}
        sells, buys = [], []
        for c in sorted(changed):
            if c not in references:
                reject(c, 'buy' if changed[c] else 'sell', t, st, 'missing_execution_bar', reason)
                continue
            p = price(c, float(references[c]), 'sell')
            current = pos[c] * p
            if wanted[c] < current - 1e-10:
                sells.append((c, (current - wanted[c]) / p))
            elif wanted[c] > current + 1e-10:
                buys.append((c, wanted[c] - current))
        for c, desired in sells:
            p = price(c, float(references[c]), 'sell')
            q = min(pos[c], _round(desired, spec(c).get('lotSz')))
            if q <= 0 or q < float(spec(c).get('minSz', 0)):
                reject(c, 'sell', t, st, 'lot_or_minimum', reason)
                continue
            before = pos[c]
            proceeds = q * p * (1 - fee)
            cost = basis[c] * q / before
            charge = q * p * fee
            cash += proceeds
            pos[c] = max(0.0, before - q)
            basis[c] = max(0.0, basis[c] - cost)
            total_fees += charge
            fills.append(dict(timestamp=t, signal_timestamp=st, coin=c, side='sell', status='filled',
                              quantity=q, price=p, reference_price=float(references[c]), fee_rate=fee,
                              fee_quote=charge, fee_asset=0.0, cash_delta=proceeds, asset_delta=-q,
                              cash_after=cash, asset_after=pos[c], reason=reason, forced_proxy=terminal, budget_quote=wanted[c],
                              portfolio_equity_at_order=value))
            if changed[c] == 0:
                if active[c]:
                    trades.append(dict(coin=c, entry_signal_timestamp=entered.get(c), exit_timestamp=t,
                                       quantity=q, cost=cost, proceeds=proceeds, pnl=proceeds-cost,
                                       return_fraction=proceeds/cost-1 if cost else 0, reason=reason,
                                       residual_quantity=pos[c]))
                active[c] = False
                entered.pop(c, None)
        required = sum(notional for _, notional in buys)
        available_cash = max(0.0, cash - .1 * value)
        scale = min(1.0, available_cash / required) if required else 1.0
        for c, notional in buys:
            p = price(c, float(references[c]), 'buy')
            q = _round(notional * scale / p, spec(c).get('lotSz'))
            q = min(q, cash / p)
            if q <= 0 or q < float(spec(c).get('minSz', 0)):
                reject(c, 'buy', t, st, 'lot_or_minimum', reason)
                continue
            spending = q * p
            net = q * (1-fee)
            cash -= spending
            if cash < -1e-8:
                raise AssertionError('negative cash')
            cash = max(0.0, cash)
            pos[c] += net
            basis[c] += spending
            charge = q * fee * p
            total_fees += charge
            if not active[c]:
                entered[c] = st
            active[c] = True
            fills.append(dict(timestamp=t, signal_timestamp=st, coin=c, side='buy', status='filled',
                              quantity=q, price=p, reference_price=float(references[c]), fee_rate=fee,
                              fee_quote=0.0, fee_asset=q*fee, fee_quote_equivalent=charge,
                              cash_delta=-spending, asset_delta=net, cash_after=cash, asset_after=pos[c],
                              reason=reason, forced_proxy=terminal, budget_quote=wanted[c],
                              portfolio_equity_at_order=value))
        # Failed entries do not establish a strategy holding. Successful exits
        # may leave untradeable dust; it remains explicitly valued and recorded.
        for c, w in changed.items():
            if w == 0 and not active[c] or w > 0 and active[c]:
                last_targets[c] = w

    def decision(t):
        nonlocal baseline_sent
        eligible = {c: lookup[c][t] for c in coins if t in lookup[c] and lookup[c][t] >= WARMUP}
        if not eligible or family == 'cash':
            return
        targets = {}
        def valid(c, i, count):
            window = series[c][i-count:i+1]
            if len(window) != count+1 or any(not b['valid'] for b in window):
                signals.append(dict(timestamp=t, family=family, coin=c,
                                    reason='invalid_feature_input', targets={},
                                    execution_timestamp=None))
                return False
            return True
        if family == 'hold':
            if baseline_sent or len(eligible) != len(coins):
                return
            baseline_sent = True
            targets = {c: .9 / 8 for c in coins}
        elif family == 'trend':
            n, m = candidate['entry_bars'], candidate['exit_bars']
            for c, i in eligible.items():
                if not valid(c, i, max(n,m)):
                    continue
                b = series[c][i]
                if active[c] and b['c'] < min(x['l'] for x in series[c][i-m:i]):
                    targets[c] = 0.0
                elif not active[c] and b['c'] > max(x['h'] for x in series[c][i-n:i]):
                    targets[c] = .9 / 8
        elif family == 'reversion':
            n, z, holding = candidate.get('band_bars', 20), candidate['z'], candidate['hold_bars']
            for c, i in eligible.items():
                if active[c]:
                    if t - entered[c] >= holding * FOUR:
                        targets[c] = 0.0
                    continue
                if not valid(c, i, 21):
                    continue
                closes = [x['c'] for x in series[c][i-20:i+1]]
                previous = closes[:-1]
                path = [x['c'] for x in series[c][i-21:i]]
                movement = sum(abs(b-a) for a,b in zip(path, path[1:]))
                er = abs(path[-1]-path[0]) / movement if movement else 0.0
                if (path[-1] < path[0] and er >= .3 and
                    previous[-1] < _lower(previous, n, z) and closes[-1] >= _lower(closes, n, z)):
                    targets[c] = .9 / 8
        elif family == 'rotation':
            if len(eligible) != len(coins):
                return
            if series[coins[0]][eligible[coins[0]]]['index'] % candidate['rebalance_bars']:
                return
            n = candidate['lookback_bars']
            if not all([valid(c, i, n) for c,i in eligible.items()]):
                return
            ranks = sorted(((series[c][i]['c']/series[c][i-n]['c']-1,c) for c,i in eligible.items()),
                           key=lambda pair: (-pair[0], pair[1]))
            selected = [c for momentum,c in ranks if momentum > 0][:candidate['top_k']]
            weight = min(.9 / candidate['top_k'], .25)
            desired = {c: weight if c in selected else 0.0 for c in coins}
            targets = {c:w for c,w in desired.items() if w != last_targets[c]}
        if targets:
            execution_t = t + delay * HOUR
            signals.append(dict(timestamp=t, execution_timestamp=execution_t, family=family,
                                targets=dict(targets), reason=family))
            if execution_t < end_ms:
                pending.setdefault(execution_t, []).append((t, targets, family))

    for t in hours:
        decision(t)
        opens = {c: float(rr[t][1]) for c,rr in rows.items() if t in rr}
        for event in pending.pop(t, []):
            execute(t, event, opens)
        for c, rr in rows.items():
            if t in rr:
                last_close[c] = float(rr[t][4])
        value, exposure = mark(last_close)
        equity.append(dict(timestamp=t+HOUR, cash=cash, positions=dict(pos), equity=value, exposure=exposure))
    execute(end_ms, (end_ms, {c:0.0 for c in coins}, 'terminal'), last_close, terminal=True)
    value, exposure = mark(last_close)
    # Final mark is after proxy liquidation, including any untradeable dust.
    equity[-1] = dict(timestamp=end_ms, cash=cash, positions=dict(pos), equity=value, exposure=exposure)
    peak = float(initial)
    drawdown = 0.0
    for point in equity:
        peak = max(peak, point['equity'])
        drawdown = max(drawdown, 1 - point['equity'] / peak)
    daily = {}
    for point in equity:
        daily[(point['timestamp']-1)//(24*HOUR)] = point['equity']
    previous = float(initial)
    daily_returns = []
    for day, v in sorted(daily.items()):
        daily_returns.append(dict(day_utc=day, return_fraction=v/previous-1))
        previous = v
    metrics = dict(total_return=value/initial-1, max_drawdown=drawdown,
                   closed_trades=len(trades), final_equity=value, fees=total_fees,
                   exposure=mean(p['exposure'] for p in equity),
                   rejected_orders=rejected, daily_returns=daily_returns,
                   specifications_historical_validity='UNKNOWN_current_spec_proxy' if specs else 'UNKNOWN_no_specs',
                   allocation_policy='targets_only_no_continuous_rebalance_drift_possible',
                   cash_reserve_policy='10pct_pre_batch_liquidation_equity_on_buys',
                   terminal_liquidation='last_hour_close_adverse_slippage_fee_proxy',
                   untradeable_residuals={c:q for c,q in pos.items() if q > 1e-12})
    return dict(metrics=metrics, equity=equity, fills=fills, trades=trades, signals=signals)
