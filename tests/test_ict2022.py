import unittest

from ict_trader.backtest import Backtester
from ict_trader.ict2022 import ICT2022Strategy
from ict_trader.strategy import SHORT
from tests.helpers import ny_bar, simple_config


def scenario(displacement=True, fill=True):
    """PDH 1.1050 swept in London, displacement through the 1.1025 swing low, bearish FVG
    [1.1038, 1.1042] in premium, retrace fills the sell limit at 1.1038, then price runs
    to PDL 1.1000."""
    f = ("2026-06-03 02:25", 1.1037, 1.1038, 1.1015, 1.1018) if displacement else ("2026-06-03 02:25", 1.1037, 1.1038, 1.1033, 1.1036)
    bars = [
        ny_bar("2026-06-01 18:00", 1.1020, 1.1050, 1.1000, 1.1020),   # prior day: PDH 1.1050 / PDL 1.1000
        ny_bar("2026-06-02 18:00", 1.1030, 1.1040, 1.1010, 1.1035),
        ny_bar("2026-06-03 02:00", 1.1035, 1.1040, 1.1030, 1.1038),
        ny_bar("2026-06-03 02:05", 1.1038, 1.1041, 1.1025, 1.1039),   # swing low 1.1025
        ny_bar("2026-06-03 02:10", 1.1039, 1.1046, 1.1034, 1.1044),
        ny_bar("2026-06-03 02:15", 1.1044, 1.1058, 1.1042, 1.1052),   # sweep of PDH to 1.1058
        ny_bar("2026-06-03 02:20", 1.1052, 1.1055, 1.1040, 1.1041),
        ny_bar(*f),                                                    # displacement + FVG
    ]
    if fill:
        bars.append(ny_bar("2026-06-03 02:30", 1.1018, 1.1039, 1.1016, 1.1035))  # retrace fills 1.1038
    bars += [ny_bar("2026-06-03 02:35", 1.1035, 1.1036, 1.1010, 1.1012),
             ny_bar("2026-06-03 02:40", 1.1012, 1.1014, 1.0995, 1.0998)]          # runs through PDL
    return bars


def config():
    return simple_config(model="nonarrative", flatten_time=None, target_pref="draw")


class ICT2022Test(unittest.TestCase):
    def run_strategy(self, bars):
        cfg = config()
        st = ICT2022Strategy(cfg.strategy, cfg.instrument)
        sigs = [s for b in bars if (s := st.on_bar(b)) is not None]
        return st, sigs

    def test_full_model_sell_limit_fills_in_the_gap(self):
        st, sigs = self.run_strategy(scenario())
        self.assertEqual(len(sigs), 1, [d.message for d in st.decisions])
        s = sigs[0]
        self.assertEqual(s.direction, SHORT)
        self.assertEqual(s.entry_type, "limit")
        self.assertAlmostEqual(s.entry_ref, 1.1038)     # FVG near edge
        self.assertAlmostEqual(s.stop, 1.1059)          # sweep extreme + 1 pip
        self.assertAlmostEqual(s.target, 1.1000)        # PDL, opposing liquidity
        self.assertEqual(s.level.name, "PDH")
        rules = " ".join(s.reasons)
        for rid in ("KZ-1", "SW-01", "MS-02", "FV-01", "EN-01", "SL-01", "TP-01", "TP-02"):
            self.assertIn(rid, rules)

    def test_limit_is_staged_before_it_fills(self):
        st, sigs = self.run_strategy(scenario(fill=False)[:8])
        self.assertEqual(sigs, [])
        self.assertEqual(len(st.staged), 1)
        self.assertAlmostEqual(st.staged[0]["limit"], 1.1038)

    def test_no_displacement_no_trade(self):
        st, sigs = self.run_strategy(scenario(displacement=False))
        self.assertEqual(sigs, [])

    def test_sweep_outside_killzone_is_spent_not_traded(self):
        bars = [b for b in scenario()]
        cfg = simple_config(model="nonarrative", flatten_time=None, killzones=())
        st = ICT2022Strategy(cfg.strategy, cfg.instrument)
        self.assertEqual([s for b in bars if (s := st.on_bar(b)) is not None], [])
        self.assertTrue(any(d.rule == "RL-07" for d in st.decisions))

    def test_backtest_fills_at_limit_and_hits_target(self):
        res = Backtester(config()).run(scenario())
        self.assertEqual(len(res.trades), 1)
        t = res.trades[0]
        self.assertAlmostEqual(t.entry_price, 1.1038)
        self.assertTrue(t.exit_reason.startswith("TP"), t.exit_reason)
        self.assertIn("TP1 partial", t.exit_reason)
        # half at TP1 (1.1015, ~1.1R) and half at TP2 (1.1000, ~1.8R), less the spread
        self.assertGreater(t.r_multiple, 1.3)

    def test_kz01_no_short_when_the_sweep_is_below_the_midnight_open(self):
        cfg = config()
        st = ICT2022Strategy(cfg.strategy, cfg.instrument)
        bars = scenario()
        st.on_bar(bars[0]), st.on_bar(bars[1]), st.on_bar(bars[2])
        st._midnight_open = 1.1070  # a day that opened above the sweep high: not a Judas swing
        self.assertEqual([s for b in bars[3:] if (s := st.on_bar(b)) is not None], [])
        self.assertTrue(any(d.rule == "KZ-01" for d in st.decisions))

    def test_kz01_reason_when_the_sweep_is_above_the_midnight_open(self):
        st, sigs = self.run_strategy(scenario())
        self.assertTrue(any(r.startswith("KZ-01") for r in sigs[0].reasons))

    def test_en04_expiry_is_fifteen_minutes_on_one_minute_charts(self):
        cfg = simple_config(model="nonarrative", timeframe_minutes=1)
        self.assertEqual(ICT2022Strategy(cfg.strategy, cfg.instrument)._expiry_bars(), 15)
        self.assertEqual(ICT2022Strategy(config().strategy, config().instrument)._expiry_bars(), 3)

    def test_sl05_breakeven_after_75_percent_of_the_way(self):
        bars = scenario()[:9] + [
            ny_bar("2026-06-03 02:35", 1.1035, 1.1036, 1.1008, 1.1020),   # 79% of the way to PDL
            ny_bar("2026-06-03 02:40", 1.1020, 1.1045, 1.1018, 1.1044),   # back up through entry
        ]
        cfg = simple_config(model="nonarrative", flatten_time=None, move_be_at_75_pct=True, trim_stop_at_50_pct=True, partial_at_tp1=0, target_pref="draw")
        res = Backtester(cfg).run(bars)
        self.assertEqual(len(res.trades), 1)
        self.assertIn("SL-05", res.trades[0].exit_reason)
        self.assertAlmostEqual(res.trades[0].r_multiple, 0.0, places=1)

    def test_rl05_daily_bias_blocks_a_short_on_a_bullish_day(self):
        # D-2 (trading day 1 Jun) 1.0950-1.1010; D-1 (2 Jun) closed 1.1020, above D-2's high
        bars = [ny_bar("2026-05-31 18:00", 1.0980, 1.1010, 1.0950, 1.0990)] + scenario()
        st, sigs = self.run_strategy(bars)
        self.assertEqual(sigs, [])
        self.assertTrue(any(d.rule == "RL-05" for d in st.decisions))
        self.assertEqual(st.daily_bias()[0], 1)

    def test_rl05_short_allowed_when_yesterday_ran_highs_and_closed_inside(self):
        bars = [ny_bar("2026-05-31 18:00", 1.1010, 1.1040, 1.0990, 1.1030)] + scenario()
        st, sigs = self.run_strategy(bars)
        self.assertEqual(len(sigs), 1)
        self.assertTrue(any(r.startswith("RL-05 daily bias bearish") for r in sigs[0].reasons))

    def test_tp04_partial_at_tp1_then_rest_at_breakeven(self):
        bars = scenario()[:9] + [
            ny_bar("2026-06-03 02:35", 1.1035, 1.1036, 1.1012, 1.1020),   # reaches TP1 1.1015
            ny_bar("2026-06-03 02:40", 1.1020, 1.1045, 1.1018, 1.1044),   # back through entry
        ]
        res = Backtester(config()).run(bars)
        t = res.trades[0]
        self.assertIn("TP-04", t.exit_reason)
        self.assertAlmostEqual(t.r_multiple, 0.5 * 0.0023 / 0.0021, delta=0.1)  # half booked at TP1, rest flat

    def test_ob01_order_block_entry_when_the_displacement_leaves_no_gap(self):
        bars = scenario()[:7] + [
            ny_bar("2026-06-03 02:25", 1.1041, 1.1043, 1.1015, 1.1018),   # displacement, overlaps 02:15 low: no FVG
            ny_bar("2026-06-03 02:30", 1.1018, 1.1051, 1.1016, 1.1040),   # retrace to the OB's 50%
            ny_bar("2026-06-03 02:35", 1.1040, 1.1041, 1.0995, 1.0998),
        ]
        st, sigs = self.run_strategy(bars)
        self.assertEqual(len(sigs), 1, [d.message for d in st.decisions])
        s = sigs[0]
        self.assertAlmostEqual(s.entry_ref, 1.1050)  # mean threshold of the 02:15 up-close candle [1.1042, 1.1058]
        self.assertTrue(any(r.startswith("OB-01") for r in s.reasons))
        self.assertEqual(s.meta["entry_kind"], "ob")


if __name__ == "__main__":
    unittest.main()
