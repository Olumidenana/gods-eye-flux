"""Top-down: the higher timeframe says where price may turn; the entry zone has to be there (htf.py, ict2022._htf_poi)."""

import unittest

from ict_trader.htf import HtfArrays
from ict_trader.ict2022 import ICT2022Strategy
from ict_trader.sessions import Level
from tests.helpers import ny_bar, simple_config


def hour(hh, o, h, l, c, day=3):  # noqa: E741
    """Twelve 5-minute candles that make one 1-hour candle with exactly this open, high, low and close (New York time)."""
    mid = min(max((o + c) / 2, l), h)
    return [ny_bar(f"2026-06-{day:02d} {hh:02d}:{k * 5:02d}", o if k == 0 else mid, h if k == 3 else max(mid, o if k == 0 else mid) + 0.001,
                   l if k == 6 else min(mid, c if k == 11 else mid) - 0.001, c if k == 11 else mid) for k in range(12)]


def feed(h, hours):
    for hr in hours:
        for b in hr:
            h.feed(b)


# a dummy first hour (the first bucket is a partial candle and is not used), then a bullish gap: H0 high 101, H2 low 103
BULL = [hour(7, 99, 100, 98, 99.5), hour(8, 101, 101, 99.5, 100), hour(9, 100.5, 106, 100, 105), hour(10, 105, 108, 103, 107)]


class ArrayTests(unittest.TestCase):
    def test_a_bullish_gap_and_its_order_block_are_found_once_the_third_candle_has_closed(self):
        h = HtfArrays((60,))
        feed(h, BULL)
        self.assertEqual(h.arrays(60), [])                       # the 10:00 candle is still forming: nothing is known from it yet (no look-ahead)
        feed(h, [hour(11, 107, 108, 106, 107)[:1]])              # its first candle closes the 10:00 one
        arrays = h.arrays(60)
        self.assertTrue(any(a.kind == "FVG" and a.dir == 1 and abs(a.lo - 101) < 0.01 and abs(a.hi - 103) < 0.01 for a in arrays))
        self.assertTrue(any(a.kind == "OB" and a.dir == 1 and a.lo < 101 for a in arrays))   # the down-close candle before the rally

    def test_a_gap_that_price_has_closed_through_is_gone(self):
        h = HtfArrays((60,))
        feed(h, BULL + [hour(11, 107, 108, 100, 100.5), hour(12, 100.5, 101, 100, 100.8)[:1]])   # the 11:00 candle closes at 100.5, under the gap's 101
        self.assertEqual([a for a in h.arrays(60) if a.kind == "FVG" and a.dir == 1], [])

    def test_at_finds_the_array_a_zone_sits_in_and_respects_direction(self):
        h = HtfArrays((60,))
        feed(h, BULL + [hour(11, 107, 108, 106, 107)[:1]])
        self.assertIsNotNone(h.at(1, 101.2, 102.5))              # a buy zone inside the bullish gap
        self.assertIsNone(h.at(-1, 101.2, 102.5))                # a sell there is not at a bearish array
        self.assertIsNone(h.at(1, 110.0, 110.5))                 # nowhere near any array

    def test_four_hour_candles_open_at_17_and_every_four_hours_after(self):
        h = HtfArrays((240,))
        for hh in (16, 17, 18, 19, 20, 21):
            for b in hour(hh, 100, 101, 99, 100):
                h.feed(b)
        self.assertEqual(len(h._done[240]), 1)                   # 17:00-21:00 closed when 21:00 began; the partial 13:00 bucket was skipped


class StrategyTests(unittest.TestCase):
    def strategy(self, **kw):
        cfg = simple_config(htf_arrays=True, **kw)
        return ICT2022Strategy(cfg.strategy, cfg.instrument)

    def test_the_entry_must_be_at_a_higher_timeframe_array_unless_the_raid_was_on_a_higher_timeframe_pool(self):
        st = self.strategy()
        for hr in BULL + [hour(11, 107, 108, 106, 107)[:1]]:
            for b in hr:
                st.on_bar(b)
        inside, outside = (101.2, 102.5), (110.0, 110.5)
        self.assertEqual(st._htf_poi(1, Level("ASIA_L", 100.0, "low"), inside)["state"], "array")
        self.assertEqual(st._htf_poi(1, Level("ASIA_L", 100.0, "low"), outside)["state"], "none")
        self.assertEqual(st._htf_poi(1, Level("PDL", 100.0, "low"), outside)["state"], "pool")      # the raid itself is the higher-timeframe point
        self.assertIn("1h", st._htf_poi(1, Level("ASIA_L", 100.0, "low"), inside)["text"])

    def test_with_no_higher_timeframe_to_ask_the_rule_does_not_apply(self):
        self.assertIsNone(self.strategy(timeframe_minutes=240)._htf_poi(1, Level("ASIA_L", 1.0, "low"), (1.0, 2.0)))   # nothing above 4h

    def test_the_rule_is_off_unless_asked_for(self):
        cfg = simple_config()
        self.assertFalse(cfg.strategy.htf_arrays)
        self.assertIsNone(ICT2022Strategy(cfg.strategy, cfg.instrument)._htf_poi(1, Level("ASIA_L", 1.0, "low"), (1.0, 2.0)))


if __name__ == "__main__":
    unittest.main()


class LadderTests(unittest.TestCase):
    """The bias comes from the rung above the execution timeframe: 1m from the 1h, 5m from the 4h, 15m and up from the daily."""

    def test_the_rungs(self):
        from ict_trader import htf
        self.assertEqual([htf.ladder(t)["tf"] for t in (1, 2, 3, 5, 15, 60, 240)], [60, 60, 60, 240, 1440, 1440, 1440])
        self.assertEqual((htf.ladder(5)["name"], htf.ladder(5)["up_name"]), ("4-hour", "daily"))
        self.assertEqual((htf.ladder(1)["name"], htf.ladder(1)["up_name"]), ("1-hour", "4-hour"))

    def test_candle_bias_reads_a_close_beyond_the_prior_range_and_a_run_that_came_back(self):
        from ict_trader import htf
        from ict_trader.sessions import Bar
        from datetime import datetime, timezone
        t = datetime(2026, 6, 3, tzinfo=timezone.utc)
        c = lambda o, h, l, cl: Bar(t, o, h, l, cl)   # noqa: E731
        prior = c(100, 102, 99, 101)
        self.assertEqual(htf.candle_bias([prior, c(101, 106, 100.5, 105)])[0], 1)          # closed above the prior high
        self.assertEqual(htf.candle_bias([prior, c(100, 101.5, 97, 98)])[0], -1)           # closed below the prior low
        self.assertEqual(htf.candle_bias([prior, c(101, 103, 100, 101.5)])[0], -1)         # ran the prior high, closed back inside: that was the raid
        self.assertEqual(htf.candle_bias([prior, c(100, 101.5, 98, 100.5)])[0], 1)         # ran the prior low, closed back inside
        self.assertEqual(htf.candle_bias([prior, c(100.5, 101.5, 99.5, 101)])[0], 0)       # inside
        self.assertEqual(htf.candle_bias([prior])[0], 0)

    def test_a_5_minute_strategy_takes_its_bias_from_the_4_hour(self):
        cfg = simple_config(timeframe_minutes=5, bias_ladder=True)
        st = ICT2022Strategy(cfg.strategy, cfg.instrument)
        flat = lambda hh, lo, hi_: hour(hh, (lo + hi_) / 2, hi_, lo, (lo + hi_) / 2)   # noqa: E731
        feed_hours = [hour(4, 100, 101, 99.5, 100.5),                                                       # a dummy first bucket
                      hour(5, 100, 102, 99, 101), flat(6, 100.5, 101.5), flat(7, 100.5, 101.5), flat(8, 100.5, 101.5),     # the 05:00 four-hour candle: high 102
                      hour(9, 101, 106, 100.5, 105), flat(10, 104.5, 105.5), flat(11, 104.5, 105.5), hour(12, 104.5, 105.5, 104.5, 105),   # the 09:00 candle closes at 105, above 102
                      hour(13, 105, 105.5, 104.5, 105)[:1]]                                                  # its first candle closes the 09:00 one
        for hr in feed_hours:
            for b in hr:
                st.on_bar(b)
        lb = st.ladder_bias()
        self.assertEqual(lb["names"], ("4-hour", "daily"))
        self.assertEqual(lb["p"][0], 1)
        self.assertIn("above the prior candle's high", lb["p"][1])
        self.assertEqual(lb["range_name"], "the 4-hour range")
        daily = ICT2022Strategy(simple_config(timeframe_minutes=5, bias_ladder=False).strategy, cfg.instrument).ladder_bias()
        self.assertEqual(daily["names"], ("daily", "weekly"))        # ladder off: the daily rung, as before

    def test_a_model_with_no_matrix_is_read_against_the_same_top_down_bias(self):
        from datetime import datetime, timezone
        from ict_trader.scanner import _judge
        js = {"direction": "long", "rr": 3.0, "time": datetime.now(timezone.utc).isoformat(), "level": "ASIA_L", "reasons": [], "cls": "synthetic"}
        lb = {"p": (1, "x"), "u": (1, "y"), "s": (1, "z"), "names": ("4-hour", "daily"), "range": None, "range_name": "the 4-hour range"}
        a = _judge(js, lb)
        self.assertIn("4-hour draw with the trade", a["rows"][0]["why"])
        self.assertEqual(a["rows"][0]["points"], 25)
        against = _judge(js, {**lb, "p": (-1, "x"), "u": (-1, "y")})
        self.assertIn("AGAINST the 4-hour draw", against["rows"][0]["why"])
        self.assertEqual(against["rows"][0]["points"], 0)


class LadderOfArraysTests(unittest.TestCase):
    """The rest of the PD-array matrix, the daily and weekly arrays, the nesting test, continuation and the first partial."""

    def _bars(self, rows, start="2026-06-01"):
        from datetime import datetime, timedelta, timezone
        t0 = datetime.fromisoformat(start).replace(tzinfo=timezone.utc)
        from ict_trader.sessions import Bar
        return [Bar(t0 + timedelta(days=i), *r) for i, r in enumerate(rows)]

    def test_rejection_block_is_the_wick_at_a_swing_extreme(self):
        from ict_trader.pd_arrays import detect_rejection_blocks
        rows = [(100, 101, 99, 100.5)] * 8 + [(100.5, 103, 100, 100.8)] + [(100.8, 101, 99.5, 100)] * 4
        up = detect_rejection_blocks(self._bars(rows))
        self.assertEqual([(a.direction, a.bottom, a.top, a.mitigated, a.broken) for a in up], [(-1, 100.8, 103, False, False)])
        down = detect_rejection_blocks(self._bars([(100, 101, 99, 100.5)] * 8 + [(100.2, 100.5, 97, 100)] + [(100.2, 101, 99.5, 100.4)] * 4))
        self.assertEqual([(a.direction, a.bottom, a.top) for a in down], [(1, 97, 100)])
        back = detect_rejection_blocks(self._bars(rows[:9] + [(100.8, 101, 99.5, 100)] * 2 + [(100.8, 102.5, 100, 101)] + [(101, 101.2, 100, 100.5)]))
        self.assertTrue(back[0].mitigated)                                    # price traded back into the wick
        self.assertEqual(detect_rejection_blocks(self._bars([(100, 101, 99, 100.5)] * 8 + [(100.5, 101.1, 100.2, 100.8)] + [(100.8, 101, 99.5, 100)] * 4)), [])   # no wick, no block

    def test_daily_and_weekly_candles_give_arrays_and_the_outermost_kind_wins(self):
        h = HtfArrays((60,))
        daily = self._bars([(99, 100, 98, 99.5), (100, 101, 99, 100.5), (103, 106, 102.5, 105), (105, 107, 101, 106)])   # day 0 high 100, day 2 low 102.5: a bullish gap
        h.set_fixed(1440, daily)
        self.assertEqual(h.all_tfs, (60, 1440))
        gap = [a for a in h.arrays(1440) if a.kind == "FVG" and a.dir == 1]
        self.assertEqual([(a.lo, a.hi) for a in gap], [(100, 102.5)])
        self.assertEqual(h.at(1, 101, 102).tf, 1440)
        self.assertIsNone(h.at(-1, 101, 102))                                  # a seller does not sit at a bullish array
        self.assertIn("daily bullish", h.at(1, 101, 102).text())

    def test_nesting_lists_every_timeframe_that_has_an_array_at_the_zone(self):
        h = HtfArrays((60,))
        feed(h, BULL + [hour(11, 107, 108, 106, 107)[:1]])
        h.set_fixed(1440, self._bars([(99, 100, 98, 99.5), (100, 101, 99, 100.5), (103, 106, 100.8, 105), (105, 107, 104, 106)]))
        self.assertEqual(h.nested(1, 101.5, 102.5), ["1h", "daily"])
        self.assertEqual(h.nested(1, 120, 121), [])

    def test_strategy_hands_the_completed_days_and_weeks_to_the_arrays(self):
        from datetime import date
        cfg = simple_config(timeframe_minutes=5, htf_arrays=True)
        s = ICT2022Strategy(cfg.strategy, cfg.instrument)
        # three completed weeks (Mon-Fri) and the day in progress; week 3 opens above week 1's high: a weekly gap
        for w, base in enumerate((100, 101, 110)):
            for k in range(5):
                s._days[date(2026, 6, 1) + __import__("datetime").timedelta(days=7 * w + k)] = [base, base + 2, base - 1, base + 1]
        s._days[date(2026, 6, 22)] = [111, 112, 110, 111]    # Monday of week 4, still forming
        h = s._htf()
        self.assertEqual([len(h.fixed[1440]), len(h.fixed[10080])], [15, 3])  # the day in progress and the forming week are left out
        wk = h.fixed[10080]
        self.assertEqual((wk[0].open, wk[0].high, wk[0].low, wk[0].close), (100, 102, 99, 101))
        self.assertTrue(any(a.kind == "FVG" and a.dir == 1 for a in h.arrays(10080)))

    def test_ht01_asks_the_4_hour_range_on_a_1_minute_chart_and_the_20_day_on_a_5_minute(self):
        from ict_trader.sessions import Bar
        from datetime import datetime, timedelta, timezone
        one = ICT2022Strategy(simple_config(timeframe_minutes=1, bias_ladder=True).strategy, simple_config().instrument)
        self.assertEqual(one._gate_range(), (None, "the 4-hour range"))          # no 4-hour candles yet: the rule does not apply
        one._lad = HtfArrays((60, 240))
        t0 = datetime(2026, 6, 1, tzinfo=timezone.utc)
        one._lad._done[240] = [Bar(t0 + timedelta(hours=4 * i), 100, 101 + i, 99 - i, 100) for i in range(8)]
        self.assertEqual(one._gate_range(), ((108, 92), "the 4-hour range"))
        five = ICT2022Strategy(simple_config(timeframe_minutes=5, bias_ladder=True).strategy, simple_config().instrument)
        self.assertEqual(five._gate_range()[1], f"the {five.config.ipda_days}-day range")

    def test_array_levels_are_the_stops_beyond_arrays_on_the_side_of_the_bias(self):
        from types import SimpleNamespace as NS
        from unittest import mock
        from datetime import datetime, timezone
        from ict_trader.htf import Array
        from ict_trader.sessions import Bar
        cfg = simple_config(timeframe_minutes=5, htf_arrays=True, array_levels=True)
        s = ICT2022Strategy(cfg.strategy, cfg.instrument)
        t = datetime(2026, 6, 3, 10, tzinfo=timezone.utc)
        s._bars.append(Bar(t, 105, 105.5, 104.5, 105))
        arr = [Array(240, "OB", 1, 100, 101, t), Array(60, "FVG", 1, 103, 104, t), Array(60, "FVG", 1, 107, 108, t), Array(60, "OB", -1, 99, 100, t)]
        h = NS(all_tfs=(60, 240), arrays=lambda tf: [a for a in arr if a.tf == tf], tfs=(60, 240), set_fixed=lambda *a: None)
        with mock.patch.object(s, "_htf", lambda: h), mock.patch.object(s, "ladder_bias", lambda: {"p": (1, "x")}):
            lv = s._array_levels()
            self.assertEqual([(l.price, l.side) for l in lv], [(103, "low"), (100, "low")])   # below price, with the bias, nearest first
            self.assertTrue(all(not l.name.startswith(("PD", "PW", "IPDA")) for l in lv))
        with mock.patch.object(s, "_htf", lambda: h), mock.patch.object(s, "ladder_bias", lambda: {"p": (-1, "x")}):
            self.assertEqual([(l.price, l.side) for l in s._array_levels()], [])           # the one bearish array is below price: not a stop to raid
        with mock.patch.object(s, "_htf", lambda: h), mock.patch.object(s, "ladder_bias", lambda: {"p": (0, "x")}):
            self.assertEqual(s._array_levels(), [])
        off = ICT2022Strategy(simple_config(timeframe_minutes=5, htf_arrays=True).strategy, cfg.instrument)
        self.assertEqual(off._array_levels(), [])

    def test_the_first_partial_comes_off_before_the_first_wall(self):
        from unittest import mock
        s = ICT2022Strategy(simple_config(timeframe_minutes=5).strategy, simple_config().instrument)
        with mock.patch.object(s, "_walls", lambda *a: [(104.0, 104.5), (106.0, 107.0)]):
            self.assertEqual(s._first_partial(1, 100.0, 1.0, 110.0, 105.0, 5), 104.0)      # the leg's 105 is beyond the wall at 104
            self.assertEqual(s._first_partial(1, 100.0, 1.0, 110.0, 103.0, 5), 103.0)      # the leg's extreme comes first: unchanged
            self.assertEqual(s._first_partial(1, 100.0, 1.0, 110.0, 99.0, 5), 104.0)       # no leg partial: the wall's edge is the first
            self.assertEqual(s._first_partial(1, 100.0, 9.0, 110.0, 105.0, 5), 105.0)      # the wall is under half an R away: ignored
            self.assertEqual(s._first_partial(-1, 110.0, 1.0, 100.0, 105.0, 5), 107.0)     # a short meets the highest wall first, at its top edge
        off = ICT2022Strategy(simple_config(timeframe_minutes=5, tp1_before_wall=False).strategy, simple_config().instrument)
        with mock.patch.object(off, "_walls", lambda *a: [(104.0, 104.5)]):
            self.assertEqual(off._first_partial(1, 100.0, 1.0, 110.0, 105.0, 5), 105.0)
