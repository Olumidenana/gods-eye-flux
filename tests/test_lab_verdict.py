"""The Research lab says how sure it is, even below 30 trades, and the block models are not strangled by gates meant for others."""
import math
import random
import unittest
from dataclasses import replace
from datetime import datetime, timedelta, timezone

from ict_trader.config import load_config
from ict_trader.metrics import summarize, t_crit95
from ict_trader.models import PATTERN_MODELS, resolve
from ict_trader.research import research
from ict_trader.sessions import Bar

CFG = load_config("examples/config.example.toml")


def fake(symbol, tf, days):
    r = random.Random(11)
    p, t = 1000.0, datetime(2026, 8, 1, tzinfo=timezone.utc)
    out = []
    for i in range(days * 24 * 60 // tf):
        o = p
        c = o + r.gauss(0, 0.7)
        out.append(Bar(t + timedelta(minutes=tf * i), round(o, 2), round(max(o, c) + abs(r.gauss(0, 0.3)), 2), round(min(o, c) - abs(r.gauss(0, 0.3)), 2), round(c, 2)))
        p = c
    return out


class SureNessTest(unittest.TestCase):
    def test_small_samples_get_a_wide_student_t_range_and_a_trades_needed_figure(self):
        self.assertEqual((t_crit95(1), t_crit95(3), t_crit95(29), t_crit95(500)), (12.71, 3.18, 2.04, 1.96))

        class T:   # the bits of a trade that summarize reads
            def __init__(self, r):
                self.r_multiple, self.pnl, self.exit_reason = r, r * 100, "TP"
        rs = [2.0, -1.0, -1.0, 2.0, -1.0, 2.0, -1.0, -1.0]
        st = summarize([T(r) for r in rs], [(datetime(2026, 1, 1, tzinfo=timezone.utc), 10_000.0)], 10_000.0)
        mean = sum(rs) / len(rs)
        sd = math.sqrt(sum((r - mean) ** 2 for r in rs) / (len(rs) - 1))
        lo, hi = st["expectancy_ci95"]
        self.assertAlmostEqual(hi - lo, 2 * t_crit95(7) * sd / math.sqrt(len(rs)), places=6)
        self.assertEqual(st["trades_needed"], math.ceil((2 * sd / mean) ** 2) if mean > 0 else None)
        self.assertFalse(st["statistically_meaningful"])      # 8 trades: never judged

    def test_the_lab_says_so_far_how_wide_the_luck_range_is_and_what_would_settle_it(self):
        r = research("R_75", 5, 40, "allday", fetch=fake, model="nonarrative")   # the control: the narrative-gated model may have no trades at all here
        v = r["verdict"]
        self.assertEqual(v["code"] if isinstance(v, dict) else v[0], "not enough setups")
        text = v["text"] if isinstance(v, dict) else v[1]
        for part in ("Thirty trades is the least", "luck alone could put the true figure anywhere from", "pool more markets"):
            self.assertIn(part, text)
        self.assertIn("expectancy_ci95", r["stats"])


class BlockWiringTest(unittest.TestCase):
    def test_zone_blocks_aim_at_old_highs_and_lows_and_the_live_pattern_models_are_unchanged(self):
        for k in ("mitigation", "rejection", "propulsion", "suspension", "vimb", "vacuum"):
            self.assertTrue(resolve(replace(CFG.strategy, model=k, liquidity_pools=False)).liquidity_pools, k)
        for k in ("venom", "atm", "mm"):
            self.assertFalse(resolve(replace(CFG.strategy, model=k, liquidity_pools=False)).liquidity_pools, k)
        self.assertTrue(set(("mitigation", "venom")) <= set(PATTERN_MODELS))

    def test_a_block_with_a_small_stop_trades_instead_of_dying_at_the_stop_gate(self):
        r = research("R_75", 5, 40, "allday", fetch=fake, model="mitigation")
        self.assertGreater(r["stats"]["trades"], 10)       # was 1 of 306 detected blocks before the stop was widened to the market's minimum


if __name__ == "__main__":
    unittest.main()
