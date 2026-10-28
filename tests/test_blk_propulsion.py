"""Propulsion Block: a down candle that trades into a bullish order block and then proves itself (ict_trader/blk_propulsion.py).

All bars are 5-minute (open, high, low, close) tuples fed through tests.test_patterns.run (pip size 0.01, so one tick is 0.01).
The hand-built case is bullish; every bearish case is the same bars mirrored (price p becomes 200 - p), and every negative runs both ways.

The reference story (bullish), bar numbers in brackets:
  [0-3]    a swing high at 100.60 (bar 2): the structure the displacement will take
  [4-7]    a decline; bar 7 is the order block A (the last down candle before the move): [98.90, 99.25], open 99.20
  [8]      the displacement: a 1.85 body (the median is 0.25) closing at 100.80, above the swing high
  [9-11]   the leg: its top is the swing high at 102.10 (bar 10), the liquidity the target aims at; bar 11 turns down
  [12]     B, the propulsion candle: a down candle, open 101.60, close 99.80, whose low 99.15 reaches into A (<= 99.25)
           MT = 100.70, so the zone is [100.70, 101.60]
  [13]     the high 101.70 takes B's open and the candle closes at 101.65: the block is valid, the limit is staged at 101.60,
           the stop is one tick under MT at 100.69
  [14]     the retest trades down to 101.40 and the order fills
"""

import random
import unittest
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from unittest import mock

from ict_trader import blk_propulsion
from ict_trader.blk_propulsion import PropulsionStrategy
from ict_trader.models import is_model, make_strategy
from ict_trader.sessions import Bar
from tests.test_patterns import CFG, T0, run

LEAD = [(100.00, 100.15, 99.90, 100.05),     # 0
        (100.05, 100.20, 99.95, 100.10),     # 1
        (100.10, 100.60, 100.05, 100.15),    # 2 the swing high 100.60
        (100.15, 100.25, 99.90, 99.95),      # 3
        (99.95, 100.00, 99.65, 99.70),       # 4
        (99.70, 99.75, 99.40, 99.45),        # 5
        (99.45, 99.50, 99.15, 99.20)]        # 6
OB = (99.20, 99.25, 98.90, 98.95)            # 7 the order block A: open 99.20, high 99.25, low 98.90
DISP = (98.95, 100.85, 98.90, 100.80)        # 8 body 1.85, closes above 100.60
LEG = [(100.80, 101.10, 100.70, 101.00),     # 9
       (101.00, 102.10, 100.95, 102.00),     # 10 the swing high 102.10
       (102.00, 102.05, 101.50, 101.60)]     # 11
PROP = (101.60, 101.65, 99.15, 99.80)        # 12 B: open 101.60, close 99.80, MT 100.70, low 99.15 reaches A's high 99.25
VALID = (99.80, 101.70, 99.70, 101.65)       # 13 the high takes 101.60, the close stays above the entry
RETEST = (101.65, 101.70, 101.40, 101.50)    # 14 trades down to the entry
QUIET_LEG = [(100.80, 101.10, 100.70, 101.00),     # 9  a leg with no big body of its own: the displacement at bar 8 is the only candidate
             (101.00, 102.10, 100.95, 101.05),     # 10 the swing high 102.10 is a wick
             (101.50, 101.65, 101.45, 101.52)]     # 11
FILL_UP = (101.60, 101.80, 101.55, 101.70)   # a quiet up candle at the top of the leg (below the 102.10 swing high)
CHOP = (100.90, 101.30, 100.80, 101.10)      # a quiet up candle inside B's zone (never above B's open, never under MT)
GONE = (99.80, 101.70, 99.70, 101.60)        # a wick over B's open that closes ON the entry: B has proved itself, but no limit can rest yet
AGAIN = (101.60, 101.90, 101.55, 101.80)     # the next candle: closes above the entry


LOW_SWING = [(99.00, 99.10, 98.80, 98.90), (98.90, 99.00, 98.60, 98.70), (98.70, 98.80, 98.40, 98.50), (98.50, 98.90, 98.45, 98.85),
             (98.85, 99.05, 98.80, 99.00),       # 4 a swing high at 99.05 ...
             (98.90, 98.95, 98.70, 98.75), (98.75, 98.90, 98.70, 98.85)]      # ... that lies BELOW the order block's high (99.25)


def story(a=OB, disp=DISP, mid=(), leg=LEG, pad=(), prop=PROP, wait=(), valid=VALID, after=(RETEST,), lead=None):
    """The bullish bars; `mid` sits between A and the displacement, `pad` between the leg and B, `wait` between B and the validating candle."""
    return list(lead or LEAD) + [a] + list(mid) + [disp] + list(leg) + list(pad) + [prop] + list(wait) + [valid] + list(after)


def mirror(bars, m=200.0):
    """The same market upside down (price p becomes m - p): every high becomes a low."""
    return [(round(m - o, 4), round(m - l, 4), round(m - h, 4), round(m - c, 4)) for o, h, l, c in bars]


def both(bars):
    return [("bullish", bars), ("bearish", mirror(bars))]


def signals(bars, **kw):
    return run("propulsion", bars, **kw)[1]


def staged(bars, **kw):
    """The 'staged' events (an order was placed) of a run: how often the detector found a block, whatever the fill and the daily cap."""
    return [e for e in run("propulsion", bars, **kw)[0].events if e["type"] == "staged"]


class PropulsionBlockTest(unittest.TestCase):
    def none_either_way(self, bars, msg="", **kw):
        for name, bs in both(bars):
            with self.subTest(f"{name} {msg}"):
                self.assertEqual(signals(bs, **kw), [], msg)

    def one_either_way(self, bars, msg="", **kw):
        for name, bs in both(bars):
            with self.subTest(f"{name} {msg}"):
                self.assertEqual(len(signals(bs, **kw)), 1, msg)

    # ------------------------------------------------------------------ the clean case and its mirror
    def test_registered_and_parameters_match_the_report(self):
        self.assertTrue(is_model("propulsion"))
        self.assertIsInstance(make_strategy(replace(CFG.strategy, model="propulsion"), CFG.instrument), PropulsionStrategy)
        self.assertEqual((blk_propulsion.PB_MAX_AB, blk_propulsion.PB_TOL_TICKS, blk_propulsion.PB_ENTRY_DEPTH), (10, 1, 0.0))

    def test_bullish_a_down_candle_trades_into_an_order_block_then_proves_itself(self):
        bars = story()
        s, sigs = run("propulsion", bars)
        self.assertEqual(len(sigs), 1)
        i, sig = sigs[0]
        self.assertEqual(i, 14)                                      # filled on the retest, not before
        self.assertEqual(sig.direction, 1)
        self.assertAlmostEqual(sig.entry_ref, 101.60, places=4)      # B's open
        self.assertAlmostEqual(sig.stop, 100.69, places=4)           # one tick under MT (100.70)
        self.assertAlmostEqual(sig.target, 102.10, places=4)         # the swing high at the top of the leg
        self.assertEqual(sig.entry_type, "limit")
        self.assertTrue(sig.reasons[0].startswith("PB-01"))
        self.assertTrue(sig.reasons[1].startswith("PB-02") and sig.reasons[2].startswith("PB-03") and sig.reasons[3].startswith("RL-05"))
        trail = " ".join(sig.reasons)
        for price in ("98.900", "99.250", "100.600", "101.600", "99.800", "99.150", "100.700", "100.690"):
            self.assertIn(price, trail)                              # the real prices are in the trail
        self.assertEqual(sig.meta["entry_mode"], "propulsion")
        self.assertEqual(tuple(round(x, 4) for x in sig.meta["fvg"]), (100.70, 101.60))     # the zone [MT, open]

    def test_the_order_is_staged_on_the_validating_candle_and_not_earlier(self):
        bars = story()
        before = run("propulsion", bars[:13])[0]                     # up to and including B: nothing yet
        self.assertEqual((before.staged, before._setups), ([], []))
        after = run("propulsion", bars[:14])[0]                      # the validating candle has closed
        self.assertEqual(len(after.staged), 1)
        o = after.staged[0]
        self.assertEqual((o["direction"], o["limit"], o["target"]), ("long", 101.6, 102.1))
        self.assertAlmostEqual(o["stop"], 100.69, places=4)
        self.assertEqual(tuple(round(x, 4) for x in o["fvg"]), (100.70, 101.60))

    def test_bearish_is_the_exact_mirror(self):
        s, sigs = run("propulsion", mirror(story()))
        self.assertEqual(len(sigs), 1)
        i, sig = sigs[0]
        self.assertEqual((i, sig.direction), (14, -1))
        self.assertAlmostEqual(sig.entry_ref, 98.40, places=4)       # B's open
        self.assertAlmostEqual(sig.stop, 99.31, places=4)            # one tick above MT (99.30)
        self.assertAlmostEqual(sig.target, 97.90, places=4)          # the swing low at the bottom of the leg
        self.assertGreater(sig.stop, sig.entry_ref)
        self.assertTrue(sig.reasons[0].startswith("PB-01") and "bearish order block" in sig.reasons[0])
        self.assertTrue(sig.reasons[1].startswith("PB-02") and sig.reasons[2].startswith("PB-03"))
        self.assertEqual(tuple(round(x, 4) for x in sig.meta["fvg"]), (98.40, 99.30))

    def test_the_stop_distance_is_half_the_body_plus_one_tick_and_the_risk_is_kept_in_pips(self):
        for name, bs in both(story()):
            with self.subTest(name):
                sig = signals(bs)[0][1]
                self.assertAlmostEqual(abs(sig.entry_ref - sig.stop), 0.91, places=4)         # (101.60 - 100.70) + 0.01

    def test_the_rules_trail_reads_right_for_a_buy_and_for_a_sell(self):
        buy, sell = signals(story())[0][1].reasons, signals(mirror(story()))[0][1].reasons
        self.assertEqual(buy[0], "PB-01 bullish order block: the last down candle [98.900, 99.250] before a displacement that took the swing high at 100.600")
        self.assertEqual(buy[1], "PB-02 propulsion candle: a later down candle (open 101.600, close 99.800) traded down into the block, its low 99.150 reaching 99.250")
        self.assertEqual(buy[2], "PB-03 validated: a later candle's high 101.700 took its open 101.600; zone [100.700, 101.600], limit at 101.600, "
                                 "stop 100.690 under the mean threshold 100.700; a body close below 100.690 voids the block")
        self.assertEqual(sell[0], "PB-01 bearish order block: the last up candle [100.750, 101.100] before a displacement that took the swing low at 99.400")
        self.assertEqual(sell[1], "PB-02 propulsion candle: a later up candle (open 98.400, close 100.200) traded up into the block, its high 100.850 reaching 100.750")
        # a sell's stop sits OVER the mean threshold and a body close ABOVE it voids the block
        self.assertEqual(sell[2], "PB-03 validated: a later candle's low 98.300 took its open 98.400; zone [98.400, 99.300], limit at 98.400, "
                                  "stop 99.310 over the mean threshold 99.300; a body close above 99.310 voids the block")

    # ------------------------------------------------------------------ the order block A
    def test_a_doji_is_not_a_down_candle_so_the_order_block_is_the_down_candle_before_it(self):
        doji = (99.20, 99.25, 98.90, 99.20)                          # closes on its open: not a down-close candle
        for name, bs in both(story(a=doji)):
            with self.subTest(name):
                sig = signals(bs)[0][1]
                self.assertIn("[99.150, 99.500]" if name == "bullish" else "[100.500, 100.850]", sig.reasons[0])     # bar 6, not the doji at bar 7

    def test_no_order_block_when_the_displacement_does_not_take_the_swing_high(self):
        # the swing high is at 100.60; the leg is quiet here so that only bar 8 can be the displacement
        self.none_either_way(story(leg=QUIET_LEG, disp=(98.95, 100.55, 98.90, 100.50)), msg="closes under the swing high")
        self.none_either_way(story(leg=QUIET_LEG, disp=(98.95, 100.65, 98.90, 100.60)), msg="closes exactly on it: the wick took it, the body did not")
        self.one_either_way(story(leg=QUIET_LEG, disp=(98.95, 100.65, 98.90, 100.61)), msg="closes one tick over it")
        # with the default leg a later big candle (bar 10, within 3 of A) is itself a displacement that takes the swing: still an order block
        self.one_either_way(story(disp=(98.95, 100.55, 98.90, 100.50)))

    def test_no_order_block_without_a_swing_high_above_it(self):
        stair = [(101.2 - 0.2 * i, 101.25 - 0.2 * i, 101.0 - 0.2 * i, 101.05 - 0.2 * i) for i in range(7)]   # every high lower than the last
        stair = [tuple(round(x, 4) for x in b) for b in stair]
        self.none_either_way(story(lead=stair))

    def test_the_swing_high_that_is_taken_must_lie_above_the_order_block(self):
        # the only swing high behind A is at 99.05, under A's own high 99.25: taking it is no break of structure
        self.none_either_way(story(lead=LOW_SWING, a=(99.00, 99.25, 98.90, 98.95)))
        # the same market with a swing high above A (the standard lead) is an order block
        self.one_either_way(story(a=(99.20, 99.25, 98.90, 98.95)))

    def test_no_order_block_when_the_displacement_body_is_small(self):
        self.none_either_way(story(), msg="a displacement must be 10x the median body here", displacement_body_mult=10.0)
        self.one_either_way(story(), displacement_body_mult=1.5)

    def test_the_order_block_is_the_last_down_candle_before_the_displacement(self):
        later = (98.95, 98.98, 98.70, 98.75)                         # another down candle, high 98.98, BETWEEN A and the displacement
        # B's low (99.15) reached the earlier candle (high 99.25) but not the real order block (high 98.98): no propulsion block
        self.none_either_way(story(mid=[later], disp=(98.75, 100.85, 98.70, 100.80)))
        # the same B does trade into the new order block when its low goes low enough
        self.one_either_way(story(mid=[later], disp=(98.75, 100.85, 98.70, 100.80), prop=(101.60, 101.65, 98.95, 99.80)))

    def test_the_displacement_must_follow_the_order_block_closely(self):
        quiet = [(98.95, 99.05, 98.90, 99.00), (99.00, 99.10, 98.95, 99.05), (99.05, 99.15, 99.00, 99.10)]   # three quiet up candles
        self.one_either_way(story(mid=quiet[:2], disp=(99.10 - 0.15, 100.85, 99.00, 100.80)), msg="the displacement is the 3rd candle after A")
        self.none_either_way(story(mid=quiet, disp=(99.15, 100.85, 99.10, 100.80)), msg="the displacement is the 4th candle after A")

    # ------------------------------------------------------------------ the propulsion candle B
    def test_b_must_be_a_down_close_candle(self):
        up = (99.50, 101.65, 99.15, 101.60)                          # same low, but an up candle
        self.none_either_way(story(prop=up))
        self.none_either_way(story(prop=(101.60, 101.65, 99.15, 101.60)), msg="a doji (closes on its open) is not a down-close candle")

    def test_b_low_must_reach_into_the_order_block(self):
        self.none_either_way(story(prop=(101.60, 101.65, 99.26, 99.80)), msg="low one tick over A's high 99.25")
        self.one_either_way(story(prop=(101.60, 101.65, 99.25, 99.80)), msg="low exactly at A's high")
        self.one_either_way(story(prop=(101.60, 101.65, 98.50, 99.80)), msg="low through A: the lesson only asks that it reached in")

    def test_b_must_come_within_ten_candles_of_the_order_block(self):
        # A is bar 7; the leg ends at bar 11, so 5 pads put B at bar 17 (10 after A) and 6 pads at bar 18 (11 after A)
        self.one_either_way(story(pad=[FILL_UP] * 5), msg="B is 10 candles after A")
        self.none_either_way(story(pad=[FILL_UP] * 6), msg="B is 11 candles after A")

    def test_b_must_come_after_the_displacement(self):
        # a down candle right after A (before the displacement) is the order block, it cannot also be the propulsion candle
        early = (98.95, 99.00, 98.60, 98.65)
        bars = story(mid=[early], disp=(98.65, 100.85, 98.60, 100.80), prop=(101.60, 101.65, 99.20, 99.80))
        self.none_either_way(bars)

    # ------------------------------------------------------------------ validation
    def test_valid_only_once_a_later_high_takes_the_open_of_b(self):
        self.none_either_way(story(valid=(99.80, 101.59, 99.70, 101.55)), msg="the high stays under B's open")
        self.none_either_way(story(valid=(99.80, 101.60, 99.70, 101.55)), msg="the high only equals B's open")
        self.one_either_way(story(valid=(99.80, 101.61, 99.70, 101.605)), msg="one tick over it")

    def test_nothing_rests_on_a_candle_that_closes_at_or_under_the_entry(self):
        # its wick took B's open but it closed back inside the zone: a limit at the entry would sit above the market, so nothing is staged
        # on that candle (and nothing later in these stories closes above the entry either)
        self.none_either_way(story(valid=GONE))
        self.none_either_way(story(valid=(99.80, 101.70, 99.70, 101.20)))
        self.one_either_way(story(valid=(99.80, 101.70, 99.70, 101.61)))

    def test_a_wick_over_the_open_that_closes_back_inside_the_zone_leaves_the_block_valid(self):
        # the report: valid after ANY later high over B's open, void only on a body close under MT. So the block is not lost when the
        # candle that proved it closed inside the zone: the limit is staged on the first later candle that closes above the entry
        for name, bs in both(story(valid=GONE, after=(AGAIN, RETEST))):
            with self.subTest(name):
                self.assertEqual(run("propulsion", bs[:14])[0].staged, [])               # the wick candle: no limit can rest yet
                self.assertEqual(len(run("propulsion", bs[:15])[0].staged), 1)           # the candle that closes above the entry: staged
                s, sigs = run("propulsion", bs)
                self.assertEqual([i for i, _ in sigs], [15])                             # and filled on the retest
                sig = sigs[0][1]
                self.assertAlmostEqual(sig.entry_ref, 101.60 if name == "bullish" else 98.40, places=4)
                self.assertIn("101.900" if name == "bullish" else "98.100", sig.reasons[2])    # the trail names the highest high that proved it

    def test_the_wick_validated_block_is_still_bound_by_the_ten_candle_window(self):
        self.one_either_way(story(valid=GONE, after=[CHOP] * 8 + [AGAIN, RETEST]), msg="the staging candle is the 10th after B")
        self.none_either_way(story(valid=GONE, after=[CHOP] * 9 + [AGAIN, RETEST]), msg="the staging candle is the 11th after B")

    def test_a_body_close_under_mt_between_the_wick_and_the_staging_candle_voids_the_block(self):
        self.none_either_way(story(valid=GONE, after=[(101.55, 101.60, 100.20, 100.60), AGAIN, RETEST]), msg="a body closed under MT")
        self.none_either_way(story(valid=GONE, after=[(101.55, 101.60, 100.20, 100.68), AGAIN, RETEST]), msg="a close two ticks under MT")
        self.one_either_way(story(valid=GONE, after=[(101.55, 101.60, 100.20, 101.50), AGAIN, RETEST]), msg="a wick under MT, the body above")
        self.one_either_way(story(valid=GONE, after=[(101.55, 101.60, 100.40, 100.69), AGAIN, RETEST]), msg="a close one tick under MT")

    def test_a_validated_block_is_staged_once_however_many_later_candles_close_above_its_entry(self):
        more = [AGAIN, (101.80, 101.95, 101.70, 101.90), (101.90, 101.99, 101.75, 101.95)]
        for name, bs in both(story(after=more)):
            with self.subTest(name):
                self.assertEqual(len(staged(bs, max_signals_per_day=100)), 1)

    def test_a_rejected_block_is_not_met_again_on_every_later_candle(self):
        # min_rr 2: the 0.55R to the swing high at 102.10 is rejected. Without the looked-at set it would be rejected (and logged) on each
        # of the following candles that close above the entry
        more = [AGAIN, (101.80, 101.95, 101.70, 101.90), (101.90, 101.99, 101.75, 101.95)]
        for name, bs in both(story(after=more)):
            with self.subTest(name):
                st = replace(CFG.strategy, model="propulsion", timeframe_minutes=5, min_stop_pips=0, max_stop_pips=1e9, min_rr=2.0,
                             liquidity_pools=True, daily_bias_filter=False)
                s = make_strategy(st, replace(CFG.instrument, pip_size=0.01))
                for i, b in enumerate(bs):
                    s.on_bar(Bar(T0 + timedelta(minutes=5 * i), *b))
                self.assertEqual([e["type"] for e in s.events if e["type"] in ("rejected", "staged")], ["rejected"])

    def test_the_validating_high_must_come_within_ten_candles_of_b(self):
        self.one_either_way(story(wait=[CHOP] * 9), msg="the validating candle is the 10th after B")
        self.none_either_way(story(wait=[CHOP] * 10), msg="the validating candle is the 11th after B")

    # ------------------------------------------------------------------ the invalidation rule: a BODY close below MT
    def test_a_body_close_below_mt_voids_the_block_even_if_price_then_runs_above_its_open(self):
        for close in (100.60, 100.68, 99.90):                         # MT is 100.70, the tolerance 0.01
            squash = (100.80, 100.85, 99.80, close)
            self.none_either_way(story(wait=[squash]), msg=f"close {close}")

    def test_a_wick_through_mt_does_not_void_it(self):
        wick = (100.75, 100.95, 99.10, 100.80)                        # the low is far under MT (and under B's low), the body stays over MT
        self.one_either_way(story(wait=[wick]))

    def test_a_close_one_tick_under_mt_does_not_void_it(self):
        # the lesson's NQ example: the retest closed one tick under MT and price still ran
        self.one_either_way(story(wait=[(100.75, 100.80, 100.50, 100.69)]), msg="one tick under MT 100.70")
        self.none_either_way(story(wait=[(100.75, 100.80, 100.50, 100.68)]), msg="two ticks under MT")

    def test_a_close_under_mt_on_the_validating_candle_itself_voids_it(self):
        self.none_either_way(story(valid=(99.80, 101.70, 99.70, 100.50)))

    def test_after_staging_a_close_through_the_stop_cancels_an_order_that_could_not_fill(self):
        # max_signals_per_day=0: the order can rest but never fill, so only the lifecycle can remove it
        bars = story(after=())
        s, sigs = run("propulsion", bars, max_signals_per_day=0)
        self.assertEqual((len(s._setups), sigs), (1, []))
        for i, bar in enumerate([(101.65, 101.80, 101.62, 101.70)]):                          # stays above the entry
            s.on_bar(Bar(T0 + timedelta(minutes=5 * (len(bars) + i)), *bar))
        self.assertEqual(len(s._setups), 1)
        s.on_bar(Bar(T0 + timedelta(minutes=5 * (len(bars) + 1)), 101.70, 101.70, 100.30, 100.50))
        self.assertEqual(s._setups, [])                               # a body closed through MT: gone
        self.assertTrue(any(d.rule == "EN-04" and "cancelled" in d.message for d in s.decisions))

    def test_the_resting_order_expires(self):
        calm = [(101.70, 101.80, 101.65, 101.75)] * blk_propulsion.PB_EXPIRY          # never comes back to 101.60, never reaches 102.10
        for name, bs in both(story(after=calm)):
            with self.subTest(name):
                s, sigs = run("propulsion", bs)
                self.assertEqual((sigs, s._setups), ([], []))
        # one candle short of the expiry the order is still resting
        s, sigs = run("propulsion", story(after=calm[:-1]))
        self.assertEqual((len(s._setups), sigs), (1, []))

    # ------------------------------------------------------------------ entry, bias, one per block, no lookahead
    def test_entry_depth_moves_the_limit_down_the_zone(self):
        deep = story(after=[(101.65, 101.70, 101.30, 101.50), (101.50, 101.52, 101.10, 101.20)])
        with mock.patch.object(blk_propulsion, "PB_ENTRY_DEPTH", 0.5):
            for name, bs in both(deep):
                with self.subTest(name):
                    i, sig = signals(bs)[0]
                    self.assertAlmostEqual(abs(sig.entry_ref - (101.15 if name == "bullish" else 98.85)), 0.0, places=4)   # open - 0.5 * (open - MT)
                    self.assertEqual(i, 15)                                                                              # not touched on the first retest candle
                    self.assertAlmostEqual(abs(sig.stop - (100.69 if name == "bullish" else 99.31)), 0.0, places=4)

    def test_with_a_deeper_entry_a_high_that_only_equals_the_open_is_still_not_a_validation(self):
        equal = (99.80, 101.60, 99.70, 101.50)                       # closes above the deep entry 101.15, but the high never took 101.60
        with mock.patch.object(blk_propulsion, "PB_ENTRY_DEPTH", 0.5):
            self.none_either_way(story(valid=equal, after=[(101.50, 101.52, 101.10, 101.20)]))     # a retest deep enough to fill, if staged
            self.one_either_way(story(valid=(99.80, 101.61, 99.70, 101.50), after=[(101.50, 101.52, 101.10, 101.20)]))

    def test_respects_the_daily_bias_like_the_other_pattern_models(self):
        for name, bs, d in (("bullish", story(), 1), ("bearish", mirror(story()), -1)):
            with self.subTest(name):
                with mock.patch.object(PropulsionStrategy, "daily_bias", return_value=(d, "test draw")):
                    self.assertEqual(len(signals(bs)), 1)
                with mock.patch.object(PropulsionStrategy, "daily_bias", return_value=(-d, "test draw")):
                    self.assertEqual(signals(bs), [])
                with mock.patch.object(PropulsionStrategy, "daily_bias", return_value=(0, "no draw")):
                    self.assertEqual(len(signals(bs)), 1)

    def test_one_propulsion_block_per_order_block(self):
        # a second down candle trades into the same order block and proves itself too: it is not a second setup
        second = [(101.50, 101.55, 99.20, 99.90), (99.90, 101.60, 99.85, 101.58)]
        bars = story(after=[RETEST] + second)
        self.assertEqual(len(staged(bars, max_signals_per_day=100)), 1)
        self.assertEqual(len(staged(mirror(bars), max_signals_per_day=100)), 1)

    def test_no_lookahead_each_prefix_of_the_run_gives_the_same_signals(self):
        bars = story(after=[RETEST, (101.50, 101.60, 101.30, 101.55), (101.55, 102.20, 101.50, 102.15)])
        for name, bs in both(bars):
            full = signals(bs)
            for n in range(1, len(bs) + 1):
                with self.subTest(f"{name} {n}"):
                    self.assertEqual([i for i, _ in signals(bs[:n])], [i for i, _ in full if i < n])

    def test_price_only_it_does_not_care_about_the_clock(self):
        for start in (datetime(2026, 10, 11, 3, 0, tzinfo=timezone.utc), datetime(2026, 10, 10, 22, 35, tzinfo=timezone.utc)):    # Sunday, Saturday
            st = replace(CFG.strategy, model="propulsion", timeframe_minutes=5, min_stop_pips=0, max_stop_pips=1e9, min_rr=0.1,
                         liquidity_pools=True, daily_bias_filter=False)
            s = make_strategy(st, replace(CFG.instrument, pip_size=0.01))
            fired = [i for i, b in enumerate(story()) if s.on_bar(Bar(start + timedelta(minutes=5 * i), *b))]
            self.assertEqual(fired, [14], start)

    # ------------------------------------------------------------------ noise
    def test_a_random_walk_does_not_raise_and_fires_modestly(self):
        rng = random.Random(7)
        price, bars = 100.0, []
        for _ in range(3000):
            o = price
            c = o + rng.gauss(0, 0.25)
            bars.append((o, max(o, c) + abs(rng.gauss(0, 0.1)), min(o, c) - abs(rng.gauss(0, 0.1)), c))
            price = c
        s, sigs = run("propulsion", bars)                                               # the default cap: one signal a day
        s2, fills = run("propulsion", bars, max_signals_per_day=1000)                   # no cap: every block that gets retested
        found = [e for e in s2.events if e["type"] == "staged"]
        print(f"\npropulsion on 3000 noise bars: {len(sigs)} signals (daily cap 1), {len(found)} orders staged and {len(fills)} filled (no cap)")
        # 3000 five-minute bars is 10.4 days, so the cap allows 11 or 12 signals at most; uncapped, a block needs a displacement taking a
        # swing high, a down candle back into the origin candle within 10 bars, and then a high over its open: a few percent of the bars
        self.assertLessEqual(len(sigs), 12)
        self.assertGreaterEqual(len(found), 10)                                         # the detector is alive on noise (49 at the time of writing)
        self.assertLessEqual(len(found), 3000 // 30)                                    # and picky: under one order per 30 bars (the loosest
                                                                                        # existing pattern, ATM, stages 78 on this same walk)
        # the same walk upside down must give the mirror image: same count, directions swapped (this also exercises the daily bias path)
        upside = [(200 - o, 200 - l, 200 - h, 200 - c) for o, h, l, c in bars]
        s3, fills3 = run("propulsion", upside, max_signals_per_day=1000)
        found3 = [e for e in s3.events if e["type"] == "staged"]
        self.assertEqual([e["dir"] for e in found3], [-e["dir"] for e in found])
        self.assertEqual([i for i, _ in fills3], [i for i, _ in fills])
        self.assertEqual({g.direction for _, g in fills} | {g.direction for _, g in fills3}, {1, -1})      # both directions occur on noise


if __name__ == "__main__":
    unittest.main()
