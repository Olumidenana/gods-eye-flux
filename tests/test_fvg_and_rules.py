import os
import unittest
from datetime import datetime, time, timedelta, timezone

from ict_trader.config import Config, InstrumentConfig, StrategyConfig, RiskConfig, Window, load_config
from ict_trader.risk import RiskManager, lots_for_risk
from ict_trader.sessions import Bar, utc
from ict_trader.strategy import LONG, SHORT, TimeAndPriceStrategy

from tests.helpers import ny_bar, pdh_sweep, prior_day, quiet_open, simple_config

ROOT = os.path.dirname(os.path.dirname(__file__))


class DynamicRiskReductionTests(unittest.TestCase):
    def test_dynamic_risk_reduction_schedule(self):
        # Base risk 1.0%, daily floor 5%, weekly floor 10%
        cfg = RiskConfig(
            risk_per_trade_pct=1.0,
            enable_dynamic_risk_reduction=True,
            max_consecutive_losses=3,  # RK-05 would halt after 2; this test walks the RK-02 tiers
            loss_recovery_threshold_pct=50.0,
        )
        rm = RiskManager(cfg, 10000.0, time(17))

        # First trade: full 1.0% risk ($100)
        dec = rm.check(open_positions=0)
        self.assertTrue(dec.allowed)
        self.assertAlmostEqual(dec.risk_amount, 100.0)

        # 1 loss: PnL = -$100 (equity = 9900) -> cuts risk to 50% of base (0.50% = $49.50)
        rm.mark(utc(2026, 6, 3, 10, 0), 9900.0)
        rm.record_close(-100.0)
        dec2 = rm.check(open_positions=0)
        self.assertTrue(dec2.allowed)
        self.assertIn("50% risk reduction after 1 loss", dec2.reason)
        self.assertAlmostEqual(dec2.risk_amount, 9900.0 * 0.005)

        # 2nd loss: PnL = -$50 (equity = 9850) -> cuts risk to 25% of base (0.25% = $24.625)
        rm.mark(utc(2026, 6, 3, 11, 0), 9850.0)
        rm.record_close(-50.0)
        dec3 = rm.check(open_positions=0)
        self.assertTrue(dec3.allowed)
        self.assertIn("75% risk reduction after 2+ losses", dec3.reason)
        self.assertAlmostEqual(dec3.risk_amount, 9850.0 * 0.0025)

        # Drawdown is from 10000 to 9850 ($150 drawdown).
        # Win of $80 (equity reaches 9930): recovered $80 / $150 = 53.3% (>50% recovery threshold)
        # Should restore base risk!
        rm.mark(utc(2026, 6, 3, 14, 0), 9930.0)
        rm.record_close(80.0)
        self.assertFalse(rm.is_in_reduced_risk)
        self.assertEqual(rm.consecutive_losses, 0)
        dec4 = rm.check(open_positions=0)
        self.assertAlmostEqual(dec4.risk_amount, 9930.0 * 0.01)


class SmallAccountSizingTests(unittest.TestCase):
    def test_small_account_micro_lot_floor(self):
        # On a $10 account with GBPUSD (value per unit per lot = 100,000):
        # 10 pip stop = 0.0010 stop distance.
        # 1% risk of $10 is $0.10.
        # Raw lots = 0.10 / (0.0010 * 100,000) = 0.001 lots < min_lots 0.01.
        # In standard institutional mode, it returns 0.0 (skipped):
        lots_std = lots_for_risk(0.10, 0.0010, 100000, 0.01, 0.01, 5.0, small_account_mode=False)
        self.assertEqual(lots_std, 0.0)

        # In small_account_mode, it permits min_lots (0.01) floor so the trader can trade:
        lots_small = lots_for_risk(0.10, 0.0010, 100000, 0.01, 0.01, 5.0, small_account_mode=True)
        self.assertEqual(lots_small, 0.01)

    def test_milestone_compounding_tiers(self):
        milestones = (
            (10.0, 0.01),
            (25.0, 0.01),
            (50.0, 0.02),
            (100.0, 0.03),
            (200.0, 0.05),
        )
        # At $20 equity -> 0.01 lot
        self.assertEqual(lots_for_risk(1.0, 0.0010, 100000, 0.01, 0.01, 5.0, small_account_mode=True, compounding_milestones=milestones, equity=20.0), 0.01)
        # At $55 equity -> 0.02 lot
        self.assertEqual(lots_for_risk(1.0, 0.0010, 100000, 0.01, 0.01, 5.0, small_account_mode=True, compounding_milestones=milestones, equity=55.0), 0.02)
        # At $120 equity -> 0.03 lot
        self.assertEqual(lots_for_risk(1.0, 0.0010, 100000, 0.01, 0.01, 5.0, small_account_mode=True, compounding_milestones=milestones, equity=120.0), 0.03)
        # At $250 equity -> 0.05 lot
        self.assertEqual(lots_for_risk(1.0, 0.0010, 100000, 0.01, 0.01, 5.0, small_account_mode=True, compounding_milestones=milestones, equity=250.0), 0.05)


class LiquidityPurgeOrderTests(unittest.TestCase):
    def test_enforce_purge_order_rejects_short_if_ssl_swept_first(self):
        cfg = simple_config(enforce_liquidity_purge_order=True)
        strat = TimeAndPriceStrategy(cfg.strategy, cfg.instrument)

        # Prior day levels: PDH = 1.1050, PDL = 1.1000
        for b in prior_day() + quiet_open():
            strat.on_bar(b)

        # Outside or early bar sweeps PDL (SSL) first!
        ssl_sweep_bar = ny_bar("2026-06-03 01:30", 1.1005, 1.1008, 1.0990, 1.1002)
        strat.on_bar(ssl_sweep_bar)

        # Later in London killzone, price sweeps PDH (BSL)
        bsl_sweep_bar = pdh_sweep()
        sig = strat.on_bar(bsl_sweep_bar)

        # Short setup must be rejected under SW-02 because SSL was purged before BSL
        self.assertIsNone(sig)
        self.assertTrue(any(d.rule == "SW-02" and "SSL was purged before BSL" in d.message for d in strat.decisions))


class FVGAndDisplacementTests(unittest.TestCase):
    def test_require_fvg_rejects_trade_when_no_fvg(self):
        cfg = simple_config(require_fvg=True)
        strat = TimeAndPriceStrategy(cfg.strategy, cfg.instrument)

        # Standard bars where candles overlap tightly (no gap)
        for b in prior_day() + quiet_open():
            strat.on_bar(b)

        # Single bar sweep and close back inside without 3-candle imbalance
        sig = strat.on_bar(pdh_sweep())
        self.assertIsNone(sig)
        self.assertTrue(any(d.rule == "FV-01" and "no 3-candle FVG" in d.message for d in strat.decisions))

    def test_fvg_detected_and_signal_produced(self):
        cfg = simple_config(require_fvg=True, fvg_in_premium_discount=False)
        strat = TimeAndPriceStrategy(cfg.strategy, cfg.instrument)

        for b in prior_day() + quiet_open():
            strat.on_bar(b)

        # Create a 3-candle sequence with an FVG:
        # Candle 0 (02:55): Low = 1.1050
        b0 = ny_bar("2026-06-03 02:55", 1.1052, 1.1055, 1.1050, 1.1053)
        # Candle 1 (03:00): Sweeps PDH (1.1050), High = 1.1057, Low = 1.1048
        b1 = ny_bar("2026-06-03 03:00", 1.1053, 1.1057, 1.1048, 1.1050)
        # Candle 2 (03:05): Displaces down, High = 1.1044, Close = 1.1042 (< PDH 1.1050)
        # Gap between b0.low (1.1050) and b2.high (1.1044) is 6 pips!
        b2 = ny_bar("2026-06-03 03:05", 1.1048, 1.1044, 1.1040, 1.1042)

        strat.on_bar(b0)
        strat.on_bar(b1)
        sig = strat.on_bar(b2)

        self.assertIsNotNone(sig)
        self.assertEqual(sig.direction, SHORT)
        self.assertTrue(any(r.startswith("FV-01") for r in sig.reasons))


class SilverBulletAndSmallAccountRRTests(unittest.TestCase):
    def test_silver_bullet_window_filtering(self):
        cfg = simple_config(enable_silver_bullet=True)
        strat = TimeAndPriceStrategy(cfg.strategy, cfg.instrument)

        for b in prior_day() + quiet_open():
            strat.on_bar(b)

        # Bar at 02:30 NY (inside standard London KZ, but OUTSIDE London Silver Bullet 03:00-04:00, does not sweep)
        outside_sb = ny_bar("2026-06-03 02:30", 1.1030, 1.1040, 1.1025, 1.1035)
        sig = strat.on_bar(outside_sb)
        self.assertIsNone(sig)

        # Bar at 03:05 NY (inside London Silver Bullet 03:00-04:00, sweeps PDH 1.1050)
        inside_sb = ny_bar("2026-06-03 03:05", 1.1040, 1.1056, 1.1038, 1.1045)
        sig2 = strat.on_bar(inside_sb)
        self.assertIsNotNone(sig2)
        self.assertEqual(sig2.killzone, "london_sb")
        self.assertTrue(any(r.startswith("SB-01") for r in sig2.reasons))

    def test_small_account_min_rr_filter(self):
        # Setup offering 2.0R
        cfg = simple_config(small_account_mode=True, small_account_min_rr=3.0, target_mode="rr", target_rr=2.0)
        strat = TimeAndPriceStrategy(cfg.strategy, cfg.instrument)

        for b in prior_day() + quiet_open():
            strat.on_bar(b)

        # 2.0R setup rejected under SA-03
        sig = strat.on_bar(pdh_sweep())
        self.assertIsNone(sig)
        self.assertTrue(any(d.rule == "SA-03" and "below minimum 3.0" in d.message for d in strat.decisions))


class ExampleConfigValidationTests(unittest.TestCase):
    def test_all_example_configs_load(self):
        configs = ["gbpusd.toml", "xauusd.toml", "small_account.toml", "cent_account.toml"]
        for name in configs:
            path = os.path.join(ROOT, "examples", name)
            self.assertTrue(os.path.exists(path), f"Missing {path}")
            cfg = load_config(path)
            self.assertIsNotNone(cfg.instrument.symbol)
            self.assertGreater(cfg.initial_equity, 0)


if __name__ == "__main__":
    unittest.main()
