import unittest
from datetime import datetime, time, timedelta, timezone

from ict_trader.backtest import Backtester
from ict_trader.config import InstrumentConfig, StrategyConfig, Window
from ict_trader.models import make_strategy
from ict_trader.sessions import Bar, Level
from ict_trader.strategy import LONG, SHORT

T0 = datetime(2026, 10, 14, 7, 0, tzinfo=timezone.utc)


def make_bar(i: int, o: float, h: float, l: float, c: float) -> Bar:
    return Bar(T0 + timedelta(minutes=i * 5), o, h, l, c, 100)


class InstitutionalStrategyTest(unittest.TestCase):
    def setUp(self):
        self.strat_cfg = StrategyConfig(
            model="institutional",
            killzones=(Window("london", time(2, 0), time(12, 0)),),
            reference_ranges=(),
            min_sweep_pips=1.0,
            stop_buffer_pips=1.0,
            min_stop_pips=2.0,
            max_stop_pips=50.0,
            min_rr=1.5,
            mss_max_bars=10,
            entry_expiry_bars=10,
            displacement_body_mult=1.0,
            timeframe_minutes=5,
        )
        self.inst_cfg = InstrumentConfig(symbol="EURUSD", pip_size=0.0001)

    def test_factory_creates_institutional_strategy(self):
        strat = make_strategy(self.strat_cfg, self.inst_cfg)
        self.assertEqual(strat.__class__.__name__, "ICTInstitutionalStrategy")

    def test_full_institutional_lifecycle(self):
        strat = make_strategy(self.strat_cfg, self.inst_cfg)
        from ict_trader.sessions import trading_day
        strat._tracker.day = trading_day(T0, self.strat_cfg.day_rollover)
        strat._tracker._prior_high = 1.1050
        strat._tracker._prior_low = 1.0950

        # Bar 0: Inside London, sweeps PDH 1.1050 up to 1.1058
        b0 = make_bar(0, 1.1045, 1.1058, 1.1042, 1.1055)
        sig0 = strat.on_bar(b0)
        self.assertIsNone(sig0)
        self.assertEqual(len(strat._setups), 1)
        self.assertEqual(strat._setups[0].stage, "await_mss")

        # Bar 1: Creates swing low at 1.1040
        b1 = make_bar(1, 1.1055, 1.1056, 1.1040, 1.1048)
        strat.on_bar(b1)

        # Bar 2: Small pull up to 1.1052
        b2 = make_bar(2, 1.1048, 1.1052, 1.1046, 1.1050)
        strat.on_bar(b2)

        # Bar 3: Large displacement down closing below 1.1040 (closes at 1.1025)
        # Leaves an FVG / OB between Bar 2 and Bar 3
        b3 = make_bar(3, 1.1050, 1.1051, 1.1022, 1.1025)
        sig3 = strat.on_bar(b3)
        self.assertIsNone(sig3)
        # Setup should now be staged as a limit order
        self.assertEqual(len(strat.staged), 1)
        staged_limit = strat.staged[0]["limit"]
        self.assertTrue(staged_limit > 1.1025)

        # Bar 4: Price retraces back UP into the staged limit level, filling the order
        b4 = make_bar(4, 1.1025, staged_limit + 0.0002, 1.1024, staged_limit - 0.0001)
        sig4 = strat.on_bar(b4)
        self.assertIsNotNone(sig4)
        assert sig4 is not None
        self.assertEqual(sig4.direction, SHORT)
        self.assertEqual(sig4.entry_type, "limit")
        self.assertEqual(sig4.entry_ref, staged_limit)
        self.assertTrue(any("PD-01" in r or "OTE-01" in r for r in sig4.reasons))
        self.assertTrue(any("PO3-01" in r for r in sig4.reasons))

    def test_backtester_runs_on_institutional_model(self):
        from ict_trader.config import Config, RiskConfig
        from ict_trader.data import synthetic_bars
        cfg = Config(
            strategy=self.strat_cfg,
            instrument=self.inst_cfg,
            risk=RiskConfig(),
        )
        bars = synthetic_bars(T0 - timedelta(days=5), days=5, timeframe_minutes=5, seed=42)
        bt = Backtester(cfg)
        res = bt.run(bars)
        self.assertIsInstance(res.trades, list)
        self.assertIsInstance(res.equity_curve, list)


if __name__ == "__main__":
    unittest.main()
