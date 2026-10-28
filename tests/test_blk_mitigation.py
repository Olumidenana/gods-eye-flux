"""Mitigation Block (ict_trader/blk_mitigation.py): a failure swing, the break of its low, the zone of the last candle at that low.

The bars are 5-minute (open, high, low, close) tuples run through the same helper as the other pattern models. The sell case is
written out by hand (prices around 100, one pip = 0.01) and the buy case is its mirror (every price p becomes MIRROR - p), so one
set of numbers covers both directions and every negative below is run both ways.
"""

import math
import random
import unittest
from dataclasses import replace
from datetime import timedelta
from unittest import mock

from ict_trader import blk_mitigation
from ict_trader.models import make_strategy
from ict_trader.sessions import Bar
from ict_trader.strategy import LONG, SHORT
from tests.test_patterns import CFG, T0, run

MIRROR = 205.0

# ---- the sell case, bar by bar (index in the list):
#   0-9    flat filler;  10-12 the rise;  13 H0, the old high (102.6);  14-15 and 16-17 the decline into A (a pause may sit between)
#   18     A: the swing low (99.3) and the block candle, a down candle that opened at 100.0 and closed at 99.5 (zone 99.3 to 100.0)
#   19-22  the rally, 23 B: its top (101.9), below H0;  24-26 the fall back;  then the trigger: the first close below A (99.0)
#   then three bars back up: the limit at 100.0 fills on the last one.
HEAD = [(100.0, 100.2, 99.8, 100.0)] * 10 + [(100.0, 100.6, 99.9, 100.5), (100.5, 101.2, 100.4, 101.1), (101.1, 101.8, 101.0, 101.7)]
H0 = (101.7, 102.6, 101.6, 102.3)
DECLINE1 = [(102.1, 102.2, 101.5, 101.6), (101.6, 101.7, 100.9, 101.0)]
PAUSE_HA = (101.0, 101.1, 100.9, 101.0)
DECLINE2 = [(101.0, 101.1, 100.3, 100.4), (100.4, 100.5, 99.8, 99.9)]
A = (100.0, 100.4, 99.3, 99.5)
RALLY = [(99.5, 99.9, 99.4, 99.8), (99.8, 100.5, 99.7, 100.4), (100.4, 101.0, 100.3, 100.9), (100.9, 101.6, 100.8, 101.5)]
PAUSE_AB = (99.8, 100.0, 99.6, 99.8)
B = (101.5, 101.9, 101.3, 101.4)
FALL = [(101.4, 101.5, 100.8, 100.9), (100.9, 101.0, 100.2, 100.3), (100.3, 100.4, 99.6, 99.7)]
PAUSE_BT = (99.7, 99.9, 99.6, 99.7)
TRIGGER = (99.7, 99.8, 98.9, 99.0)
TAIL = [(99.0, 99.5, 98.8, 99.4), (99.4, 99.9, 99.3, 99.8), (99.8, 100.1, 99.7, 99.9)]


def sell_case(a=A, h0=H0, b=B, trig=TRIGGER, decline1=DECLINE1, decline2=DECLINE2, rally=RALLY, fall=FALL, tail=TAIL, gap_ha=0, gap_ab=0, gap_bt=0):
    """The sell case and the index of its trigger candle. The gaps add flat candles between H0 and A, A and B, B and the trigger."""
    bars = (HEAD + [h0] + decline1 + [PAUSE_HA] * gap_ha + decline2 + [a] + rally[:1] + [PAUSE_AB] * gap_ab + rally[1:] + [b] + fall
            + [PAUSE_BT] * gap_bt)
    return bars + [trig] + tail, len(bars)


def mirror(bars, k=MIRROR):
    return [(k - o, k - l, k - h, k - c) for o, h, l, c in bars]


def both(bars):
    return (("sell", bars), ("buy", mirror(bars)))


def staged(s):
    return [e for e in s.events if e["type"] == "staged"]


def make(**kw):
    """The strategy exactly as run() builds it, for the tests that need to poke it between bars."""
    st = replace(CFG.strategy, model="mitigation", timeframe_minutes=5, min_stop_pips=0, max_stop_pips=1e9, min_rr=0.1,
                 liquidity_pools=True, daily_bias_filter=False)
    return make_strategy(replace(st, **kw), replace(CFG.instrument, pip_size=0.01))


def feed(s, bars, start=0):
    out = []
    for i, b in enumerate(bars, start):
        x = s.on_bar(Bar(T0 + timedelta(minutes=5 * i), *b))
        if x:
            out.append((i, x))
    return out


def walk(seed, n, sigma=0.3):
    r, p, out = random.Random(seed), 100.0, []
    for _ in range(n):
        o, c = p, p + r.gauss(0, sigma)
        out.append((o, max(o, c) + abs(r.gauss(0, sigma / 2)), min(o, c) - abs(r.gauss(0, sigma / 2)), c))
        p = c
    return out


class BlockTest(unittest.TestCase):
    def test_sell_block_clean_case(self):
        bars, ti = sell_case()
        s, sigs = run("mitigation", bars)
        self.assertEqual([i for i, _ in sigs], [ti + 3])           # the limit fills when price returns to the zone top
        sig = sigs[0][1]
        self.assertEqual(sig.direction, SHORT)
        self.assertEqual(sig.entry_type, "limit")
        self.assertAlmostEqual(sig.entry_ref, 100.0, places=2)      # the block's open
        self.assertAlmostEqual(sig.stop, 100.28, places=2)          # above the top by 0.4 x the 0.7 zone height
        self.assertAlmostEqual(sig.stop - sig.entry_ref, 0.4 * 0.7, places=2)
        self.assertAlmostEqual(sig.target, 97.5, places=2)          # -1 SD: 99.5 - (101.5 - 99.5)
        self.assertTrue(sig.meta["target_name"].startswith("-1 SD"))
        self.assertEqual([r[:5] for r in sig.reasons[:3]], ["MB-01", "MB-02", "MB-03"])
        self.assertIn("102.600", sig.reasons[0])                    # the old high
        self.assertIn("101.900", sig.reasons[0])                    # the lower high
        self.assertIn("99.300", sig.reasons[1])                     # the swing low that broke
        self.assertIn("[99.300, 100.000]", sig.reasons[2])          # the zone
        self.assertTrue(any(r.startswith("EN-01") for r in sig.reasons))

    def test_buy_block_is_the_mirror(self):
        bars, ti = sell_case()
        s, sigs = run("mitigation", mirror(bars))
        self.assertEqual([i for i, _ in sigs], [ti + 3])
        sig = sigs[0][1]
        self.assertEqual(sig.direction, LONG)
        self.assertAlmostEqual(sig.entry_ref, MIRROR - 100.0, places=2)
        self.assertAlmostEqual(sig.entry_ref - sig.stop, 0.28, places=2)      # the stop sits below the zone
        self.assertLess(sig.stop, sig.entry_ref)
        self.assertAlmostEqual(sig.target, MIRROR - 97.5, places=2)
        self.assertEqual(sorted(round(v, 2) for v in sig.meta["fvg"]), [105.0, 105.7])        # open (the near edge) to the high (the far wick)
        self.assertTrue(sig.meta["target_name"].startswith("+1 SD"))
        self.assertEqual([r[:5] for r in sig.reasons[:3]], ["MB-01", "MB-02", "MB-03"])
        self.assertIn("a low at 102.400", sig.reasons[0])
        self.assertIn("a higher low at 103.100", sig.reasons[0])
        self.assertIn("above 105.700", sig.reasons[1])

    def test_lesson_chart_numbers(self):
        # MNQ 1-minute, 6 Mar 2024 (20240306_0OIplRTKYOA 04m00s and 05m20s), prices read off the frames: H0 wick 18127, the block candle
        # opened 18079 / closed 18073.5 / low 18070.4, B wick 18115 with its body top at 18108.75. The frame's own measurements are the
        # expected values: the box 18070.4 to 18079, the stop about 3.4 above it (18082.50 in the live trade), the -1 SD line at 18038.25.
        up = [(18090, 18095, 18085, 18090)] * 10 + [(18090, 18100, 18088, 18098), (18098, 18112, 18096, 18110), (18110, 18127, 18108, 18115)]
        down = [(18115, 18118, 18104, 18106), (18106, 18108, 18096, 18098), (18098, 18100, 18090, 18092), (18092, 18094, 18084, 18086), (18086, 18088, 18077, 18079)]
        block = [(18079, 18087, 18070.4, 18073.5)]
        rally = [(18073.5, 18082, 18072, 18080), (18080, 18090, 18078, 18088), (18088, 18098, 18086, 18096), (18096, 18106, 18094, 18104), (18106, 18115, 18104, 18108.75)]
        fall = [(18108, 18109, 18098, 18100), (18100, 18101, 18090, 18092), (18092, 18093, 18080, 18082), (18082, 18084, 18072, 18074)]
        trigger = [(18074, 18076, 18060, 18062)]                      # B to the break: 5 candles, as on the chart
        back = [(18062, 18075, 18060, 18074), (18074, 18081, 18072, 18080)]
        s, sigs = run("mitigation", up + down + block + rally + fall + trigger + back)
        self.assertEqual(len(sigs), 1)
        sig = sigs[0][1]
        self.assertEqual(sig.direction, SHORT)
        self.assertAlmostEqual(sig.entry_ref, 18079.0, places=2)
        self.assertAlmostEqual(sig.stop, 18082.44, places=2)          # 18079 + 0.4 x (18079 - 18070.4)
        self.assertLess(abs(sig.stop - 18082.5), 0.1)
        self.assertAlmostEqual(sig.target, 18038.25, places=2)
        self.assertEqual(sorted(round(v, 2) for v in sig.meta["fvg"]), [18070.4, 18079.0])

    def test_the_order_rests_at_the_zone_top_until_price_returns(self):
        bars, ti = sell_case()
        s = make()
        self.assertEqual(feed(s, bars[:ti + 1]), [])               # the trigger candle only places the order
        self.assertEqual(len(staged(s)), 1)
        (o,) = s.staged
        self.assertEqual(o["direction"], "short")
        self.assertAlmostEqual(o["limit"], 100.0, places=2)
        self.assertAlmostEqual(o["stop"], 100.28, places=2)
        self.assertAlmostEqual(o["target"], 97.5, places=2)
        self.assertEqual(sorted(round(v, 2) for v in o["fvg"]), [99.3, 100.0])
        self.assertEqual(feed(s, bars[ti + 1:ti + 3], ti + 1), [])  # the retrace that stays short of the top does not fill
        self.assertEqual(len(feed(s, bars[ti + 3:], ti + 3)), 1)

    def test_only_closed_candles_up_to_the_trigger_decide_the_order(self):
        # what is staged at the trigger candle cannot depend on any later candle: the same order comes out whatever follows
        bars, ti = sell_case()
        for label, x in both(bars):
            with self.subTest(label):
                kept = []
                for tail in (x[ti + 1:], [(x[ti][3], x[ti][3] + 5, x[ti][3] - 5, x[ti][3])] * 3, []):
                    s = make()
                    feed(s, x[:ti + 1] + tail)
                    kept.append({k: v for k, v in staged(s)[0].items() if k != "type"})
                self.assertEqual(kept[0], kept[1])
                self.assertEqual(kept[0], kept[2])

    def test_chart_geometry_points_at_the_pattern(self):
        bars, ti = sell_case()
        s, sigs = run("mitigation", bars)
        m = sigs[0][1].meta
        step = timedelta(minutes=5)
        self.assertAlmostEqual(m["sweep_price"], 101.9, places=2)             # B, the failed high
        self.assertEqual(m["sweep_time"], T0 + 23 * step)
        self.assertEqual(m["swing_time"], T0 + 18 * step)                      # A
        self.assertAlmostEqual(m["mss_level"], 99.3, places=2)                 # the broken swing low
        self.assertEqual(m["mss_time"], T0 + ti * step)                        # the trigger candle
        self.assertEqual(m["fvg_time"], T0 + 19 * step)                        # the web draws the zone from the block candle (18) on
        self.assertEqual(staged(s)[0]["fvg_time"], T0 + 19 * step)
        self.assertEqual(sigs[0][1].level.name, "SWH 101.900")
        self.assertEqual(run("mitigation", mirror(bars))[1][0][1].level.name, "SWL 103.100")

    def test_block_is_the_last_down_candle_before_the_first_up_candle(self):
        # a second down candle sits between A and the rally: it, not A's candle, is the block (zone 99.4 to 99.6)
        bars, ti = sell_case(rally=[(99.45, 99.9, 99.4, 99.8)] + RALLY[1:], a=A)
        bars.insert(19, (99.6, 99.7, 99.4, 99.45))
        for label, x in both(bars):
            with self.subTest(label):
                s, sigs = run("mitigation", x)
                self.assertEqual(len(sigs), 1)
                sig = sigs[0][1]
                self.assertAlmostEqual(abs(sig.entry_ref - (MIRROR if label == "buy" else 0)), 99.6, places=2)
                self.assertAlmostEqual(abs(sig.stop - sig.entry_ref), 0.4 * 0.2, places=2)
        # A closes UP (a hammer): the block is the down candle just before it (zone 99.8 to 100.4)
        a_up = (99.4, 99.7, 99.3, 99.6)
        bars, ti = sell_case(a=a_up, tail=TAIL[:2] + [(99.8, 100.5, 99.7, 100.0)])
        for label, x in both(bars):
            with self.subTest("hammer " + label):
                s, sigs = run("mitigation", x)
                self.assertEqual(len(sigs), 1)
                self.assertAlmostEqual(abs(sigs[0][1].entry_ref - (MIRROR if label == "buy" else 0)), 100.4, places=2)
        # nothing to call a block: A closes up and the two candles before it have no body either (a down candle three back is too far)
        bars, _ = sell_case(a=a_up, decline1=[DECLINE1[0], (101.4, 101.7, 100.9, 101.0)], decline2=[(100.5, 100.6, 100.3, 100.5), (100.2, 100.3, 99.8, 100.2)])
        self.assertNoSetup(bars)

    # ------------------------------------------------------------------ the geometry, broken one condition at a time
    def assertNoSetup(self, bars, msg=""):
        for label, x in both(bars):
            s, sigs = run("mitigation", x)
            self.assertEqual(staged(s), [], f"{label}: {msg}")
            self.assertEqual(sigs, [], f"{label}: {msg}")
            self.assertEqual(s._seen, set(), f"{label}: {msg} (the geometry itself must fail, not the stop or target checks)")

    def assertOneSignal(self, bars, msg=""):
        for label, x in both(bars):
            s, sigs = run("mitigation", x)
            self.assertEqual(len(sigs), 1, f"{label}: {msg}")

    def test_a_higher_high_is_a_breaker_not_a_mitigation_block(self):
        self.assertNoSetup(sell_case(b=(101.5, 102.9, 101.3, 101.4))[0], "B above H0 (102.6)")
        self.assertNoSetup(sell_case(b=(101.5, 102.6, 101.3, 101.4))[0], "B equal to H0: the failure must be strict")
        self.assertOneSignal(sell_case(b=(101.5, 102.5, 101.3, 101.4))[0], "B just below H0 is still a failure swing")

    def test_no_signal_without_a_close_below_the_swing_low(self):
        self.assertNoSetup(sell_case(trig=(99.7, 99.8, 98.9, 99.35))[0], "a wick through A that closes back above it")
        self.assertNoSetup(sell_case(trig=(99.7, 99.8, 98.9, 99.3))[0], "a close exactly at A")
        self.assertOneSignal(sell_case(trig=(99.7, 99.8, 98.9, 99.29))[0], "a close just below A")

    def test_the_break_must_not_be_the_candle_that_takes_the_failed_high(self):
        self.assertNoSetup(sell_case(trig=(99.7, 102.0, 98.9, 99.0))[0], "the trigger ran past B (101.9) before closing below A")
        self.assertOneSignal(sell_case(trig=(99.7, 101.8, 98.9, 99.0))[0], "the same candle with a high just short of B")

    def test_a_lower_low_within_two_candles_moves_the_swing_low(self):
        # a wick runs below A (99.3) on the second candle after it: A is no longer lower than the 2 candles after it, so it is
        # not a swing low and the wick low (99.2) is the swing low to break
        pierced = [(99.5, 99.9, 99.4, 99.8), (99.8, 100.5, 99.2, 100.4)] + RALLY[2:]
        self.assertNoSetup(sell_case(rally=pierced, trig=(99.7, 99.8, 98.9, 99.25))[0], "closed below A but not below the pierce")
        self.assertOneSignal(sell_case(rally=pierced)[0], "closed below the pierce: the structure is the same, the break is of 99.2")

    def test_a_wick_through_the_swing_low_that_closes_back_is_not_a_break(self):
        # three candles after A a wick runs below it (99.2) and closes back at 100.5: only a CLOSE below a low breaks it, so A (99.3)
        # is still the swing low and the block is still A's own candle (the wick is no swing low: no down candle ahead of it)
        late = [(99.5, 99.9, 99.4, 99.8), (99.8, 100.5, 99.7, 100.4), (100.4, 100.6, 99.2, 100.5), (100.5, 101.6, 100.4, 101.5)]
        for label, x in both(sell_case(rally=late)[0]):
            with self.subTest(label):
                s, sigs = run("mitigation", x)
                self.assertEqual(len(sigs), 1)
                sig, sign = sigs[0][1], (-1 if label == "buy" else 1)
                self.assertAlmostEqual(sig.meta["mss_level"], (MIRROR if label == "buy" else 0) + sign * 99.3, places=2)   # A's low, not the wick
                self.assertAlmostEqual(abs(sig.entry_ref - (MIRROR if label == "buy" else 0)), 100.0, places=2)
        # a close below A (99.3) that stays above the wick (99.2) breaks A all the same
        self.assertOneSignal(sell_case(rally=late, trig=(99.7, 99.8, 98.9, 99.25))[0], "closed below A, above the wick")

    def test_a_swing_low_already_closed_below_cannot_be_broken_again(self):
        # three candles after A (99.3) a candle closes below it (99.25), then a wick-low candle (F, 99.1) rallies away to a lower high.
        # Closing at 99.2 later is not the first close below A, and F is not broken, so there is nothing to place
        early = [(99.5, 99.9, 99.4, 99.8), (99.8, 100.0, 99.5, 99.6), (99.6, 99.65, 99.2, 99.25), (99.25, 100.5, 99.1, 100.4)] + RALLY[2:]
        self.assertNoSetup(sell_case(rally=early, trig=(99.7, 99.8, 98.9, 99.2))[0], "A was broken before the failed rally")
        # closing below the new swing low (F) is a break of F instead: the block is the down candle just before F's rally
        for label, x in both(sell_case(rally=early)[0]):
            with self.subTest(label):
                s, sigs = run("mitigation", x)
                self.assertEqual(len(sigs), 1)
                self.assertAlmostEqual(abs(sigs[0][1].entry_ref - (MIRROR if label == "buy" else 0)), 99.6, places=2)
        # a candle that only CLOSES ON the low (99.3, a wick under it) has not closed below it: A still breaks
        touch = FALL[:2] + [(100.3, 100.4, 99.25, 99.3)]
        self.assertOneSignal(sell_case(fall=touch)[0], "a close exactly at A is not a close below it")

    def test_the_old_high_must_be_close_enough_and_a_swing(self):
        self.assertOneSignal(sell_case(gap_ha=25)[0], "H0 exactly 30 candles before A")
        self.assertNoSetup(sell_case(gap_ha=26)[0], "H0 31 candles before A")
        # an equal high right after H0 (102.6): neither is a swing top (strict, eq_tol 0) and no other high stands out in the 30 candles
        self.assertNoSetup(sell_case(decline1=[(102.1, 102.6, 101.5, 101.6), DECLINE1[1]])[0], "H0 has an equal high beside it")
        self.assertOneSignal(sell_case(decline1=[(102.1, 102.55, 101.5, 101.6), DECLINE1[1]])[0], "the same with the neighbour a hair lower")

    def test_the_old_high_is_the_last_swing_high_before_the_swing_low(self):
        # H0 -> A -> B are consecutive swings. A lower high M (101.8) stands in the decline between the top (102.6) and A, so M is the
        # high B must fail against: B at 101.9 took it (a higher high), although it is still below the top of the whole decline.
        down = [(102.1, 102.2, 101.5, 101.6), (101.6, 101.7, 100.9, 101.0), (101.0, 101.4, 100.9, 101.3), (101.3, 101.8, 101.2, 101.6),
                (101.6, 101.7, 100.8, 100.9), (100.9, 101.0, 100.3, 100.4)]
        self.assertNoSetup(sell_case(decline1=down)[0], "B (101.9) is above the last swing high M (101.8)")
        self.assertOneSignal(sell_case(decline1=down, b=(101.5, 101.75, 101.3, 101.4))[0], "B (101.75) just below M")
        # the stepladder reads the same way: the second failed rally is judged against the first one's top, not against the old top
        ladder = [(99.0, 99.3, 98.6, 98.7), (98.7, 98.8, 98.3, 98.4), (98.4, 98.9, 98.35, 98.8), (98.8, 99.2, 98.7, 99.0), (99.0, 99.1, 98.5, 98.55), (98.55, 98.6, 98.1, 98.15)]
        higher = list(ladder)
        higher[3] = (98.8, 102.0, 98.7, 99.0)                 # the second rally's top (102.0) is above the first one's (101.9)
        bars, ti = sell_case()
        for label, x in both(bars[:ti + 1] + higher):
            with self.subTest(label):
                s = make()
                feed(s, x)
                self.assertEqual(len(staged(s)), 1)         # only the first block: the second rally took the first rally's top

    def test_the_rally_may_take_at_most_30_candles(self):
        self.assertOneSignal(sell_case(gap_ab=25)[0], "B exactly 30 candles after A")
        self.assertNoSetup(sell_case(gap_ab=26)[0], "B 31 candles after A")

    def test_the_break_must_come_within_20_candles_of_the_top(self):
        self.assertOneSignal(sell_case(gap_bt=16)[0], "the trigger exactly 20 candles after B")
        self.assertNoSetup(sell_case(gap_bt=17)[0], "the trigger 21 candles after B")

    def test_the_failed_top_must_be_a_swing(self):
        # an equal high right after B: B is not the one clear top
        self.assertNoSetup(sell_case(fall=[(101.4, 101.9, 100.8, 100.9)] + FALL[1:])[0])

    def test_the_block_must_open_below_the_rally_body(self):
        # a rally that never gets its body above the block's open (100.3): nothing is being mitigated
        bars, _ = sell_case(a=(100.3, 100.4, 99.3, 99.4), rally=[(99.4, 99.7, 99.35, 99.6), (99.6, 99.9, 99.5, 99.8), (99.8, 100.0, 99.7, 99.95), (99.95, 100.1, 99.9, 100.0)],
                            b=(100.0, 100.2, 99.9, 100.1), fall=[(100.1, 100.15, 99.9, 99.95), (99.95, 100.0, 99.6, 99.65), (99.65, 99.7, 99.4, 99.45)])
        self.assertNoSetup(bars)
        # the same shape with a body that does clear it is a setup
        bars, _ = sell_case(a=(100.3, 100.4, 99.3, 99.4), rally=[(99.4, 99.7, 99.35, 99.6), (99.6, 99.9, 99.5, 99.8), (99.8, 100.0, 99.7, 99.95), (99.95, 100.1, 99.9, 100.0)],
                            b=(100.0, 100.5, 99.9, 100.45), fall=[(100.1, 100.15, 99.9, 99.95), (99.95, 100.0, 99.6, 99.65), (99.65, 99.7, 99.4, 99.45)],
                            tail=[(99.0, 99.5, 98.8, 99.4), (99.4, 100.0, 99.3, 99.8), (99.8, 100.35, 99.7, 99.9)])
        s, sigs = run("mitigation", bars)
        self.assertEqual(len(staged(s)), 1)

    def test_equal_lows_beside_the_swing_low_make_no_swing(self):
        # strict, eq_tol 0: a low equal to A's (99.3) one or two candles away leaves A no lower than its neighbours
        self.assertNoSetup(sell_case(decline2=[DECLINE2[0], (100.4, 100.5, 99.3, 99.9)])[0], "an equal low just before A")
        self.assertNoSetup(sell_case(rally=[(99.5, 99.9, 99.3, 99.8)] + RALLY[1:])[0], "an equal low just after A")
        self.assertNoSetup(sell_case(rally=[RALLY[0], (99.8, 100.5, 99.3, 100.4)] + RALLY[2:])[0], "an equal low two candles after A")

    def test_the_break_candle_must_stay_below_the_failed_top_strictly(self):
        self.assertNoSetup(sell_case(trig=(99.7, 101.9, 98.9, 99.0))[0], "the trigger's high equals B (101.9)")

    def test_the_failed_top_must_stand_out_from_the_candles_before_it_too(self):
        # B comes two candles after A and its high (100.3) is under A's own high (100.4): not a swing top, only a bounce off A's range
        small = dict(rally=[(99.5, 99.8, 99.4, 99.6)], fall=[(100.2, 100.25, 99.6, 99.7), (99.7, 99.8, 99.45, 99.5), (99.5, 99.6, 99.4, 99.45)], trig=(99.45, 99.5, 98.9, 99.0))
        self.assertNoSetup(sell_case(b=(99.6, 100.3, 99.5, 100.2), **small)[0], "B under the high of A's candle")
        small["fall"] = [(100.3, 100.4, 99.6, 99.7)] + small["fall"][1:]
        self.assertOneSignal(sell_case(b=(99.6, 100.5, 99.5, 100.3), **small)[0], "the same with B above A's high")

    def test_a_doji_is_neither_the_first_up_candle_nor_the_last_down_candle(self):
        up, doji = (99.45, 100.5, 99.42, 100.4), (99.45, 99.6, 99.4, 99.45)
        # A (down), a down candle, a doji, then the first up candle: the doji is not a down candle, so the block is the one before it
        bars, _ = sell_case(rally=[(99.6, 99.65, 99.4, 99.45), doji, up] + RALLY[2:])
        # A (down), a doji, a down candle, then the first up candle: the doji is not an up candle, so the rally starts at the up candle
        bars2, _ = sell_case(rally=[(99.5, 99.7, 99.4, 99.5), (99.55, 99.6, 99.4, 99.45), up] + RALLY[2:])
        for label, x, want in (("down, doji", bars, 99.6), ("doji, down", bars2, 99.55)):
            for side, y in both(x):
                with self.subTest(label + " " + side):
                    s, sigs = run("mitigation", y)
                    self.assertEqual(len(sigs), 1)
                    self.assertAlmostEqual(abs(sigs[0][1].entry_ref - (MIRROR if side == "buy" else 0)), want, places=2)

    def test_a_down_candle_after_an_up_closing_swing_low_does_not_take_the_block(self):
        # A closes up (a hammer): it is itself the first up candle of the rally, so the block is the down candle before it (zone 99.8 to
        # 100.4) even though a down candle follows A before the next up candle
        a_up = (99.4, 99.7, 99.3, 99.6)
        rally = [(99.6, 99.65, 99.4, 99.45), (99.45, 100.5, 99.42, 100.4)] + RALLY[2:]
        bars, _ = sell_case(a=a_up, rally=rally, tail=TAIL[:2] + [(99.8, 100.5, 99.7, 100.0)])
        for label, x in both(bars):
            with self.subTest(label):
                s, sigs = run("mitigation", x)
                self.assertEqual(len(sigs), 1)
                self.assertAlmostEqual(abs(sigs[0][1].entry_ref - (MIRROR if label == "buy" else 0)), 100.4, places=2)

    def test_the_block_cannot_be_the_old_high_candle_itself(self):
        # the old high is a down candle (a shooting star: open 101.0, high 102.6) two candles before an up-closing swing low, and the
        # one between them is an up candle: the only down candle in reach is the top itself, which is not a block
        bars, _ = sell_case(h0=(101.0, 102.6, 100.7, 100.8), decline1=[(100.2, 100.5, 99.9, 100.4)], decline2=[], a=(99.4, 99.7, 99.3, 99.6))
        self.assertNoSetup(bars)

    # ------------------------------------------------------------------ the daily bias, the parameters, the stop and target rules
    def test_a_daily_bias_against_the_trade_skips_it(self):
        bars, ti = sell_case()
        for bias, label, x, ok in ((LONG, "sell", bars, False), (SHORT, "sell", bars, True), (LONG, "buy", mirror(bars), True), (SHORT, "buy", mirror(bars), False)):
            with self.subTest(f"bias {bias} {label}"):
                s = make()
                s.daily_bias = lambda b=bias: (b, "test")
                sigs = feed(s, x)
                self.assertEqual(len(sigs), 1 if ok else 0)
                self.assertEqual(len(staged(s)), 1 if ok else 0)

    def test_entry_fraction_moves_the_limit_down_the_zone(self):
        bars, ti = sell_case()
        with mock.patch.object(blk_mitigation, "MB_ENTRY_FRAC", 0.5):
            for label, x in both(bars):
                s, sigs = run("mitigation", x)
                self.assertEqual(len(sigs), 1)
                self.assertAlmostEqual(abs(sigs[0][1].entry_ref - (MIRROR if label == "buy" else 0)), 99.65, places=2)   # half way from 100.0 to 99.3
                self.assertAlmostEqual(abs(sigs[0][1].stop - sigs[0][1].entry_ref), 0.35 + 0.28, places=2)       # the stop did not move

    def test_stop_buffer_applies_when_it_beats_the_zone_fraction(self):
        bars, _ = sell_case()
        with mock.patch.object(blk_mitigation, "MB_STOP_FRAC", 0.0):
            s, sigs = run("mitigation", bars)
            self.assertAlmostEqual(sigs[0][1].stop, 100.01, places=2)         # zone top + stop_buffer_pips (1 pip = 0.01)
            s, sigs = run("mitigation", mirror(bars))
            self.assertAlmostEqual(sigs[0][1].stop, MIRROR - 100.01, places=2)

    def test_a_stop_that_is_too_wide_is_rejected_once(self):
        bars, _ = sell_case()
        s = make(max_stop_pips=10)                                          # the stop is 28 pips
        self.assertEqual(feed(s, bars), [])
        self.assertEqual(staged(s), [])
        self.assertEqual(sum(1 for d in s.decisions if d.rule == "SL-03"), 1)     # said once, not on every later candle

    def test_a_stop_that_is_too_tight_is_moved_out_to_the_minimum_not_thrown_away(self):
        bars, _ = sell_case()
        for label, x in both(bars):
            s = make(min_stop_pips=100)                                     # the stop is 28 pips: inside the market's noise
            sigs = feed(s, x)
            self.assertEqual(len(sigs), 1, label)
            sig = sigs[0][1]
            self.assertAlmostEqual(abs(sig.stop - sig.entry_ref), 100 * 0.01, places=2)   # the minimum, 1.0 price unit at 0.01 a pip
            self.assertEqual((sig.stop - sig.entry_ref) * sig.direction < 0, True)        # on the losing side of the entry
            self.assertTrue(any("widened" in d.message for d in s.decisions), label)

    def test_target_falls_back_to_liquidity_when_the_projection_pays_too_little(self):
        bars, _ = sell_case()
        for label, x in both(bars):
            s = make(min_rr=10)                                               # the -1 SD target is 8.9R
            self.assertEqual(feed(s, x), [])
            self.assertTrue(any(d.rule == "TP-01" for d in s.decisions), label)   # and there is no liquidity to aim at
        deep = list(bars)
        deep[5] = (100.0, 100.2, 95.0, 100.0)                                 # an unswept swing low far below
        s = make(min_rr=10)
        sigs = feed(s, deep)
        self.assertEqual(len(sigs), 1)
        self.assertAlmostEqual(sigs[0][1].target, 95.0, places=2)
        self.assertTrue(sigs[0][1].meta["target_name"].startswith("SWL"))
        s = make(min_rr=10)
        sigs = feed(s, mirror(deep))                                          # the same, mirrored: an unswept swing high far above
        self.assertAlmostEqual(sigs[0][1].target, MIRROR - 95.0, places=2)
        self.assertTrue(sigs[0][1].meta["target_name"].startswith("SWH"))

    def test_a_target_price_has_already_traded_through_is_not_used(self):
        # the rally is so small that the -1 SD price (99.4 - 0.45 = 98.95) is above the trigger candle's low (98.5): price already passed it
        bars, ti = sell_case(a=(99.8, 100.0, 99.3, 99.4), rally=[(99.4, 99.6, 99.35, 99.5), (99.5, 99.7, 99.4, 99.6), (99.6, 99.8, 99.5, 99.7), (99.7, 99.9, 99.6, 99.8)],
                             b=(99.85, 99.95, 99.7, 99.8), fall=[(99.75, 99.8, 99.5, 99.55), (99.55, 99.6, 99.4, 99.45), (99.45, 99.5, 99.35, 99.4)],
                             trig=(99.4, 99.45, 98.5, 98.6), tail=[(98.6, 99.0, 98.5, 98.9), (98.9, 99.6, 98.8, 99.4), (99.4, 99.9, 99.3, 99.8)])
        deep = list(bars)
        deep[5] = (100.0, 100.2, 95.0, 100.0)
        s = make(min_rr=2)
        sigs = feed(s, deep)
        self.assertEqual(len(sigs), 1)
        self.assertTrue(sigs[0][1].meta["target_name"].startswith("SWL"), sigs[0][1].meta["target_name"])

    # ------------------------------------------------------------------ invalidation and the stepladder
    def test_a_body_close_beyond_the_block_voids_an_order_that_could_not_fill(self):
        # With the day's signal cap reached a touched limit cannot fill; the guard then judges the closed candles.
        bars, ti = sell_case()
        wick = (99.0, 100.1, 98.8, 99.4)        # a wick through the top (100.0) that closes inside the zone: the body is not violated
        calm = (99.4, 99.6, 99.2, 99.5)
        body = (99.5, 100.2, 99.4, 100.1)       # a body that closes above the top
        after = (100.1, 100.15, 99.9, 100.0)
        for label, x in both(bars):
            with self.subTest(label):
                wick_b, calm_b, body_b, after_b = (mirror([w])[0] if label == "buy" else w for w in (wick, calm, body, after))
                s = make()
                feed(s, x[:ti + 1])
                self.assertEqual(len(s._setups), 1)
                s._signals_today = s.config.max_signals_per_day
                self.assertEqual(feed(s, [wick_b, calm_b], ti + 1), [])
                self.assertEqual(len(s._setups), 1)                                    # the wick alone does not void it
                self.assertEqual(feed(s, [body_b], ti + 3), [])
                self.assertEqual(len(s._setups), 1)                                    # judged on the next candle: only closed candles count
                self.assertEqual(feed(s, [after_b], ti + 4), [])
                self.assertEqual(s._setups, [])                                        # now it is gone, and it never fills later
                self.assertTrue(any(d.rule == "EN-04" and "mitigation block limit cancelled: a body closed" in d.message for d in s.decisions))
                self.assertEqual(feed(s, [calm_b, wick_b, after_b], ti + 5), [])

    def test_trading_beyond_the_old_high_is_a_breaker(self):
        bars, ti = sell_case()
        for label, x, old, ran, edge in (("sell", bars, 102.6, 102.7, 100.0), ("buy", mirror(bars), MIRROR - 102.6, MIRROR - 102.7, MIRROR - 100.0)):
            with self.subTest(label):
                s = make()
                feed(s, x[:ti + 1])
                o = s._setups[0]
                mk = lambda hi, lo, c: Bar(T0, c, hi, lo, c)
                if label == "sell":
                    self.assertIn("breaker", s._void_reason(o, mk(ran, 99.8, 99.9)))
                    self.assertIsNone(s._void_reason(o, mk(old, 99.8, 99.9)))        # equal to the old high is not beyond it
                    self.assertIsNone(s._void_reason(o, mk(100.1, 99.8, edge)))      # closing exactly on the open is not beyond it
                    self.assertIn("violated", s._void_reason(o, mk(100.2, 99.8, edge + 0.01)))
                else:
                    self.assertIn("breaker", s._void_reason(o, mk(MIRROR - 99.8, ran, MIRROR - 99.9)))
                    self.assertIsNone(s._void_reason(o, mk(MIRROR - 99.8, old, MIRROR - 99.9)))
                    self.assertIsNone(s._void_reason(o, mk(MIRROR - 99.8, MIRROR - 100.1, edge)))
                    self.assertIn("violated", s._void_reason(o, mk(MIRROR - 99.8, MIRROR - 100.2, edge - 0.01)))

    def test_a_new_lower_swing_makes_a_new_block_and_replaces_the_resting_order(self):
        bars, ti = sell_case()
        ladder = [(99.0, 99.3, 98.6, 98.7), (98.7, 98.8, 98.3, 98.4), (98.4, 98.9, 98.35, 98.8), (98.8, 99.2, 98.7, 99.0), (99.0, 99.1, 98.5, 98.55), (98.55, 98.6, 98.1, 98.15)]
        for label, x in both(bars[:ti + 1] + ladder):
            with self.subTest(label):
                s = make()
                self.assertEqual(feed(s, x[:ti + 1]), [])
                (first,) = s._setups
                self.assertEqual(feed(s, x[ti + 1:], ti + 1), [])
                self.assertEqual(len(staged(s)), 2)
                (only,) = s._setups                                                   # the old order was replaced, not left beside it
                self.assertIsNot(only, first)
                self.assertAlmostEqual(abs(only.limit - (MIRROR if label == "buy" else 0)), 98.7, places=2)
                self.assertTrue(any(e["type"] == "cancelled" and "replaced by the block at the new swing" in e["message"] for e in s.events))

    def test_the_order_expires(self):
        bars, ti = sell_case()
        quiet = [(98.9, 99.1, 98.7, 98.9)] * 70                                       # stays below the zone for good
        s = make()
        feed(s, bars[:ti + 1] + quiet)
        self.assertEqual(s._setups, [])
        self.assertTrue(any(d.rule == "EN-04" and "not filled before it expired" in d.message for d in s.decisions))

    def test_a_structure_is_used_once(self):
        bars, ti = sell_case()
        s, sigs = run("mitigation", bars + [(99.9, 100.0, 99.0, 99.1)] * 3 + bars[ti + 1:ti + 3])
        self.assertEqual(len(staged(s)), 1)
        self.assertEqual(s._seen, {(SHORT, 18)})

    # ------------------------------------------------------------------ noise
    def test_noise_fires_a_modest_number_of_signals_and_never_breaks(self):
        # 3000 five-minute bars (about 10.4 days) of a seeded random walk
        bars = walk(7, 3000)
        s, sigs = run("mitigation", bars)
        n_staged = len(staged(s))
        # The engine allows one signal a trading day (~11 days here), so the signal count is capped at ~12 by the config; the
        # detector's own selectivity is read from the staged orders: a failure swing with every condition is rare in noise
        # (measured: 66 orders in 3000 bars, 11 fills with the daily cap, 26 without it), far below one setup per 25 bars (120).
        self.assertTrue(1 <= len(sigs) <= 12, len(sigs))
        self.assertTrue(5 <= n_staged <= 120, n_staged)
        s2, free = run("mitigation", bars, max_signals_per_day=10 ** 6)
        self.assertTrue(len(sigs) <= len(free) <= 40, len(free))
        self.assertEqual(len(staged(s2)), n_staged)                                  # the cap never changes what is detected
        self.assertEqual({x.direction for _, x in free}, {SHORT, LONG})              # both sides appear

    def test_noise_signals_obey_the_geometry(self):
        s, sigs = run("mitigation", walk(7, 3000), max_signals_per_day=10 ** 6)
        for i, x in sigs:
            lo, hi = sorted(x.meta["fvg"])
            self.assertEqual([r[:5] for r in x.reasons[:3]], ["MB-01", "MB-02", "MB-03"])
            if x.direction == SHORT:
                self.assertAlmostEqual(x.entry_ref, hi, places=9)                     # a limit at the open (top) of the block
                self.assertGreater(x.stop, hi)
                self.assertLess(x.target, x.entry_ref)
            else:
                self.assertAlmostEqual(x.entry_ref, lo, places=9)
                self.assertLess(x.stop, lo)
                self.assertGreater(x.target, x.entry_ref)
            self.assertGreaterEqual(abs(x.stop - x.entry_ref), 0.01 - 1e-9)           # at least the one pip buffer

    def test_the_buy_side_is_the_exact_mirror_on_noise(self):
        bars = walk(7, 3000)
        outs = []
        for x in (bars, mirror(bars)):
            s = make(max_signals_per_day=10 ** 6)
            s.daily_bias = lambda: (0, "off")                                       # the bias rule is the engine's, not the detector's
            outs.append(feed(s, x))
        self.assertGreater(len(outs[0]), 5)
        self.assertEqual([(i, x.direction) for i, x in outs[0]], [(i, -x.direction) for i, x in outs[1]])
        for (_, a), (_, b) in zip(*outs):
            self.assertAlmostEqual(a.entry_ref, MIRROR - b.entry_ref, places=6)
            self.assertAlmostEqual(a.stop, MIRROR - b.stop, places=6)
            self.assertAlmostEqual(a.target, MIRROR - b.target, places=6)

    def test_short_and_degenerate_histories_do_not_raise(self):
        for n in (0, 1, 2, 5, 11, 12, 13, 25):
            run("mitigation", walk(3, n))
        run("mitigation", [(100.0, 100.0, 100.0, 100.0)] * 120)                       # no range at all
        run("mitigation", [(100.0 + math.sin(i), 101.0 + math.sin(i), 99.0 + math.sin(i), 100.0 + math.sin(i + 1)) for i in range(300)])


if __name__ == "__main__":
    unittest.main()
