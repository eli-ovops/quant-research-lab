"""Synthetic audit tests: do not load research/confirmation data or write artifacts."""
import copy
import unittest

import replay


def rows(prices, start=0):
    return [[start+i*replay.HOUR, str(p), str(p*1.01), str(p*.99),
             str(p), "100", "100", "100", "1"] for i, p in enumerate(prices)]


class IndependentPrimitives(unittest.TestCase):
    def test_decimal_rounding_and_adverse_slip(self):
        spec = {"tickSz": "0.05", "lotSz": "0.001", "minSz": "0.001"}
        self.assertEqual(replay.price(10, "buy", {"slip": .001}, spec), 10.05)
        self.assertEqual(replay.price(10, "sell", {"slip": .001}, spec), 9.95)
        self.assertEqual(replay.rounded("0.009999999", ".001"), .009)

    def test_close_bar_availability_and_no_future_input(self):
        indexed = replay.index_data({"BTC": rows([100]*528)})
        bars = replay.four_hour_bars(indexed)["BTC"]
        self.assertEqual(bars[0]["timestamp"], 4*replay.HOUR)
        candidate = {"family": "trend", "entry_bars": 12, "exit_bars": 3}
        before = replay.primitive_signals(indexed, candidate)
        changed = copy.deepcopy(indexed)
        # Final hour affects final signal only, never an earlier closed bar.
        changed["BTC"][527*replay.HOUR][4] = "100.5"
        after = replay.primitive_signals(changed, candidate)
        for key in before:
            if key[1] < 528*replay.HOUR:
                self.assertEqual(before[key], after[key])

    def test_zero_volume_blocks_complete_rotation_dependency(self):
        raw = rows([100+i*.01 for i in range(1024)])
        raw[12][5] = "0"
        triggers = replay.primitive_signals(replay.index_data({"BTC": raw}), {
            "family": "rotation", "lookback_bars": 126,
            "top_k": 1, "rebalance_bars": 6})
        self.assertEqual(triggers["BTC", 127*replay.BAR],
                         {"invalid_feature_input": True})
        self.assertNotIn("invalid_feature_input", triggers["BTC", 131*replay.BAR])

    def test_independent_drawdown_includes_initial_equity(self):
        m = replay.independent_metrics([95, 110, 88, 99], 100, 2)
        self.assertAlmostEqual(m["max_drawdown"], .2)
        self.assertAlmostEqual(m["return"], -.01)
        self.assertEqual(m["closed_trades"], 2)

    def test_bad_candles_rejected(self):
        raw = rows([100]*4)
        raw[0][8] = "0"
        with self.assertRaises(replay.AuditError):
            replay.index_data({"BTC": raw})


class LedgerCrossCheck(unittest.TestCase):
    def setUp(self):
        # Only test fixtures call engine; replay itself never imports it.
        from engine import run
        self.run_engine = run
        self.coins = ["BTC", "ETH", "SOL", "XRP", "DOGE", "ADA", "LINK", "LTC"]
        self.specs = {c:{"tickSz":".01","lotSz":".001","minSz":".001"}
                      for c in self.coins}
        self.cost = {"fee":.002,"slip":.001,"delay_hours":1}

    def fixture(self, mode="trend"):
        data = {}
        for rank, c in enumerate(self.coins):
            prices = []
            for hour in range(180*4):
                b = hour//4
                if mode == "reversion":
                    p = (110 if b < 106 else
                         110-(b-106)*1.5 if b < 126 else
                         65 if b == 126 else 85)
                elif mode == "rotation":
                    p = 100 + b*(.01+.02*rank) if b < 145 else 200+(b-145)*(.2-.02*rank)
                else:
                    p = 100+b*.4 if b < 145 else 158-(b-145)*1.1
                prices.append(p)
            data[c] = rows(prices)
            for row in data[c]:
                p = float(row[1])
                row[2], row[3] = str(p+.02), str(p-.02)
        return data

    def checked(self, family, data=None, specs=None):
        candidate = {"family":family, "entry_bars":12,"exit_bars":3,
                     "band_bars":20,"z":1.5,"hold_bars":6,
                     "lookback_bars":126,"top_k":2,"rebalance_bars":6}
        data = data if data is not None else self.fixture(family)
        specs = self.specs if specs is None else specs
        start, end = 126*replay.BAR, 175*replay.BAR
        result = self.run_engine(data, specs, candidate, self.cost, start, end)
        audit = replay.verify(data,specs,candidate,self.cost,start,end,result)
        self.assertEqual(audit["status"], "PASS")
        return data, specs, candidate, start, end, result

    def test_all_three_families_and_controls(self):
        for family in ("trend","reversion","rotation","hold","cash"):
            with self.subTest(family=family):
                *_, result = self.checked(family)
                if family not in ("cash",):
                    self.assertGreater(result["metrics"]["closed_trades"], 0)

    def test_lot_minimum_rejection_and_dust(self):
        specs = {c:dict(s,minSz="1000000") for c,s in self.specs.items()}
        *_, result = self.checked("hold",specs=specs)
        self.assertGreater(result["metrics"]["rejected_orders"],0)
        self.assertEqual(result["metrics"]["closed_trades"],0)
        *_, normal = self.checked("hold")
        self.assertTrue(normal["metrics"]["untradeable_residuals"])

    def test_mutated_cash_signal_price_and_metric_fail_closed(self):
        data,specs,candidate,start,end,result = self.checked("trend")
        for mutation in ("cash", "signal", "price", "drawdown", "missing_fill"):
            altered = copy.deepcopy(result)
            if mutation == "cash":
                altered["equity"][3]["cash"] += 1
            elif mutation == "signal":
                altered["signals"][0]["execution_timestamp"] -= replay.HOUR
            elif mutation == "price":
                altered["fills"][0]["price"] += .01
            elif mutation == "drawdown":
                altered["metrics"]["max_drawdown"] += .01
            else:
                altered["fills"].pop(0)
            with self.subTest(mutation=mutation), self.assertRaises(replay.AuditError):
                replay.verify(data,specs,candidate,self.cost,start,end,altered)

    def test_zero_guard_and_trading_period_hard_failure(self):
        data = self.fixture("rotation")
        data["BTC"][18*4][5] = "0"
        *_, result = self.checked("rotation", data=data)
        self.assertTrue(any(s["reason"] == "invalid_feature_input" for s in result["signals"]))
        data["BTC"][127*4][5] = "0"
        with self.assertRaises(replay.AuditError):
            self.checked("rotation",data=data)


if __name__ == "__main__":
    unittest.main()
