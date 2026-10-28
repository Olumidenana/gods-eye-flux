import json
import unittest
from datetime import datetime, timedelta, timezone

from ict_trader import research as rs
from ict_trader.data import synthetic_bars

NOW = datetime.now(timezone.utc).replace(microsecond=0)


def walk(sym, tf, days):
    return synthetic_bars(NOW - timedelta(days=days), days, timeframe_minutes=tf, price=1000.0, seed=11)


class ResearchTest(unittest.TestCase):
    def test_runs_every_timeframe_and_mode(self):
        for tf in rs.TIMEFRAMES:
            for mode in rs.MODES:
                out = rs.research("R_75", tf, 10 if tf <= 15 else None, mode, fetch=walk)
                self.assertEqual(out["timeframe_minutes"], tf)
                self.assertIn(out["verdict"]["code"], ("edge", "no edge", "unproven", "not enough setups"))
                json.dumps(out)
                from ict_trader import management
                self.assertEqual([m["partial"] for m in out["management"]][:2], [management.plan(tf, "ict2022")["partial_at_tp1"], 0.0])
                self.assertTrue(all(m["trades"] == out["stats"]["trades"] for m in out["management"][2:]))  # same entries, other exits
                self.assertEqual(out["management"][0]["trades"], out["stats"]["trades"])
                self.assertEqual(len(out["trade_charts"]), min(rs.TRADE_CHARTS_MAX, out["stats"]["trades"]))
                self.assertEqual(len(out["r_list"]), out["stats"]["trades"])
                self.assertEqual(len(out["g_list"]), out["stats"]["trades"])
                self.assertTrue(set(out["g_list"]) <= {"A+", "A", "B", "C"})
                sp = out["split"]
                self.assertEqual(sp["older"]["trades"] + sp["recent"]["trades"], out["stats"]["trades"])  # every trade in one half
                self.assertIn(sp["holds"], (True, False, None))
                for key in ("by_weekday", "by_hour", "by_date"):  # every trade counted once in each breakdown
                    self.assertEqual(sum(v["trades"] for v in out[key].values()), out["stats"]["trades"])
                for t in out["trade_charts"]:
                    self.assertTrue(t["candles"] and t["time_ny"] and t["outcome"]["status"] in ("win", "loss", "breakeven"))

    def test_allday_mode_trades_at_any_hour_without_flatten(self):
        cfg = rs.build_config(rs.Market("R_75", "V75", "", "", "", 0, "", "synthetic"), walk("R_75", 5, 5), 5, "allday")
        self.assertEqual(cfg.strategy.killzones[0].name, "all_day")
        self.assertIsNone(cfg.strategy.flatten_time)
        self.assertEqual(cfg.strategy.timeframe_minutes, 5)

    def test_time_models_need_a_time_filter(self):
        # with no time filter, Silver Bullet and Judas Swing would just repeat the ICT 2022 Model's trades
        for model in ("silver_bullet", "judas_swing"):
            for tf, mode in ((5, "allday"), (60, "ict")):
                with self.assertRaises(ValueError):
                    rs.research("R_75", tf, None, mode, fetch=walk, model=model)
            with self.assertRaises(ValueError):   # a synthetic index has no killzones, so "ICT hours" is no time filter there either
                rs.research("R_75", 5, 10, "ict", fetch=walk, model=model)
            self.assertEqual(rs.research("EURUSD", 5, 10, "ict", fetch=walk, model=model)["model"], model)
        out = rs.research("R_75", 5, 10, "allday", fetch=walk)
        self.assertEqual(len(out["r_keys"]), len(out["r_list"]))

    def test_how_far_trades_went_and_fixed_targets(self):
        from ict_trader.metrics import Trade
        from ict_trader.sessions import Bar
        t0 = NOW
        # a long from 100, stop 99 (1R = 1), own target 110: rises to +2.5R, then falls back to the stop
        path = [(100, 100.5, 99.8), (100.4, 101.2, 100.3), (101.1, 102.5, 101.0), (102.4, 102.4, 100.5), (100.5, 100.6, 98.9)]
        bars = [Bar(t0 + timedelta(minutes=5 * i), o, h, lo, lo) for i, (o, h, lo) in enumerate(path)]
        t = Trade("X", 1, t0, 100.0, 99.0, 110.0, 1, 1, bars[-1].time, 99.0, "SL stop loss", -1, -1.0, ())
        self.assertAlmostEqual(rs._excursion([t], bars)[0], 2.5)
        self.assertEqual(rs._fixed_exit([t], bars, 0.0, 2.0), [2.0])   # a 2R target would have been hit
        self.assertEqual(rs._fixed_exit([t], bars, 0.0, 3.0), [-1.0])  # 3R never came
        self.assertEqual(rs._fixed_exit([t], bars, 0.0, 0, half_at=2.0), [1.0])  # half at 2R, rest stopped at entry
        near = Trade("X", 1, t0, 100.0, 99.0, 101.0, 1, 1, bars[-1].time, 99.0, "SL stop loss", -1, -1.0, ())
        self.assertEqual(rs._fixed_exit([near, t], bars, 0.0, 0, half_at=2.0), [1.0, 1.0])  # a near target never changes the next trade's rule
        out = rs.research("R_75", 5, 30, "allday", fetch=walk)
        self.assertEqual([m["name"] for m in out["management"]][2:], [
            "Fixed target at 2R", "Fixed target at 3R", "Fixed target at 5R", "Fixed target at 10R",
            "Fixed target at 20R (runner)", "Half off at 2R, stop to entry, rest to final target",
            "Half off at 3R, stop to entry, rest to 10R runner",
        ])
        self.assertEqual([x["r"] for x in out["reach"]["levels"]], [0.5, 1, 2, 3, 5, 8, 10, 15, 20])

    def test_rejects_unknown_timeframe(self):
        with self.assertRaises(ValueError):
            rs.research("R_75", 4, 10, "ict", fetch=walk)

    def test_history_pages_back_over_one_connection(self):
        # fetch_deriv_history cuts off at the real clock, so the fake feed must end now too
        NOW = datetime.now(timezone.utc)
        start = int((NOW - timedelta(days=3)).timestamp())

        class FakeWS:
            def __init__(self):
                self.out = []
            def send(self, raw):
                r = json.loads(raw)
                end = int(NOW.timestamp()) if r["end"] == "latest" else r["end"]
                c = [{"epoch": t, "open": 1, "high": 2, "low": 0.5, "close": 1.5} for t in range(end - 300 * 500, end, 300) if t >= start - 3000]
                self.out.append(json.dumps({"req_id": r["req_id"], "candles": c}))
            def recv(self):
                return self.out.pop(0)
            def close(self):
                pass

        bars = rs.fetch_deriv_history("R_75", 5, 3, connect=lambda url: FakeWS())
        self.assertGreater(len(bars), 500)  # more than one 500-candle page
        self.assertEqual(len(bars), len({b.time for b in bars}))


if __name__ == "__main__":
    unittest.main()
