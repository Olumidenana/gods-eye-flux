"""Volume Imbalance (ict_trader/blk_vimb.py): two adjacent candles whose bodies do not overlap while their wicks do.

The bars are 5-minute (open, high, low, close) tuples run through the same helper as the other pattern models (one pip = 0.01, so
a tick is 0.01 here). The bullish case is written out by hand and the bearish case is its mirror (every price p becomes MIRROR - p),
so one set of numbers covers both directions and every negative below is run both ways.

The bullish story, bar by bar (index in the list):
  0-11   flat filler candles, range 0.4 (open equals close, so none of them can be candle 2: no displacement)
  12     a swing high at 102.0 (a lower high on each side): the pool the engine takes as the target
  13     filler;  14 candle 1: up, body 100.00 to 100.40, high 100.50
  15     candle 2: opens at 100.80, 0.40 above candle 1's close, low 100.45 (reaches candle 1's high 100.50), closes up at 101.20
         -> the volume imbalance 100.40 to 100.80, CE 100.60, a buy limit at 100.60, stop 100.40 - 1 tick - the stop buffer
  16     the retest: low 100.55 reaches the CE, close 100.90 holds above the far edge.
"""

import random
import statistics
import unittest
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from unittest import mock

from ict_trader import blk_vimb
from ict_trader.blk_vimb import VolumeImbalanceStrategy
from ict_trader.models import make_strategy
from ict_trader.sessions import Bar
from tests.test_patterns import CFG, T0, run

MIRROR = 200.0
PIP = 0.01

FILL = (100.0, 100.2, 99.8, 100.0)
WIDE = (100.0, 101.0, 99.0, 100.0)               # a filler with a median range of 2.0, to test the 5%-of-the-median-range term
TIGHT = (100.0, 100.1, 99.9, 100.0)              # a filler with a median range of 0.2: 5% of it is under two ticks, so the tick floor rules
SWING = (100.0, 102.0, 99.9, 100.1)
C1 = (100.00, 100.50, 99.90, 100.40)
C2 = (100.80, 101.30, 100.45, 101.20)
RETEST = (101.15, 101.20, 100.55, 100.90)
FLAT_ABOVE = (101.2, 101.3, 101.1, 101.2)        # sits above the zone, never touches it, and is a doji (no candle 2)
LATE_RETEST = (101.20, 101.25, 100.55, 100.90)   # a retest that opens at the doji's close (no gap of its own): the CE is touched
VOID = (100.95, 100.96, 100.385, 100.39)         # opens inside the bodies of candle 2 and of the retest (no gap), trades down through the CE, closes at 100.39: one
                                                 # tick under the far edge 100.40, and its low stays above the stop 100.38
FIRST_VI_BAR = 15                                # the index of candle 2
BUY_STOP = 100.40 - PIP - CFG.strategy.stop_buffer_pips * PIP     # the far edge less one tick less the stop buffer


def gap2(gap):
    """Candle 2 opening `gap` above candle 1's close 100.40 (a valid candle: its low is at most its open)."""
    o = 100.40 + gap
    return (o, 101.30, min(100.45, o), 101.20)


def story(c1=C1, c2=C2, after=(RETEST,), fill=FILL, lead=12):
    return [fill] * lead + [SWING, fill, c1, c2] + list(after)


def mirror(bars, k=MIRROR):
    return [(k - o, k - l, k - h, k - c) for o, h, l, c in bars]


def both(bars):
    return (("bullish", bars), ("bearish", mirror(bars)))


def staged(s):
    return [e for e in s.events if e["type"] == "staged"]


def cancelled(s):
    return [e for e in s.events if e["type"] == "cancelled"]


class VolumeImbalanceTest(unittest.TestCase):
    def none_either_way(self, bars, **kw):
        for name, bs in both(bars):
            with self.subTest(name):
                s, sigs = run("vimb", bs, **kw)
                self.assertEqual(staged(s), [])
                self.assertEqual(sigs, [])

    def one_either_way(self, bars, **kw):
        """Exactly one order staged and filled in each direction; returns the two runs."""
        out = []
        for (name, bs), d in zip(both(bars), (1, -1)):
            with self.subTest(name):
                s, sigs = run("vimb", bs, **kw)
                self.assertEqual(len(staged(s)), 1)
                self.assertEqual(len(sigs), 1)
                self.assertEqual(sigs[0][1].direction, d)
                out.append((s, sigs))
        return out

    # ------------------------------------------------------------------ the clean cases
    def test_a_bullish_imbalance_rests_a_buy_limit_at_the_ce_with_the_stop_under_the_far_edge(self):
        s, sigs = run("vimb", story())
        self.assertEqual(len(sigs), 1)
        i, sig = sigs[0]
        self.assertEqual(i, 16)                                          # filled on the retest candle
        self.assertEqual(sig.direction, 1)
        self.assertAlmostEqual(sig.entry_ref, 100.60, places=6)          # the CE of 100.40 to 100.80
        self.assertAlmostEqual(sig.stop, BUY_STOP, places=6)             # below the far edge by a tick and the stop buffer
        self.assertLess(sig.stop, 100.40)
        self.assertGreater(sig.target, sig.entry_ref)                    # the swing high above, the engine's usual target
        self.assertTrue(sig.reasons[0].startswith("VI-01"))
        ids = [r.split()[0] for r in sig.reasons]
        self.assertEqual(ids[:4], ["VI-01", "VI-02", "VI-03", "RL-05"])
        self.assertLess(ids.index("VI-03"), ids.index("EN-01"))          # the pattern's own lines come before the order lines
        f = s._fmt
        self.assertIn(f(100.40), sig.reasons[1])                         # the real prices are in the trail
        self.assertIn(f(100.80), sig.reasons[1])
        self.assertIn(f(100.60), sig.reasons[2])
        self.assertIn(f(100.50), sig.reasons[0])                         # candle 1's high, the wick contact
        # the order is staged on the candle that forms the imbalance, not before and not later
        st = staged(s)
        self.assertEqual(len(st), 1)
        self.assertEqual(st[0]["time"], T0 + timedelta(minutes=5 * FIRST_VI_BAR))
        self.assertEqual((st[0]["dir"], st[0]["fvg"]), (1, (100.40, 100.80)))
        self.assertAlmostEqual(st[0]["limit"], 100.60, places=6)

    def test_a_bearish_imbalance_is_the_mirror(self):
        s, sigs = run("vimb", mirror(story()))
        self.assertEqual(len(sigs), 1)
        i, sig = sigs[0]
        self.assertEqual(i, 16)
        self.assertEqual(sig.direction, -1)
        self.assertAlmostEqual(sig.entry_ref, MIRROR - 100.60, places=6)
        self.assertAlmostEqual(sig.stop, MIRROR - BUY_STOP, places=6)
        self.assertGreater(sig.stop, MIRROR - 100.40)                    # above the far edge (the zone's top)
        self.assertLess(sig.target, sig.entry_ref)
        self.assertTrue(sig.reasons[0].startswith("VI-01"))
        st = staged(s)
        self.assertEqual((st[0]["dir"], st[0]["time"]), (-1, T0 + timedelta(minutes=5 * FIRST_VI_BAR)))
        lo, hi = st[0]["fvg"]
        self.assertAlmostEqual(lo, MIRROR - 100.80, places=6)
        self.assertAlmostEqual(hi, MIRROR - 100.40, places=6)

    def test_the_stop_buffer_and_the_entry_parameter_move_the_stop_and_the_limit(self):
        for (name, bs), d in zip(both(story()), (1, -1)):
            with self.subTest(name):
                s, sigs = run("vimb", bs, stop_buffer_pips=5.0)
                self.assertEqual(len(sigs), 1)
                far = 100.40 if d == 1 else MIRROR - 100.40
                self.assertAlmostEqual(sigs[0][1].stop, far - d * (1 + 5.0) * PIP, places=6)
        # the near edge instead of the CE: 100.80 for the buy, 99.20 for the sell (the edge price comes back to first)
        with mock.patch.object(blk_vimb, "VI_ENTRY", "edge"):
            (_, buy), (_, sell) = self.one_either_way(story())
        self.assertAlmostEqual(buy[0][1].entry_ref, 100.80, places=6)
        self.assertAlmostEqual(sell[0][1].entry_ref, MIRROR - 100.80, places=6)
        self.assertTrue(buy[0][1].reasons[2].startswith("VI-03") and "near edge" in buy[0][1].reasons[2])

    def test_a_down_candle_1_works_when_the_bodies_are_apart(self):
        # candle 1 down: its body top is its OPEN, so the zone is 100.40 (the open) to 100.80, not the lower close
        down1 = (100.40, 100.50, 99.90, 100.00)
        (_, buy), _ = self.one_either_way(story(c1=down1))
        self.assertAlmostEqual(buy[0][1].entry_ref, 100.60, places=6)
        # opening above candle 1's close but inside its body is not a volume imbalance (the bodies overlap)
        self.none_either_way(story(c1=down1, c2=(100.20, 101.30, 100.15, 101.20)))

    def test_it_stays_one_order_per_imbalance_and_a_run_of_imbalances_gives_one_each(self):
        s, sigs = run("vimb", story(after=[RETEST, (100.90, 101.10, 100.80, 101.00)]), max_signals_per_day=100)
        self.assertEqual(len(staged(s)), 1)                              # the pair is read once, when candle 2 closes
        # three up candles with an imbalance either side of the middle one: two zones, each its own order
        a, b, c = (100.00, 100.50, 99.90, 100.40), (100.80, 101.40, 100.45, 101.30), (101.70, 102.20, 101.35, 102.10)
        bars = [FILL] * 12 + [(100.0, 105.0, 99.9, 100.1), FILL, a, b, c, (102.1, 102.2, 102.0, 102.1)]     # the pool at 105 is above all of it
        s, _ = run("vimb", bars, max_signals_per_day=100)
        zones = [e["fvg"] for e in staged(s)]
        self.assertEqual(len(zones), 2)
        self.assertEqual([tuple(round(x, 2) for x in z) for z in zones], [(100.40, 100.80), (101.30, 101.70)])

    def test_a_pair_that_was_already_read_is_not_staged_again(self):
        s, _ = run("vimb", story(after=[]))
        self.assertEqual((len(staged(s)), len(s._setups)), (1, 1))
        s._detect(FIRST_VI_BAR, T0 + timedelta(minutes=5 * (FIRST_VI_BAR + 1)), PIP)         # the same candle read a second time
        self.assertEqual((len(staged(s)), len(s._setups)), (1, 1))

    def test_the_engines_stop_distance_check_applies_to_the_order(self):
        # a tall zone puts the CE 32 pips above the stop; the default config allows 25
        tall = story(c2=(101.00, 101.50, 100.45, 101.40), after=[(101.20, 101.30, 100.60, 101.00)])
        st = replace(CFG.strategy, model="vimb", timeframe_minutes=5, liquidity_pools=True, daily_bias_filter=False)
        for name, bs in both(tall):
            with self.subTest(name):
                self.assertEqual(len(run("vimb", bs)[1]), 1)                       # the helper lifts the limits, as in the other model tests
                s = make_strategy(st, replace(CFG.instrument, pip_size=0.01))
                self.assertEqual([x for i, b in enumerate(bs) if (x := s.on_bar(Bar(T0 + timedelta(minutes=5 * i), *b)))], [])
                self.assertEqual(staged(s), [])
                self.assertTrue(any(d.rule == "SL-03" for d in s.decisions))
        s = make_strategy(st, replace(CFG.instrument, pip_size=0.01))                # the clean story risks 22 pips: inside the limits
        self.assertEqual(len([x for i, b in enumerate(story()) if (x := s.on_bar(Bar(T0 + timedelta(minutes=5 * i), *b)))]), 1)

    # ------------------------------------------------------------------ each condition of the geometry broken in turn
    def test_bodies_that_touch_or_overlap_are_no_imbalance(self):
        self.none_either_way(story(c2=(100.40, 101.30, 100.35, 101.20)))        # opens exactly at candle 1's close: no gap at all
        self.none_either_way(story(c2=(100.30, 101.30, 100.25, 101.20)))        # opens inside candle 1's body
        self.none_either_way(story(c2=(99.90, 101.30, 99.85, 101.20)))          # opens under candle 1's body

    def test_wicks_that_do_not_touch_are_a_vacuum_not_an_imbalance(self):
        self.none_either_way(story(c2=(100.80, 101.30, 100.51, 101.20)))        # low 100.51 is one tick above candle 1's high 100.50
        self.none_either_way(story(c2=(100.80, 101.30, 100.70, 101.20)))        # a clean gap, nothing overlaps
        self.one_either_way(story(c2=(100.80, 101.30, 100.50, 101.20)))         # the low touching the high exactly is still contact
        self.one_either_way(story(c2=(100.80, 101.30, 100.10, 101.20)))         # and a wick that goes deep into candle 1 is contact too

    def test_a_fair_value_gap_without_a_gap_between_neighbours_is_not_a_volume_imbalance(self):
        # three candles, wick to wick: A's high 100.50 is under C's low 100.80, yet each candle opens at the close before it
        a, b, c = (100.00, 100.50, 99.90, 100.40), (100.40, 101.40, 100.40, 101.30), (101.30, 101.70, 100.80, 101.60)
        self.assertLess(a[1], c[2])                                             # it IS a fair value gap
        self.assertEqual((b[0], c[0]), (a[3], b[3]))                            # with no close-to-open gap anywhere
        retest = (101.40, 101.50, 100.60, 101.35)                               # back into the gap [100.50, 100.80]; opens inside c's body
        self.none_either_way(story(c1=a, c2=b, after=[c, retest]))

    def test_the_imbalance_must_be_at_least_two_ticks_and_five_percent_of_the_median_range(self):
        retest = [(101.15, 101.20, 100.30, 100.90)]
        # a median range of 0.4: 5% is 0.02, the same as the two-tick floor
        for gap, ok in ((0.01, False), (0.02, True), (0.05, True)):
            with self.subTest(f"gap {gap}"):
                (self.one_either_way if ok else self.none_either_way)(story(c2=gap2(gap), after=retest))
        # a median range of 0.2: 5% is only one tick, so the two-tick floor is what rejects 1.5 ticks
        for gap, ok in ((0.015, False), (0.02, True)):
            with self.subTest(f"tight gap {gap}"):
                (self.one_either_way if ok else self.none_either_way)(story(fill=TIGHT, c2=gap2(gap), after=retest))
        # a median range of 2.0: the floor is 0.10, so 8 ticks is no longer enough and 12 ticks is
        for gap, ok in ((0.08, False), (0.12, True)):
            with self.subTest(f"wide gap {gap}"):
                (self.one_either_way if ok else self.none_either_way)(story(fill=WIDE, c2=gap2(gap), after=retest))

    def test_candle_2_must_close_in_the_direction_of_the_imbalance(self):
        # opens above candle 1's body (bodies apart, wicks touching) but closes down: no displacement, so no buy; and it is no sell either
        self.none_either_way(story(c2=(100.80, 101.00, 100.45, 100.60)))
        self.none_either_way(story(c2=(100.80, 101.00, 100.45, 100.80)))        # a doji
        # a bullish imbalance is bought, never sold: one order, in one direction only
        for name, bs in both(story()):
            s, _ = run("vimb", bs)
            self.assertEqual({e["dir"] for e in staged(s)}, {1 if name == "bullish" else -1})

    def test_the_two_candles_must_be_adjacent(self):
        # candle 1, a doji, then the gap-up candle: candle 1 and candle 2 would be an imbalance if nothing sat between them (open 100.80
        # over the close 100.40, low 100.45 reaching the high 100.50), but the neighbours are (candle 1, doji) and (doji, candle 2), and
        # the doji's high 100.35 does not reach candle 2's low 100.45: a vacuum
        doji = (100.20, 100.35, 100.10, 100.20)
        self.none_either_way(story(c2=doji, after=[C2, RETEST]))
        self.one_either_way(story(c2=C2, after=[RETEST]))                          # the same two candles side by side do fire

    def test_it_waits_for_enough_history(self):
        with mock.patch.object(blk_vimb, "VI_WARMUP", 100):
            self.none_either_way(story())
        self.one_either_way(story())
        short = [FILL] * 3 + [C1, C2, RETEST]                                    # candle 2 at index 4
        self.none_either_way(short)

    # ------------------------------------------------------------------ the daily bias
    def test_respects_the_daily_bias_like_the_other_pattern_models(self):
        for name, bs, d in (("bullish", story(), 1), ("bearish", mirror(story()), -1)):
            with self.subTest(name):
                with mock.patch.object(VolumeImbalanceStrategy, "daily_bias", return_value=(d, "test draw")):
                    s, sigs = run("vimb", bs)
                    self.assertEqual(len(sigs), 1)
                    self.assertIn("test draw", sigs[0][1].reasons[3])         # the RL-05 line carries the draw
                with mock.patch.object(VolumeImbalanceStrategy, "daily_bias", return_value=(-d, "test draw")):
                    s, sigs = run("vimb", bs)
                    self.assertEqual((sigs, staged(s)), ([], []))
                with mock.patch.object(VolumeImbalanceStrategy, "daily_bias", return_value=(0, "no draw")):
                    self.assertEqual(len(run("vimb", bs)[1]), 1)

    # ------------------------------------------------------------------ the invalidation rule and the order lifecycle
    def test_a_body_close_through_the_far_edge_voids_the_zone_and_the_candle_does_not_fire(self):
        # the candle trades down through the CE (a fill, as far as the base lifecycle sees) but closes at 100.39, under the far edge
        # 100.40; its low 100.385 stays above the stop 100.38 so the stop is not what cancels it
        void = VOID
        for name, bs in both(story(after=[void])):
            with self.subTest(name):
                s, sigs = run("vimb", bs)
                self.assertEqual(len(staged(s)), 1)
                self.assertEqual(sigs, [])
                self.assertEqual(s._setups, [])
                self.assertEqual(len(cancelled(s)), 1)
                self.assertIn("far edge", cancelled(s)[0]["message"])
                self.assertEqual(cancelled(s)[0]["time"], T0 + timedelta(minutes=5 * (FIRST_VI_BAR + 1)))
        # without that rule the base lifecycle would have filled it: the override is what voids the zone
        with mock.patch.object(VolumeImbalanceStrategy, "_drop_void"):
            for name, bs in both(story(after=[void])):
                with self.subTest(f"base only {name}"):
                    self.assertEqual(len(run("vimb", bs)[1]), 1)

    def test_a_wick_through_the_far_edge_or_a_close_on_it_is_tolerated(self):
        # the lesson frame (-Td-D-vKJDg at 14:40): the retest wick goes one tick under the lower edge and the zone holds
        wick = (101.15, 101.20, 100.39, 100.90)
        self.one_either_way(story(after=[wick]))
        on_edge = (101.15, 101.20, 100.395, 100.40)                              # closes exactly on the far edge: not through it
        self.one_either_way(story(after=[on_edge]))
        # a close back inside the zone's far half is a retest that holds
        self.one_either_way(story(after=[(101.15, 101.20, 100.41, 100.43)]))

    def test_a_resting_order_that_cannot_fill_is_still_voided_by_a_close_through_the_far_edge(self):
        # the daily cap reached (zero signals allowed): the order rests, price touches the CE without filling it, then a body closes through
        for name, bs in both(story(after=[RETEST])):
            with self.subTest(name):
                s, sigs = run("vimb", bs, max_signals_per_day=0)
                self.assertEqual((len(staged(s)), sigs, len(s._setups)), (1, [], 1))
        void = VOID
        for name, bs in both(story(after=[RETEST, void])):
            with self.subTest(f"void {name}"):
                s, sigs = run("vimb", bs, max_signals_per_day=0)
                self.assertEqual((len(staged(s)), sigs, s._setups, len(cancelled(s))), (1, [], [], 1))

    def test_the_order_expires_after_the_wait(self):
        n = blk_vimb.VI_EXPIRY
        late = lambda waits: story(after=[FLAT_ABOVE] * waits + [LATE_RETEST])         # the retest comes after `waits` candles of waiting
        for waits in (n - 2, n - 1):                                              # n - 1 waits: the retest is the n-th candle after the staging one,
            for name, bs in both(late(waits)):                                    # the last one the order may fill (a fill is tried before the expiry)
                with self.subTest(f"in time {waits} {name}"):
                    sigs = run("vimb", bs)[1]
                    self.assertEqual(len(sigs), 1)
                    self.assertEqual(sigs[0][0], FIRST_VI_BAR + 1 + waits)
        for name, bs in both(late(n)):                                            # one candle later the order is gone
            with self.subTest(f"too late {name}"):
                s, sigs = run("vimb", bs)
                self.assertEqual((len(staged(s)), sigs), (1, []))
                self.assertEqual(s._setups, [])

    def test_the_live_order_list_counts_the_candles_left_from_the_models_own_expiry(self):
        # the Desk and the analysis read "candles left" from _expiry_bars() - bars waited: it must be this model's 20 candles, not the
        # base class's 90 minutes (18 candles on 5m, 90 on 1m, 6 on 15m)
        n = blk_vimb.VI_EXPIRY
        for tf in (1, 5, 15):
            st = replace(CFG.strategy, model="vimb", timeframe_minutes=tf)
            self.assertEqual(make_strategy(st, replace(CFG.instrument, pip_size=0.01))._expiry_bars(), n, tf)
        for name, bs in both(story(after=[FLAT_ABOVE] * (n + 2))):
            with self.subTest(name):
                st = replace(CFG.strategy, model="vimb", timeframe_minutes=5, min_stop_pips=0, max_stop_pips=1e9, min_rr=0.1,
                             liquidity_pools=True, daily_bias_filter=False)
                s = make_strategy(st, replace(CFG.instrument, pip_size=0.01))
                left = {}
                for i, b in enumerate(bs):
                    s.on_bar(Bar(T0 + timedelta(minutes=5 * i), *b))
                    if s.staged:
                        left[i] = s.staged[0]["bars_left"]
                first = FIRST_VI_BAR
                self.assertEqual(left[first], n)                                  # the staging candle: all of the wait is still ahead
                self.assertEqual(left[first + 1], n - 1)
                self.assertEqual(left[first + n - 1], 1)                          # one candle still to come (the n-th may still fill it) ...
                self.assertEqual(min(left.values()), 1)                           # ... so the count never reaches zero, let alone goes negative
                self.assertEqual(sorted(left), list(range(first, first + n)))     # and on the n-th candle the unfilled order is gone from the list

    def test_the_target_or_the_stop_reached_before_the_fill_cancels_the_order(self):
        run_away = (101.30, 102.10, 101.25, 102.05)                               # takes the swing high 102.0 (the target) without a retest
        for name, bs in both(story(after=[run_away, RETEST])):
            with self.subTest(name):
                s, sigs = run("vimb", bs)
                self.assertEqual((len(staged(s)), sigs, s._setups), (1, [], []))

    # ------------------------------------------------------------------ no lookahead, no clock
    def test_no_lookahead_each_prefix_of_the_run_gives_the_same_signals(self):
        bars = story(after=[RETEST, (100.90, 101.10, 100.80, 101.00)])
        for name, bs in both(bars):
            full = run("vimb", bs)[1]
            for n in range(1, len(bs) + 1):
                with self.subTest(f"{name} {n}"):
                    self.assertEqual([i for i, _ in run("vimb", bs[:n])[1]], [i for i, _ in full if i < n])
        # and the same on a noisy walk with gaps, where many imbalances form: what was staged on the first n candles is a prefix
        bars = walk(1200, gap_chance=0.15)
        whole = run("vimb", bars, max_signals_per_day=1000)
        for n in (150, 400, 777, 1200):
            part = run("vimb", bars[:n], max_signals_per_day=1000)
            self.assertEqual([(i, g.direction, g.entry_ref, g.stop, g.target) for i, g in part[1]],
                             [(i, g.direction, g.entry_ref, g.stop, g.target) for i, g in whole[1] if i < n])
            self.assertEqual([(e["time"], e["limit"]) for e in staged(part[0])], [(e["time"], e["limit"]) for e in staged(whole[0]) if e["time"] <= part[0]._bars[-1].time])

    def test_price_only_it_does_not_care_about_the_clock(self):
        for start in (datetime(2026, 10, 11, 3, 0, tzinfo=timezone.utc), datetime(2026, 10, 10, 22, 35, tzinfo=timezone.utc)):    # Sunday, Saturday
            st = replace(CFG.strategy, model="vimb", timeframe_minutes=5, min_stop_pips=0, max_stop_pips=1e9, min_rr=0.1,
                         liquidity_pools=True, daily_bias_filter=False)
            s = make_strategy(st, replace(CFG.instrument, pip_size=0.01))
            fired = [i for i, b in enumerate(story()) if s.on_bar(Bar(start + timedelta(minutes=5 * i), *b))]
            self.assertEqual(fired, [16], start)

    def test_the_memory_of_read_pairs_stays_small(self):
        s, _ = run("vimb", walk(3000, gap_chance=0.5), max_signals_per_day=1000)
        self.assertLessEqual(len(s._seen), 16)

    # ------------------------------------------------------------------ noise
    def test_a_random_walk_does_not_raise_and_fires_modestly(self):
        bars = walk(3000, gap_chance=0.1)
        s, sigs = run("vimb", bars)                                              # the default cap: one signal a day
        s2, fills = run("vimb", bars, max_signals_per_day=1000)                  # no cap: every imbalance that gets retested
        found = staged(s2)
        print(f"\nvimb on 3000 noise bars (a gap on one bar in ten): {len(sigs)} signals (daily cap 1), "
              f"{len(found)} orders staged and {len(fills)} filled (no cap)")
        # 3000 five-minute bars is 10.4 days, so the cap allows 11 or 12 signals at most; uncapped, an imbalance needs a gap bar and a
        # candle 2 that closes the same way: a few percent of the bars, so far fewer than one order per 20 candles
        self.assertLessEqual(len(sigs), 12)
        self.assertGreaterEqual(len(found), 10)                                  # the detector is alive on noise
        self.assertLessEqual(len(found), 3000 // 20)                             # and picky
        self.assertLessEqual(len(fills), len(found))
        self.assertEqual({g.direction for _, g in fills}, {1, -1})               # both directions occur on noise
        # the same walk upside down gives the mirror image
        upside = mirror(bars, 200.0)
        s3, fills3 = run("vimb", upside, max_signals_per_day=1000)
        self.assertEqual([e["dir"] for e in staged(s3)], [-e["dir"] for e in found])
        self.assertEqual([i for i, _ in fills3], [i for i, _ in fills])

    def test_it_agrees_with_a_hand_written_reference_on_noisy_walks(self):
        # the engine may refuse an order (no target, reward too small), and says so in its decisions; everything else must be staged, and
        # nothing may be staged that the reference does not see: that pins the geometry, the size floor, the daily bias and both directions
        # on real noise. (The daily bias is patched: the engine's own reading of the walk would hide half of the imbalances.)
        for gap_chance, seed in ((0.3, 11), (0.6, 5)):
            bars = walk(2500, gap_chance=gap_chance, seed=seed)
            for name, bs in both(bars):
                for bias in (0, 1, -1):
                    with self.subTest(f"{name} gaps {gap_chance} bias {bias}"), \
                            mock.patch.object(VolumeImbalanceStrategy, "daily_bias", return_value=(bias, "test draw")):
                        want = {(i, d): (lo, hi) for i, d, lo, hi in reference(bs) if bias in (0, d)}
                        self.assertGreater(len(want), 20)
                        s, _ = run("vimb", bs, max_signals_per_day=1000)
                        got = {(round((e["time"] - T0) / timedelta(minutes=5)), e["dir"]): e["fvg"] for e in staged(s)}
                        refused = {round((x.time - T0) / timedelta(minutes=5)) - 1 for x in s.decisions if x.rule in ("SL-03", "TP-01", "TP-02")}
                        self.assertEqual(set(got) - set(want), set())                    # no imbalance the reference does not see
                        self.assertEqual({k for k in set(want) - set(got) if k[0] not in refused}, set())    # and none missed unless the engine refused it
                        self.assertGreater(len(got), len(want) // 3)                     # (the refusals are the minority, not a way to hide a miss)
                        for k, (lo, hi) in got.items():
                            self.assertAlmostEqual(want[k][0], lo, places=6)
                            self.assertAlmostEqual(want[k][1], hi, places=6)

    def test_a_walk_without_gaps_has_no_imbalance_and_a_gap_every_bar_still_runs(self):
        s, sigs = run("vimb", walk(3000, gap_chance=0.0), max_signals_per_day=1000)    # every open equals the last close
        self.assertEqual((staged(s), sigs), ([], []))
        s, sigs = run("vimb", walk(3000, gap_chance=1.0), max_signals_per_day=1000)    # a stress run: imbalances everywhere
        self.assertLessEqual(len(sigs), len(staged(s)))
        self.assertGreater(len(staged(s)), 0)


def reference(bars, pip=PIP):
    """Every volume imbalance on the candles, found the long way: each direction written out by hand (no mirroring trick), candle 2 must
    close the way it gapped, and the median range comes from the 20 candles before candle 2. Returns (index of candle 2, direction,
    zone low, zone high)."""
    out = []
    for i in range(blk_vimb.VI_WARMUP, len(bars)):
        o1, h1, l1, c1 = bars[i - 1]
        o2, h2, l2, c2 = bars[i]
        need = max(blk_vimb.VI_MIN_TICKS * pip, blk_vimb.VI_MIN_RANGE * statistics.median(h - l for _, h, l, _ in bars[max(0, i - 20):i]))
        if c2 > o2 and o2 > max(o1, c1) and l2 <= h1 and o2 - max(o1, c1) >= need:
            out.append((i, 1, max(o1, c1), o2))
        elif c2 < o2 and o2 < min(o1, c1) and h2 >= l1 and min(o1, c1) - o2 >= need:
            out.append((i, -1, o2, min(o1, c1)))
    return out


def walk(n, gap_chance, seed=7):
    """A seeded random walk of 5-minute candles around 100. Each open equals the last close, except that with probability `gap_chance`
    it jumps by a Gaussian step (a fast bar): only those can leave a gap between two bodies."""
    rng = random.Random(seed)
    price, bars = 100.0, []
    for _ in range(n):
        o = price + (rng.gauss(0, 0.15) if rng.random() < gap_chance else 0.0)
        c = o + rng.gauss(0, 0.25)
        bars.append((o, max(o, c) + abs(rng.gauss(0, 0.1)), min(o, c) - abs(rng.gauss(0, 0.1)), c))
        price = c
    return bars


if __name__ == "__main__":
    unittest.main()
