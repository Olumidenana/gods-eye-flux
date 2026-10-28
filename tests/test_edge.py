"""The edge pipeline must find an edge that is really there and decline when there is none; the engine itself is not touched by it."""
import random
import unittest
from datetime import datetime, timedelta, timezone

from ict_trader.data import synthetic_bars
from ict_trader.edge import features, sizing, synthetic, validate
from ict_trader.edge.candidates import Candidate, extract, outcome
from ict_trader.edge.model import MIN_TRAIN, EdgeModel, NotEnoughData
from ict_trader.edge.monitor import DriftMonitor
from ict_trader.edge.stats import cluster_bootstrap_mean, fit_logistic, logit, predict_interval, sigmoid
from ict_trader.sessions import Bar

T0 = datetime(2026, 1, 5, 12, 0, tzinfo=timezone.utc)


def bar(i: int, o: float, h: float, l: float, c: float) -> Bar:  # noqa: E741
    return Bar(T0 + timedelta(minutes=5 * i), o, h, l, c)


class StatsTest(unittest.TestCase):
    def test_the_fit_recovers_planted_coefficients(self):
        rnd = random.Random(3)
        rows = [[1.0 if rnd.random() < 0.5 else 0.0, rnd.random()] for _ in range(4000)]
        y = [1 if rnd.random() < sigmoid(-0.3 + 1.2 * r[0] - 0.8 * r[1]) else 0 for r in rows]
        coef, _ = fit_logistic(rows, y, ridge=1.0)
        self.assertAlmostEqual(coef[1], 1.2, delta=0.2)
        self.assertAlmostEqual(coef[2], -0.8, delta=0.3)

    def test_a_coefficient_with_the_wrong_sign_is_held_at_zero(self):
        rnd = random.Random(4)
        rows = [[1.0 if rnd.random() < 0.5 else 0.0] for _ in range(1500)]
        y = [1 if rnd.random() < sigmoid(-1.0 * r[0]) else 0 for r in rows]   # the data say "lowers the chance"
        coef, cov = fit_logistic(rows, y, ridge=1.0, signs=[1])               # ICT says "raises it"
        self.assertEqual(coef[1], 0.0)
        self.assertEqual(cov[1][1], 0.0)

    def test_the_offset_is_the_random_walk_baseline(self):
        # with no features and the baseline offset, the fitted chance is 1 / (1 + T) when the data are a random walk
        rnd = random.Random(5)
        t = 2.0
        y = [1 if rnd.random() < 1 / (1 + t) else 0 for _ in range(3000)]
        coef, cov = fit_logistic([[0.0] for _ in y], y, offset=logit(1 / (1 + t)), ridge=1.0)
        p, lo = predict_interval(coef, cov, [0.0], offset=logit(1 / (1 + t)))
        self.assertAlmostEqual(p, 1 / 3, delta=0.03)
        self.assertLess(lo, p)

    def test_the_bootstrap_resamples_days_not_trades(self):
        vals = [1.0] * 10 + [-1.0] * 10
        mean, lo, hi = cluster_bootstrap_mean(vals, ["a"] * 10 + ["b"] * 10, reps=300)
        self.assertEqual(mean, 0.0)
        self.assertLessEqual(lo, -1.0 + 1e-9)    # two days: the whole of either can drop out
        self.assertGreaterEqual(hi, 1.0 - 1e-9)


class OutcomeTest(unittest.TestCase):
    def test_furthest_excursion_before_the_stop(self):
        bars = [bar(0, 1.0, 1.0, 1.0, 1.0), bar(1, 1.0, 1.003, 0.9995, 1.002), bar(2, 1.002, 1.0045, 1.001, 1.004), bar(3, 1.004, 1.0041, 0.998, 0.998)]
        mfe, stopped = outcome(bars, 0, 1, 1.0, 0.001, 10)   # a buy at 1.0000 risking 10 pips: the third bar ran 45 pips, then the fourth stopped it
        self.assertAlmostEqual(mfe, 4.5)
        self.assertTrue(stopped)

    def test_a_bar_that_touches_both_is_a_stop(self):
        bars = [bar(0, 1.0, 1.0, 1.0, 1.0), bar(1, 1.0, 1.01, 0.998, 1.0)]
        mfe, stopped = outcome(bars, 0, 1, 1.0, 0.001, 10)
        self.assertEqual(mfe, 0.0)
        self.assertTrue(stopped)

    def test_a_sell_measures_down(self):
        bars = [bar(0, 1.0, 1.0, 1.0, 1.0), bar(1, 1.0, 1.0005, 0.997, 0.998)]
        mfe, stopped = outcome(bars, 0, -1, 1.0, 0.001, 10)
        self.assertAlmostEqual(mfe, 3.0)
        self.assertFalse(stopped)

    def test_results_in_r(self):
        c = Candidate("X", T0, 1, 1.0, 0.999, 0.001, 2.0, 0.05, 2.4, False, [])
        self.assertEqual(c.hit(2.0), 1)
        self.assertEqual(c.hit(3.0), 0)
        self.assertAlmostEqual(c.result(2.0), 1.95)
        self.assertAlmostEqual(c.result(3.0), -1.05)


class FeaturesTest(unittest.TestCase):
    def test_a_row_is_always_the_same_width(self):
        self.assertEqual(len(features.vector({})), len(features.NAMES))
        self.assertEqual(len(features.vector({"dir": -1, "bias": -1, "pd": 0.4, "level": "PDH", "poi": {"state": "array"}, "htf_trend": {"1h": 1, "4h": -1}}, 8)), len(features.NAMES))

    def test_the_killzone_is_read_from_the_clock_and_never_on_a_synthetic_index(self):
        i = features.NAMES.index("in_window")
        self.assertEqual(features.vector({}, 8)[i], 1.0)
        self.assertEqual(features.vector({}, 13)[i], 0.0)
        self.assertEqual(features.vector({}, 8, clock=False)[i], 0.0)

    def test_each_feature_points_the_way_ict_teaches(self):
        s = dict(features.FEATURES)
        self.assertEqual(s["bias_with"], 1)
        self.assertEqual(s["bias_against"], -1)
        self.assertEqual(s["obstacles"], -1)
        self.assertEqual(s["pd_wrong"], -1)


class PowerTest(unittest.TestCase):
    """The test of the test: a planted edge is found, pure noise is not."""

    def test_a_planted_edge_is_found_out_of_sample(self):
        r = validate.validate(synthetic.table(n=1800, edge=0.8, seed=1))
        self.assertEqual(r.verdict, "EDGE", r.message)
        self.assertGreater(r.mean_r, 0.2)
        self.assertGreater(r.ci_low, 0.0)
        self.assertGreater(r.trades, 100)

    def test_noise_is_never_called_an_edge(self):
        for seed in range(1, 5):
            r = validate.validate(synthetic.table(n=1600, edge=0.0, seed=seed))
            self.assertNotEqual(r.verdict, "EDGE", f"seed {seed}: {r.message}")

    def test_even_a_permissive_model_loses_its_costs_on_noise(self):
        # margin 0 and no conservatism: it takes everything it likes, and on a random walk that is -costs, not a profit
        r = validate.validate(synthetic.table(n=2500, edge=0.0, seed=2), margin=0.0, z=0.0)
        self.assertNotEqual(r.verdict, "EDGE", r.message)
        self.assertLess(r.mean_r, 0.1)

    def test_it_will_not_conclude_from_a_few_trades(self):
        r = validate.validate(synthetic.table(n=300, edge=0.8, seed=1))
        self.assertIn(r.verdict, ("NOT ENOUGH DATA", "UNPROVEN"))
        self.assertNotEqual(r.verdict, "EDGE")

    def test_the_folds_never_look_ahead(self):
        cands = synthetic.table(n=1500, edge=0.5, seed=3)
        pairs, folds = validate.walk_forward(cands)
        first = min(c.month for c in cands)
        self.assertGreater(folds, 3)
        self.assertTrue(all(c.month > first for c, _ in pairs))

    def test_the_permutation_test_reports_how_often_chance_does_as_well(self):
        r = validate.validate(synthetic.table(n=1200, edge=0.8, seed=1), perms=3)
        self.assertIsNotNone(r.perm_p)
        self.assertGreater(r.perm_p, 0.0)
        self.assertLessEqual(r.perm_p, 1.0)

    def test_the_report_names_what_the_data_say_about_each_question(self):
        r = validate.validate(synthetic.table(n=1800, edge=0.8, seed=1))
        txt = validate.text(r)
        self.assertIn("EDGE", txt)
        self.assertGreater(r.coefficients["bias_with"][2.0], 0.1)     # planted
        self.assertLess(r.coefficients["bias_against"][2.0], -0.1)    # planted, and the right sign
        self.assertLessEqual(r.coefficients["raid_session"][2.0], 0.3)


class ModelTest(unittest.TestCase):
    def test_too_few_candidates_are_refused(self):
        with self.assertRaises(NotEnoughData):
            EdgeModel().fit(synthetic.table(n=MIN_TRAIN - 1))

    def test_chance_never_rises_with_the_target(self):
        cands = synthetic.table(n=800, edge=0.6, seed=2)
        m = EdgeModel().fit(cands)
        for c in cands[:50]:
            ps = [r[1] for r in m.curve(c)]
            self.assertEqual(ps, sorted(ps, reverse=True))

    def test_it_abstains_when_nothing_clears_the_costs(self):
        cands = synthetic.table(n=800, edge=0.0, seed=2)
        m = EdgeModel().fit(cands)
        taken = [c for c in cands if m.decide(c) is not None]
        self.assertLess(len(taken), 0.10 * len(cands))    # in-sample, so a few slip through; out of sample they lose (the test above)


class ExtractTest(unittest.TestCase):
    def test_random_prices_give_no_edge_through_the_whole_pipeline(self):
        bars = synthetic_bars(T0, 60, price=1.1, seed=3)
        cands = extract(bars, "TEST", "forex", 5, spread_pips=0.05)
        for c in cands:
            self.assertEqual(len(c.x), len(features.NAMES))
            self.assertGreaterEqual(c.mfe_r, 0.0)
            self.assertGreater(c.cost_r, 0.0)
            self.assertGreater(c.risk, 0.0)
        r = validate.validate(cands)
        self.assertNotEqual(r.verdict, "EDGE")

    def test_the_live_engine_is_unchanged_by_extraction(self):
        from ict_trader import scanner
        from ict_trader.config import StrategyConfig
        before = StrategyConfig().model
        extract(synthetic_bars(T0, 10, price=1.1, seed=3), "TEST", "forex", 5, spread_pips=0.05)
        self.assertEqual(StrategyConfig().model, before)
        self.assertTrue(hasattr(scanner, "scan_market"))


class SizingTest(unittest.TestCase):
    def test_no_edge_no_bet(self):
        self.assertEqual(sizing.kelly_fraction(1 / 3, 2.0, 0.0), 0.0)
        self.assertEqual(sizing.risk_fraction(0.30, 2.0, 0.05), 0.0)

    def test_kelly_from_the_lower_bound_and_the_cap(self):
        self.assertAlmostEqual(sizing.kelly_fraction(0.5, 2.0, 0.0), 0.25)       # edge 0.5 R on a 2R target
        self.assertAlmostEqual(sizing.risk_fraction(0.5, 2.0, 0.0, 0.25, 0.01), 0.01)   # a quarter of 0.25 is 6.25%: capped at 1%
        self.assertAlmostEqual(sizing.risk_fraction(0.36, 2.0, 0.0, 0.25, 0.05), 0.25 * (0.36 * 2 - 0.64) / 2)


class MonitorTest(unittest.TestCase):
    def test_a_model_that_does_what_it_said_stays_on(self):
        rnd = random.Random(8)
        mon = DriftMonitor()
        for _ in range(400):
            self.assertTrue(mon.record(0.5, rnd.random() < 0.5))
        self.assertFalse(mon.off)

    def test_a_model_that_stops_working_switches_itself_off(self):
        rnd = random.Random(9)
        mon = DriftMonitor()
        for _ in range(300):
            mon.record(0.5, rnd.random() < 0.25)   # it says 50%, the market gives 25%
        self.assertTrue(mon.off)
        self.assertTrue(mon.reason)
        self.assertFalse(mon.record(0.5, True))    # and it stays off: it never re-tunes itself


if __name__ == "__main__":
    unittest.main()
