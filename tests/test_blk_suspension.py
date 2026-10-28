"""Suspension Block (ict_trader/blk_suspension.py): three candles closing the same way with a volume imbalance either side of B.

The bars are 5-minute (open, high, low, close) tuples run through the same helper as the other pattern models (pip size 0.01, so the
one-tick overshoot is 0.01). Four hand-built stories cover both candle colours in both trade directions, because the colour of the
three candles does not decide the direction, the location does:

  buy_case    up-up-up in DISCOUNT: price is above the box, a buy limit rests at once in its lower half (a retest from above)
  sell_case   up-up-up in PREMIUM:  price is above the box, so the box is armed until a candle closes back under the limit, then the
              sell limit rests and the return fills it
  mirror(...) every price p becomes 200 - p: down-down-down in PREMIUM (a sell) and in DISCOUNT (a buy, armed)

The lead-in is built so that nothing else fires: every lead bar opens at the previous close (no imbalance anywhere), and every turn
pokes out a little further than its neighbour so the swing highs and lows are clean liquidity for the target. Bar numbers (index in
the list): the lead is 0-22, A = 23, B = 24, C = 25, then the tail.

buy_case numbers:   A closes 99.30, B opens 99.45 (lower imbalance 99.30-99.45), closes 99.75, C opens 99.90 (upper imbalance
                    99.75-99.90). Box [99.30, 99.90], CE 99.60. B's wicks overrun the box (low 99.25, high 99.95): they are not
                    the edges. Dealing range 98.60-101.40, equilibrium 100.00: the CE is in discount. Limit 99.60, stop 99.29,
                    target the swing high 100.80 (3.87R). D trades down to 99.55 and fills.
sell_case numbers:  A closes 100.70, B opens 100.85, closes 101.15, C opens 101.30. Box [100.70, 101.30], CE 101.00; range
                    98.60-101.80, equilibrium 100.20: premium. Limit 101.00, stop 101.31. C closes at 101.70, above the limit, so
                    the box waits; D closes at 100.90 (below the limit) and the order rests; E trades up to 101.05 and fills.
"""

import random
import unittest
from dataclasses import replace
from datetime import timedelta
from unittest import mock

from ict_trader import blk_suspension
from ict_trader.models import make_strategy
from ict_trader.sessions import Bar
from ict_trader.strategy import LONG, SHORT
from tests.test_patterns import CFG, T0, run

MIRROR = 200.0


def chain(start, segs, step=0.3, wick=0.1):
    """Bars that each open at the previous close (so no volume imbalance anywhere), walking straight lines of `step` per bar.

    segs = [(bars, +1 or -1), ...]. The bar that turns the walk pokes out one extra wick beyond its neighbour: a clean swing.
    Every bar is `step` + 2 wicks tall, so the median range is known (0.5 with the defaults).
    """
    p, bars = start, [(start, start + wick, start - wick, start)]
    for n, sgn in segs:
        for j in range(n):
            o, c = p, round(p + sgn * step, 4)
            tip = wick if j == n - 1 else 0.0
            bars.append((o, round(max(o, c) + wick + (tip if sgn > 0 else 0.0), 4), round(min(o, c) - wick - (tip if sgn < 0 else 0.0), 4), c))
            p = c
    return bars


def mirror(bars, k=MIRROR):
    return [(round(k - o, 4), round(k - l, 4), round(k - h, 4), round(k - c, 4)) for o, h, l, c in bars]


def flip(bars, k):
    """The same market upside down, unrounded (for the noise walk: rounding would nudge the geometry)."""
    return [(k - o, k - l, k - h, k - c) for o, h, l, c in bars]


def both(bars):
    return (("as built", bars), ("mirrored", mirror(bars)))


def make(**kw):
    """The strategy exactly as run() builds it, for the tests that need to poke at it between bars."""
    st = replace(CFG.strategy, model="suspension", timeframe_minutes=5, min_stop_pips=0, max_stop_pips=1e9, min_rr=0.1,
                 liquidity_pools=True, daily_bias_filter=False)
    return make_strategy(replace(st, **kw), replace(CFG.instrument, pip_size=0.01))


def feed(s, bars, start=0):
    out = []
    for i, b in enumerate(bars, start):
        x = s.on_bar(Bar(T0 + timedelta(minutes=5 * i), *b))
        if x:
            out.append((i, x))
    return out


def staged(s):
    return [e for e in s.events if e["type"] == "staged"]


def edit(bars, changes):
    out = list(bars)
    for i, b in changes.items():
        out[i] = b
    return out


LEAD_BUY = chain(100.0, [(4, 1), (8, -1), (6, 1), (4, -1)])      # 23 bars, ends at 99.40; swing highs 101.40 and 100.80
LEAD_SELL = chain(100.0, [(4, -1), (8, 1), (6, -1), (4, 1)])     # 23 bars, ends at 100.60; swing lows 98.60 and 99.20
BUY_ABC = [(99.10, 99.45, 99.05, 99.30), (99.45, 99.95, 99.25, 99.75), (99.90, 100.30, 99.70, 100.20)]
BUY_TAIL = [(100.10, 100.15, 99.55, 99.80)]                                    # D: dips to 99.55 and fills the 99.60 limit
SELL_ABC = [(100.55, 100.95, 100.50, 100.70), (100.85, 101.45, 100.65, 101.15), (101.30, 101.80, 101.10, 101.70)]
SELL_LEAVE = (101.60, 101.65, 100.80, 100.90)                                   # D: closes under the 101.00 limit
SELL_RETURN = (100.90, 101.05, 100.80, 100.95)                                  # E: trades up to 101.05 and fills
A_IDX, C_IDX = 23, 25


def buy_case(abc=BUY_ABC, tail=BUY_TAIL, lead=None):
    return list(lead or LEAD_BUY) + list(abc) + list(tail)


def sell_case(abc=SELL_ABC, tail=(SELL_LEAVE, SELL_RETURN), lead=None):
    return list(lead or LEAD_SELL) + list(abc) + list(tail)


def walk(seed, n, sigma=0.3, gap=0.4):
    """A random walk whose candles open a little away from the previous close (a pure chain never has an imbalance)."""
    r, p, out = random.Random(seed), 100.0, []
    for _ in range(n):
        o = p + r.gauss(0, gap * sigma)
        c = o + r.gauss(0, sigma)
        out.append((o, max(o, c) + abs(r.gauss(0, sigma / 2)), min(o, c) - abs(r.gauss(0, sigma / 2)), c))
        p = c
    return out


class BoxTest(unittest.TestCase):
    # ------------------------------------------------------------------ the clean stories, both colours, both directions
    def test_up_up_up_in_discount_is_a_buy_block_with_the_limit_in_the_lower_half(self):
        s, sigs = run("suspension", buy_case())
        self.assertEqual([i for i, _ in sigs], [26])                       # D trades down to the limit
        sig = sigs[0][1]
        self.assertEqual(sig.direction, LONG)
        self.assertEqual(sig.entry_type, "limit")
        self.assertAlmostEqual(sig.entry_ref, 99.60, places=6)             # the CE of [99.30, 99.90]
        self.assertAlmostEqual(sig.stop, 99.29, places=6)                  # the box bottom less one tick
        self.assertAlmostEqual(sig.target, 100.80, places=6)               # the nearest swing high above
        self.assertEqual([r[:5] for r in sig.reasons[:3]], ["SB-01", "SB-02", "SB-03"])
        self.assertIn("up candles", sig.reasons[0])
        self.assertIn("99.300 to 99.450 and 99.750 to 99.900", sig.reasons[0])          # the two imbalances, with prices
        self.assertIn("99.300 to 99.900", sig.reasons[1])
        self.assertIn("consequent encroachment 99.600", sig.reasons[1])
        self.assertIn("discount", sig.reasons[2])
        self.assertIn("buy block", sig.reasons[2])
        self.assertTrue(sig.reasons[3].startswith("RL-05"))
        lo, hi = sorted(sig.meta["fvg"])
        self.assertAlmostEqual(lo, 99.30, places=6)                        # the far edges of the imbalances: A's close and C's open ...
        self.assertAlmostEqual(hi, 99.90, places=6)                        # ... not B's low 99.25 and high 99.95
        self.assertEqual(s._seen, {(1, A_IDX)})

    def test_down_down_down_in_premium_is_a_sell_block_the_exact_mirror(self):
        s, sigs = run("suspension", mirror(buy_case()))
        self.assertEqual([i for i, _ in sigs], [26])
        sig = sigs[0][1]
        self.assertEqual(sig.direction, SHORT)
        self.assertAlmostEqual(sig.entry_ref, 100.40, places=6)
        self.assertAlmostEqual(sig.stop, 100.71, places=6)                 # the box top plus one tick
        self.assertAlmostEqual(sig.target, 99.20, places=6)                # the nearest swing low below
        self.assertEqual([r[:5] for r in sig.reasons[:3]], ["SB-01", "SB-02", "SB-03"])
        self.assertIn("down candles", sig.reasons[0])
        self.assertIn("premium", sig.reasons[2])
        self.assertIn("sell block", sig.reasons[2])
        lo, hi = sorted(sig.meta["fvg"])
        self.assertAlmostEqual(lo, 100.10, places=6)
        self.assertAlmostEqual(hi, 100.70, places=6)
        self.assertEqual(s._seen, {(-1, A_IDX)})

    def test_up_up_up_in_premium_waits_armed_until_price_leaves_then_sells_the_return(self):
        bars = sell_case()
        s = make()
        out = feed(s, bars[:C_IDX + 1])                                    # up to and including C
        self.assertEqual(out, [])
        self.assertEqual(len(s._armed), 1)                                 # price (101.70) is above the limit: it cannot rest yet
        self.assertEqual(s.staged, [])
        out += feed(s, bars[C_IDX + 1:C_IDX + 2], C_IDX + 1)               # D closes at 100.90, under the limit
        self.assertEqual(s._armed, [])
        self.assertEqual(len(s.staged), 1)
        self.assertEqual(s.staged[0]["direction"], "short")
        self.assertAlmostEqual(s.staged[0]["limit"], 101.00, places=6)
        self.assertEqual(out, [])
        out += feed(s, bars[C_IDX + 2:], C_IDX + 2)                        # E trades back up into the box
        self.assertEqual([i for i, _ in out], [27])
        sig = out[0][1]
        self.assertEqual(sig.direction, SHORT)
        self.assertAlmostEqual(sig.entry_ref, 101.00, places=6)
        self.assertAlmostEqual(sig.stop, 101.31, places=6)
        self.assertAlmostEqual(sig.target, 99.20, places=6)
        self.assertEqual([r[:5] for r in sig.reasons[:3]], ["SB-01", "SB-02", "SB-03"])
        self.assertIn("premium", sig.reasons[2])
        self.assertIn("came back", sig.reasons[2])                         # the trail says price had left first
        lo, hi = sorted(sig.meta["fvg"])
        self.assertAlmostEqual(lo, 100.70, places=6)
        self.assertAlmostEqual(hi, 101.30, places=6)

    def test_down_down_down_in_discount_is_the_armed_buy_block(self):
        bars = mirror(sell_case())
        s = make()
        feed(s, bars[:C_IDX + 1])
        self.assertEqual(len(s._armed), 1)
        self.assertEqual(s.staged, [])
        out = feed(s, bars[C_IDX + 1:], C_IDX + 1)
        self.assertEqual([i for i, _ in out], [27])
        sig = out[0][1]
        self.assertEqual(sig.direction, LONG)
        self.assertAlmostEqual(sig.entry_ref, 99.00, places=6)
        self.assertAlmostEqual(sig.stop, 98.69, places=6)                  # the box bottom less one tick
        self.assertAlmostEqual(sig.target, 100.80, places=6)
        self.assertIn("discount", sig.reasons[2])
        self.assertIn("down candles", sig.reasons[0])

    def test_the_colour_of_the_candles_does_not_decide_the_direction_the_location_does(self):
        seen = set()
        for name, bars in (("up in discount", buy_case()), ("up in premium", sell_case()),
                           ("down in premium", mirror(buy_case())), ("down in discount", mirror(sell_case()))):
            s, sigs = run("suspension", bars)
            self.assertEqual(len(sigs), 1, name)
            sig = sigs[0][1]
            seen.add(("up" if "up candles" in sig.reasons[0] else "down", sig.direction))
        self.assertEqual(seen, {("up", LONG), ("up", SHORT), ("down", SHORT), ("down", LONG)})

    def test_the_chart_gets_the_box_from_candle_a(self):
        s, sigs = run("suspension", buy_case())
        ev = staged(s)
        self.assertEqual(len(ev), 1)
        self.assertEqual(ev[0]["fvg"], (99.3, 99.9))
        self.assertEqual(ev[0]["fvg_time"], T0 + timedelta(minutes=5 * (A_IDX + 1)))    # the chart draws from fvg_time minus one candle
        self.assertAlmostEqual(ev[0]["limit"], 99.60, places=6)
        self.assertEqual(len(s.staged), 0)                                  # filled: nothing is left resting

    # ------------------------------------------------------------------ the lesson's own chart, replayed
    def test_the_nq_daily_block_of_486N8ow3U2A_is_read_and_traded_as_the_lesson_shows_it(self):
        # 486N8ow3U2A@00m25 (NQ daily, Jan-Feb 2026), prices read off the frame (about 1.9 points a pixel). The orange box is the
        # left edge of A's close to C's open, with the dotted CE at 25,979; B's wicks overrun both edges; price falls back into the box
        # (D opens above its top, closes inside it above the CE), drops through it, and the rally two candles later wicks into the CE.
        lead = chain(25425.0, [(4, -1), (8, 1), (6, -1), (4, 1)], step=75.0, wick=90.0)            # 23 daily-sized bars, ends at 25,575
        a, b, c = (25575, 25934, 25560, 25845), (25860, 26117, 25838, 26072), (26111, 26347, 25994, 26156)
        d, e = (26281, 26293, 25350, 25998), (25994, 26018, 25569, 25668)
        f, g = (25528, 25948, 25180, 25849), (25873, 26028, 25342, 25398)                           # f stops short of the CE, g wicks through it
        bars = list(lead) + [a, b, c, d, e, f, g]
        for orient, bb, side in (("as built", bars, SHORT), ("mirrored", mirror(bars, 51000.0), LONG)):
            with self.subTest(orient=orient):
                s = make()
                feed(s, bb[:C_IDX + 1])
                self.assertEqual(len(s._armed), 1)                                       # price is above the CE after C: armed
                self.assertAlmostEqual(abs(s._armed[0].hi - s._armed[0].lo), 266.0, places=6)    # 25,845 to 26,111
                self.assertAlmostEqual(abs(s._armed[0].ce - (25978.0 if side == SHORT else 51000.0 - 25978.0)), 0.0, places=6)
                feed(s, bb[C_IDX + 1:C_IDX + 2], C_IDX + 1)                              # D closes inside the box, above the CE: still armed
                self.assertEqual((len(s._armed), s.staged), (1, []))
                feed(s, bb[C_IDX + 2:C_IDX + 3], C_IDX + 2)                              # E closes under the CE: the limit rests
                self.assertEqual((s._armed, [x["direction"] for x in s.staged]), ([], ["short" if side == SHORT else "long"]))
                out = feed(s, bb[C_IDX + 3:C_IDX + 4], C_IDX + 3)
                self.assertEqual(out, [])                                                # f stops 30 points short of the CE
                out = feed(s, bb[C_IDX + 4:], C_IDX + 4)
                self.assertEqual([i for i, _ in out], [C_IDX + 4])
                sig = out[0][1]
                self.assertEqual(sig.direction, side)
                self.assertAlmostEqual(sig.entry_ref, 25978.0 if side == SHORT else 51000.0 - 25978.0, places=6)    # the dotted line
                self.assertAlmostEqual(abs(sig.stop - sig.entry_ref), 133.01, places=6)  # the box edge (26,111) plus one tick, not B's 26,117
                self.assertIn("premium" if side == SHORT else "discount", sig.reasons[2])
                lo, hi = sorted(sig.meta["fvg"])
                self.assertAlmostEqual(hi - lo, 266.0, places=6)

    # ------------------------------------------------------------------ near misses: one condition broken at a time
    NEAR_MISSES = {
        "A closes down": {23: (99.30, 99.45, 99.05, 99.10)},
        "B closes down": {24: (99.75, 99.95, 99.25, 99.45)},
        "C closes down": {25: (100.20, 100.30, 99.70, 99.90)},
        "B is a doji": {24: (99.45, 99.95, 99.25, 99.45)},
        "no lower imbalance: B opens at A's close": {24: (99.30, 99.95, 99.25, 99.75)},
        "lower bodies overlap: B opens inside A's body": {24: (99.20, 99.95, 99.15, 99.75)},
        "no upper imbalance: C opens at B's close": {25: (99.75, 100.30, 99.70, 100.20)},
        "upper bodies overlap: C opens inside B's body": {25: (99.65, 100.30, 99.60, 100.20)},
        "lower imbalance of 2 ticks is under 5% of the 0.50 median range": {24: (99.32, 99.95, 99.25, 99.75)},
        "upper imbalance of 2 ticks is under 5% of the 0.50 median range": {25: (99.77, 100.30, 99.70, 100.20)},
        "lower gap without wick contact is a vacuum, not an imbalance": {23: (99.10, 99.35, 99.05, 99.30), 24: (99.45, 99.95, 99.40, 99.75)},
        "upper gap without wick contact is a vacuum, not an imbalance": {25: (100.10, 100.40, 100.00, 100.30)},
        "a plain fair value gap (A high under C low) with bodies overlapping": {23: (99.00, 99.40, 98.95, 99.35), 24: (99.30, 99.80, 99.25, 99.70),
                                                                              25: (99.65, 100.20, 99.50, 100.10)},
    }

    def test_each_broken_condition_gives_no_block(self):
        for label, changes in self.NEAR_MISSES.items():
            for orient, bars in both(edit(buy_case(), changes)):
                with self.subTest(label, orient=orient):
                    s, sigs = run("suspension", bars)
                    self.assertEqual(sigs, [])
                    self.assertEqual((s.staged, s._armed, s._seen), ([], [], set()))
                    self.assertEqual([d for d in s.decisions if "suspension" in d.message], [])     # not even considered

    def test_the_same_edits_pass_when_the_condition_is_only_just_met(self):
        # an imbalance of 3 ticks clears 5% of 0.50 (2.5 ticks); the zone is still A's close to C's open
        for orient, bars in both(edit(buy_case(), {24: (99.33, 99.95, 99.25, 99.75)})):
            with self.subTest(orient=orient):
                s, sigs = run("suspension", bars)
                self.assertEqual(len(sigs), 1)
        for orient, bars in both(edit(buy_case(), {25: (99.78, 100.30, 99.70, 100.20)})):
            with self.subTest(orient=orient, side="upper"):
                s, sigs = run("suspension", bars)                            # the box is now [99.30, 99.78]: the limit (99.54) does not fill
                ev = staged(s)
                self.assertEqual(len(ev), 1)
                self.assertAlmostEqual(abs(ev[0]["fvg"][1] - ev[0]["fvg"][0]), 0.48, places=6)

    def test_the_two_tick_floor_binds_in_a_quiet_market(self):
        def scaled(bars, f):
            return [tuple(100 + (p - 100) * f for p in b) for b in bars]
        # the whole story shrunk: imbalances 0.15 x f; the median range is tiny, so only the 2-tick floor (0.02) matters
        _, small = run("suspension", scaled(buy_case(), 0.1))               # imbalances of 1.5 ticks: under the floor
        self.assertEqual(small, [])
        _, ok = run("suspension", scaled(buy_case(), 0.15))                 # 2.25 ticks: over it
        self.assertEqual(len(ok), 1)

    def test_nothing_is_read_before_twenty_candles_of_history(self):
        for n, expect_considered in ((17, False), (18, True)):             # C is bar 19 (too early) or bar 20 (the first allowed)
            s, sigs = run("suspension", LEAD_BUY[:n] + BUY_ABC + BUY_TAIL)
            considered = [d for d in s.decisions if "suspension" in d.message]
            self.assertEqual(bool(considered), expect_considered, n)

    def test_a_box_exactly_on_the_equilibrium_has_no_side(self):
        lead = chain(100.0, [(4, 1), (8, -1), (6, 1), (4, -1)], step=0.5, wick=0.25)    # range 97.50-102.50, equilibrium exactly 100.0
        abc = [(99.0, 99.75, 98.75, 99.5), (99.75, 100.5, 99.25, 100.25), (100.5, 101.0, 100.0, 100.75)]     # box [99.5, 100.5]: CE 100.0

        def shifted(dy):
            return list(lead) + [tuple(p + dy for p in b) for b in abc]
        for dy in (0.0, 1e-12, -1e-12):                                     # float noise around the equilibrium is still the equilibrium
            s = make()
            feed(s, shifted(dy))
            self.assertEqual((s.staged, s._armed, s._seen), ([], [], set()), dy)
        s = make()
        feed(s, shifted(0.0625))                                            # a hair above: premium, price is above the box: armed sell
        self.assertEqual([(x.d, x.m) for x in s._armed], [(SHORT, 1)])
        s = make()
        feed(s, shifted(-0.0625))                                           # a hair below: discount: a buy limit rests at once
        self.assertEqual([x["direction"] for x in s.staged], ["long"])

    def test_the_dealing_range_is_the_last_sixty_candles_only(self):
        # 51 candles on a plateau at 80 (a long way down), then 34 bars at 100, then the buy story: 60 candles back from C starts
        # after the plateau, so the box (CE 99.60) is in discount of 98.60-101.40, a buy. Over the whole history it would be a sell.
        plateau = [(80.0, 80.1, 79.9, 80.0)] * 51 + [(100.0, 100.1, 99.9, 100.0)] * 34
        s, sigs = run("suspension", plateau + buy_case())
        self.assertEqual([x.direction for _, x in sigs], [LONG])
        self.assertIn("last 60 candles", sigs[0][1].reasons[2])
        with mock.patch.object(blk_suspension, "SB_RANGE", 200):
            s, sigs = run("suspension", plateau + buy_case())
        self.assertEqual(sigs, [])                                          # now armed as a sell: price never leaves the box downward

    # ------------------------------------------------------------------ the daily bias
    def test_the_daily_bias_is_respected_like_the_other_pattern_models(self):
        for name, bars, d in (("up in discount", buy_case(), LONG), ("up in premium", sell_case(), SHORT),
                              ("down in premium", mirror(buy_case()), SHORT), ("down in discount", mirror(sell_case()), LONG)):
            for bias, want in ((0, 1), (d, 1), (-d, 0)):
                with self.subTest(name, bias=bias):
                    s = make()
                    s.daily_bias = lambda b=bias: (b, "test draw")
                    out = feed(s, bars)
                    self.assertEqual(len(out), want)
                    if want:
                        self.assertTrue(out[0][1].reasons[3].startswith("RL-05"))
                        self.assertIn("test draw", out[0][1].reasons[3])
                    else:
                        self.assertEqual((s._seen, s._armed, s.staged), (set(), [], []))

    # ------------------------------------------------------------------ the invalidation rule: a body close outside the box
    BACK = (101.70, 101.75, 101.15, 101.20)        # D: closes back inside the 100.70-101.30 box, above the 101.00 limit: price is at the box

    def test_an_armed_box_is_void_when_price_came_back_into_it_and_a_body_then_closes_beyond_its_stop_side_edge(self):
        tail = [self.BACK,
                (101.20, 102.00, 101.15, 101.90),         # E closes at 101.90, above the 101.30 top: the retest failed
                (101.90, 101.95, 100.50, 100.60),         # F closes under the limit: it would have rested
                (100.60, 101.10, 100.50, 100.90)]         # G trades up through 101.00
        for orient, bars, word in (("as built", sell_case(tail=tail), "above"), ("mirrored", mirror(sell_case(tail=tail)), "below")):
            with self.subTest(orient=orient):
                s, sigs = run("suspension", bars)
                self.assertEqual(sigs, [])
                self.assertEqual((s.staged, s._armed), ([], []))
                self.assertEqual(staged(s), [])                                # the order never rested, so nothing was ever staged
                self.assertTrue(any("void" in d.message and word in d.message and "came back" in d.message for d in s.decisions))

    def test_closes_beyond_the_edge_while_the_run_that_built_the_box_goes_on_do_not_void_it(self):
        # -Td-D-vKJDg@14m40: the orange sell block is candles A, B, C of a run of five up candles. D and E close far above the box
        # top (C itself did), then price falls back through the block and rallies into it from below: the lesson trades that return.
        up = [(101.70, 102.05, 101.65, 102.00), (102.00, 102.30, 101.95, 102.25)]       # D and E open at the previous close: no new box
        fall = [(102.25, 102.30, 101.40, 101.50), (101.50, 101.55, 100.70, 100.80), (100.80, 100.85, 100.20, 100.30)]
        rally = (100.30, 101.10, 100.25, 100.60)                                          # trades up through the 101.00 CE
        bars = sell_case(tail=up + fall + [rally])
        for orient, b, side in (("as built", bars, SHORT), ("mirrored", mirror(bars), LONG)):
            with self.subTest(orient=orient):
                s = make()
                feed(s, b[:C_IDX + 3])                                                   # through E
                self.assertEqual(len(s._armed), 1)                                       # still armed: not voided by D or E
                self.assertEqual(s.staged, [])
                out = feed(s, b[C_IDX + 3:], C_IDX + 3)
                self.assertEqual([i for i, _ in out], [C_IDX + 6])
                sig = out[0][1]
                self.assertEqual(sig.direction, side)
                self.assertAlmostEqual(sig.entry_ref, 101.00 if side == SHORT else 99.00, places=6)
                self.assertAlmostEqual(abs(sig.stop - sig.entry_ref), 0.31, places=6)    # the box edge plus one tick
                self.assertFalse(any("void" in d.message for d in s.decisions))

    def test_a_newer_armed_box_of_the_same_run_replaces_the_older_one_and_the_older_cannot_take_the_order_back(self):
        d4 = (101.85, 102.25, 101.75, 102.15)      # a fourth up candle: a second box B-C-D [101.15, 101.85], CE 101.50
        e = (102.15, 102.20, 101.20, 101.30)       # closes under 101.50: the newer box's order rests (the older box's 101.00 is still above)
        f = (101.30, 101.40, 100.70, 100.80)       # closes under 101.00: the older box would now rest, and replace the newer order
        g = (100.80, 101.55, 100.75, 101.40)       # trades up through 101.50
        bars = sell_case(tail=[d4, e, f, g])
        for orient, b in both(bars):
            with self.subTest(orient=orient):
                s = make()
                feed(s, b[:C_IDX + 1])
                self.assertEqual([round(x.entry, 4) for x in s._armed], [101.0 if orient == "as built" else 99.0])
                feed(s, b[C_IDX + 1:C_IDX + 2], C_IDX + 1)
                self.assertEqual(len(s._armed), 1)                                       # the older box was dropped, the newer one waits
                self.assertTrue(any("dropped" in d.message and "replaced by the newer box" in d.message for d in s.decisions))
                feed(s, b[C_IDX + 2:C_IDX + 3], C_IDX + 2)
                want = 101.50 if orient == "as built" else 98.50
                self.assertEqual([round(x["limit"], 4) for x in s.staged], [want])
                feed(s, b[C_IDX + 3:C_IDX + 4], C_IDX + 3)
                self.assertEqual([round(x["limit"], 4) for x in s.staged], [want])      # still the newer box's order
                out = feed(s, b[C_IDX + 4:], C_IDX + 4)
                self.assertEqual([(i, round(x.entry_ref, 4)) for i, x in out], [(C_IDX + 4, want)])

    def test_a_close_one_tick_beyond_and_wicks_through_the_edge_are_tolerated(self):
        stay = [(101.70, 101.80, 101.20, 101.31),      # closes exactly one tick over the top (101.30): tolerated, still above the limit
                (101.31, 103.00, 101.20, 101.25)]      # a wick 1.70 through the top that closes back inside: wicks do not count
        leave = (101.25, 101.30, 100.80, 100.90)       # now a close under the limit: the order rests
        fill = (100.90, 101.05, 100.80, 100.95)
        for orient, bars in both(sell_case(tail=stay + [leave, fill])):
            with self.subTest(orient=orient):
                s = make()
                feed(s, bars[:C_IDX + 3])
                self.assertEqual(len(s._armed), 1)                           # still armed after both
                out = feed(s, bars[C_IDX + 3:], C_IDX + 3)
                self.assertEqual([i for i, _ in out], [C_IDX + 4])
                self.assertAlmostEqual(abs(out[0][1].stop - out[0][1].entry_ref), 0.31, places=6)

    def test_after_the_return_two_ticks_beyond_voids_it_and_one_tick_does_not(self):
        for close, rests in ((101.31, 1), (101.32, 0)):                     # 101.31 is 1 tick over the 101.30 top, 101.32 is 2
            tail = [self.BACK, (101.20, close + 0.05, 101.15, close), (close, close + 0.02, 100.50, 100.60)]    # D back in, E out, F under the limit
            for orient, bars in both(sell_case(tail=tail)):
                with self.subTest(close=close, orient=orient):
                    s, sigs = run("suspension", bars)
                    self.assertEqual((sigs, len(s.staged)), ([], rests))     # F closes under the limit: it rests unless the box is void
                    self.assertEqual(s._armed, [])

    def test_a_resting_order_is_cancelled_when_a_body_closes_through_the_stop(self):
        # an order that cannot fill (no signal allowed today) is cancelled by the lifecycle the moment a bar goes through the stop,
        # which is where a body close beyond the box edge plus one tick ends up: no extra override is needed for orders
        bars = buy_case(tail=[(100.10, 100.15, 99.00, 99.10)])               # closes under the 99.30 bottom, low under the 99.29 stop
        for orient, b in both(bars):
            with self.subTest(orient=orient):
                s, sigs = run("suspension", b, max_signals_per_day=0)
                self.assertEqual((sigs, s.staged), ([], []))
                self.assertTrue(any(d.rule == "EN-04" and "stop" in d.message for d in s.decisions))
        s, sigs = run("suspension", bars)                                    # with a signal allowed, the same bar fills the limit first
        self.assertEqual([i for i, _ in sigs], [26])

    # ------------------------------------------------------------------ waiting and expiry
    def test_an_armed_box_gives_up_after_thirty_candles(self):
        inside = (101.20, 101.25, 101.15, 101.20)                            # above the limit, inside the box, under its top: stays armed
        out_beyond = (101.60, 101.65, 101.55, 101.60)                        # above the box top (the run's leg): stays armed too, never tested
        away = (101.20, 101.25, 100.80, 100.90)                              # closes under the limit
        edge = blk_suspension.SB_ARM_BARS
        for name, hover in (("inside", inside), ("beyond", out_beyond)):
            for n, expect in ((edge - 1, 1), (edge, 0)):
                for orient, bars in both(sell_case(tail=[hover] * n + [away])):
                    with self.subTest(hover=name, hovers=n, orient=orient):
                        s = make()
                        feed(s, bars)
                        self.assertEqual(len(s.staged), expect)

    def test_a_resting_order_expires_after_thirty_candles(self):
        quiet = (100.50, 100.60, 100.40, 100.50)
        edge = blk_suspension.SB_EXPIRY
        base = sell_case(tail=[SELL_LEAVE])
        for orient, bars in both(base):
            s = make()
            feed(s, bars)
            self.assertEqual(len(s.staged), 1)
            q = mirror([quiet]) if orient == "mirrored" else [quiet]
            feed(s, q * (edge - 1), len(bars))
            self.assertEqual(len(s.staged), 1, orient)
            feed(s, q, len(bars) + edge - 1)
            self.assertEqual(len(s.staged), 0, orient)
            self.assertTrue(any("expired" in d.message for d in s.decisions))

    def test_an_armed_box_does_not_survive_the_trading_day_roll(self):
        # the engine clears its resting orders at 17:00 New York (bar 108 on this clock); an armed box goes the same way
        plateau = lambda n: [(100.0, 100.1, 99.9, 100.0)] * n                # doji bars: no imbalance, no colour
        for pad, expect in ((62, 1), (82, 0)):                               # D at bar 88 (same day) or bar 108 (next day)
            for orient, bars in both(plateau(pad) + sell_case(tail=[SELL_LEAVE, SELL_RETURN])):
                with self.subTest(pad=pad, orient=orient):
                    s, sigs = run("suspension", bars)
                    self.assertEqual(len(sigs), expect)

    # ------------------------------------------------------------------ a run of candles, and the parameters
    def test_a_newer_box_sharing_a_candle_replaces_the_resting_order(self):
        lead = list(LEAD_BUY)
        lead[4] = (lead[4][0], 102.50, lead[4][2], lead[4][3])               # a taller first peak keeps both boxes in discount
        d4 = (100.35, 100.75, 100.15, 100.70)                                # a fourth up candle: a second box B-C-D, CE 100.05
        bars = lead + BUY_ABC + [d4, (100.60, 100.65, 100.00, 100.30)]
        s = make()
        out = feed(s, bars[:C_IDX + 1])
        self.assertEqual([x["limit"] for x in s.staged], [99.60])
        out += feed(s, bars[C_IDX + 1:C_IDX + 2], C_IDX + 1)
        self.assertEqual([round(x["limit"], 4) for x in s.staged], [100.05])    # the newer box replaced the older order
        self.assertTrue(any("replaced by the newer box" in d.message for d in s.decisions))
        out += feed(s, bars[C_IDX + 2:], C_IDX + 2)
        self.assertEqual([(i, round(x.entry_ref, 4)) for i, x in out], [(27, 100.05)])    # only one trade
        self.assertEqual(s._seen, {(1, 23), (1, 24)})

    def test_the_entry_fraction_moves_the_limit_towards_the_stop_side_edge(self):
        with mock.patch.object(blk_suspension, "SB_ENTRY_FRAC", 0.5):
            for orient, bars, want in (("buy", buy_case(), 99.45), ("sell", mirror(buy_case()), 100.55)):
                s = make()
                feed(s, bars[:C_IDX + 1])
                self.assertAlmostEqual(s.staged[0]["limit"], want, places=6, msg=orient)    # halfway from the CE to the edge

    def test_the_stop_buffer_is_at_least_the_engine_stop_buffer(self):
        s, sigs = run("suspension", buy_case(), stop_buffer_pips=3)
        self.assertAlmostEqual(sigs[0][1].stop, 99.30 - 0.03, places=6)
        s, sigs = run("suspension", buy_case(), stop_buffer_pips=0)          # never less than one tick
        self.assertAlmostEqual(sigs[0][1].stop, 99.29, places=6)

    def test_a_stop_outside_the_allowed_range_is_rejected_and_not_retried(self):
        s = make(max_stop_pips=10)                                           # the stop is 31 pips away
        self.assertEqual(feed(s, buy_case()), [])
        self.assertEqual(len([d for d in s.decisions if d.rule == "SL-03"]), 1)
        self.assertEqual((s.staged, s._armed), ([], []))

    def test_short_and_degenerate_histories_do_not_raise(self):
        flat = [(100.0, 100.0, 100.0, 100.0)] * 40
        for bars in ([], flat[:1], flat[:2], flat[:3], flat, [(100.0, 100.0, 100.0, 100.0), (100.0, 101.0, 99.0, 100.5)] * 30):
            s, sigs = run("suspension", bars)
            self.assertEqual(sigs, [])
        rising = [(100.0 + i, 100.5 + i, 99.9 + i, 100.4 + i) for i in range(40)]
        run("suspension", rising)                                            # every candle up, a gap under each, no raise

    # ------------------------------------------------------------------ noise
    def test_a_close_to_close_walk_has_no_imbalance_so_no_block(self):
        s, sigs = run("suspension", walk(7, 3000, gap=0.0))
        self.assertEqual((sigs, s._seen, s._armed), ([], set(), []))

    def test_noise_fires_a_modest_number_of_signals_and_never_breaks(self):
        # 3000 five-minute bars (about 10.4 days) of a seeded random walk whose candles open a little off the previous close
        bars = walk(7, 3000)
        s, sigs = run("suspension", bars)
        n_staged = len(staged(s))
        # The engine allows one signal a trading day (11 days touched here), so the signal count is capped at 12 by the config. The
        # detector's own selectivity is read from the staged orders: a box with every condition (three same-colour candles, two
        # imbalances above the size floor, wicks touching, a side by location, the stop and reward checks) is rare in noise.
        # Measured: 21 orders in 3000 bars (one per 143), 8 signals with the daily cap and 15 without it. The bounds are 5 and 90
        # (3 per 100 candles, about 4x what was measured): the lower one catches a detector that has gone dead, the upper one a
        # detector that stopped requiring the imbalance or the wick contact.
        self.assertTrue(1 <= len(sigs) <= 12, len(sigs))
        self.assertTrue(5 <= n_staged <= 90, n_staged)
        s2, free = run("suspension", bars, max_signals_per_day=10 ** 6)
        self.assertEqual(len(staged(s2)), n_staged)                          # the cap never changes what is detected
        self.assertTrue(len(sigs) <= len(free) <= 40, len(free))
        self.assertEqual({x.direction for _, x in free}, {SHORT, LONG})      # both sides appear
        self.assertLessEqual(len(s2._armed), blk_suspension.SB_MAX_ARMED)
        self.assertTrue(all(k[1] >= 2999 - 2 * blk_suspension.SB_RANGE for k in s2._seen), s2._seen)     # the memory of used boxes is pruned

    def test_noise_signals_obey_the_geometry(self):
        s, sigs = run("suspension", walk(7, 3000), max_signals_per_day=10 ** 6)
        self.assertGreater(len(sigs), 5)
        for i, x in sigs:
            lo, hi = sorted(x.meta["fvg"])
            self.assertEqual([r[:5] for r in x.reasons[:3]], ["SB-01", "SB-02", "SB-03"])
            self.assertAlmostEqual(x.entry_ref, (lo + hi) / 2, places=9)     # a limit at the CE
            self.assertGreater(hi - lo, 0.04)                                # two imbalances of at least two ticks each
            if x.direction == SHORT:
                self.assertIn("premium", x.reasons[2])
                self.assertAlmostEqual(x.stop, hi + 0.01, places=9)          # one tick over the box top
                self.assertLess(x.target, x.entry_ref)
            else:
                self.assertIn("discount", x.reasons[2])
                self.assertAlmostEqual(x.stop, lo - 0.01, places=9)
                self.assertGreater(x.target, x.entry_ref)

    def test_the_buy_side_is_the_exact_mirror_on_noise(self):
        bars = walk(7, 3000)
        outs = []
        for x in (bars, flip(bars, 205.0)):
            s = make(max_signals_per_day=10 ** 6)
            s.daily_bias = lambda: (0, "off")                                # the bias rule is the engine's, not the detector's
            outs.append(feed(s, x))
        self.assertGreater(len(outs[0]), 5)
        self.assertEqual([(i, x.direction) for i, x in outs[0]], [(i, -x.direction) for i, x in outs[1]])
        for (_, a), (_, b) in zip(*outs):
            self.assertAlmostEqual(a.entry_ref, 205.0 - b.entry_ref, places=6)
            self.assertAlmostEqual(a.stop, 205.0 - b.stop, places=6)
            self.assertAlmostEqual(a.target, 205.0 - b.target, places=6)

    def test_no_lookahead_a_prefix_gives_the_same_signals(self):
        bars = walk(7, 3000)
        _, full = run("suspension", bars, max_signals_per_day=10 ** 6)
        _, head = run("suspension", bars[:1500], max_signals_per_day=10 ** 6)
        self.assertGreater(len(head), 2)
        self.assertEqual([(i, x.direction, x.entry_ref, x.stop) for i, x in head],
                         [(i, x.direction, x.entry_ref, x.stop) for i, x in full if i < 1500])


if __name__ == "__main__":
    unittest.main()
