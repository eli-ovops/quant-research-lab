"""Offline paper accounting only. No network, credentials, or exchange execution."""
import copy
import hashlib
import json
import os
import time
import fcntl
from decimal import Decimal, ROUND_DOWN
from pathlib import Path

D = Decimal
ASSETS = ('BTC-USDT', 'ETH-USDT')


def number(value):
    x = D(str(value))
    if not x.is_finite():
        raise ValueError('NONFINITE')
    return x


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def initial():
    return {'cash': '150', 'positions': {a: '0' for a in ASSETS}, 'fills': [], 'attempts': []}


def validate_book(book, decision_ms, now_ms):
    ts = int(book['ts'])
    if not decision_ms < ts <= now_ms or now_ms - ts > 5000:
        raise ValueError('STALE_OR_PREDECISION_BOOK')
    sides = {}
    for side in ('asks', 'bids'):
        levels = [(number(p), number(q)) for p, q in book[side]]
        if not levels or any(p <= 0 or q <= 0 for p, q in levels):
            raise ValueError('INVALID_BOOK')
        sides[side] = sorted(levels, reverse=side == 'bids')
    if sides['bids'][0][0] >= sides['asks'][0][0]:
        raise ValueError('CROSSED_BOOK')
    return sides


def sweep(levels, quantity):
    remaining, cost = quantity, D(0)
    for price, size in levels:
        taken = min(remaining, size)
        cost += price * taken
        remaining -= taken
        if remaining == 0:
            return cost
    raise ValueError('INSUFFICIENT_DEPTH')


def fill(state, order, book, spec, decision_ms, now_ms, fee_bps=10, buffer_bps=5, buy_fee_currency='quote'):
    """All-or-reject simulated order. Input state never mutated on failure."""
    asset, side = order['asset'], order['side']
    if asset not in ASSETS or side not in ('BUY', 'SELL'):
        raise ValueError('INVALID_ORDER')
    if buy_fee_currency not in ('base', 'quote'):
        raise ValueError('INVALID_FEE_CURRENCY')
    fee, buffer = number(fee_bps) / 10000, number(buffer_bps) / 10000
    if not 0 <= fee < 1 or not 0 <= buffer < 1:
        raise ValueError('INVALID_COST')
    q, lot, minimum = number(order['quantity']), number(spec['lotSz']), number(spec['minSz'])
    if lot <= 0 or minimum <= 0 or q <= 0 or q < minimum or q % lot != 0:
        raise ValueError('INVALID_SIZE')
    levels = validate_book(book, decision_ms, now_ms)
    gross = sweep(levels['asks' if side == 'BUY' else 'bids'], q)
    notional = gross * (1 + buffer if side == 'BUY' else 1 - buffer)
    cash, pos = number(state['cash']), number(state['positions'][asset])
    if side == 'BUY':
        debit = notional * (1 + fee) if buy_fee_currency == 'quote' else notional
        credit = q if buy_fee_currency == 'quote' else q * (1 - fee)
        if debit > cash:
            raise ValueError('INSUFFICIENT_CASH')
        cash -= debit
        pos += credit
        fee_amount = notional * fee if buy_fee_currency == 'quote' else q * fee
        fee_ccy = 'USDT' if buy_fee_currency == 'quote' else asset.split('-')[0]
    else:
        if q > pos:
            raise ValueError('INSUFFICIENT_POSITION')
        cash += notional * (1 - fee)
        pos -= q
        fee_amount, fee_ccy = notional * fee, 'USDT'
    out = copy.deepcopy(state)
    out['cash'], out['positions'][asset] = str(cash), str(pos)
    out['fills'].append({**order, 'notional': str(notional), 'fee': str(fee_amount),
                         'fee_currency': fee_ccy, 'book_ts': book['ts'],
                         'status': 'PAPER_ESTIMATE_NOT_EXCHANGE_FILL'})
    return out


def liquidation_value(state, books, decision_ms, now_ms, fee_bps=10, buffer_bps=5):
    """Depth-based liquidation estimate; insufficient depth raises, never valued as zero."""
    value = number(state['cash'])
    for a, qty in state['positions'].items():
        q = number(qty)
        if q:
            levels = validate_book(books[a], decision_ms, now_ms)
            value += sweep(levels['bids'], q) * (1-number(buffer_bps)/10000) * (1-number(fee_bps)/10000)
    return value


def validate_decision(decision):
    w = decision['weights']
    if set(w) != set(ASSETS) or any(number(x) not in (D(0), D('.25'), D('.5')) for x in w.values()):
        raise ValueError('INVALID_WEIGHTS')
    if sum(map(number, w.values())) > D('.5'):
        raise ValueError('EXPOSURE_LIMIT')
    if not decision.get('input_sha256') or not decision.get('rationale'):
        raise ValueError('MISSING_PROVENANCE')


def executable_liquidation(state, books, specs, decision_ms, now_ms, fee_bps=10, buffer_bps=5):
    """Cash obtainable under size rules; dust is disclosed separately, never sold."""
    cash = number(state['cash'])
    dust = {}
    for a, qty in state['positions'].items():
        q = number(qty)
        lot, minimum = number(specs[a]['lotSz']), number(specs[a]['minSz'])
        if lot <= 0 or minimum <= 0 or q < 0:
            raise ValueError('INVALID_SIZE')
        sellable = (q / lot).to_integral_value(rounding=ROUND_DOWN) * lot
        if sellable < minimum:
            sellable = D(0)
        dust[a] = str(q - sellable)
        if sellable:
            levels = validate_book(books[a], decision_ms, now_ms)
            cash += sweep(levels['bids'], sellable) * (1-number(buffer_bps)/10000) * (1-number(fee_bps)/10000)
    return {'liquidatable_cash':str(cash), 'unsellable_dust':dust}


def commit_decision(directory, decision):
    """Exclusive creation blocks accidental duplicate/revised decisions per slot."""
    validate_decision(decision)
    slot = decision['slot']
    if not slot or any(c not in '0123456789T-Z_' for c in slot):
        raise ValueError('INVALID_SLOT')
    decision = copy.deepcopy(decision)
    decision['committed_ms'] = time.time_ns() // 1000000
    envelope = {'decision': decision, 'sha256': digest(decision)}
    path = Path(directory) / (slot + '.decision.json')
    with path.open('x') as f:
        json.dump(envelope, f, sort_keys=True, indent=2)
        f.flush()
        os.fsync(f.fileno())
    return path


def rebalance(state, decision, books, specs, now_ms, fee_bps=10, buffer_bps=5, buy_fee_currency='quote'):
    """Generate lot-rounded targets using midpoint equity; apply sells before buys.

    Each rejected leg leaves that leg unchanged; successful earlier legs remain.
    Caller must persist decision before fetching these books. File runner verifies this.
    """
    validate_decision(decision)
    t = int(decision['committed_ms'])
    levels = {a: validate_book(books[a], t, now_ms) for a in ASSETS}
    mid = {a: (levels[a]['asks'][0][0]+levels[a]['bids'][0][0])/2 for a in ASSETS}
    equity = number(state['cash']) + sum(number(state['positions'][a])*mid[a] for a in ASSETS)
    orders = []
    for a in ASSETS:
        lot = number(specs[a]['lotSz'])
        if lot <= 0:
            raise ValueError('INVALID_LOT')
        target = equity * number(decision['weights'][a]) / mid[a]
        diff = target - number(state['positions'][a])
        q = (abs(diff)/lot).to_integral_value(rounding=ROUND_DOWN)*lot
        if q >= number(specs[a]['minSz']):
            orders.append({'asset': a, 'side': 'BUY' if diff > 0 else 'SELL', 'quantity': str(q)})
    out = copy.deepcopy(state)
    for order in sorted(orders, key=lambda o:o['side'] != 'SELL'):
        try:
            requested = order['quantity']
            if order['side'] == 'BUY':
                # Fixed asset order, largest feasible lot quantity no greater than target.
                # Monotonic under nonnegative fees/buffer and sorted ask levels.
                lot = number(specs[order['asset']]['lotSz'])
                lo, hi = 0, int(number(requested)/lot)
                while lo < hi:
                    n = (lo + hi + 1)//2
                    trial = {**order, 'quantity':str(n*lot)}
                    try:
                        # Search below minSz too; final order still obeys true minSz.
                        trial_spec = {**specs[order['asset']], 'minSz':str(lot)}
                        c = fill(out,trial,books[order['asset']],trial_spec,t,now_ms,
                                 fee_bps,buffer_bps,buy_fee_currency)
                        r = sum(number(c['positions'][a])*mid[a] for a in ASSETS)
                        feasible = r <= (number(c['cash'])+r)*D('.5')
                    except ValueError as e:
                        if str(e) not in ('INSUFFICIENT_CASH','INSUFFICIENT_DEPTH'):
                            raise
                        feasible = False
                    if feasible:
                        lo = n
                    else:
                        hi = n-1
                if lo*lot < number(specs[order['asset']]['minSz']):
                    raise ValueError('NO_FEASIBLE_BUY_SIZE')
                order = {**order, 'quantity':str(lo*lot), 'requested_quantity':requested}
            candidate = fill(out, order, books[order['asset']], specs[order['asset']], t, now_ms,
                             fee_bps, buffer_bps, buy_fee_currency)
            risk = sum(number(candidate['positions'][a])*mid[a] for a in ASSETS)
            if order['side']=='BUY' and risk > (number(candidate['cash'])+risk)*D('.5'):
                raise ValueError('POST_COST_EXPOSURE_LIMIT')
            out = candidate
            result = 'PAPER_FILLED'
        except ValueError as e:
            result = str(e)
        out['attempts'].append({**order, 'result': result})
    return out


def settle(directory, decision_path, books, specs, fee_bps=10, buffer_bps=5, buy_fee_currency='quote'):
    """One scenario per directory; locked append journal, crash/corruption fail closed."""
    root = Path(directory)
    envelope = json.loads(Path(decision_path).read_text())
    d = envelope['decision']
    if digest(d) != envelope['sha256']:
        raise ValueError('DECISION_HASH_MISMATCH')
    config = {'fee_bps':str(number(fee_bps)), 'buffer_bps':str(number(buffer_bps)),
              'buy_fee_currency':buy_fee_currency, 'initial_usdt':'150'}
    journal = root / 'journal.jsonl'
    with (root / 'journal.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        previous, state, slots, last_settled_ms = '', initial(), set(), -1
        if journal.exists():
            for line in journal.read_text().splitlines():
                event = json.loads(line)
                recorded = event.pop('sha256')
                if digest(event) != recorded or event['previous'] != previous:
                    raise ValueError('JOURNAL_HASH_MISMATCH')
                if event['config'] != config:
                    raise ValueError('SCENARIO_CONFIG_CHANGED')
                previous, state = recorded, event['state']
                last_settled_ms = event['settled_ms']
                slots.add(event['slot'])
        if d['slot'] in slots:
            raise ValueError('ALREADY_SETTLED')
        if int(d['committed_ms']) <= last_settled_ms:
            raise ValueError('OUT_OF_ORDER_DECISION')
        now = time.time_ns() // 1000000
        result = rebalance(state,d,books,specs,now,fee_bps,buffer_bps,buy_fee_currency)
        event = {'slot':d['slot'],'decision_sha256':envelope['sha256'],
                 'settled_ms':now,'previous':previous,'config':config,
                 'books':books,'specs':specs,'state':result,
                 'scope':'PAPER_ONLY_NO_EXCHANGE_EXECUTION'}
        event['sha256']=digest(event)
        with journal.open('a') as f:
            f.write(json.dumps(event,sort_keys=True)+'\n')
            f.flush();os.fsync(f.fileno())
        return result
