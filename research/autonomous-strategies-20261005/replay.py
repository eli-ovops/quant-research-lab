"""Independent offline ledger audit. Accepts caller-supplied data; never reads data files.

The engine is intentionally not imported. Audit failure raises AuditError; no
profitability or blind-holdout claim is made by a successful accounting audit.
"""
from decimal import Decimal, ROUND_CEILING, ROUND_FLOOR
import math
import statistics

HOUR = 3_600_000
BAR = 4 * HOUR


class AuditError(ValueError):
    pass


def number(value):
    x = float(value)
    if not math.isfinite(x):
        raise AuditError("nonfinite_number")
    return x


def close(actual, expected, label, atol=1e-7, rtol=1e-8):
    actual, expected = number(actual), number(expected)
    if abs(actual - expected) > atol + rtol * max(abs(actual), abs(expected)):
        raise AuditError(f"{label}: {actual!r} != {expected!r}")


def rounded(value, increment, upward=False):
    value, increment = Decimal(str(value)), Decimal(str(increment))
    if increment <= 0:
        raise AuditError("invalid_increment")
    n = (value / increment).to_integral_value(
        rounding=ROUND_CEILING if upward else ROUND_FLOOR)
    return float(n * increment)


def price(reference, side, condition, spec):
    ref = Decimal(str(reference))
    slip = Decimal(str(condition["slip"]))
    adjusted = ref * (1 + slip if side == "buy" else 1 - slip)
    return rounded(adjusted, spec["tickSz"], upward=side == "buy")


def index_data(data):
    indexed = {}
    for coin, rows in data.items():
        by_time = {}
        for row in rows:
            t = int(row[0])
            if t % HOUR or len(row) != 9 or str(row[8]) != "1":
                raise AuditError("unconfirmed_or_misaligned_candle")
            o, hi, lo, c = map(number, row[1:5])
            if not 0 < lo <= min(o, c) <= max(o, c) <= hi:
                raise AuditError("invalid_OHLC")
            if t in by_time and by_time[t] != row:
                raise AuditError("conflicting_duplicate")
            by_time[t] = row
        indexed[coin] = by_time
    if not indexed:
        raise AuditError("empty_assets")
    return indexed


def four_hour_bars(indexed):
    """Reconstruct complete UTC bars, with close availability at boundary t+4h."""
    out = {}
    for coin, by_time in indexed.items():
        bars = []
        for t in sorted(by_time):
            if t % BAR or not all(t + j * HOUR in by_time for j in range(4)):
                continue
            rows = [by_time[t + j * HOUR] for j in range(4)]
            bars.append({"timestamp": t + BAR, "open": number(rows[0][1]),
                         "high": max(number(r[2]) for r in rows),
                         "low": min(number(r[3]) for r in rows),
                         "close": number(rows[-1][4]),
                         "valid": all(number(r[5]) > 0 for r in rows)})
        out[coin] = bars
    return out


def primitive_signals(indexed, candidate):
    """All eligible closed-bar raw triggers, independent of portfolio inventory.

    Portfolio-dependent orders are checked separately against these primitives.
    No absent-order claim follows merely from this trigger reconstruction.
    """
    bars = four_hour_bars(indexed)
    triggers = {}
    family = candidate["family"]
    for coin, series in bars.items():
        for i in range(126, len(series)):
            b = series[i]
            dependencies = (max(candidate["entry_bars"], candidate["exit_bars"])
                            if family == "trend" else 21 if family == "reversion"
                            else candidate.get("lookback_bars", 0))
            if not all(x["valid"] for x in series[i-dependencies:i+1]):
                triggers[coin, b["timestamp"]] = {"invalid_feature_input": True}
                continue
            if family == "trend":
                n, m = candidate["entry_bars"], candidate["exit_bars"]
                enter = b["close"] > max(x["high"] for x in series[i-n:i])
                leave = b["close"] < min(x["low"] for x in series[i-m:i])
                triggers[coin, b["timestamp"]] = {"entry": enter, "exit": leave}
            elif family == "reversion":
                n, z = candidate["band_bars"], candidate["z"]
                current = [x["close"] for x in series[i-n+1:i+1]]
                previous = [x["close"] for x in series[i-n:i]]
                current_lower = statistics.mean(current) - z * statistics.pstdev(current)
                previous_lower = statistics.mean(previous) - z * statistics.pstdev(previous)
                state_closes = [x["close"] for x in series[i-21:i]]
                movement = state_closes[-1] - state_closes[0]
                distance = sum(abs(v-u) for u, v in zip(state_closes, state_closes[1:]))
                er = abs(movement)/distance if distance else 0.0
                enter = (movement < 0 and er >= .30 and
                         series[i-1]["close"] < previous_lower and
                         b["close"] >= current_lower)
                triggers[coin, b["timestamp"]] = {"entry": enter}
            elif family == "rotation":
                n = candidate["lookback_bars"]
                triggers[coin, b["timestamp"]] = {
                    "momentum": b["close"] / series[i-n]["close"] - 1}
            elif family == "hold":
                continue
            else:
                raise AuditError("unknown_family")
    return triggers


def independent_metrics(values, initial, closed_trades):
    if not values:
        raise AuditError("empty_equity")
    peak, dd = initial, 0.0
    for value in values:
        value = number(value)
        peak = max(peak, value)
        if peak > 0:
            dd = max(dd, (peak-value)/peak)
    return {"return": values[-1]/initial-1,
            "max_drawdown": dd, "closed_trades": closed_trades,
            "final_equity": values[-1]}


def verify(data, specs, candidate, condition, start_ms, end_ms, result, initial=2000):
    """Independently rebuild decisions, executions, inventory, and hourly marks.

    Accept only caller-provided slices. This function never selects candidates,
    imports the production engine, or reads confirmation data from disk.
    """
    indexed = index_data(data)
    coins = sorted(indexed)
    hours = list(range(start_ms, end_ms, HOUR))
    if not hours or start_ms % HOUR or end_ms % HOUR:
        raise AuditError("invalid_interval")
    for coin in coins:
        if any(t not in indexed[coin] for t in hours):
            raise AuditError("missing_trading_hour")
        if any(number(indexed[coin][t][5]) <= 0 for t in hours):
            raise AuditError("zero_volume_in_trading_period")
    normalized_specs = {c: specs.get(c, specs.get(c+"-USDT", {})) for c in coins}
    for spec in normalized_specs.values():
        if any(k not in spec for k in ("tickSz", "lotSz", "minSz")):
            raise AuditError("missing_specification")
    fee = number(condition["fee"])
    delay = int(condition.get("delay_hours", 0))*HOUR
    family = candidate["family"]
    triggers = {} if family in ("hold", "cash") else primitive_signals(indexed, candidate)
    bars = four_hour_bars(indexed)
    available = {c: {b["timestamp"] for b in seq[126:]} for c, seq in bars.items()}
    signals_at, fills_at = {}, {}
    for s in result["signals"]:
        signals_at.setdefault(int(s["timestamp"]), []).append(s)
    for f in result["fills"]:
        fills_at.setdefault(int(f["timestamp"]), []).append(f)
    if any(t < start_ms or t > end_ms for t in fills_at):
        raise AuditError("fill_outside_interval")
    if any(t not in hours for t in signals_at):
        raise AuditError("signal_outside_interval")
    balance = float(initial)
    inventory = {c: 0.0 for c in coins}
    cost_basis = {c: 0.0 for c in coins}
    active = {c: False for c in coins}
    entry_time = {}
    previous_target = {c: 0.0 for c in coins}
    pending = {}
    expected_trades = []
    hourly_values, hourly_exposures = [], []
    fee_sum, rejected_count, invalid_count = 0.0, 0, 0
    hold_sent = False

    def mark(references):
        invested = sum(inventory[c] * price(references[c], "sell", condition,
                                            normalized_specs[c]) * (1-fee) for c in coins)
        return balance+invested, invested

    def consume(t, event, references, actual, terminal=False):
        nonlocal balance, fee_sum, rejected_count
        st, targets, reason = event
        value, _ = mark(references)
        changed = {c:w for c,w in targets.items() if terminal or w != previous_target[c]}
        wanted = {c:value*w for c,w in changed.items()}
        sell_orders, buy_orders = [], []
        for c in sorted(changed):
            sell_price = price(references[c], "sell", condition, normalized_specs[c])
            current = inventory[c]*sell_price
            delta = wanted[c]-current
            if delta < -1e-10:
                sell_orders.append((c, -delta/sell_price))
            elif delta > 1e-10:
                buy_orders.append((c, delta))

        def fill(c, side, q):
            nonlocal balance, fee_sum, rejected_count
            if not actual:
                raise AuditError("missing_fill_or_rejection")
            f = actual.pop(0)
            for field, expected in (("timestamp", t), ("signal_timestamp", st),
                                    ("coin", c), ("side", side), ("reason", reason),
                                    ("forced_proxy", terminal)):
                if f.get(field) != expected:
                    raise AuditError("fill_"+field)
            minimum = number(normalized_specs[c]["minSz"])
            status = "rejected" if q <= 0 or q < minimum else "filled"
            if f["status"] != status:
                raise AuditError("fill_status")
            if status == "rejected":
                rejected_count += 1
                for field in ("quantity", "cash_delta", "asset_delta"):
                    close(f[field], 0, "rejected_"+field)
            else:
                p = price(references[c], side, condition, normalized_specs[c])
                before = inventory[c]
                close(f["quantity"], q, "quantity")
                close(f["price"], p, "price")
                close(f["reference_price"], references[c], "reference_price")
                close(f["fee_rate"], fee, "fee_rate")
                close(f["budget_quote"], wanted[c], "budget_quote")
                close(f["portfolio_equity_at_order"], value, "pretrade_equity")
                if side == "buy":
                    spend = q*p
                    asset_delta, cash_delta = q*(1-fee), -spend
                    close(f["fee_asset"], q*fee, "base_fee")
                    close(f["fee_quote"], 0, "buy_quote_fee")
                    close(f["fee_quote_equivalent"], q*p*fee, "fee_equivalent")
                    cost_basis[c] += spend
                    if not active[c]:
                        entry_time[c] = st
                    active[c] = True
                else:
                    if q > before+1e-9:
                        raise AuditError("oversell")
                    cash_delta, asset_delta = q*p*(1-fee), -q
                    close(f["fee_asset"], 0, "sell_base_fee")
                    close(f["fee_quote"], q*p*fee, "quote_fee")
                    cost = cost_basis[c]*q/before
                    cost_basis[c] = max(0.0, cost_basis[c]-cost)
                    if changed[c] == 0 and active[c]:
                        expected_trades.append({"coin": c, "entry_signal_timestamp": entry_time[c],
                            "exit_timestamp": t, "quantity": q, "cost": cost,
                            "proceeds": cash_delta, "pnl": cash_delta-cost,
                            "return_fraction": cash_delta/cost-1 if cost else 0,
                            "reason": reason, "residual_quantity": max(0.0, before-q)})
                        active[c] = False
                        entry_time.pop(c, None)
                balance += cash_delta
                inventory[c] = max(0.0, before+asset_delta)
                fee_sum += q*p*fee
                close(f["cash_delta"], cash_delta, "cash_delta")
                close(f["asset_delta"], asset_delta, "asset_delta")
                if balance < -1e-7 or inventory[c] < -1e-9:
                    raise AuditError("negative_ledger")
                balance = max(0.0, balance)
            close(f["cash_after"], balance, "cash_after")
            close(f["asset_after"], inventory[c], "asset_after")

        for c, q in sell_orders:
            fill(c, "sell", min(inventory[c], rounded(q, normalized_specs[c]["lotSz"])))
        required = sum(notional for c, notional in buy_orders)
        available_cash = max(0.0, balance-.1*value)
        scale = min(1.0, available_cash/required) if required else 1.0
        for c, notional in buy_orders:
            p = price(references[c], "buy", condition, normalized_specs[c])
            q = rounded(notional*scale/p, normalized_specs[c]["lotSz"])
            fill(c, "buy", min(q, balance/p))
        for c, w in changed.items():
            if (w == 0 and not active[c]) or (w > 0 and active[c]):
                previous_target[c] = w

    def decision(t):
        nonlocal hold_sent, invalid_count
        eligible = [c for c in coins if t in available[c]]
        expected, targets = [], {}
        if family == "hold":
            if not hold_sent and len(eligible) == len(coins):
                hold_sent = True
                targets = {c:.9/8 for c in coins}
        elif family == "trend":
            for c in eligible:
                trigger = triggers[c, t]
                if trigger.get("invalid_feature_input"):
                    expected.append({"timestamp":t,"family":family,"coin":c,
                                     "reason":"invalid_feature_input", "targets":{},
                                     "execution_timestamp":None})
                elif active[c] and trigger["exit"]:
                    targets[c] = 0.0
                elif not active[c] and trigger["entry"]:
                    targets[c] = .9/8
        elif family == "reversion":
            for c in eligible:
                trigger = triggers[c, t]
                if active[c]:
                    if t-entry_time[c] >= candidate["hold_bars"]*BAR:
                        targets[c] = 0.0
                elif trigger.get("invalid_feature_input"):
                    expected.append({"timestamp":t,"family":family,"coin":c,
                                     "reason":"invalid_feature_input", "targets":{},
                                     "execution_timestamp":None})
                elif trigger["entry"]:
                    targets[c] = .9/8
        elif family == "rotation" and len(eligible) == len(coins):
            if ((t-BAR)//BAR) % candidate["rebalance_bars"] == 0:
                invalid = [c for c in eligible if triggers[c,t].get("invalid_feature_input")]
                for c in invalid:
                    expected.append({"timestamp":t,"family":family,"coin":c,
                                     "reason":"invalid_feature_input", "targets":{},
                                     "execution_timestamp":None})
                if not invalid:
                    ranking = sorted(eligible, key=lambda c:(-triggers[c,t]["momentum"],c))
                    chosen = [c for c in ranking if triggers[c,t]["momentum"] > 0][:candidate["top_k"]]
                    w = min(.9/candidate["top_k"], .25)
                    targets = {c:w if c in chosen else 0.0 for c in coins
                               if (w if c in chosen else 0.0) != previous_target[c]}
        elif family not in ("cash", "rotation"):
            raise AuditError("unknown_family")
        invalid_count += len(expected)
        if targets:
            expected.append({"timestamp":t,"execution_timestamp":t+delay,
                             "family":family,"targets":targets,"reason":family})
            if t+delay < end_ms:
                pending.setdefault(t+delay, []).append((t,targets,family))
        actual = signals_at.get(t, [])
        if actual != expected:
            raise AuditError(f"signal_reconstruction_mismatch@{t}")

    if len(result["equity"]) != len(hours):
        raise AuditError("hourly_curve_length")
    for i, t in enumerate(hours):
        decision(t)
        actual = list(fills_at.get(t, []))
        references = {c:number(indexed[c][t][1]) for c in coins}
        for event in pending.pop(t, []):
            consume(t, event, references, actual)
        if actual:
            raise AuditError("extra_fill")
        closes = {c:number(indexed[c][t][4]) for c in coins}
        if t+HOUR == end_ms:
            actual = list(fills_at.get(end_ms, []))
            consume(end_ms, (end_ms,{c:0.0 for c in coins},"terminal"), closes, actual, True)
            if actual:
                raise AuditError("extra_terminal_fill")
        value, invested = mark(closes)
        point = result["equity"][i]
        if point["timestamp"] != t+HOUR or set(point["positions"]) != set(coins):
            raise AuditError("curve_timestamp_or_assets")
        close(point["cash"], balance, "curve_cash")
        for c in coins:
            close(point["positions"][c], inventory[c], "curve_inventory")
        close(point["equity"], value, "curve_equity")
        exposure = invested/value if value > 0 else 0.0
        close(point["exposure"], exposure, "curve_exposure")
        hourly_values.append(value)
        hourly_exposures.append(exposure)
    if len(result["trades"]) != len(expected_trades):
        raise AuditError("closed_trade_count")
    for expected, actual in zip(expected_trades, result["trades"]):
        for k, v in expected.items():
            if isinstance(v, (int, float)):
                close(actual[k], v, "trade_"+k)
            elif actual[k] != v:
                raise AuditError("trade_"+k)
    m = independent_metrics(hourly_values, initial, len(expected_trades))
    actual_m = result["metrics"]
    for field, expected in (("total_return",m["return"]),("max_drawdown",m["max_drawdown"]),
                            ("final_equity",m["final_equity"]),("closed_trades",m["closed_trades"]),
                            ("fees",fee_sum),("rejected_orders",rejected_count),
                            ("exposure",statistics.mean(hourly_exposures))):
        close(actual_m[field], expected, "metric_"+field)
    daily_closes = {}
    for t, value in zip(hours, hourly_values):
        daily_closes[t//(24*HOUR)] = value
    daily_expected, previous = [], float(initial)
    for day in sorted(daily_closes):
        value = daily_closes[day]
        daily_expected.append({"day_utc":day,"return_fraction":value/previous-1})
        previous = value
    if len(actual_m["daily_returns"]) != len(daily_expected):
        raise AuditError("daily_return_count")
    for actual, expected in zip(actual_m["daily_returns"], daily_expected):
        if actual["day_utc"] != expected["day_utc"]:
            raise AuditError("daily_return_day")
        close(actual["return_fraction"], expected["return_fraction"], "daily_return")
    residuals = {c:q for c,q in inventory.items() if q > 1e-12}
    if set(actual_m["untradeable_residuals"]) != set(residuals):
        raise AuditError("terminal_residual_assets")
    for c, q in residuals.items():
        close(actual_m["untradeable_residuals"][c], q, "terminal_residual_quantity")
    return {"status":"PASS", "coverage":"independent_closed_bar_signals_and_full_ledger",
            "hours":len(hours), "fills":len(result["fills"]),
            "invalid_feature_inputs":invalid_count, "independent_metrics":m,
            "limitations":["current specs are historical proxies", "execution/depth remain model assumptions",
                           "success does not establish blind holdout or profitability"]}
