"""The noise canary: on random prices (no edge by construction) a disciplined engine takes almost no trades.

A rule that was loosened without evidence shows up here first. On 40 days of random-walk candles the ICT 2022 family (which builds the
story first and trades only a raid that fits it) took ZERO trades in every series, as ICT's own approach would: no story, no trade. When
its gates had been switched off (the narrative, premium / discount, the gap's half of the leg, the higher-timeframe arrays), the same
models took 20 to 70 trades each on the same random data, with targets averaging 7R. If this test fails after you loosen a rule, do not raise
the limits: show, on real candles and out of sample, that the loosened rule wins more than it costs (docs/ENGINE.md, "Changing the engine").
"""
import os
import unittest
from datetime import datetime, timedelta, timezone
from unittest import mock

from ict_trader import scanner
from ict_trader.data import synthetic_bars
from ict_trader.models import LIVE_MODELS

NOW = datetime(2026, 6, 10, 15, 0, tzinfo=timezone.utc)
MARKETS = ((scanner.Market("NZDCAD", "NZD/CAD", "FAKE", "t", "", 5, "NZD_CAD", "forex"), 1.1),
           (scanner.Market("R_100", "Volatility 100", "FAKE", "t", "", 2, "R_100", "synthetic"), 100.0))
SEEDS = (3, 5, 11)
SPINE = ("ict2022", "ote", "full", "stack_trend", "judas_swing", "silver_bullet")   # the models that read the whole story
LIMIT = {"spine": 4, "sweep": 14}   # trades over all the series; measured on this data: 0 for the spine, 8 for Turtle Soup


def trades(model: str) -> int:
    n = 0
    with mock.patch.dict(os.environ, {"SIGNAL_MODEL": model}):
        for seed in SEEDS:
            for m, price in MARKETS:
                f = lambda t, r, s=seed, p=price: synthetic_bars(NOW - timedelta(days=40), 41, price=p, seed=s)   # noqa: E731
                out = scanner.scan_market(m, f, NOW, "history")
                n += sum(1 for s in out.get("recent", []) if s["outcome"]["status"] not in ("not_taken", "open"))
    return n


class NoiseCanaryTest(unittest.TestCase):
    def test_the_story_models_take_no_trades_on_random_prices(self):
        for model in SPINE:
            if model in LIVE_MODELS:
                self.assertLessEqual(trades(model), LIMIT["spine"], f"{model} trades noise: a rule was loosened without evidence")

    def test_turtle_soup_needs_a_daily_draw_and_so_trades_noise_rarely(self):
        self.assertLessEqual(trades("sweep"), LIMIT["sweep"])

    def test_models_without_a_measured_edge_are_not_live(self):
        for model in ("venom", "atm", "mm"):
            self.assertNotIn(model, LIVE_MODELS)


if __name__ == "__main__":
    unittest.main()
