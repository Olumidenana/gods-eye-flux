"""Rejection Block: the body-to-wick zone of a swing high/low with long wicks (ict_trader/blk_rejection.py).

All bars are 5-minute (open, high, low, close) tuples fed through tests.test_patterns.run (pip size 0.01, so the
2-pip stop buffer is 0.02). The hand-built case is bearish; every bullish case is the same bars mirrored.

The reference story (bearish), bar numbers in brackets:
  [0-19]   a swing low at 97.4 (the opposing liquidity the target aims at), then a steady rise to 101
  [20-26]  the cluster: swing high at bar 23 (high 102.8), long upper wicks on bars 21 and 23, the highest body
           edge 102.0, so the zone is [102.0, 102.8]; the cluster's lowest low is 100.7
  [27]     the confirming close, 100.3, below the cluster's lowest low: the limit is staged at 102.0, stop 102.82
  [28-30]  the retrace; bar 30 trades up to 102.1 and the order fills
"""

import math
import random
import statistics
import unittest
from dataclasses import replace
from datetime import timedelta

from ict_trader.models import make_strategy
from ict_trader.sessions import Bar
from tests.test_patterns import CFG, T0, run


def candle(o, c, up=0.0, dn=0.0):
    """(open, high, low, close) with an upper and a lower wick of the given sizes beyond the body."""
    return (o, round(max(o, c) + up, 4), round(min(o, c) - dn, 4), c)


def mirror(bars, m=200.0):
    """The same market upside down (price p becomes m - p): every high becomes a low."""
    return [(round(m - o, 4), round(m - l, 4), round(m - h, 4), round(m - c, 4)) for o, h, l, c in bars]


def lead():
    """Bars 0-19: a swing low at 97.4 (bar 3), then a steady rise (each bar a higher low and high: no other swings)."""
    bars = [candle(98.0, 98.1, 0.1, 0.1) for _ in range(6)]
    bars[3] = (98.0, 98.1, 97.4, 97.9)
    for i in range(6, 20):
        base = round(98.0 + 0.2 * (i - 5), 4)
        bars.append((base, round(base + 0.3, 4), round(base - 0.15, 4), round(base + 0.15, 4)))
    return bars


CLUSTER = [candle(101.3, 101.5, 0.1, 0.1),      # 20
           candle(101.5, 101.7, 0.7, 0.1),      # 21 long upper wick: wick/body 3.5, wick/range 0.70 (strong)
           candle(101.7, 101.8, 0.15, 0.2),     # 22 a small wick, buried beneath the 102.0 body edge
           candle(101.8, 102.0, 0.8, 0.2),      # 23 the swing high 102.8: wick/body 4, wick/range 0.67 (strong); body edge 102.0
           candle(101.9, 101.5, 0.2, 0.1),      # 24
           candle(101.5, 101.1, 0.2, 0.1),      # 25
           candle(101.1, 100.8, 0.2, 0.1)]      # 26 the cluster's lowest low, 100.7
CONFIRM = candle(100.8, 100.3, 0.1, 0.1)        # 27 closes at 100.3, below 100.7
RETRACE = [(100.3, 100.9, 100.2, 100.8), (100.8, 101.5, 100.7, 101.4), (101.4, 102.1, 101.3, 101.9)]   # 28-30, bar 30 fills 102.0
HOLD = candle(101.2, 101.1, 0.1, 0.1)           # a quiet bar above the cluster's low and well below the zone
AWAY = candle(100.3, 100.0, 0.1, 0.1)           # a quiet bar after the confirmation that stays far from the zone


def bearish(cluster=None, after=None, pre=None):
    return list(pre or lead()) + list(cluster or CLUSTER) + list(after or [CONFIRM] + RETRACE)


def exact_mirror(bars, m=256.0):
    """The market upside down with no rounding at all (exact when the prices are multiples of 1/64)."""
    return [(m - o, m - l, m - h, m - c) for o, h, l, c in bars]


def tick_walk(n, seed, tick=0.01, price=100.0, vol=0.2, wick=0.25):
    """A random walk of candles rounded to the tick, so equal highs and equal lows happen the way they do on a real chart."""
    rng, out, p = random.Random(seed), [], price
    snap = lambda v: round(round(v / tick) * tick, 10)
    for _ in range(n):
        o = p
        c = o + rng.gauss(0, vol)
        h, l = snap(max(o, c) + abs(rng.gauss(0, wick))), snap(min(o, c) - abs(rng.gauss(0, wick)))
        o, c = snap(o), snap(c)
        out.append((o, max(h, o, c), min(l, o, c), c))
        p = c
    return out


def orders(s):
    """Every order the model put down, as the chart and the replay read them."""
    return [e for e in s.events if e["type"] == "staged"]


def assert_well_formed(test, s, sigs):
    """Every order (filled or not) has its stop on the losing side, its target on the winning side, a positive reward,
    sits on the zone edge nearest the body and keeps the stop beyond the far edge; every time stamp is the past."""
    for e in orders(s):
        d, lim, stp, tgt = e["dir"], e["limit"], e["stop"], e["target"]
        lo, hi = e["fvg"]
        test.assertTrue(all(math.isfinite(v) for v in (lim, stp, tgt, lo, hi, e["rr"])), e)
        test.assertGreater((lim - stp) * d, 0, e)
        test.assertGreater((tgt - lim) * d, 0, e)
        test.assertGreater(e["rr"], 0, e)
        test.assertLess(lo, hi, e)
        test.assertEqual(lim, lo if d == -1 else hi, e)
        test.assertTrue(stp > hi if d == -1 else stp < lo, e)
        test.assertLessEqual(e["fvg_time"], e["time"] + timedelta(minutes=5), e)
    for i, x in sigs:
        test.assertGreater((x.entry_ref - x.stop) * x.direction, 0)
        test.assertGreater((x.target - x.entry_ref) * x.direction, 0)
        test.assertGreater(x.rr, 0)
        test.assertTrue(all(x.meta[k] <= x.meta["mss_time"] for k in ("sweep_time", "swing_time")), x.meta)
        test.assertLessEqual(x.meta["fvg_time"], x.meta["mss_time"] + timedelta(minutes=5))


def edit(bars, changes):
    out = list(bars)
    for i, b in changes.items():
        out[i] = b
    return out


def staged(s):
    """How many limit orders the model put down (whether or not they later filled)."""
    return sum(1 for d in s.decisions if d.rule == "EN-01" and "staged" in d.message)


def drift(n, end, step):
    """n bars walking steadily to `end` (rising or falling every day, so the daily bias is clear). No swings."""
    out = []
    for i in range(n):
        base = round(end - step * (n - i), 4)
        c = round(base + step, 4)
        out.append((base, round(max(base, c) + 0.01, 4), round(min(base, c) - 0.01, 4), c))
    return out


class RejectionBlockTest(unittest.TestCase):
    def silent(self, bars, **kw):
        """No order was ever put down and nothing fired, for the market as given and for its mirror image."""
        for name, series in (("as built", bars), ("mirrored", mirror(bars))):
            with self.subTest(name):
                s, sigs = run("rejection", series, **kw)
                self.assertEqual(sigs, [])
                self.assertEqual(staged(s), 0, [d.message for d in s.decisions])

    def armed(self, bars, **kw):
        """Exactly one order was put down, for the market as given and for its mirror image; returns the first one's strategy and signals."""
        out = None
        for name, series in (("as built", bars), ("mirrored", mirror(bars))):
            with self.subTest(name):
                s, sigs = run("rejection", series, **kw)
                self.assertEqual(staged(s), 1, [d.message for d in s.decisions])
                out = out or (s, sigs)
        return out

    # ------------------------------------------------------------------ the clean cases
    def test_bearish_block_confirmed_then_a_limit_at_the_body_edge(self):
        s, sigs = run("rejection", bearish())
        self.assertEqual(len(sigs), 1)
        i, sig = sigs[0]
        self.assertEqual(i, 30)                                        # filled on the retrace, not before
        self.assertEqual(sig.direction, -1)
        self.assertEqual(sig.entry_type, "limit")
        self.assertAlmostEqual(sig.entry_ref, 102.0, places=6)         # the highest body edge of the cluster
        self.assertAlmostEqual(sig.stop, 102.82, places=6)             # the wick high 102.8 plus the 2-pip buffer
        self.assertGreater(sig.stop, 102.8)
        self.assertAlmostEqual(sig.target, 97.4, places=6)             # the nearest opposing liquidity, not the wick logic
        self.assertTrue(sig.reasons[0].startswith("RJ-01"))
        self.assertTrue(sig.reasons[1].startswith("RJ-02"))
        self.assertTrue(sig.reasons[2].startswith("RJ-03"))
        self.assertIn("102.000 to 102.800", sig.reasons[0])           # the zone, with the real prices
        self.assertIn("2 candles with long upper wicks", sig.reasons[0])
        self.assertIn("100.700", sig.reasons[1])                       # the confirming level
        self.assertEqual(staged(s), 1)
        self.assertEqual(s.staged, [])                                 # nothing still resting after the fill
        self.assertTrue(any(k[0] == -1 for k in s._seen))              # the cluster is remembered: it cannot fire twice

    def test_bullish_block_is_the_mirror_image(self):
        s, sigs = run("rejection", mirror(bearish()))
        self.assertEqual(len(sigs), 1)
        i, sig = sigs[0]
        self.assertEqual(i, 30)
        self.assertEqual(sig.direction, 1)
        self.assertEqual(sig.entry_type, "limit")
        self.assertAlmostEqual(sig.entry_ref, 98.0, places=6)          # the lowest body edge
        self.assertAlmostEqual(sig.stop, 97.18, places=6)              # 2 pips below the wick low 97.2
        self.assertLess(sig.stop, 97.2)
        self.assertAlmostEqual(sig.target, 102.6, places=6)            # the mirror of the swing low pool
        self.assertTrue(sig.reasons[0].startswith("RJ-01"))
        self.assertTrue(sig.reasons[1].startswith("RJ-02"))
        self.assertTrue(sig.reasons[2].startswith("RJ-03"))
        self.assertIn("2 candles with long lower wicks", sig.reasons[0])
        self.assertIn("97.200 to 98.000", sig.reasons[0])
        self.assertIn("a close above the cluster's highest high 99.300", sig.reasons[1])
        self.assertTrue(any(k[0] == 1 for k in s._seen))

    def test_the_order_is_staged_on_the_confirming_candle_and_never_earlier(self):
        bars = bearish()
        s, sigs = run("rejection", bars[:27])                          # everything up to the candle before the confirmation
        self.assertEqual((sigs, staged(s), s.staged), ([], 0, []))
        s, sigs = run("rejection", bars[:28])                          # the confirming close has just printed
        self.assertEqual(sigs, [])
        self.assertEqual(staged(s), 1)
        self.assertEqual(len(s.staged), 1)
        self.assertEqual((s.staged[0]["direction"], round(s.staged[0]["limit"], 6), round(s.staged[0]["stop"], 6)), ("short", 102.0, 102.82))
        s, sigs = run("rejection", bars[:30])                          # still not filled one candle before the touch
        self.assertEqual(sigs, [])
        s, sigs = run("rejection", bars[:31])
        self.assertEqual([i for i, _ in sigs], [30])

    def test_a_much_higher_high_outside_the_window_does_not_matter(self):
        # no new extreme is needed (this is not Turtle Soup): a far higher high 20+ candles back is simply history
        pre = [(98.0, 98.2, 97.9, 98.1)] * 10 + lead()
        pre[2] = (98.0, 105.0, 97.9, 98.1)
        s, sigs = run("rejection", bearish(pre=pre))
        self.assertEqual([(i, x.direction) for i, x in sigs], [(40, -1)])

    def test_two_moderate_wicks_make_a_block_when_neither_is_strong(self):
        # swing candle: wick/body 0.90, wick/range 0.47 (long, not strong); bar 22: wick/body 0.86, wick/range 0.43
        cluster = edit(CLUSTER, {1: candle(101.5, 101.7, 0.1, 0.1), 2: (101.6, 102.25, 101.55, 101.95), 3: candle(101.5, 102.0, 0.45, 0.0)})
        s, sigs = self.armed(bearish(cluster=cluster))
        self.assertEqual(len(sigs), 1)
        self.assertIn("2 candles with long upper wicks", sigs[0][1].reasons[0])
        self.assertAlmostEqual(sigs[0][1].entry_ref, 102.0, places=6)
        self.assertAlmostEqual(sigs[0][1].stop, 102.47, places=6)      # the wick high is 102.45

    def test_the_lesson_slide_ratios_pass_with_two_candles_but_not_with_one(self):
        # the bullish slide: body 140, lower wick 107 (wick/body 0.76, wick/range 0.43); scaled to a body of 0.2
        slide = lambda top: candle(101.8, 102.0, top, 0.0)             # wick 0.153: wick/body 0.765, wick/range 0.434
        self.assertGreaterEqual(0.153 / 0.2, 0.75)
        self.assertGreaterEqual(0.153 / (0.2 + 0.153), 0.40)
        quiet = candle(101.5, 101.7, 0.1, 0.1)
        two = edit(CLUSTER, {1: quiet, 2: slide(0.153), 3: slide(0.16)})
        s, sigs = self.armed(bearish(cluster=two))
        self.assertIn("2 candles with long upper wicks", sigs[0][1].reasons[0])
        one = edit(CLUSTER, {1: quiet, 2: candle(101.7, 101.8, 0.1, 0.1), 3: slide(0.153)})
        self.silent(bearish(cluster=one))

    # ------------------------------------------------------------------ near misses, one condition broken at a time
    def test_no_confirming_close_means_no_order(self):
        self.silent(bearish(after=[candle(100.8, 100.75, 0.1, 0.35)] + RETRACE))      # lows at 100.4 but the close stays above 100.7
        self.silent(bearish(after=[candle(100.8, 100.7, 0.1, 0.3)] + RETRACE))        # a close exactly at the low is not below it

    def test_the_confirmation_must_come_within_ten_candles(self):
        late = lambda n: bearish(after=[HOLD] * n + [candle(101.1, 100.3, 0.1, 0.1)] + RETRACE)
        self.armed(late(9))                                            # the 10th candle after the cluster: still in time
        self.silent(late(10))                                          # the 11th: too late

    def test_only_the_first_close_below_the_low_confirms(self):
        # confirmed at bar 27 but price never comes back to the zone; a later dip below the low must not arm it again
        away = [AWAY] * 6                                              # 28-33: the 5-candle order expires unfilled
        again = [candle(100.0, 101.2, 0.1, 0.1), candle(101.2, 100.4, 0.1, 0.1)]      # 34 recovers above the low, 35 closes below it again
        s, sigs = self.armed(bearish(after=[CONFIRM] + away + again))
        self.assertEqual(sigs, [])

    def test_a_close_above_the_wick_high_before_the_confirmation_kills_the_block(self):
        # bar 27 closes above 102.8 (price accepted above the wick: no rejection), then price drops through the low
        up = candle(101.2, 102.95, 0.05, 0.1)
        down = candle(102.95, 100.2, 0.05, 0.2)
        self.silent(bearish(after=[up, down] + RETRACE))
        # the same path with a wick-only pierce (high 102.9, close back at 102.3) is still a block: the pierce is the trade
        pierce = (101.2, 102.9, 101.1, 102.3)
        s, sigs = self.armed(bearish(after=[pierce, candle(102.3, 100.3, 0.1, 0.1)] + RETRACE))
        self.assertAlmostEqual(sigs[0][1].entry_ref, 102.0, places=6)
        self.assertAlmostEqual(sigs[0][1].stop, 102.82, places=6)

    def test_a_close_exactly_at_the_wick_high_is_not_a_close_above_it(self):
        self.armed(bearish(after=[(101.2, 102.9, 101.1, 102.8), candle(102.8, 100.3, 0.1, 0.1)] + RETRACE))

    def test_bullish_invalidation_is_the_mirror(self):
        up = candle(101.2, 102.95, 0.05, 0.1)
        down = candle(102.95, 100.2, 0.05, 0.2)
        self.silent(mirror(bearish(after=[up, down] + RETRACE)))
        pierce = (101.2, 102.9, 101.1, 102.3)
        s, sigs = self.armed(mirror(bearish(after=[pierce, candle(102.3, 100.3, 0.1, 0.1)] + RETRACE)))
        self.assertEqual(sigs[0][1].direction, 1)

    def test_a_bar_that_runs_through_the_zone_fills_the_resting_order_before_the_stop(self):
        # the limit is already resting when price rips through the zone: it fills (the engine's fill rule) and the stop ends
        # the idea; the close is never used to cancel a bar that already traded at the limit (that would hide the loser)
        s, sigs = self.armed(bearish(after=[CONFIRM, (100.3, 103.0, 100.2, 102.9)]))
        self.assertEqual([(i, x.direction) for i, x in sigs], [(28, -1)])

    def test_a_marubozu_swing_candle_is_an_order_block_shape_not_a_rejection(self):
        # displacement up into the high with no wicks: the zone is body space, not wick space
        cluster = edit(CLUSTER, {1: candle(101.0, 101.7, 0.02, 0.02), 3: candle(101.2, 102.8, 0.02, 0.02)})
        self.silent(bearish(cluster=cluster))

    def test_wick_to_body_too_small_even_though_wick_to_range_passes(self):
        # both wicks: wick/body 0.69-0.71 (needs 0.75) with wick/range 0.41 (passes); a smaller body (0.4) makes the same
        # wicks strong and the block forms: the body is the only difference
        def pair(o):
            return edit(CLUSTER, {1: candle(o, 102.2, 0.55, 0.0), 3: candle(o, 102.2, 0.60, 0.0)})
        self.assertLess(0.55 / 0.80, 0.75)
        self.assertLess(0.60 / 0.85, 0.75)
        self.silent(bearish(cluster=pair(101.4)))
        self.armed(bearish(cluster=pair(101.8)))

    def test_wick_to_range_too_small_even_though_wick_to_body_passes(self):
        # a long lower shadow: wick/body 7 but wick/range 0.37 (needs 0.40); with a shorter lower shadow (0.5) the range
        # ratio is 0.54 and the block forms: the lower shadow is the only difference
        def swing(dn):
            return edit(CLUSTER, {1: candle(101.5, 101.7, 0.1, 0.1), 3: candle(101.5, 101.6, 0.7, dn)})
        self.assertLess(0.7 / (0.7 + 0.1 + 1.1), 0.40)
        self.silent(bearish(cluster=swing(1.1), after=[candle(100.8, 100.2, 0.1, 0.1)] + RETRACE))
        s, sigs = self.armed(bearish(cluster=swing(0.5)))
        self.assertAlmostEqual(sigs[0][1].entry_ref, 101.9, places=6)  # the highest body edge is now bar 24's open
        self.assertAlmostEqual(sigs[0][1].stop, 102.32, places=6)

    def test_one_moderate_wick_alone_is_not_enough(self):
        # wick/body 0.90 and wick/range 0.47: long but not strong, and the only long wick in the cluster
        cluster = edit(CLUSTER, {1: candle(101.5, 101.7, 0.1, 0.1), 3: candle(101.5, 102.0, 0.45, 0.0)})
        self.silent(bearish(cluster=cluster))
        # wick/body 1.33 but wick/range 0.44 (a strong single wick needs 0.50 of the range): still one candle short; with a
        # lower shadow of 0.05 the same candle reaches 0.53 and is enough on its own
        lone = lambda dn: edit(CLUSTER, {1: candle(101.5, 101.7, 0.1, 0.1), 3: candle(101.6, 101.9, 0.4, dn)})
        self.silent(bearish(cluster=lone(0.2)))
        self.armed(bearish(cluster=lone(0.05)))

    # The next four tests pin each numeric threshold of the spec from both sides, about 1-7% either side of it, so a drifting
    # constant is caught. The cluster keeps bars 20-26 of the reference story with the wicks under test on bars 21 and 23
    # (body 101.6-102.0, so the highest body edge is 102.0 and the entry stays there).
    @staticmethod
    def twin(up, dn=0.0):
        """Bars 21 and 23 are two candles with an upper wick `up` (bar 21 a hair shorter, so bar 23 is the swing) and a lower shadow `dn`."""
        return [candle(101.3, 101.5, 0.1, 0.1),                            # 20
                candle(101.6, 102.0, round(up - 0.001, 4), dn),            # 21
                candle(101.7, 101.8, 0.05, 0.05),                          # 22 quiet, under the body edge
                candle(101.6, 102.0, up, dn),                              # 23 the swing high
                candle(101.9, 101.5, 0.05, 0.1),                           # 24
                CLUSTER[5], CLUSTER[6]]                                    # 25, 26 (the cluster's lowest low, 100.7)

    def test_the_wick_to_body_threshold_is_three_quarters(self):
        # body 0.4: wick 0.296 is 0.74 of it (not long), 0.304 is 0.76 (long); both candles are far above 0.40 of their range
        self.silent(bearish(cluster=self.twin(0.296)))
        s, sigs = self.armed(bearish(cluster=self.twin(0.304)))
        self.assertIn("2 candles with long upper wicks", sigs[0][1].reasons[0])

    def test_the_wick_to_range_threshold_is_forty_percent(self):
        # wick 0.8 on a 0.4 body (wick/body 2.0): a lower shadow of 0.82 puts the wick at 0.396 of the range (not long), 0.78 at 0.404
        self.silent(bearish(cluster=self.twin(0.8, 0.82)))
        s, sigs = self.armed(bearish(cluster=self.twin(0.8, 0.78)))
        self.assertIn("2 candles with long upper wicks", sigs[0][1].reasons[0])

    def test_one_candle_alone_needs_half_of_its_range(self):
        # a single candle with wick 0.8 on a 0.4 body: a lower shadow of 0.42 gives wick/range 0.494 (not enough alone), 0.38 gives 0.506
        def lone(dn):
            return edit(CLUSTER, {1: candle(101.5, 101.7, 0.1, 0.1), 2: candle(101.7, 101.8, 0.05, 0.05), 3: candle(101.6, 102.0, 0.8, dn),
                                  4: candle(101.9, 101.5, 0.05, 0.1)})
        self.silent(bearish(cluster=lone(0.42)))
        self.armed(bearish(cluster=lone(0.38)))

    def test_the_zone_threshold_is_fifteen_percent_of_the_median_candle_range(self):
        def tiny(h):
            return [candle(101.70, 101.70, 0.0, 0.0)] * 3 + [candle(101.70, 101.71, h, 0.01)] + [candle(101.70, 101.70, 0.0, 0.0)] * 3
        confirm = candle(101.7, 100.3, 0.0, 0.0)
        probe = bearish(cluster=tiny(0.06), after=[confirm] + RETRACE)
        mr = statistics.median(hi - lo for _, hi, lo, _ in probe[7:27])    # the 20 candles before the confirming one (bar 27)
        self.assertAlmostEqual(mr, 0.45, places=6)
        self.silent(bearish(cluster=tiny(round(0.93 * 0.15 * mr, 4)), after=[confirm] + RETRACE))     # 0.0628: just under
        self.armed(bearish(cluster=tiny(round(1.07 * 0.15 * mr, 4)), after=[confirm] + RETRACE))      # 0.0722: just over

    def test_a_wick_buried_beneath_another_candles_body_is_not_part_of_the_zone(self):
        # bar 22 has a long wick (wick/body 1.1, wick/range 0.44) but its high 101.98 stays under the 102.0 body edge
        buried = (101.6, 101.98, 101.53, 101.78)
        cluster = edit(CLUSTER, {1: candle(101.5, 101.7, 0.1, 0.1), 2: buried, 3: candle(101.5, 102.0, 0.45, 0.0)})
        self.silent(bearish(cluster=cluster))
        # the same pair with the second wick poking above the body edge (102.25 vs 102.0) counts and the block forms
        self.armed(bearish(cluster=edit(cluster, {2: (101.6, 102.25, 101.55, 101.95)})))

    def test_a_sliver_of_a_zone_is_below_the_minimum_height(self):
        # a cluster of tiny doji-like candles: the wicks are long for their bodies but the zone (0.04) is smaller than
        # 0.15 x the median candle range (0.45 -> 0.0675); at 0.12 it passes
        def tiny(h):
            return [candle(101.70, 101.70, 0.0, 0.0)] * 3 + [candle(101.70, 101.71, h, 0.01)] + [candle(101.70, 101.70, 0.0, 0.0)] * 3
        confirm = candle(101.7, 100.3, 0.0, 0.0)
        self.silent(bearish(cluster=tiny(0.04), after=[confirm] + RETRACE))
        self.armed(bearish(cluster=tiny(0.12), after=[confirm] + RETRACE))

    def test_the_swing_must_hold_the_highest_high_of_twenty_candles(self):
        # 19 candles before the swing is inside its 20-candle window; 20 candles before is outside it
        inside, outside = lead(), lead()
        inside[4] = (98.0, 103.0, 97.9, 98.1)
        outside[3] = (98.0, 103.0, 97.4, 97.9)
        self.silent(bearish(pre=inside))
        self.armed(bearish(pre=outside))

    def test_a_higher_high_in_the_three_candles_after_means_it_is_not_the_swing(self):
        cluster = edit(CLUSTER, {4: candle(101.9, 101.5, 1.1, 0.1)})    # bar 24 prints 103.0: a new swing whose cluster has not confirmed
        self.silent(bearish(cluster=cluster))

    def test_zero_range_candles_do_not_divide_by_zero(self):
        self.silent([(100.0, 100.0, 100.0, 100.0)] * 80)
        flat = edit(CLUSTER, {0: (101.5, 101.5, 101.5, 101.5), 2: (101.8, 101.8, 101.8, 101.8)})
        s, sigs = run("rejection", bearish(cluster=flat))
        self.assertEqual(len(sigs), 1)                                 # the flat candles are skipped, the two real wicks still count

    def test_gravestone_dojis_count_as_long_wicks_with_no_body(self):
        # open = close: wick/body is unbounded, and what decides is the wick to range (0.88 and 0.91)
        cluster = edit(CLUSTER, {1: (101.6, 102.3, 101.5, 101.6), 3: (101.8, 102.8, 101.7, 101.8)})
        s, sigs = self.armed(bearish(cluster=cluster))
        self.assertAlmostEqual(sigs[0][1].entry_ref, 101.9, places=6)  # the highest body edge is now bar 24's open
        self.assertAlmostEqual(sigs[0][1].stop, 102.82, places=6)

    def test_too_little_history_does_not_raise_or_fire(self):
        for n in (0, 1, 10, 22, 23):
            s, sigs = run("rejection", bearish()[:n])
            self.assertEqual((sigs, staged(s)), ([], 0))

    # ------------------------------------------------------------------ the order lifecycle
    def test_the_limit_rests_for_five_candles_then_expires(self):
        away = [AWAY] * 4                                              # 28-31
        s, sigs = self.armed(bearish(after=[CONFIRM] + away + [(100.0, 102.1, 99.9, 100.5)]))     # 32: the 5th candle may still fill
        self.assertEqual([i for i, _ in sigs], [32])
        s, sigs = self.armed(bearish(after=[CONFIRM] + away + [AWAY, (100.0, 102.1, 99.9, 100.5)]))   # 33: the order is gone
        self.assertEqual(sigs, [])
        self.assertTrue(any("expired" in d.message for d in s.decisions))

    def test_the_live_order_list_counts_candles_left_from_the_models_own_expiry(self):
        # the scanner and the analysis page show `bars_left` / `_expiry_bars() - bars`: for this model that is the 5 candles the
        # limit may rest, not the 18 (90 minutes) the opening-range base would say
        for name, series in (("as built", bearish()), ("mirrored", mirror(bearish()))):
            with self.subTest(name):
                s, _ = run("rejection", series[:28])                   # the confirming close has just printed: 5 candles left
                self.assertEqual(s._expiry_bars(), 5)
                self.assertEqual(s.staged[0]["bars_left"], 5)
                s, _ = run("rejection", series[:30])                   # two candles later, still resting
                self.assertEqual(s.staged[0]["bars_left"], 3)
                self.assertEqual(s._expiry_bars() - s._setups[0].bars, 3)

    # ------------------------------------------------------------------ what the chart and the story are told
    def test_the_shift_is_the_close_through_the_clusters_far_extreme_and_the_zone_starts_at_the_cluster(self):
        tf = timedelta(minutes=5)
        # bearish: the confirming close (bar 27) broke the cluster's lowest low 100.7 (printed by bar 26), not the 102.0 entry;
        # the zone box starts at the first candle of the cluster (bar 20; the page subtracts one candle from fvg_time)
        # mirrored: the same story upside down, the cluster's highest high 99.3
        for name, series, shift in (("as built", bearish(), 100.7), ("mirrored", mirror(bearish()), 99.3)):
            with self.subTest(name):
                s, sigs = run("rejection", series)
                m = sigs[0][1].meta
                self.assertAlmostEqual(m["mss_level"], shift, places=6)
                self.assertEqual(m["mss_time"], T0 + 27 * tf)          # the confirming candle
                self.assertEqual(m["swing_time"], T0 + 26 * tf)        # where the shift line starts: the candle that printed the far extreme
                self.assertEqual(m["sweep_time"], T0 + 23 * tf)        # the wick high (low) that ran the liquidity
                self.assertEqual(m["fvg_time"], T0 + 21 * tf)          # cluster start (bar 20) + one candle
                self.assertEqual(m["fvg"], (102.0, 102.8) if name == "as built" else (97.2, 98.0))
                staged_ev = [e for e in s.events if e["type"] == "staged"]
                self.assertEqual(len(staged_ev), 1)
                self.assertEqual(staged_ev[0]["fvg_time"], T0 + 21 * tf)       # the event the replay and the chart read agrees

    # ------------------------------------------------------------------ the stop buffer
    def test_a_wider_configured_stop_buffer_wins_over_the_two_pip_default(self):
        # pip size 0.01: the default config buffer (1 pip) is under the 2-pip floor, so the stop is the wick plus 0.02 (see the
        # clean cases); a configured 5-pip buffer moves it to 0.05; 1.5 pips changes nothing
        for name, series, ext, sign in (("as built", bearish(), 102.8, 1), ("mirrored", mirror(bearish()), 97.2, -1)):
            with self.subTest(name):
                self.assertAlmostEqual(run("rejection", series, stop_buffer_pips=5.0)[1][0][1].stop, ext + sign * 0.05, places=6)
                self.assertAlmostEqual(run("rejection", series, stop_buffer_pips=1.5)[1][0][1].stop, ext + sign * 0.02, places=6)

    # ------------------------------------------------------------------ the daily draw
    def test_a_bearish_block_is_skipped_against_a_bullish_daily_draw_and_the_bullish_one_is_taken(self):
        up = drift(684, 97.0, 0.02)                                    # three trading days, each closing above the last high
        self.silent(up + bearish())
        s, sigs = run("rejection", up + mirror(bearish(), 196.0))      # the bullish block agrees with the draw
        self.assertEqual([x.direction for _, x in sigs], [1])
        self.assertIn("RJ-03 not against the daily draw (yesterday closed", sigs[0][1].reasons[2])

    def test_a_bullish_block_is_skipped_against_a_bearish_daily_draw_and_the_bearish_one_is_taken(self):
        down = drift(684, 99.0, -0.02)
        self.silent(down + mirror(bearish(), 196.0))
        s, sigs = run("rejection", down + bearish())
        self.assertEqual([x.direction for _, x in sigs], [-1])

    # ------------------------------------------------------------------ noise
    def test_noise_a_random_walk_fires_a_modest_number_of_signals(self):
        rng = random.Random(7)
        price, bars = 100.0, []
        for _ in range(3000):
            o = price
            c = o + rng.gauss(0, 0.2)
            bars.append((round(o, 4), round(max(o, c) + abs(rng.gauss(0, 0.1)), 4), round(min(o, c) - abs(rng.gauss(0, 0.1)), 4), round(c, 4)))
            price = c
        s, sigs = run("rejection", bars)                              # the default cap: one signal per trading day
        self.assertLessEqual(len(sigs), 11)                            # 3000 bars is ~10.4 trading days
        s2, sigs2 = run("rejection", bars, max_signals_per_day=99)    # the cap lifted: what the detector itself puts down
        n_staged, n_filled = staged(s2), len(sigs2)
        print(f"\n[rejection noise] 3000 bars, seed 7: {n_staged} orders staged, {n_filled} filled (cap lifted); {len(sigs)} signals at the default cap of one a day")
        # Measured on this walk (seed 7): 224 swings of 20 candles (highs and lows), 102 of them confirmed by a close through
        # the cluster within 10 candles, 35 of those with the wicks of a block, 22 big enough and not against the daily draw
        # (staged), 5 of which price came back to fill. The bound is twice the staged count and under a fifth of the swings,
        # so a detector that fires on every swing or every confirmed cluster fails it, yet a small threshold tweak does not.
        self.assertGreaterEqual(n_staged, 1)                           # not dead on noise either
        self.assertLessEqual(n_staged, 45)
        self.assertLessEqual(n_filled, n_staged)
        for i, x in sigs2:                                             # whatever it fires is well formed
            self.assertTrue(x.reasons[0].startswith("RJ-01") and x.reasons[1].startswith("RJ-02") and x.reasons[2].startswith("RJ-03"))
            self.assertEqual(x.entry_type, "limit")
            self.assertGreater((x.entry_ref - x.stop) * x.direction, 0)    # the stop is on the losing side of the entry
            self.assertGreater((x.target - x.entry_ref) * x.direction, 0)  # the target on the winning side

    # ------------------------------------------------------------------ one idea at a time
    def test_an_equal_high_inside_the_swing_window_is_the_same_block_not_a_second_order(self):
        # bar 25 prints the same high 102.8 as the swing candle (bar 23): both are swings, with overlapping clusters. The first
        # confirms at bar 27 (order resting), the second at bar 29 while the first still rests: one order, one fill, never two
        double = edit(CLUSTER, {5: (101.5, 102.8, 101.0, 101.1)})
        after = [CONFIRM, (100.3, 100.9, 100.2, 100.8), (100.8, 100.9, 99.9, 100.0), (100.0, 101.2, 99.9, 101.1),
                 (101.1, 102.1, 101.0, 101.5), (101.5, 102.2, 101.3, 101.6)]       # 27-32: 31 touches the limit, so does 32
        s, sigs = self.armed(bearish(cluster=double, after=after), max_signals_per_day=99)
        self.assertEqual([(i, x.direction) for i, x in sigs], [(31, -1)])
        s, sigs = run("rejection", mirror(bearish(cluster=double, after=after)), max_signals_per_day=99)
        self.assertEqual([(i, x.direction) for i, x in sigs], [(31, 1)])

    def test_an_equal_high_after_the_first_order_is_gone_is_still_the_same_block(self):
        # the first order expires unfilled (5 candles), then the equal-high swing confirms: still the block already staged
        double = edit(CLUSTER, {5: (101.5, 102.8, 101.0, 101.1)})
        away = [(100.3, 100.9, 100.2, 100.8)] + [candle(100.5, 100.2, 0.05, 0.05)] * 4        # 28-32
        late = [(100.3, 100.4, 99.4, 99.5)]                                                    # 33 closes below every low so far
        s, sigs = self.armed(bearish(cluster=double, after=[CONFIRM] + away + late))
        self.assertEqual(sigs, [])

    def test_no_two_orders_of_one_side_rest_together_and_no_equal_high_is_staged_twice(self):
        # random walks rounded to the tick: equal highs/lows are common, and used to put the same block down twice
        tf, total = timedelta(minutes=5), 0
        for seed in range(6):
            for tick in (0.01, 0.05):
                s = self.build(max_signals_per_day=99)
                for i, b in enumerate(tick_walk(2500, seed, tick)):
                    s.on_bar(Bar(T0 + i * tf, *b))
                    sides = [x["direction"] for x in s.staged]
                    self.assertEqual(len(sides), len(set(sides)), (seed, tick, i))
                st = orders(s)
                total += len(st)
                for j, a in enumerate(st):
                    for b in st[j + 1:]:                                   # the zone box starts 3 candles before the swing: a 20-candle gap = one swing window
                        if a["dir"] == b["dir"] and a["level"] == b["level"]:
                            self.assertGreaterEqual(b["fvg_time"] - a["fvg_time"], 20 * tf, (seed, tick, a, b))
        self.assertGreater(total, 60)                                      # the walks do produce blocks: the checks above are not empty

    # ------------------------------------------------------------------ robustness
    @staticmethod
    def build(**kw):
        st = replace(CFG.strategy, model="rejection", timeframe_minutes=5, min_stop_pips=0, max_stop_pips=1e9, min_rr=0.1,
                     liquidity_pools=True, daily_bias_filter=False, **kw)
        return make_strategy(st, replace(CFG.instrument, pip_size=0.01))

    def test_a_missing_or_broken_price_never_raises_and_never_reaches_an_order(self):
        nan, inf = float("nan"), float("inf")
        base = bearish()
        for bad in (nan, inf, -inf):
            for i in range(14, len(base)):                                 # the lead-in's last candles, the cluster, the confirmation, the retrace
                for k in range(4):
                    b = list(base[i])
                    b[k] = bad
                    series = edit(base, {i: tuple(b)})
                    for name, ser in (("as built", series), ("mirrored", mirror(series))):
                        s, sigs = run("rejection", ser)
                        for e in orders(s):                                # (the target comes from the engine's shared pools: an infinite price poisons those for every model)
                            mine = (e["limit"], e["stop"], *e["fvg"]) + ((e["target"],) if math.isnan(bad) else ())
                            self.assertTrue(all(math.isfinite(v) for v in mine), (bad, i, k, name, e))
        rng = random.Random(3)
        for seed in range(10):                                             # and a walk with a bad price here and there
            bars = tick_walk(600, seed)
            for _ in range(10):
                j, b = rng.randrange(25, 590), None
                b = list(bars[j])
                b[rng.randrange(4)] = rng.choice([nan, inf, -inf])
                bars[j] = tuple(b)
            s, sigs = run("rejection", bars, max_signals_per_day=99)
            for e in orders(s):
                self.assertTrue(all(math.isfinite(v) for v in (e["limit"], e["stop"], e["target"], *e["fvg"])), (seed, e))

    def test_flat_and_inverted_candles_and_zero_prices_do_not_raise(self):
        for series in ([(0.0,) * 4] * 120, [(100.0,) * 4] * 120, [(5.0, 4.0, 6.0, 5.0)] * 120,        # all zero, all flat, high below low
                       [(100.0, 100.0, 100.0, 100.0)] * 40 + [(100.0, 101.0, 100.0, 100.0)] + [(100.0,) * 4] * 40):
            for ser in (series, mirror(series)):
                s, sigs = run("rejection", ser)
                assert_well_formed(self, s, sigs)
        rng = random.Random(1)
        for _ in range(20):                                                # any four numbers at all, even a close outside its own candle
            s, sigs = run("rejection", [tuple(round(100 + rng.gauss(0, 1), 2) for _ in range(4)) for _ in range(400)], max_signals_per_day=99)
            assert_well_formed(self, s, sigs)

    def test_any_price_scale_and_pip_size_builds_only_well_formed_orders(self):
        # EURUSD-like (pip 0.0001), JPY-like (0.01), indices (1.0), from tiny prices to huge ones; the buffer is 2 pips wherever the pip is
        raw = tick_walk(1200, 4)
        seen = 0
        for scale in (1e-4, 1.0, 1e6):
            for pip in (1e-5, 1e-4, 0.01, 1.0):
                series = [tuple(v * scale / 100.0 for v in b) for b in raw]
                for ser in (series, exact_mirror(series, 2.0 * scale)):
                    st = replace(CFG.strategy, model="rejection", timeframe_minutes=5, min_stop_pips=0, max_stop_pips=1e12, min_rr=0.01,
                                 liquidity_pools=True, daily_bias_filter=False, max_signals_per_day=99)
                    s = make_strategy(st, replace(CFG.instrument, pip_size=pip))
                    sigs = [(i, x) for i, b in enumerate(ser) if (x := s.on_bar(Bar(T0 + timedelta(minutes=5 * i), *b)))]
                    assert_well_formed(self, s, sigs)
                    seen += len(orders(s))
        self.assertGreater(seen, 100)

    def test_the_stop_buffer_is_two_pips_whatever_the_pip_size(self):
        for pip, ndigits in ((0.01, 6), (0.0001, 8), (1.0, 4)):
            scale = pip / 0.01
            series = [tuple(v * scale for v in b) for b in bearish()]
            st = replace(CFG.strategy, model="rejection", timeframe_minutes=5, min_stop_pips=0, max_stop_pips=1e12, min_rr=0.01,
                         liquidity_pools=True, daily_bias_filter=False)
            s = make_strategy(st, replace(CFG.instrument, pip_size=pip))
            sigs = [x for i, b in enumerate(series) if (x := s.on_bar(Bar(T0 + timedelta(minutes=5 * i), *b)))]
            self.assertEqual(len(sigs), 1)
            self.assertAlmostEqual(sigs[0].stop - 102.8 * scale, 2 * pip, places=ndigits)

    # ------------------------------------------------------------------ the past only
    def test_a_longer_history_never_changes_what_was_staged_earlier(self):
        # a decision on candle i is made from candles up to i: every prefix of a series reports exactly the orders and fills
        # the full run had reported by then (the same walk, cut at several places, in both directions)
        tf = timedelta(minutes=5)
        full = tick_walk(1500, 9, 0.05, vol=0.3, wick=0.35)
        for ser in (full, mirror(full, 200.0)):
            s, sigs = run("rejection", ser, max_signals_per_day=99)
            mark = lambda st, sg, cut: ([(e["time"], e["dir"], e["limit"], e["stop"], e["target"], e["fvg_time"]) for e in orders(st)
                                         if e["time"] <= T0 + (cut - 1) * tf], [(i, x.direction, x.entry_ref, x.stop) for i, x in sg if i < cut])
            self.assertGreater(len(orders(s)), 5)
            for cut in (80, 200, 333, 640, 1001, 1400):
                s2, sigs2 = run("rejection", ser[:cut], max_signals_per_day=99)
                self.assertEqual(mark(s2, sigs2, cut), mark(s, sigs, cut), cut)

    def test_every_order_on_long_random_walks_is_well_formed(self):
        for seed in range(4):
            for tick in (0.01, 0.05):
                bars = tick_walk(2500, seed, tick)
                for ser in (bars, mirror(bars, 200.0)):
                    s, sigs = run("rejection", ser, max_signals_per_day=99)
                    assert_well_formed(self, s, sigs)

    def test_mirror_symmetry_on_exact_prices(self):
        # prices on a 1/64 lattice and the reflection price -> 256 - price are exact, so even the threshold ties must agree:
        # same candles ordered, opposite sides, same distances, same reward, same fills
        total = 0
        for seed in range(8):
            rng = random.Random(seed)
            bars = tick_walk(2000, seed, 1 / 64, 128.0, vol=rng.choice([0.15, 0.3, 0.6]), wick=rng.choice([0.15, 0.3, 0.7]))
            s1, g1 = run("rejection", bars, max_signals_per_day=99)
            s2, g2 = run("rejection", exact_mirror(bars), max_signals_per_day=99)
            o1, o2 = orders(s1), orders(s2)
            total += len(o1)
            self.assertEqual(len(o1), len(o2), seed)
            for a, b in zip(o1, o2):
                self.assertEqual((a["time"], a["dir"], a["fvg_time"]), (b["time"], -b["dir"], b["fvg_time"]))
                self.assertAlmostEqual(a["limit"] + b["limit"], 256.0, places=9)
                self.assertAlmostEqual(a["stop"] + b["stop"], 256.0, places=9)
                self.assertAlmostEqual(a["target"] + b["target"], 256.0, places=9)
                self.assertAlmostEqual(a["rr"], b["rr"], places=9)
            self.assertEqual([(i, x.direction) for i, x in g1], [(i, -x.direction) for i, x in g2], seed)
        self.assertGreater(total, 60)

    # ------------------------------------------------------------------ the cost and the memory
    def test_the_detector_reads_a_bounded_number_of_candles_per_candle(self):
        class Counting(list):
            reads = 0

            def __getitem__(self, k):
                Counting.reads += len(range(*k.indices(len(self)))) if isinstance(k, slice) else 1
                return list.__getitem__(self, k)

        s = self.build(max_signals_per_day=99)
        s._bars, calm, orig, quiet = Counting(), [], s._detect, []

        def watched(idx, close_time, pip):
            r, n = Counting.reads, len(s.events)
            orig(idx, close_time, pip)
            (calm if len(s.events) == n else quiet).append((idx, Counting.reads - r))

        s._detect = watched
        for i, b in enumerate(tick_walk(3000, 2)):
            s.on_bar(Bar(T0 + timedelta(minutes=5 * i), *b))
        self.assertGreater(len(quiet), 10)                                 # orders were put down (their staging is the shared base code, not measured here)
        self.assertLessEqual(max(r for _, r in calm), 100)                 # every other candle: a swing test, a median and a geometry at most (about 75 at worst)
        self.assertLessEqual(max(r for i, r in calm if i > 2500), max(r for i, r in calm if i < 500) + 25)    # nothing grows with the history

    def test_what_the_model_remembers_is_bounded_over_a_long_run(self):
        s = self.build(max_signals_per_day=99)
        judged, orig = [], s._try

        def counted(*a):
            judged.append(1)
            return orig(*a)

        s._try = counted
        peak = 0
        for i, b in enumerate(tick_walk(12000, 5)):
            s.on_bar(Bar(T0 + timedelta(minutes=5 * i), *b))
            peak = max(peak, len(s._seen), len(s._blocks), len(s._wait))
        self.assertGreater(len(judged), 300)                               # far more swings were judged than the cap: the cap is what held
        self.assertLessEqual(peak, 140)
        self.assertGreater(min(k[1] for k in s._seen), len(s._bars) - 6000)    # the old ones were forgotten (all 12000 bars' worth would be ~300)
        self.assertTrue(all(w[1] >= len(s._bars) - 20 for w in s._wait))


if __name__ == "__main__":
    unittest.main()
