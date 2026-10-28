import unittest
from dataclasses import replace
from datetime import date, datetime, timedelta, timezone

from ict_trader.config import load_config
from ict_trader.ict2022 import ICT2022Strategy
from ict_trader.models import LAB_MODELS, MODELS, make_strategy, resolve
from ict_trader.sessions import Bar

T0 = datetime(2026, 10, 5, 12, tzinfo=timezone.utc)  # a Monday


def strat(**kw):
    cfg = load_config("examples/config.example.toml")
    return ICT2022Strategy(replace(cfg.strategy, model="ict2022", **kw), cfg.instrument)


def bar(i, o, h, lo, c):
    return Bar(T0 + timedelta(minutes=5 * i), o, h, lo, c)


class ContextTest(unittest.TestCase):
    def test_every_new_model_builds_and_runs(self):
        cfg = load_config("examples/config.example.toml")
        for m in LAB_MODELS:
            s = make_strategy(replace(cfg.strategy, model=m), cfg.instrument)
            for i in range(30):
                s.on_bar(bar(i, 100, 100.5, 99.5, 100.2))
        self.assertTrue(set(LAB_MODELS) <= set(MODELS))
        self.assertTrue(resolve(replace(cfg.strategy, model="full")).htf_context)
        self.assertTrue(resolve(replace(cfg.strategy, model="full")).fvg_quality)
        self.assertTrue(resolve(replace(cfg.strategy, model="pools")).liquidity_pools)

    def test_weekly_bias_reads_the_last_two_completed_weeks(self):
        s = strat(htf_context=True)
        d0 = date(2026, 9, 14)  # Monday
        # week 1 (14-18): range 100-110; week 2 (21-25): closes above week 1's high -> bullish
        for k in range(5):
            s._days[d0 + timedelta(days=k)] = [105, 110, 100, 105]
        for k in range(5):
            s._days[d0 + timedelta(days=7 + k)] = [111, 115, 108, 114]
        s._days[date(2026, 9, 28)] = [114, 116, 113, 115]  # the forming week
        self.assertEqual(s.weekly_bias()[0], 1)
        self.assertEqual(s._htf_ranges()["week"], (115, 108))
        s._days[date(2026, 9, 21)] = [105, 109, 98, 101]  # week 2 now runs week 1's low and closes back inside
        for k in range(1, 5):
            s._days[date(2026, 9, 21) + timedelta(days=k)] = [101, 109, 98, 101]
        self.assertEqual(s.weekly_bias()[0], 1)  # ran the low of week 1 (100) and closed back inside
        self.assertEqual(strat().weekly_bias()[0], 0)  # no history: no draw

    def test_pools_track_swings_and_merge_equal_highs(self):
        s = strat(liquidity_pools=True, pool_equal_range=0.5)
        pts = [(100, 101, 99, 100), (100, 102, 99.5, 101), (101, 101.5, 100, 100.5),   # swing high 102
               (100.5, 101.8, 100, 101), (101, 101.95, 100.5, 101.5), (101.2, 101.4, 100.2, 100.6)]  # swing high 101.95 ~ equal, not taken
        for i, p in enumerate(pts):
            s.on_bar(bar(i, *p))
        names = [lv.name for lv, _ in s._pools]
        self.assertTrue(any(n.startswith("EQH") for n in names), names)
        self.assertEqual(sum(1 for lv, _ in s._pools if lv.side == "high"), 1)
        self.assertEqual(max(lv.price for lv, _ in s._pools if lv.side == "high"), 102)  # the equal highs sit at the higher one
        off = strat()
        for i, p in enumerate(pts):
            off.on_bar(bar(i, *p))
        self.assertEqual(off._pools, [])  # switched off: nothing tracked

    def test_fvg_quality_skips_tiny_and_mitigated_gaps(self):
        base = [bar(i, 100, 101, 99, 100) for i in range(22)]
        for q in (False, True):
            s = strat(fvg_quality=q)
            for b in base:
                s.on_bar(b)
            # a bearish leg leaving a 0.1 gap (median range is 2): c1.low 98.0, c3.high 97.9
            s.on_bar(bar(22, 99, 99.5, 98.0, 98.2))
            s.on_bar(bar(23, 98.2, 98.3, 96.0, 96.2))
            s.on_bar(bar(24, 96.2, 97.9, 95.0, 95.2))
            gap = s._fvg_in_leg(-1, 22, 24)
            self.assertEqual(gap is None, q, (q, gap))


if __name__ == "__main__":
    unittest.main()


class OpeningTest(unittest.TestCase):
    def _run(self, model, after):
        from ict_trader.models import make_strategy
        cfg = load_config("examples/config.example.toml")
        st = replace(cfg.strategy, model=model, timeframe_minutes=1, midnight_open_filter=False, daily_bias_filter=False)
        s = make_strategy(st, cfg.instrument)
        s._story_against = lambda d: None   # these tests are about the gap: the story gate has its own test (test_patterns)
        t, sigs = datetime(2026, 10, 5, 4, tzinfo=timezone.utc), []
        flat = []
        while t < datetime(2026, 10, 6, 13, 30, tzinfo=timezone.utc):       # to 09:30 NY on the Tuesday
            hi = 1.1100 if t == datetime(2026, 10, 5, 15, tzinfo=timezone.utc) else 1.1003
            flat.append(Bar(t, 1.1000, hi, 1.0997, 1.1000))
            t += timedelta(minutes=1)
        t0 = t
        pts = after
        for i, p in enumerate(pts):
            flat.append(Bar(t0 + timedelta(minutes=i), *p))
        for b in flat:
            x = s.on_bar(b)
            if x:
                sigs.append(x)
        return s, sigs

    def test_first_presented_fvg_enters_at_the_midpoint(self):
        # 09:30 candle, a strong up candle, then a candle whose low is above the first candle's high: a bullish gap
        s, sigs = self._run("fpfvg", [(1.1000, 1.1006, 1.1000, 1.1004), (1.1004, 1.1030, 1.1005, 1.1028),
                                      (1.1028, 1.1032, 1.1012, 1.1030), (1.1030, 1.1031, 1.1008, 1.1012)])
        self.assertEqual(len(sigs), 1, [d.message for d in s.decisions][-4:])
        sig = sigs[0]
        self.assertEqual(sig.direction, 1)
        self.assertAlmostEqual(sig.entry_ref, 1.1009, places=5)           # 50% of [1.1006, 1.1012]
        self.assertAlmostEqual(sig.stop, 1.0999, places=5)                # a pip beyond the candle that started the move
        self.assertAlmostEqual(sig.target, 1.1100, places=5)              # the prior day's high
        self.assertTrue(sig.reasons[0].startswith("FP-01"))

    def test_only_the_first_gap_counts_and_a_close_through_the_midpoint_cancels(self):
        # first gap forms, then a body closes below its midpoint before any fill
        s, sigs = self._run("fpfvg", [(1.1000, 1.1006, 1.1000, 1.1004), (1.1004, 1.1030, 1.1005, 1.1028),
                                      (1.1028, 1.1032, 1.1012, 1.1030), (1.1030, 1.1031, 1.1020, 1.1021),
                                      (1.1021, 1.1022, 1.1015, 1.1016)])
        self.assertEqual(sigs, [])
        # no gap in the first half hour at all: nothing is staged
        s2, sigs2 = self._run("fpfvg", [(1.1000, 1.1006, 1.0998, 1.1004)] * 6)
        self.assertEqual((sigs2, s2._setups), ([], []))

    def test_opening_gaps_are_found_and_used_as_levels(self):
        from ict_trader.models import make_strategy
        cfg = load_config("examples/config.example.toml")
        s = make_strategy(replace(cfg.strategy, model="gaps", timeframe_minutes=5), cfg.instrument)
        t = datetime(2026, 10, 5, 4, tzinfo=timezone.utc)                  # Monday
        for _ in range(100):                                                 # build a median range
            s.on_bar(Bar(t, 1.1000, 1.1004, 1.0996, 1.1000)); t += timedelta(minutes=5)
        # 17:00 NY Monday = 21:00 UTC; close at 1.1000, the 18:00 NY bar opens at 1.1030: a new-day gap
        while t < datetime(2026, 10, 5, 22, tzinfo=timezone.utc):
            s.on_bar(Bar(t, 1.1000, 1.1004, 1.0996, 1.1000)); t += timedelta(minutes=5)
        s.on_bar(Bar(t, 1.1030, 1.1034, 1.1026, 1.1030))
        self.assertTrue(any(g["kind"] == "NDOG" and abs(g["hi"] - 1.1030) < 1e-9 for g in s._gaps), s._gaps)
        names = [lv.name for lv in s._gap_levels()]
        self.assertTrue(any(n.startswith("NDOG") and n.endswith("H") for n in names), names)
        self.assertEqual(replace(cfg.strategy, model="ict2022").opening_gaps, False)  # off unless the model asks for it


class RegimeTest(unittest.TestCase):
    def test_obstacles_count_unmitigated_opposing_gaps_in_the_path(self):
        s = strat(regime_filter=True)
        # a bearish gap between 105 and 106 (candle 1 low 106, candle 3 high 105), still untouched
        pts = [(110, 110.5, 106, 107), (107, 107.2, 104, 104.5), (104.5, 105, 103, 104), (103.5, 104, 102, 103), (103, 103.5, 102, 103)]
        for i, p in enumerate(pts):
            s.on_bar(bar(i, *p))
        self.assertEqual(s._obstacles(1, 103.0, 112.0, len(pts) - 1), 1)   # a long from 103 to 112 has the gap in its way
        self.assertEqual(s._obstacles(1, 103.0, 104.5, len(pts) - 1), 0)   # a target short of the gap does not
        s.on_bar(bar(5, 103, 106.5, 103, 106))                              # price trades up through the gap's midpoint: mitigated
        self.assertEqual(s._obstacles(1, 103.0, 112.0, len(pts)), 0)

    def test_seek_and_destroy_needs_alternating_failed_sweeps(self):
        s = strat(regime_filter=True)
        base = [(100, 101, 99, 100)] * 14
        for i, p in enumerate(base):
            s.on_bar(bar(i, *p))
        self.assertFalse(s._seek_destroy(len(base) - 1))
        seq = [(100, 102, 99.5, 100.5), (100.5, 101, 99.5, 100.2), (100.2, 100.5, 98, 100.1), (100.1, 100.6, 99.4, 100.2),
               (100.2, 103, 99.8, 100.4), (100.4, 100.9, 99.6, 100.2), (100.2, 100.6, 96.5, 100.3)]
        for j, p in enumerate(seq):
            s.on_bar(bar(len(base) + j, *p))
        self.assertTrue(s._seek_destroy(len(base) + len(seq) - 1))        # high run and failed, low run and failed, high, low

    def test_new_models_resolve(self):
        cfg = load_config("examples/config.example.toml")
        self.assertTrue(resolve(replace(cfg.strategy, model="clear")).regime_filter)
        self.assertTrue(resolve(replace(cfg.strategy, model="dayopen")).day_open_rule)
        full = resolve(replace(cfg.strategy, model="full"))
        self.assertTrue(full.regime_filter and full.day_open_rule and full.opening_gaps and full.htf_context)


class SelectorTest(unittest.TestCase):
    def test_priors_pick_models_that_suit_the_conditions(self):
        from ict_trader import selector
        avail = ["ict2022", "ote", "sweep", "sdt", "fpfvg", "clear", "silver_bullet"]
        trend = selector.recommend({"trend": "trending", "vol": "normal", "draw": "up", "phase": "killzone", "path": "clear"}, avail, evidence={})
        self.assertIn(trend["ranked"][0]["model"], ("ict2022", "ote"))   # a clear draw in a trend: the story-led models
        opening = selector.recommend({"trend": "mixed", "phase": "open", "draw": "none"}, avail, evidence={})
        self.assertEqual(opening["ranked"][0]["model"], "fpfvg")
        rng = selector.recommend({"trend": "ranging", "phase": "killzone", "draw": "none", "vol": "normal"}, avail, evidence={})
        self.assertEqual(rng["ranked"][0]["model"], "sweep")
        aside = selector.recommend({"path": "seek", "trend": "ranging"}, avail, evidence={})
        self.assertTrue(aside["stand_aside"])
        self.assertEqual(aside["ranked"][0]["model"], "clear")  # the one that helps on such a day
        off = selector.recommend({"phase": "off"}, avail, evidence={})
        self.assertNotIn(off["ranked"][0]["model"], ("fpfvg", "silver_bullet"))  # time models are last outside their windows

    def test_lab_evidence_outweighs_the_prior_once_there_are_enough_trades(self):
        from ict_trader import selector
        conds = {"trend": "ranging", "phase": "killzone", "draw": "none"}
        base = selector.recommend(conds, ["sweep", "ote"], evidence={})["ranked"][0]["model"]
        self.assertEqual(base, "sweep")
        lab = {"EURUSD": {"sweep": {"trend": {"ranging": {"trades": 120, "expectancy_r": -0.6}}},
                          "ote": {"trend": {"ranging": {"trades": 120, "expectancy_r": 0.6}}}}}
        better = selector.recommend(conds, ["sweep", "ote"], key="frxEURUSD", evidence=lab)
        self.assertEqual(better["ranked"][0]["model"], "ote")                  # measured results move it
        few = {"EURUSD": {"ote": {"trend": {"ranging": {"trades": 5, "expectancy_r": 0.9}}}}}
        self.assertEqual(selector.recommend(conds, ["sweep", "ote"], key="EURUSD", evidence=few)["ranked"][0]["model"], "sweep")  # 5 trades is not evidence

    def test_conditions_are_read_from_price(self):
        from ict_trader import conditions as cn
        up = [100 + i * 0.5 for i in range(49)]
        flat = [100 + (0.3 if i % 2 else -0.3) for i in range(49)]
        self.assertEqual(cn.label_trend(up), "trending")
        self.assertEqual(cn.label_trend(flat), "ranging")
        self.assertIsNone(cn.label_trend(up[:10]))
        self.assertEqual(cn.parse([cn.tag({"trend": "trending", "vol": "high", "draw": "with", "phase": "open", "path": "clear"})]),
                         {"trend": "trending", "vol": "high", "draw": "with", "phase": "open", "path": "clear"})

    def test_new_models_weekly_and_measured_targets_resolve(self):
        cfg = load_config("examples/config.example.toml")
        self.assertTrue(resolve(replace(cfg.strategy, model="weekly")).weekly_profile)
        self.assertTrue(resolve(replace(cfg.strategy, model="sdt")).sd_targets)


class ReentryAndSeedTest(unittest.TestCase):
    def test_a_stop_out_that_price_runs_past_re_arms_the_idea(self):
        from ict_trader.sessions import Level
        cfg = load_config("examples/config.example.toml")
        base = replace(cfg.strategy, model="ict2022", reentry=True, midnight_open_filter=False, daily_bias_filter=False)
        killzone = base.killzones[0]
        t0 = datetime(2026, 10, 6, killzone.start.hour + 4, 5, tzinfo=timezone.utc)  # NY is UTC-4: inside the first killzone
        s = ICT2022Strategy(base, cfg.instrument)
        for i in range(30):
            s.on_bar(Bar(t0 + timedelta(minutes=5 * i), 100, 100.4, 99.6, 100.1))
        i = 30
        lvl = Level("PDH", 100.5, "high")
        s._live.append({"d": -1, "stop": 101.0, "target": 98.0, "level": lvl, "bar": i - 1})   # a short filled earlier
        s.on_bar(Bar(t0 + timedelta(minutes=5 * i), 100.1, 101.3, 100.0, 100.4))             # runs through the stop
        self.assertEqual(s._live, [])
        self.assertEqual(s._extra_signals, 1)
        self.assertTrue(any(x.stage == "await_mss" and x.direction == -1 and x.extreme == 101.3 for x in s._setups))
        self.assertTrue(any(d.rule == "RE-01" for d in s.decisions))
        self.assertTrue(any(x.reentry and x.sweep_index == i for x in s._setups))      # the second try is marked, so it can be sized down and labelled
        # a trade that reaches its target is just closed: no re-entry
        s2 = ICT2022Strategy(base, cfg.instrument)
        for j in range(30):
            s2.on_bar(Bar(t0 + timedelta(minutes=5 * j), 100, 100.4, 99.6, 100.1))
        s2._live.append({"d": -1, "stop": 101.0, "target": 99.0, "level": lvl, "bar": 29})
        s2.on_bar(Bar(t0 + timedelta(minutes=150), 100.1, 100.2, 98.8, 99.0))
        self.assertEqual((s2._live, s2._extra_signals), ([], 0))
        # off unless the model asks for it
        s3 = ICT2022Strategy(replace(base, reentry=False), cfg.instrument)
        for j in range(30):
            s3.on_bar(Bar(t0 + timedelta(minutes=5 * j), 100, 100.4, 99.6, 100.1))
        s3.on_bar(Bar(t0 + timedelta(minutes=150), 100.1, 101.3, 100.0, 100.4))
        self.assertEqual(s3._extra_signals, 0)

    def test_daily_candles_give_the_live_scan_its_weekly_and_ipda_context(self):
        cfg = load_config("examples/config.example.toml")
        s = ICT2022Strategy(replace(cfg.strategy, model="ict2022", htf_context=True), cfg.instrument)
        daily, start = [], datetime(2026, 7, 20, tzinfo=timezone.utc)   # a Monday
        for k in range(70):
            day = start + timedelta(days=k)
            if day.weekday() < 5:
                daily.append(Bar(day, 100 + k * 0.1, 101 + k * 0.1, 99 + k * 0.1, 100.5 + k * 0.1))
        self.assertEqual(s.weekly_bias()[0], 0)                             # no history yet
        s.seed_days(daily, before=date(2026, 9, 28))
        s.on_bar(Bar(datetime(2026, 9, 28, 12, tzinfo=timezone.utc), 108, 108.5, 107.5, 108))   # one live candle
        self.assertEqual(s.weekly_bias()[0], 1)                             # rising weeks: bullish draw
        r = s._htf_ranges()
        self.assertEqual(sorted(r["ipda_all"]), [20, 40, 60])
        self.assertGreater(r["ipda_all"][60][0] - r["ipda_all"][60][1], r["ipda_all"][20][0] - r["ipda_all"][20][1])
        self.assertTrue({"IPDA20_H", "IPDA40_L", "IPDA60_H"} <= {lv.name for lv in s._htf_levels()})


class ClearRoadTest(unittest.TestCase):
    """The road to the draw is clear only when no opposing PD array of any kind stands on it."""

    def _setup(self, arrays=(), htf=()):
        from types import SimpleNamespace as NS
        from unittest import mock
        s = strat(regime_filter=True)
        for i in range(6):
            s.on_bar(bar(i, 100, 100.5, 99.5, 100))
        h = NS(tfs=(60,), all_tfs=(60,), arrays=lambda tf: list(htf)) if htf else None
        patches = [mock.patch("ict_trader.ict2022.scan_pd_arrays", lambda bars, lookback=60: list(arrays)), mock.patch.object(s, "_htf", lambda: h)]
        for p in patches:
            p.start(); self.addCleanup(p.stop)
        return s

    def _pd(self, kind, direction, bottom, top, **kw):
        from ict_trader.pd_arrays import PDArray
        return PDArray(kind, direction, top, bottom, (top + bottom) / 2, 2, T0, **kw)

    def test_every_kind_of_opposing_array_is_an_obstacle(self):
        for kind in ("order_block", "breaker", "ifvg", "volume_imbalance"):
            s = self._setup([self._pd(kind, -1, 104, 105)])
            self.assertEqual(s._obstacles(1, 101.0, 110.0, 5), 1, kind)

    def test_arrays_that_do_not_block_are_not_counted(self):
        pd = self._pd
        cases = {
            "same direction as the trade": pd("order_block", 1, 104, 105),
            "already mitigated": pd("breaker", -1, 104, 105, mitigated=True),
            "broken through": pd("order_block", -1, 104, 105, broken=True),
            "behind the entry": pd("order_block", -1, 96, 97),
            "past the target": pd("order_block", -1, 111, 112),
            "a plain gap (counted by the gap scan)": pd("fvg", -1, 104, 105),
        }
        for why, a in cases.items():
            self.assertEqual(self._setup([a])._obstacles(1, 101.0, 110.0, 5), 0, why)

    def test_a_sliver_is_noise_not_a_wall(self):
        self.assertEqual(self._setup([self._pd("volume_imbalance", -1, 104, 104.1)])._obstacles(1, 101.0, 110.0, 5), 0)

    def test_a_short_meets_the_bullish_arrays_below_it(self):
        s = self._setup([self._pd("order_block", 1, 95, 96), self._pd("order_block", -1, 95, 96)])
        self.assertEqual(s._obstacles(-1, 101.0, 90.0, 5), 1)

    def test_overlapping_arrays_are_one_obstacle_and_separate_ones_are_two(self):
        pd = self._pd
        one = self._setup([pd("order_block", -1, 104, 106), pd("breaker", -1, 105, 107)])
        self.assertEqual(one._obstacles(1, 101.0, 110.0, 5), 1)
        two = self._setup([pd("order_block", -1, 104, 105), pd("breaker", -1, 107, 108)])
        self.assertEqual(two._obstacles(1, 101.0, 110.0, 5), 2)

    def test_higher_timeframe_arrays_in_the_path_count_and_merge_with_local_ones(self):
        from types import SimpleNamespace as NS
        arr = lambda d, lo, hi: NS(dir=d, lo=lo, hi=hi)
        s = self._setup(htf=[arr(-1, 104, 105), arr(1, 106, 107)])
        self.assertEqual(s._obstacles(1, 101.0, 110.0, 5), 1)        # only the opposing one
        s = self._setup([self._pd("order_block", -1, 104.5, 106)], htf=[arr(-1, 104, 105)])
        self.assertEqual(s._obstacles(1, 101.0, 110.0, 5), 1)        # the same wall seen on two timeframes
        s = self._setup([self._pd("order_block", -1, 107, 108)], htf=[arr(-1, 104, 105)])
        self.assertEqual(s._obstacles(1, 101.0, 110.0, 5), 2)
