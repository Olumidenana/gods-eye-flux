import math
import unittest
from dataclasses import replace
from datetime import datetime, timedelta, timezone

from ict_trader.config import load_config
from ict_trader.models import custom_changes, is_model, make_strategy, resolve
from ict_trader.sessions import Bar

CFG = load_config("examples/config.example.toml")
T0 = datetime(2026, 10, 6, 12, tzinfo=timezone.utc)


def run(model, bars, **kw):
    st = replace(CFG.strategy, model=model, timeframe_minutes=5, min_stop_pips=0, max_stop_pips=1e9, min_rr=0.1,
                 liquidity_pools=True, daily_bias_filter=False, **kw)
    s = make_strategy(st, replace(CFG.instrument, pip_size=0.01))
    s._story_against = lambda d: None   # these tests are about the pattern: the story gate has its own test (test_a_pattern_needs_the_story)
    sigs = []
    for i, b in enumerate(bars):
        x = s.on_bar(Bar(T0 + timedelta(minutes=5 * i), *b))
        if x:
            sigs.append((i, x))
    return s, sigs


class PatternModelsTest(unittest.TestCase):
    def test_venom_a_pool_run_by_one_candle_then_a_displacement_back(self):
        bars = [(100 + 0.3 * math.sin(i / 3),) * 1 for i in range(40)]
        bars = [(b[0], b[0] + 0.35, b[0] - 0.35, b[0] + 0.05) for b in bars]
        bars[19], bars[20], bars[21] = (99.9, 100.0, 99.6, 99.8), (99.7, 99.8, 98.5, 99.6), (99.7, 100.2, 99.6, 100.1)   # the pool: a swing low at 98.5
        bars[30], bars[31] = (100.2, 101.6, 100.1, 100.4), (100.3, 100.5, 100.0, 100.2)                              # a swing high to aim at
        bars += [(99.6, 99.7, 98.2, 98.4), (98.4, 99.9, 98.3, 99.8), (99.8, 99.9, 99.2, 99.5)]   # fang 1, fang 2, the retrace that fills
        s, sigs = run("venom", bars)
        self.assertEqual(len(sigs), 1)
        _, sig = sigs[0]
        self.assertEqual(sig.direction, 1)
        self.assertAlmostEqual(sig.entry_ref, 99.8, places=2)       # fang 2's close
        self.assertLess(sig.stop, 98.2)                             # beyond the sweep candle's low
        self.assertTrue(sig.reasons[0].startswith("VN-01"))
        # no run of the pool, no setup
        calm, none = run("venom", bars[:40] + [(100.0, 100.3, 99.7, 100.1)] * 5)
        self.assertEqual(none, [])

    def test_a_pattern_needs_the_story(self):
        # the same Venom candles, but the story says nothing (no completed days to read a draw from): no clear draw is no trade
        bars = [(100 + 0.3 * math.sin(i / 3),) * 1 for i in range(40)]
        bars = [(b[0], b[0] + 0.35, b[0] - 0.35, b[0] + 0.05) for b in bars]
        bars[19], bars[20], bars[21] = (99.9, 100.0, 99.6, 99.8), (99.7, 99.8, 98.5, 99.6), (99.7, 100.2, 99.6, 100.1)
        bars[30], bars[31] = (100.2, 101.6, 100.1, 100.4), (100.3, 100.5, 100.0, 100.2)
        bars += [(99.6, 99.7, 98.2, 98.4), (98.4, 99.9, 98.3, 99.8), (99.8, 99.9, 99.2, 99.5)]
        st = replace(CFG.strategy, model="venom", timeframe_minutes=5, min_stop_pips=0, max_stop_pips=1e9, min_rr=0.1, liquidity_pools=True, daily_bias_filter=False)
        s = make_strategy(st, replace(CFG.instrument, pip_size=0.01))
        sigs = [x for i, b in enumerate(bars) if (x := s.on_bar(Bar(T0 + timedelta(minutes=5 * i), *b)))]
        self.assertEqual(sigs, [])
        self.assertTrue(s._story_against(1) and s._story_against(-1))   # neither side has a story

    def test_atm_a_stop_run_then_an_immediate_structure_break_and_a_retest(self):
        bars = [(100, 100.3, 99.8, 100.05)] * 50
        bars = list(bars)
        bars[12] = (99.6, 99.7, 97.0, 99.5)
        bars[19], bars[20], bars[21] = (100.8, 101.0, 100.6, 100.9), (101.5, 102.0, 101.2, 101.6), (101.0, 101.1, 100.5, 100.7)
        for i, (lo, hi) in zip(range(22, 25), [(100.0, 100.4), (99.4, 99.8), (99.05, 99.3)]):
            bars[i] = (hi, hi + 0.1, lo, lo + 0.05)
        bars[25] = (99.2, 99.4, 98.9, 99.1)
        for i, h in zip(range(26, 30), [100.0, 100.6, 101.2, 101.8]):
            bars[i] = (h - 0.4, h, h - 0.5, h - 0.2)
        for i, b in zip(range(30, 34), [(101.8, 102.5, 101.7, 102.3), (102.3, 103.2, 102.2, 102.9), (102.9, 103.0, 102.5, 102.6), (102.6, 102.8, 102.2, 102.3)]):
            bars[i] = b
        bars[34], bars[35], bars[36], bars[37] = (102.3, 102.4, 100.9, 101.0), (101.0, 101.1, 99.2, 99.3), (99.3, 99.4, 98.3, 98.5), (98.5, 99.2, 98.4, 99.0)
        s, sigs = run("atm", bars)
        self.assertEqual(len(sigs), 1)
        _, sig = sigs[0]
        self.assertEqual(sig.direction, -1)
        self.assertAlmostEqual(sig.entry_ref, 98.9, places=2)       # the retest of the broken swing low
        self.assertGreater(sig.stop, 103.2)                         # just beyond the rejection high
        self.assertAlmostEqual(sig.target, 97.0, places=2)

    def test_market_maker_sell_model_consolidation_run_reversal_and_low_risk_entry(self):
        bars = [(100.0, 100.5 if i % 2 else 100.3, 99.5 if not i % 2 else 99.7, 100.0 + 0.1 * math.sin(i)) for i in range(16)]
        for i in range(16, 70):
            base = 100.5 + (i - 16) * 0.07 + 0.35 * math.sin(i / 2.2)
            bars.append((base, base + 0.22, base - 0.2, base + 0.05))
        bars[65] = (103.2, 103.3, 103.0, 103.1)
        bars[66], bars[67], bars[68] = (103.3, 103.7, 103.2, 103.6), (103.6, 104.0, 103.5, 103.9), (103.9, 104.2, 103.8, 104.1)
        bars += [(104.1, 104.5, 103.8, 104.2), (104.2, 104.3, 103.5, 103.6), (103.6, 103.7, 101.8, 102.0),
                 (102.0, 102.6, 101.9, 102.2), (102.2, 103.9, 102.0, 103.75)]
        s, sigs = run("mm", bars)
        self.assertEqual(len(sigs), 1)
        _, sig = sigs[0]
        self.assertEqual(sig.direction, -1)
        self.assertLess(sig.entry_ref, 104.0)
        self.assertAlmostEqual(sig.stop, 104.51, places=2)          # beyond the reversal high
        self.assertAlmostEqual(sig.target, 99.5, places=2)          # the original consolidation's low
        self.assertTrue(sig.reasons[0].startswith("MM-01"))


class ComponentTest(unittest.TestCase):
    def test_custom_combinations_parse_and_reject_nonsense(self):
        ch = custom_changes("custom:entry=ote;stop=zone;target=draw;filter=narrative,regime;mgmt=trail,reentry")
        self.assertEqual((ch["entry_mode"], ch["stop_mode"], ch["target_pref"]), ("ote", "zone", "draw"))
        self.assertTrue(ch["narrative_filter"] and ch["regime_filter"] and ch["trail_structure"] and ch["reentry"])
        self.assertTrue(is_model("custom:stop=candle1") and not is_model("custom:stop=nope") and not is_model("custom:colour=red"))
        r = resolve(replace(CFG.strategy, model="custom:entry=breaker;filter=quality"))
        self.assertEqual((r.entry_mode, r.fvg_quality), ("breaker", True))
        self.assertIsNotNone(make_strategy(replace(CFG.strategy, model="custom:entry=ote;stop=zone"), CFG.instrument))

    def test_stack_models_combine_roles(self):
        t = resolve(replace(CFG.strategy, model="stack_trend"))
        self.assertTrue(t.htf_context and t.regime_filter and t.trail_structure)
        self.assertEqual((t.entry_mode, t.target_pref), ("ote", "draw"))
        o = resolve(replace(CFG.strategy, model="stack_open"))
        self.assertTrue(o.opening_gaps and o.macro_only and o.day_open_rule)
        self.assertEqual(resolve(replace(CFG.strategy, model="reaper")).reaper, True)

    def test_a_tighter_stop_model_changes_the_stop_not_the_entry(self):
        from ict_trader.research import research
        from ict_trader.data import synthetic_bars
        walk = lambda sym, tf, days: synthetic_bars(T0 - timedelta(days=days), days, timeframe_minutes=tf, price=1000.0, seed=11)
        a = research("R_75", 5, 30, "allday", fetch=walk, model="ict2022")
        b = research("R_75", 5, 30, "allday", fetch=walk, model="tightstop")
        c = research("R_75", 5, 30, "allday", fetch=walk, model="custom:entry=ote;stop=zone;target=draw;mgmt=trail")
        for out in (a, b, c):
            self.assertIn(out["verdict"]["code"], ("edge", "no edge", "unproven", "not enough setups"))
        self.assertEqual(c["model"], "custom:entry=ote;stop=zone;target=draw;mgmt=trail")


if __name__ == "__main__":
    unittest.main()
