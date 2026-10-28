"""Vacuum Block (ict_trader/blk_vacuum.py): a true gap between two candles, price comes back to its near edge.

The bars are 5-minute (open, high, low, close) tuples run through the same helper as the other pattern models (pip size 0.01, so
a tick is 0.01 and the engine's stop buffer is one tick). The lead-in is a chain of candles that each open at the previous close,
so nothing but the one gap under test can be a gap; every turn pokes out a little further than its neighbour so the swing highs
and lows are clean liquidity to aim at. Bar numbers (index in the list): the lead is 0-20, the gap candle is 21.

buy_case numbers:  the last lead candle (20) is (99.10, 99.20, 98.60, 98.80), so the gap's far edge is its high, 99.20. The gap
                   candle G opens 100.00 and its low is 99.90: gap [99.20, 99.90], 0.70 wide, 1.4x the median candle range
                   (0.50), CE 99.55. Limit at the near (upper) edge 99.90, stop 99.19 (one tick under the far edge), target the swing
                   high 101.40 (2.11R). H stays above the limit; I trades down to 99.85 and fills.
mirror(buy_case)   every price p becomes 200 - p: a gap down [100.10, 100.80], a sell limit at the near (lower) edge 100.10, the
                   stop 100.81, the target the swing low 98.60.
sell_case          an independent short with its own lead (up-down-up-down chain started the other way round) and a gap candle that
                   has a long upper wick: gap [100.10, 100.80] below candle 20's low.
FRAME_1325/0745    the lesson schematic itself (bodies only, pixel rows from docs/references/video_frames turned into prices): the gap
                   [99.00, 99.84] between the small up candle C and the up candle D, a candle E that enters it, then the bounce candle
                   F that ends on the far edge (13:25) or 57% of the way down (07:45), and the rally to the target.
"""

import random
import unittest
from dataclasses import replace
from datetime import timedelta
from statistics import median
from unittest import mock

from ict_trader import blk_vacuum
from ict_trader.blk_vacuum import VacuumStrategy
from ict_trader.models import is_model, label_of, make_strategy
from ict_trader.sessions import Bar, trading_day
from ict_trader.strategy import LONG, SHORT
from tests.test_patterns import CFG, T0, run

MIRROR = 200.0
GAP_IDX = 21


def chain(start, segs, step=0.3, wick=0.1):
    """Bars that each open at the previous close (so no gap anywhere), walking straight lines of `step` per bar.

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
    """The same market upside down, unrounded (for the noise walks: rounding would nudge the geometry)."""
    return [(k - o, k - l, k - h, k - c) for o, h, l, c in bars]


def make(**kw):
    """The strategy exactly as run() builds it, for the tests that need to poke at it between bars or change the config."""
    st = replace(CFG.strategy, model="vacuum", timeframe_minutes=5, min_stop_pips=0, max_stop_pips=1e9, min_rr=0.1,
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


def said(s, rule, text):
    return [d for d in s.decisions if d.rule == rule and text in d.message]


LEAD_BUY = chain(100.0, [(4, 1), (8, -1), (4, 1), (4, -1)])      # 21 bars, ends at 98.80; swing high 101.40; the last high is 99.20
LEAD_SELL = chain(100.0, [(4, -1), (8, 1), (4, -1), (4, 1)])     # 21 bars, ends at 101.20; swing low 98.60; the last low is 100.80
G = (100.00, 100.40, 99.90, 100.30)        # the gap candle: low 99.90 against the last high 99.20 (0.70 of nothing traded)
H = (100.30, 100.50, 100.10, 100.40)       # stays above the 99.90 limit
I = (100.40, 100.45, 99.85, 100.00)        # trades down to 99.85: fills the limit
SELL_G = (100.00, 100.10, 99.20, 99.40)    # a down gap candle with a long upper wick: its high 100.10 against the last low 100.80
SELL_H = (99.40, 99.80, 99.30, 99.70)
SELL_I = (99.70, 100.15, 99.60, 100.00)    # trades up to 100.15 and fills the 100.10 limit


# The lesson schematic (shPGUz9pU-A at 07:45 and 13:25), bodies only so every wick is the body's edge: pixel rows turned into prices
# at 0.005 a row with c_C (the top of the small up candle C, row 432) at 99.00 and o_D (the bottom of D, row 263.6) at 99.84, so the
# gap is 0.84 and its CE 99.42. The slide's A and B are down candles, C and D up candles; E is the black candle that first enters
# the gap (closes at 99.54, row 325), F the black candle that comes down to the bounce: at 13:25 it ends on c_C itself (row 431) and
# at 07:45 on the line at row 360, 57% of the way down and under the CE; G and H are the green rally candles of the 13:25 frame.
FRAME_LEAD = chain(100.84, [(3, 1), (6, -1), (3, 1), (5, -1)])         # 18 candles ending at 99.34, the open of A; a swing high above
FRAME_ABCD = [(99.34, 99.34, 98.42, 98.42), (98.79, 98.79, 98.13, 98.13), (98.53, 99.00, 98.53, 99.00), (99.84, 100.23, 99.84, 100.23)]
FRAME_E = (100.11, 100.11, 99.54, 99.54)
FRAME_F_1325 = (99.61, 99.61, 99.00, 99.00)
FRAME_F_0745 = (99.61, 99.61, 99.36, 99.36)
FRAME_G, FRAME_H = (99.05, 99.83, 99.05, 99.83), (99.84, 100.47, 99.84, 100.47)
FRAME_RUN = (100.47, 102.00, 100.40, 101.95)                            # carries on past the swing high that is the target
FRAME_BOUNCE_0745 = (99.36, 100.00, 99.36, 100.00)
FRAME_1325 = FRAME_LEAD + FRAME_ABCD + [FRAME_E, FRAME_F_1325, FRAME_G, FRAME_H, FRAME_RUN]
FRAME_0745 = FRAME_LEAD + FRAME_ABCD + [FRAME_E, FRAME_F_0745, FRAME_BOUNCE_0745, FRAME_H, FRAME_RUN]


def outcome(sig, after):
    """What the trade does on the candles after the one that filled it: 'stop' or 'target' (the stop first when one candle has both)."""
    for _, h, l, _ in after:
        if (l <= sig.stop) if sig.direction == LONG else (h >= sig.stop):
            return "stop"
        if (h >= sig.target) if sig.direction == LONG else (l <= sig.target):
            return "target"
    return "open"


def buy_case(g=G, tail=(H, I), lead=None):
    return list(lead or LEAD_BUY) + [g] + list(tail)


def sell_case(g=SELL_G, tail=(SELL_H, SELL_I), lead=None):
    return list(lead or LEAD_SELL) + [g] + list(tail)


def both(bars):
    return (("as built", bars), ("mirrored", mirror(bars)))


def scaled(lead, size, unit, tail_touch=True):
    """A buy case on any lead: the gap candle's low sits `size` above the last high; candle sizes follow the lead's range `unit`."""
    low = round(lead[-1][1] + size, 6)
    g = (low + 0.2 * unit, low + unit, low, low + 0.8 * unit)
    h = (g[3], g[3] + 0.1 * unit, low + 0.5 * unit, g[3] + 0.1 * unit)
    i = (h[3], h[3], low - 0.1 * unit, low + 0.3 * unit)
    return list(lead) + [g, h] + ([i] if tail_touch else [])


def walk(seed, n, sigma=0.3, gap=0.4):
    """A random walk whose candles open off the previous close by gauss(0, gap * sigma); gap=0 is a pure close-to-close chain."""
    r, p, out = random.Random(seed), 100.0, []
    for _ in range(n):
        o = p + r.gauss(0, gap * sigma)
        c = o + r.gauss(0, sigma)
        out.append((o, max(o, c) + abs(r.gauss(0, sigma / 2)), min(o, c) - abs(r.gauss(0, sigma / 2)), c))
        p = c
    return out


def oracle(bars, pip=0.01):
    """How many candles close a true gap of at least max(4 ticks, half the median range of the 20 candles before it), counted
    independently of the detector (every candle from the 21st on)."""
    n = 0
    for i in range(20, len(bars)):
        a, b = bars[i - 1], bars[i]
        if b[2] > a[1]:
            size = b[2] - a[1]
        elif b[1] < a[2]:
            size = a[2] - b[1]
        else:
            continue
        if size >= max(4 * pip, 0.5 * median(x[1] - x[2] for x in bars[i - 20:i])) - 1e-9:
            n += 1
    return n


class VacuumBlockTest(unittest.TestCase):
    def one_either_way(self, bars, want, msg=""):
        for name, bs in both(bars):
            with self.subTest(f"{name} {msg}"):
                s, sigs = run("vacuum", bs)
                self.assertEqual(len(sigs), want, msg)

    # ------------------------------------------------------------------ the clean case and its mirror
    def test_registered_and_parameters_match_the_report(self):
        self.assertTrue(is_model("vacuum"))
        self.assertEqual(label_of("vacuum"), "Vacuum Block")
        self.assertIsInstance(make_strategy(replace(CFG.strategy, model="vacuum"), CFG.instrument), VacuumStrategy)
        self.assertEqual((blk_vacuum.VC_MIN_TICKS, blk_vacuum.VC_MIN_RANGE, blk_vacuum.VC_EXPIRY), (4, 0.5, 20))
        self.assertEqual(make()._seen, set())                                 # the memory of the gaps already read starts empty

    def test_bullish_a_gap_up_then_the_return_to_its_upper_edge_is_a_buy(self):
        s, sigs = run("vacuum", buy_case())
        self.assertEqual(len(sigs), 1)
        i, sig = sigs[0]
        self.assertEqual(i, GAP_IDX + 2)                                      # I trades down into the limit
        self.assertEqual(sig.direction, LONG)
        self.assertAlmostEqual(sig.entry_ref, 99.90, places=6)                # the gap's upper (near) edge: the gap candle's low
        self.assertAlmostEqual(sig.stop, 99.19, places=6)                     # one tick under the lower edge (the last candle's high)
        self.assertAlmostEqual(sig.entry_ref - sig.stop, 0.71, places=6)
        self.assertAlmostEqual(sig.target, 101.40, places=6)                  # the swing high above
        self.assertEqual(sig.meta["fvg"], (99.20, 99.90))
        self.assertEqual([r[:5] for r in sig.reasons[:4]], ["VC-01", "VC-02", "VC-03", "RL-05"])
        self.assertTrue(sig.reasons[0].startswith("VC-01"))
        for price in ("99.900", "99.200"):                                    # the real prices are in the first line
            self.assertIn(price, sig.reasons[0])
        for price in ("99.200", "99.900", "99.550"):                          # the zone and its CE in the second
            self.assertIn(price, sig.reasons[1])
        self.assertIn("70.0 ticks and 1.4x the median candle range", sig.reasons[1])   # 0.70 of gap against a median range of 0.50
        self.assertIn("99.190", sig.reasons[2])                               # the stop in the third
        self.assertIn("20 candles", sig.reasons[2])

    def test_bearish_the_mirror_a_gap_down_then_the_return_to_its_lower_edge_is_a_sell(self):
        s, sigs = run("vacuum", mirror(buy_case()))
        self.assertEqual(len(sigs), 1)
        i, sig = sigs[0]
        self.assertEqual(i, GAP_IDX + 2)
        self.assertEqual(sig.direction, SHORT)
        self.assertAlmostEqual(sig.entry_ref, 100.10, places=6)               # the gap candle's high: the lower edge of the gap
        self.assertAlmostEqual(sig.stop, 100.81, places=6)                    # one tick over the upper edge (the last candle's low)
        self.assertAlmostEqual(sig.stop - sig.entry_ref, 0.71, places=6)
        self.assertAlmostEqual(sig.target, 98.60, places=6)
        self.assertEqual(sig.meta["fvg"], (100.10, 100.80))
        self.assertEqual([r[:5] for r in sig.reasons[:4]], ["VC-01", "VC-02", "VC-03", "RL-05"])
        for price in ("100.100", "100.800"):
            self.assertIn(price, sig.reasons[0])
        self.assertIn("100.810", sig.reasons[2])
        self.assertIn("true gap down", sig.reasons[0])
        self.assertIn("sell limit", sig.reasons[2])

    def test_an_independent_bearish_story_with_its_own_numbers(self):
        s, sigs = run("vacuum", sell_case())
        self.assertEqual(len(sigs), 1)
        i, sig = sigs[0]
        self.assertEqual(i, GAP_IDX + 2)
        self.assertEqual(sig.direction, SHORT)
        self.assertAlmostEqual(sig.entry_ref, 100.10, places=6)               # G's high: the wick above its body does not matter
        self.assertAlmostEqual(sig.stop, 100.81, places=6)
        self.assertAlmostEqual(sig.target, 98.60, places=6)
        self.assertEqual(sig.meta["fvg"], (100.10, 100.80))
        self.assertTrue(sig.reasons[0].startswith("VC-01"))

    def test_the_lesson_frames_replayed_the_order_fills_on_the_first_candle_into_the_gap_and_outlasts_the_bounce(self):
        # 13:25: the drawn bounce comes down to c_C, the far edge, with a body that ends exactly on it (no close below c_C: not void);
        # 07:45: the body ends 57% of the way down, a close under the CE that comes after the fill, and the trade lives on. The
        # stop one tick under the far edge outlasts both frames and the rally reaches the target; half a tick more and it would not.
        for frame_name, bars, f in (("13:25", FRAME_1325, FRAME_F_1325), ("07:45", FRAME_0745, FRAME_F_0745)):
            for name, bs in both(bars):
                up = name == "as built"
                with self.subTest(f"{frame_name} {name}"):
                    self.assertEqual(oracle(bs), 1)                                   # the one gap under test and no other
                    s, sigs = run("vacuum", bs)
                    self.assertEqual(len(sigs), 1)
                    i, sig = sigs[0]
                    self.assertEqual(i, GAP_IDX + 1)                                  # E: the first candle that enters the gap fills it
                    self.assertEqual(sig.direction, LONG if up else SHORT)
                    near, far = (99.84, 99.00) if up else (100.16, 101.00)
                    ce = (near + far) / 2
                    self.assertAlmostEqual(sig.entry_ref, near, places=6)
                    self.assertAlmostEqual(sig.stop, far - 0.01 if up else far + 0.01, places=6)
                    self.assertEqual([round(v, 6) for v in sorted(sig.meta["fvg"])], sorted((near, far)))
                    d = sig.direction
                    reaction = bs[GAP_IDX + 2]                                        # F, the candle that comes down to the bounce
                    if frame_name == "13:25":                                         # a body ending exactly on c_C: touched, not closed through
                        self.assertAlmostEqual(reaction[2] if up else reaction[1], far, places=6)
                        self.assertAlmostEqual(reaction[3], far, places=6)
                    else:                                                             # a body through the CE, short of the far edge
                        self.assertLess((reaction[3] - ce) * d, 0)
                        self.assertGreater((reaction[3] - far) * d, 0)
                    self.assertEqual(outcome(sig, bs[i + 1:]), "target")
        for name, bs in both(edit(FRAME_1325, {GAP_IDX + 2: (99.61, 99.61, 98.985, 98.985)})):    # F half a tick under the stop
            with self.subTest(f"half a tick through the stop {name}"):
                s, sigs = run("vacuum", bs)
                self.assertEqual(len(sigs), 1)
                self.assertEqual(outcome(sigs[0][1], bs[sigs[0][0] + 1:]), "stop")

    def test_the_order_rests_on_the_gap_candle_and_the_zone_is_the_true_gap(self):
        bars = buy_case()
        s = make()
        out = feed(s, bars[:GAP_IDX])                                         # everything before the gap: nothing staged
        self.assertEqual((out, staged(s), s.staged), ([], [], []))
        out = feed(s, bars[GAP_IDX:GAP_IDX + 1], GAP_IDX)                     # the gap candle closes: the order rests at once
        self.assertEqual(out, [])
        self.assertEqual(len(staged(s)), 1)
        st = s._setups[0]
        self.assertEqual((st.direction, st.name, st.window), (LONG, "vacuum block entry", "vacuum"))
        self.assertAlmostEqual(st.limit, 99.90, places=6)
        self.assertAlmostEqual(st.stop, 99.19, places=6)
        self.assertEqual(st.fvg, (99.20, 99.90))
        self.assertTrue(st.ce_cancel)                                         # cancelled when a body closes through the CE ...
        self.assertEqual(st.expiry, 20)                                       # ... and after 20 candles
        self.assertEqual(s.staged[0]["limit"], 99.90)

    def test_what_the_chart_and_the_desk_are_told_about_the_signal(self):
        # the level is the limit's own price, on the side the order trades from; the chart starts at the candle before the gap and
        # the box runs from it to the gap candle; the "sweep" price is the far edge (what the stop sits beyond)
        at = lambda i: T0 + timedelta(minutes=5 * i)
        for name, bars, up in (("as built", buy_case(), True), ("mirrored", mirror(buy_case()), False)):
            with self.subTest(name):
                s, sigs = run("vacuum", bars)
                sig = sigs[0][1]
                self.assertEqual(sig.level.name, "VC 99.900" if up else "VC 100.100")
                self.assertEqual(sig.level.side, "low" if up else "high")
                self.assertAlmostEqual(sig.level.price, sig.entry_ref, places=9)
                self.assertEqual(sig.killzone, "vacuum")
                self.assertEqual(sig.entry_type, "limit")
                m = sig.meta
                self.assertEqual((m["sweep_time"], m["swing_time"], m["fvg_time"]), (at(GAP_IDX - 1),) * 3)
                self.assertEqual(m["mss_time"], at(GAP_IDX))
                self.assertAlmostEqual(m["sweep_price"], 99.20 if up else 100.80, places=9)
                self.assertAlmostEqual(m["level_price"], sig.entry_ref, places=9)
                self.assertEqual((m["entry_mode"], m["entry_kind"]), ("vacuum", "fvg"))

    def test_the_live_order_list_counts_the_candles_left_from_the_models_own_expiry(self):
        # the Desk, the push text and the analysis page read "candles left" from _expiry_bars() - candles waited: it must be this
        # model's 20 candles, not the base class's 90 minutes (18 candles on 5m, 6 on 15m, 1 on 1h: negative while still resting)
        n = blk_vacuum.VC_EXPIRY
        for tf in (1, 5, 15, 60):
            st = replace(CFG.strategy, model="vacuum", timeframe_minutes=tf)
            self.assertEqual(make_strategy(st, replace(CFG.instrument, pip_size=0.01))._expiry_bars(), n, tf)
        above = (100.30, 100.60, 100.10, 100.40)                                   # stays over the limit and under the target
        for name, bs in both(list(LEAD_BUY) + [G] + [above] * (n + 2)):
            with self.subTest(name):
                s = make()
                left = {}
                for i, b in enumerate(bs):
                    s.on_bar(Bar(T0 + timedelta(minutes=5 * i), *b))
                    if s.staged:
                        left[i] = s.staged[0]["bars_left"]
                        self.assertEqual(s._expiry_bars() - s._setups[0].bars, left[i])      # the analysis page's own sum
                self.assertEqual(left[GAP_IDX], n)                                  # the gap candle: all of the wait is still ahead
                self.assertEqual(left[GAP_IDX + 1], n - 1)
                self.assertEqual(left[GAP_IDX + n - 1], 1)                          # one candle still to come (the n-th may still fill it)
                self.assertEqual(min(left.values()), 1)                             # so the count never reaches zero or goes negative
                self.assertEqual(sorted(left), list(range(GAP_IDX, GAP_IDX + n)))   # and on the n-th candle the unfilled order is gone

    def test_the_wicks_of_the_candle_before_set_the_far_edge_not_its_body(self):
        # the last lead candle has a 0.10 upper wick over its open (99.10): the lower edge is the HIGH 99.20, where nothing traded above
        s, sigs = run("vacuum", buy_case())
        self.assertEqual(sigs[0][1].meta["fvg"][0], LEAD_BUY[-1][1])
        self.assertGreater(LEAD_BUY[-1][1], max(LEAD_BUY[-1][0], LEAD_BUY[-1][3]))

    def test_the_gap_candle_wick_inside_the_gap_is_not_a_gap(self):
        # candle G opens above the last high but its low wick drops back to 99.15, under the 99.20 high: price traded there
        self.one_either_way(buy_case(g=(100.00, 100.40, 99.15, 100.30)), 0, "a wick fills the gap")

    # ------------------------------------------------------------------ near misses: each condition of the geometry broken in turn
    def test_each_broken_condition_gives_no_signal_in_both_directions(self):
        cases = {
            "the gap candle's low only touches the last high (no gap)": edit(buy_case(), {21: (100.00, 100.40, 99.20, 100.30)}),
            "the gap candle's low is inside the last candle (overlap)": edit(buy_case(), {21: (100.00, 100.40, 99.15, 100.30)}),
            "bodies apart but the wicks overlap (a volume imbalance, not a vacuum)": edit(buy_case(), {21: (99.60, 100.40, 99.15, 100.30)}),
            "a gap of 0.24, under half the median candle range of 0.50": edit(buy_case(), {21: (100.00, 100.40, 99.44, 100.30)}),
            "no gap at all, every candle opens at the last close": [*LEAD_BUY, (98.8, 99.4, 98.7, 99.3), (99.3, 99.6, 99.2, 99.5), (99.5, 99.9, 99.4, 99.45)],
        }
        for name, bars in cases.items():
            self.one_either_way(bars, 0, name)
        # the same stories with the one condition just met do fire
        self.one_either_way(edit(buy_case(), {21: (100.00, 100.40, 99.46, 100.30), 23: (100.40, 100.45, 99.40, 100.00)}), 1, "gap of 0.26, just over half the median range")
        self.one_either_way(edit(buy_case(), {21: (100.00, 100.40, 99.21, 100.30), 23: (100.40, 100.45, 99.15, 100.00)}), 0, "a 1 tick gap is far under the floor")

    def test_the_four_tick_floor_binds_in_a_quiet_market(self):
        quiet = chain(100.0, [(4, 1), (8, -1), (4, 1), (4, -1)], step=0.02, wick=0.01)     # candles 0.04 tall: half is 0.02, under 4 ticks
        self.assertAlmostEqual(median(b[1] - b[2] for b in quiet[-21:-1]), 0.04, places=9)
        for name, bars in (("3 ticks", scaled(quiet, 0.03, 0.04)), ("4 ticks exactly", scaled(quiet, 0.04, 0.04)), ("5 ticks", scaled(quiet, 0.05, 0.04))):
            want = 0 if name == "3 ticks" else 1
            self.one_either_way(bars, want, name)

    def test_half_the_median_range_binds_in_a_volatile_market(self):
        wild = chain(100.0, [(4, 1), (8, -1), (4, 1), (4, -1)], step=0.6, wick=0.2)        # candles 1.00 tall: half is 0.50 (50 ticks)
        self.assertAlmostEqual(median(b[1] - b[2] for b in wild[-21:-1]), 1.0, places=9)
        for size, want in ((0.45, 0), (0.55, 1), (0.9, 1)):
            self.one_either_way(scaled(wild, size, 1.0), want, f"gap {size}")

    def test_nothing_is_read_before_twenty_candles_of_history(self):
        short = chain(100.0, [(4, 1), (8, -1), (4, 1), (2, -1)])                           # 19 candles: the gap would be candle 19
        ok = chain(100.0, [(4, 1), (8, -1), (4, 1), (3, -1)])                              # 20 candles: the gap is candle 20
        self.assertEqual((len(short), len(ok)), (19, 20))
        for name, lead, want in (("19", short, 0), ("20", ok, 1)):
            for label, f in (("up", lambda x: x), ("down", mirror)):
                with self.subTest(f"{label} after {name} candles"):
                    s = make()
                    out = feed(s, f(scaled(lead, 0.7, 0.5)))
                    self.assertEqual(len(out), want)
                    self.assertEqual(len(staged(s)), want)
                    self.assertEqual(s._seen, set() if not want else {len(lead)})

    # ------------------------------------------------------------------ the daily bias
    def test_the_daily_bias_is_respected_like_the_other_pattern_models(self):
        for name, bars, d in (("gap up", buy_case(), LONG), ("gap down", mirror(buy_case()), SHORT)):
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
                        self.assertEqual((staged(s), s.staged), ([], []))
                        self.assertTrue(said(s, "RL-05", "against the daily draw (test draw)"))

    # ------------------------------------------------------------------ stand aside: the lifecycle that expresses the invalidation
    def test_no_return_to_the_gap_within_twenty_candles_stands_aside(self):
        above = (100.30, 100.60, 100.10, 100.40)                              # stays above the limit and under the target
        for name, k, want in (("a touch on the 20th candle after the gap fills", 19, 1), ("a touch on the 21st is too late", 20, 0)):
            with self.subTest(name):
                bars = list(LEAD_BUY) + [G] + [above] * k + [I]
                s, sigs = run("vacuum", bars)
                self.assertEqual(len(sigs), want)
                if want:
                    self.assertEqual(sigs[0][0], GAP_IDX + 20)
                else:
                    self.assertEqual(s.staged, [])
                    self.assertTrue(said(s, "EN-04", "not filled before it expired"))

    def test_price_running_to_the_target_without_coming_back_stands_aside(self):
        bars = list(LEAD_BUY) + [G, (100.30, 101.50, 100.20, 101.30), H, I]    # the second candle reaches the 101.40 target first
        for name, bs in both(bars):
            with self.subTest(name):
                s, sigs = run("vacuum", bs)
                self.assertEqual((sigs, s.staged), ([], []))
                self.assertTrue(said(s, "EN-04", "price reached the target before filling"))

    def test_a_close_through_the_ce_cancels_the_resting_order_when_the_engine_could_not_fill_it(self):
        # The engine skips the fill check only when the day's signals are used up (max_signals_per_day=0 here): the one state where
        # a body can close through the CE without the limit having filled. The order must then be cancelled at the CE, as ICT's
        # "no bounce, stand aside", and a close above the CE must leave it resting.
        touch_and_hold = (100.30, 100.40, 99.80, 100.10)                      # trades through the 99.90 limit, closes above the CE 99.55
        close_through = (100.10, 100.15, 99.30, 99.50)                        # closes at 99.50, under the CE, stop (99.19) untouched
        for name, bars in both(list(LEAD_BUY) + [G, touch_and_hold]):
            with self.subTest(name):
                s = make(max_signals_per_day=0)
                self.assertEqual(feed(s, bars), [])
                self.assertEqual(len(s.staged), 1)                            # still resting: the close is above the CE
        s = make(max_signals_per_day=0)
        feed(s, list(LEAD_BUY) + [G, touch_and_hold, close_through])
        self.assertEqual(s.staged, [])
        self.assertTrue(said(s, "FP-02", "consequent encroachment 99.550"))
        s = make(max_signals_per_day=0)                                       # and the mirror
        feed(s, mirror(list(LEAD_BUY) + [G, touch_and_hold, close_through]))
        self.assertEqual(s.staged, [])
        self.assertTrue(said(s, "FP-02", "consequent encroachment 100.450"))

    def test_trading_through_the_far_edge_stop_cancels_an_unfilled_order(self):
        # "invalid if price closes below c_C": the stop sits one tick beyond that edge, so a candle that reaches it before the order
        # filled (again only possible when the engine did not fill it) takes the order off
        through = (100.30, 100.40, 99.10, 99.15)
        for name, bars in both(list(LEAD_BUY) + [G, through]):
            with self.subTest(name):
                s = make(max_signals_per_day=0)
                feed(s, bars)
                self.assertEqual(s.staged, [])
                self.assertTrue(said(s, "EN-04", "price reached the stop before filling"))

    def test_a_fill_that_closes_through_the_far_edge_is_still_reported_not_hidden(self):
        # no hindsight: the touch fills the limit before the candle can close, so the signal fires and the stop at the far edge ends it
        for name, bars in both(list(LEAD_BUY) + [G, (100.30, 100.35, 99.00, 99.10)]):
            with self.subTest(name):
                s, sigs = run("vacuum", bars)
                self.assertEqual(len(sigs), 1)
                self.assertEqual(sigs[0][0], GAP_IDX + 1)

    def test_the_gap_staging_is_not_repeated_and_the_memory_is_pruned(self):
        bars = buy_case(tail=(H,)) + [(100.30, 100.60, 100.10, 100.40)] * 24
        s = make()
        feed(s, bars)
        self.assertEqual(s._seen, {GAP_IDX})
        second = bars + [(bars[-1][1] + 0.8, bars[-1][1] + 1.3, bars[-1][1] + 0.7, bars[-1][1] + 1.2)]
        s = make()
        feed(s, second)
        self.assertEqual(s._seen, {len(second) - 1})                          # the first gap is more than 20 candles old: forgotten
        s = make()
        top = second[GAP_IDX + 4][1]                                          # a second gap five candles after the first, over the last high
        feed(s, second[:GAP_IDX + 5] + [(top + 0.8, top + 1.3, top + 0.7, top + 1.2)])
        self.assertEqual(s._seen, {GAP_IDX, GAP_IDX + 5})                      # two gaps in the same 20 candles are both remembered

    def test_the_stop_distance_and_reward_checks_of_the_engine_apply(self):
        wide = make(min_stop_pips=3.0, max_stop_pips=25.0)                    # the stop is 0.71 = 71 pips: too wide
        self.assertEqual(feed(wide, buy_case()), [])
        self.assertEqual(staged(wide), [])
        self.assertTrue(said(wide, "SL-03", "vacuum block entry rejected: stop 71.0 pips outside [3.0, 25.0]"))
        self.assertEqual(len(feed(make(min_stop_pips=3.0, max_stop_pips=75.0), buy_case())), 1)
        picky = make(min_rr=3.0)                                              # 2.11R is under 3R
        self.assertEqual(feed(picky, buy_case()), [])
        self.assertEqual(staged(picky), [])
        self.assertTrue(said(picky, "TP-02", "vacuum block entry rejected: 2.11R"))

    def test_a_gap_above_everything_has_nothing_to_aim_at_and_is_rejected(self):
        # a straight rise: the candle before the gap holds the highest high, so no liquidity lies above the buy limit
        rise = chain(100.0, [(20, 1)])
        for name, bars in both(scaled(rise, 0.7, 0.5)):                       # and a straight fall, mirrored: nothing below the sell limit
            with self.subTest(name):
                s = make()
                self.assertEqual(feed(s, bars), [])
                self.assertEqual((staged(s), s.staged), ([], []))
                self.assertTrue(said(s, "TP-01", "vacuum block entry rejected: no opposing liquidity to target"))

    def test_price_only_no_clock_or_session_gating(self):
        want = [(i, x.direction, x.entry_ref, x.stop, x.target) for i, x in feed(make(), buy_case())]
        self.assertEqual(len(want), 1)
        # whole days later (a Saturday, a Sunday, the small hours) and the same story gives the same signal on the same candle
        for shift, what in ((288, "Wednesday"), (288 * 4, "Saturday"), (288 * 4 + 144, "Sunday 00:00 UTC"), (288 * 5 + 40, "Sunday 15:20 UTC")):
            with self.subTest(what):
                got = [(i - shift, x.direction, x.entry_ref, x.stop, x.target) for i, x in feed(make(), buy_case(), shift)]
                self.assertEqual(got, want)

    def test_a_gap_on_the_first_candle_of_a_trading_day_keeps_its_order(self):
        # the weekend gap and the session-open gap are the model's reason to exist, and the gap candle is then the first of a new
        # trading day: the engine drops the resting orders of the old day at that candle, before the detector runs, so the order
        # staged by the gap itself must survive and fill on the second candle after it
        roll, step = CFG.strategy.day_rollover, timedelta(minutes=5)
        first = next(i for i in range(1, 600) if trading_day(T0 + step * i, roll) != trading_day(T0 + step * (i - 1), roll))
        for name, bs in both(buy_case()):
            with self.subTest(name):
                s = make()
                out = feed(s, bs, first - GAP_IDX)                                 # the gap candle lands on the first candle of the day
                self.assertEqual([i for i, _ in out], [first + 2])
                self.assertEqual(out[0][1].direction, LONG if name == "as built" else SHORT)
                self.assertNotEqual(trading_day(T0 + step * (first - 1), roll), trading_day(T0 + step * first, roll))

    def test_short_and_degenerate_histories_do_not_raise(self):
        flat = [(100.0, 100.0, 100.0, 100.0)] * 40
        for bars in ([], flat[:1], flat[:2], flat[:3], flat, flat + [(101.0, 101.0, 101.0, 101.0)], flat + [(99.0, 99.0, 99.0, 99.0)],
                     [(100.0, 100.0, 100.0, 100.0), (100.0, 101.0, 99.0, 100.5)] * 30):
            s, sigs = run("vacuum", bars)
            self.assertEqual(sigs, [])
        rising = [(100.0 + i, 100.5 + i, 99.9 + i, 100.4 + i) for i in range(40)]
        falling = [(100.0 - i, 100.1 - i, 99.5 - i, 99.6 - i) for i in range(40)]
        run("vacuum", rising)                                                 # a gap under every candle, nothing to aim at: no raise
        run("vacuum", falling)
        s, sigs = run("vacuum", flat + [(101.0, 101.0, 101.0, 101.0)])        # a zero median range: the size ratio must not divide by it
        self.assertTrue(said(s, "TP-01", "vacuum block entry rejected"))

    # ------------------------------------------------------------------ noise
    def test_a_close_to_close_walk_has_no_gap_and_costs_no_bias_work(self):
        calls = []
        s = make()
        s.daily_bias = lambda: calls.append(1) or (0, "off")
        sigs = feed(s, walk(7, 3000, gap=0.0))
        self.assertEqual((sigs, s._seen, staged(s)), ([], set(), []))
        self.assertEqual(run("vacuum", walk(7, 3000, gap=0.0))[1], [])        # nor does the plain engine run fire on it
        self.assertEqual(calls, [])                                           # no gap on a candle: the detector does no further work

    def test_noise_fires_a_modest_number_of_signals_and_never_breaks(self):
        # 3000 five-minute bars (10.4 days) of a seeded random walk (random.Random(7)) whose candles open off the previous close by
        # 0.4 sigma, and a stress walk with a much bigger scatter (1 sigma: far more gaps than any real market). The engine allows
        # one signal per trading day, so the bound on the signals is the number of trading days the bars touch; the floor only
        # proves the detector is alive on a series that has gaps (the close-to-close walk below has none and stays silent).
        for gap, floor in ((0.4, 1), (1.0, 5)):
            with self.subTest(f"open scatter {gap} sigma"):
                bars = walk(7, 3000, gap=gap)
                s, sigs = run("vacuum", bars)
                days = {trading_day(T0 + timedelta(minutes=5 * i), CFG.strategy.day_rollover) for i in range(len(bars))}
                self.assertGreaterEqual(len(sigs), floor)
                self.assertLessEqual(len(sigs), len(days))
                self.assertEqual(len({trading_day(x.time - timedelta(minutes=5), CFG.strategy.day_rollover) for _, x in sigs}), len(sigs))
                s2, free = run("vacuum", bars, max_signals_per_day=10 ** 6)
                found = oracle(bars)
                self.assertGreater(found, 0)
                n_staged = len(staged(s2))
                n_rejected = len(said(s2, "SL-03", "vacuum block entry rejected")) + len(said(s2, "TP-01", "vacuum block entry rejected")) \
                    + len(said(s2, "TP-02", "vacuum block entry rejected"))
                n_ignored = len(said(s2, "RL-05", "vacuum block ignored"))
                # every qualifying gap is read exactly once: it is staged, rejected by the engine's checks or ignored by the bias
                self.assertEqual(n_staged + n_rejected + n_ignored, found)
                # the daily cap only ever drops later signals: every capped signal is one of the uncapped run's, on the same candle
                key = lambda i, x: (i, x.direction, round(x.entry_ref, 9), round(x.stop, 9), round(x.target, 9))
                self.assertLessEqual(len(sigs), len(free))
                self.assertTrue({key(i, x) for i, x in sigs} <= {key(i, x) for i, x in free})
                self.assertLessEqual(len(free), n_staged)                     # a signal needs a staged order: at most one per gap
                self.assertLessEqual(len(free), found)                        # ... and an order needs a qualifying gap
                # a gap that qualifies is at most 6.2% of candles even in the stress walk (186 of 3000): a bound 3x that
                self.assertLessEqual(found, 0.20 * len(bars))
                self.assertLessEqual(len(s2._seen), blk_vacuum.VC_EXPIRY)     # the memory stays bounded

    def test_noise_signals_obey_the_geometry(self):
        s, sigs = run("vacuum", walk(7, 3000, gap=1.0), max_signals_per_day=10 ** 6)
        self.assertGreater(len(sigs), 20)
        seen = set()
        for i, x in sigs:
            lo, hi = sorted(x.meta["fvg"])
            self.assertEqual([r[:5] for r in x.reasons[:3]], ["VC-01", "VC-02", "VC-03"])
            self.assertGreaterEqual(hi - lo, 0.04 - 1e-9)                     # at least four ticks wide
            if x.direction == LONG:
                self.assertAlmostEqual(x.entry_ref, hi, places=9)             # the near edge of a gap up is its top
                self.assertAlmostEqual(x.stop, lo - 0.01, places=9)           # one tick under the lower edge
                self.assertGreater(x.target, x.entry_ref)
                self.assertIn("true gap up", x.reasons[0])
            else:
                self.assertAlmostEqual(x.entry_ref, lo, places=9)             # the near edge of a gap down is its bottom
                self.assertAlmostEqual(x.stop, hi + 0.01, places=9)
                self.assertLess(x.target, x.entry_ref)
                self.assertIn("true gap down", x.reasons[0])
            seen.add(x.direction)
        self.assertEqual(seen, {LONG, SHORT})                                 # both sides appear

    def test_the_sell_side_is_the_exact_mirror_on_noise(self):
        bars = walk(7, 3000, gap=1.0)
        outs = []
        for x in (bars, flip(bars, 205.0)):
            s = make(max_signals_per_day=10 ** 6)
            s.daily_bias = lambda: (0, "off")                                 # the bias rule is the engine's, not the detector's
            outs.append(feed(s, x))
        self.assertGreater(len(outs[0]), 20)
        self.assertEqual([(i, x.direction) for i, x in outs[0]], [(i, -x.direction) for i, x in outs[1]])
        for (_, a), (_, b) in zip(*outs):
            self.assertAlmostEqual(a.entry_ref, 205.0 - b.entry_ref, places=6)
            self.assertAlmostEqual(a.stop, 205.0 - b.stop, places=6)
            self.assertAlmostEqual(a.target, 205.0 - b.target, places=6)

    def test_no_lookahead_a_prefix_gives_the_same_signals(self):
        bars = walk(7, 3000, gap=1.0)
        _, full = run("vacuum", bars, max_signals_per_day=10 ** 6)
        _, head = run("vacuum", bars[:1500], max_signals_per_day=10 ** 6)
        self.assertGreater(len(head), 10)
        self.assertEqual([(i, x.direction, x.entry_ref, x.stop) for i, x in head],
                         [(i, x.direction, x.entry_ref, x.stop) for i, x in full if i < 1500])

    def test_the_parameters_are_live(self):
        with mock.patch.object(blk_vacuum, "VC_MIN_TICKS", 80):               # 80 ticks = 0.80 is wider than the 0.70 gap
            self.assertEqual(run("vacuum", buy_case())[1], [])
        with mock.patch.object(blk_vacuum, "VC_MIN_RANGE", 2.0):              # twice the median range is 1.00: wider than the gap
            self.assertEqual(run("vacuum", buy_case())[1], [])
        with mock.patch.object(blk_vacuum, "VC_EXPIRY", 3):
            late = list(LEAD_BUY) + [G, (100.30, 100.60, 100.10, 100.40), (100.30, 100.60, 100.10, 100.40), (100.30, 100.60, 100.10, 100.40), I]
            self.assertEqual(run("vacuum", late)[1], [])
        with mock.patch.object(blk_vacuum, "VC_WARMUP", 40):
            self.assertEqual(run("vacuum", buy_case())[1], [])


if __name__ == "__main__":
    unittest.main()
