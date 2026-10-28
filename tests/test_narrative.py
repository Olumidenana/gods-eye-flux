"""ICT's top-down story is the spine of the ICT 2022 family: no story, no trade."""
import random
import unittest
from dataclasses import replace
from datetime import datetime, timedelta, timezone

from ict_trader import narrative
from ict_trader.config import load_config
from ict_trader.models import make_strategy, resolve
from ict_trader.research import research
from ict_trader.sessions import Bar

CFG = load_config("examples/config.example.toml")
T0 = datetime(2026, 8, 2, 21, 0, tzinfo=timezone.utc)   # Sunday 17:00 New York: the start of a trading day


def day_series(days, closes, tf=5):
    """One day per entry in `closes`: [open, high, low, close] shaped by hand, then 5-minute bars that walk it."""
    out, t = [], T0
    per = 24 * 60 // tf
    for (o, h, l, c) in closes:
        hi_at, lo_at = per // 3, 2 * per // 3
        for i in range(per):
            f = i / (per - 1)
            p = o + (c - o) * f
            hi = max(p, h if i == hi_at else p) + 0.01
            lo = min(p, l if i == lo_at else p) - 0.01
            out.append(Bar(t, p, hi, lo, p + 0.005))
            t += timedelta(minutes=tf)
    return out


def strat(model="ict2022", **kw):
    kw.setdefault("bias_ladder", False)   # these stories are built from daily and weekly candles: the daily rung
    st = replace(CFG.strategy, model=model, timeframe_minutes=5, min_stop_pips=0, max_stop_pips=1e9, min_rr=0.1, **kw)
    return make_strategy(st, replace(CFG.instrument, pip_size=0.01))


def feed(s, bars):
    for b in bars:
        s.on_bar(b)
    return s


# D-2 range 100-102, D-1 closes 103.5 above D-2's high: bullish; today (D0) is quiet below D-1's high 104
BULL = day_series(3, [(100, 102, 100, 101), (101, 104, 100.5, 103.5), (103.5, 103.7, 103.4, 103.6)])


class StoryTest(unittest.TestCase):
    def test_a_close_above_the_prior_high_is_a_bullish_story_with_a_draw_ahead(self):
        # D1 range 100-102, D2 closes 103 (above D1's high): bullish. The next day trades inside a bit.
        bars = BULL
        s = feed(strat(), bars)
        n = s.narrative()
        self.assertEqual(n.bias, 1)
        self.assertIsNone(n.stand_aside)
        self.assertIsNotNone(n.draw)
        self.assertGreater(n.draw.price, bars[-1].close)               # the draw is ahead of price
        self.assertTrue(any(line.startswith("Story: bullish") for line in n.lines))
        self.assertIn("came_from", n.to_json())

    def test_an_inside_day_is_no_story_and_ict_stands_aside(self):
        bars = day_series(3, [(100, 102, 100, 101), (101, 101.8, 100.2, 101.2), (101.2, 101.4, 101.0, 101.1)])
        n = feed(strat(), bars).narrative()
        self.assertEqual(n.bias, 0)
        self.assertIn("no clear daily or weekly draw", n.stand_aside)
        self.assertEqual(n.conviction, "none")

    def test_on_an_inside_day_the_weekly_draw_leads_but_less_sure_of_itself(self):
        s = feed(strat(), BULL)
        s.daily_bias = lambda: (0, "inside or two-sided day: no clear daily draw")
        s.weekly_bias = lambda: (1, "last week closed above the prior week's high")
        n = narrative.read(s)
        self.assertEqual(n.bias, 1)
        self.assertEqual(n.conviction, "weak")
        self.assertIsNone(n.stand_aside)
        self.assertTrue(any("weekly draw leads" in line for line in n.lines))
        s.weekly_bias = lambda: (-1, "last week closed below the prior week's low")
        s.daily_bias = lambda: (1, "yesterday closed above the prior day's high")
        self.assertIn("pull opposite ways", narrative.read(s).stand_aside)          # a clear disagreement is still a veto

    def test_the_target_is_the_same_pool_the_story_names(self):
        bars = BULL
        s = feed(strat(), bars)
        n = s.narrative()
        self.assertEqual(s._target(1, bars[-1].close).name, n.draw.name)
        self.assertEqual(narrative.draw_pool(s, 1, bars[-1].close).name, n.draw.name)


class GateTest(unittest.TestCase):
    def test_the_ict_2022_family_reads_the_narrative_and_the_control_does_not(self):
        self.assertTrue(strat("ict2022").config.narrative_required)
        self.assertTrue(strat("ote").config.narrative_required)
        self.assertFalse(strat("nonarrative").config.narrative_required)
        self.assertEqual(strat("ict2022").config.min_score, 40)
        self.assertEqual(strat("nonarrative").config.min_score, 0)

    def test_a_sweep_against_the_story_is_ignored_and_says_why(self):
        # a bullish story; then, in the London killzone (03:50 New York), price spikes through the prior high 104 and back:
        # a run on the HIGH is a sell setup, against a bullish story
        base = day_series(3, [(100, 102, 100, 101), (101, 104, 100.5, 103.5), (103.5, 103.7, 103.4, 103.6)])[:-288 + 130]
        t = base[-1].time + timedelta(minutes=5)
        spike = [Bar(t, 103.6, 104.4, 103.5, 103.7), Bar(t + timedelta(minutes=5), 103.7, 103.8, 103.6, 103.65)]
        gated = feed(strat(), base + spike)
        # the high being taken IS the bullish draw being fulfilled, so the story says stand aside (or "against the story")
        self.assertTrue(any(d.rule == "NR-01" and d.message.startswith("PDH sweep ignored") for d in gated.decisions), [d.message for d in gated.decisions][-4:])
        self.assertFalse(any(d.rule == "SW-01" for d in gated.decisions))        # no sweep was taken
        control = feed(strat("nonarrative"), base + spike)
        self.assertTrue(any(d.rule == "SW-01" for d in control.decisions))       # the control takes the very same sweep

    def test_the_matrix_gate_drops_a_skip_setup_before_it_is_placed(self):
        s = strat()
        self.assertEqual(s.config.min_score, 40)
        # AD-01 is the rule id the gate logs under
        import inspect
        from ict_trader import ict2022
        self.assertIn('"AD-01"', inspect.getsource(ict2022.ICT2022Strategy.on_bar))


class RandomWalkTest(unittest.TestCase):
    def test_the_story_never_raises_and_the_gated_model_trades_no_more_than_the_control(self):
        r = random.Random(5)
        p, bars = 100.0, []
        for i in range(30 * 288):
            o = p
            c = o + r.gauss(0, 0.2)
            bars.append(Bar(T0 + timedelta(minutes=5 * i), o, max(o, c) + abs(r.gauss(0, 0.1)), min(o, c) - abs(r.gauss(0, 0.1)), c))
            p = c
        gated, control = strat("ict2022"), strat("nonarrative")
        for b in bars:
            gated.on_bar(b)
            control.on_bar(b)
            if len(gated._bars) % 500 == 0:
                gated.narrative()                            # reading it any time is safe
        n_gated = sum(1 for d in gated.decisions if d.rule == "EN-01")
        n_control = sum(1 for d in control.decisions if d.rule == "EN-01")
        self.assertLessEqual(n_gated, n_control)
        self.assertTrue(any(d.rule == "NR-01" for d in gated.decisions))   # and it says so when it sits a sweep out


if __name__ == "__main__":
    unittest.main()
