from datetime import datetime, timedelta, timezone
import unittest

from ict_trader.autotrade import effective_risk_pct
from ict_trader.backtest import Backtester
from ict_trader.config import Config, InstrumentConfig, StrategyConfig
from ict_trader.ict2022 import ICT2022Strategy
from ict_trader.models import custom_changes
from ict_trader.opening import FirstPresentedStrategy
from ict_trader.pd_arrays import detect_bprs, scan_pd_arrays
from ict_trader.strategy import Bar, SHORT
from tests.helpers import ny_bar, simple_config


class EngineSalvationTest(unittest.TestCase):
    def test_first_presented_strategy_feeds_ladder_and_retains_seeded_days(self):
        cfg = Config(instrument=InstrumentConfig(symbol="NAS100", pip_size=0.1), strategy=StrategyConfig(timeframe_minutes=5))
        st = FirstPresentedStrategy(cfg.strategy, cfg.instrument)

        # Seed 35 daily candles before intraday session
        base = datetime(2026, 4, 1, 0, 0, tzinfo=timezone.utc)
        daily_bars = [
            Bar(
                time=base + timedelta(days=i),
                open=18000.0 + i * 10,
                high=18080.0 + i * 10,
                low=17950.0 + i * 10,
                close=18050.0 + i * 10,
            )
            for i in range(35)
        ]
        st.seed_days(daily_bars)
        self.assertEqual(len(st._days), 35)

        # Feed 40 hours of 5m bars so 4h ladder aggregator closes >= 8 four-hour candles
        t0 = datetime(2026, 5, 11, 0, 0, tzinfo=timezone.utc)
        for k in range(40 * 12):
            px = 18400.0 + k * 0.5
            st.on_bar(Bar(time=t0 + timedelta(minutes=5 * k), open=px, high=px + 5, low=px - 2, close=px + 3))

        # Seeded daily bars must not be truncated down to 12
        self.assertGreater(len(st._days), 30)
        # 4h ladder bias must now be populated instead of 0 ("not enough closed candles yet")
        lad = st.ladder_bias()
        self.assertEqual(lad["names"][0], "4-hour")
        self.assertNotEqual(lad["p"][0], 0, lad)
        self.assertIsNotNone(lad["range"])

    def test_ict2022_retains_seeded_days_when_htf_context_is_false(self):
        cfg = simple_config(model="nonarrative", flatten_time=None, htf_context=False)
        st = ICT2022Strategy(cfg.strategy, cfg.instrument)
        base = datetime(2026, 4, 1, 0, 0, tzinfo=timezone.utc)
        daily_bars = [
            Bar(
                time=base + timedelta(days=i),
                open=1.1000 + i * 0.0005,
                high=1.1030 + i * 0.0005,
                low=1.0980 + i * 0.0005,
                close=1.1015 + i * 0.0005,
            )
            for i in range(45)
        ]
        st.seed_days(daily_bars)
        for b in [
            ny_bar("2026-06-01 18:00", 1.1020, 1.1050, 1.1000, 1.1020),
            ny_bar("2026-06-02 18:00", 1.1030, 1.1040, 1.1010, 1.1035),
        ]:
            st.on_bar(b)
        self.assertGreaterEqual(len(st._days), 45)

    def test_bpr_detection_and_entry_rule_iv02(self):
        bars = [
            ny_bar("2026-06-01 18:00", 1.1020, 1.1050, 1.1000, 1.1020),   # PDH 1.1050 / PDL 1.1000
            ny_bar("2026-06-02 18:00", 1.1030, 1.1040, 1.1010, 1.1035),
            ny_bar("2026-06-03 02:00", 1.1035, 1.1040, 1.1030, 1.1038),
            ny_bar("2026-06-03 02:05", 1.1038, 1.1039, 1.1025, 1.1036),   # swing low 1.1025
            ny_bar("2026-06-03 02:10", 1.1036, 1.1048, 1.1035, 1.1046),
            ny_bar("2026-06-03 02:15", 1.1046, 1.1058, 1.1044, 1.1052),   # sweeps PDH 1.1050, bullish FVG [1.1039, 1.1044]
            ny_bar("2026-06-03 02:20", 1.1052, 1.1055, 1.1041, 1.1042),
            ny_bar("2026-06-03 02:25", 1.1042, 1.1040, 1.1015, 1.1018),   # bearish FVG [1.1040, 1.1044], overlap [1.1040, 1.1044]
            ny_bar("2026-06-03 02:30", 1.1018, 1.1041, 1.1016, 1.1035),   # retrace fills 1.1040
        ]

        bprs = detect_bprs(bars)
        self.assertTrue(len(bprs) >= 1)
        self.assertAlmostEqual(bprs[-1].bottom, 1.1040)
        self.assertAlmostEqual(bprs[-1].top, 1.1044)
        self.assertEqual(bprs[-1].direction, SHORT)

        pda = scan_pd_arrays(bars)
        self.assertTrue(any(a.kind == "bpr" for a in pda))
        self.assertEqual(custom_changes("custom:entry=bpr"), {"entry_mode": "bpr", "enable_bpr": True})

        cfg = simple_config(model="nonarrative", flatten_time=None, entry_mode="bpr", enable_bpr=True)
        st = ICT2022Strategy(cfg.strategy, cfg.instrument)
        sigs = [s for b in bars if (s := st.on_bar(b)) is not None]
        self.assertEqual(len(sigs), 1, [d.message for d in st.decisions])
        self.assertTrue(any("IV-02" in r for r in sigs[0].reasons), sigs[0].reasons)

    def test_cbdr_40pip_cap_and_asian_range_fallback(self):
        cfg = simple_config(
            model="nonarrative",
            flatten_time=None,
            cbdr_targets=True,
            reference_ranges=StrategyConfig().reference_ranges,
        )
        st = ICT2022Strategy(cfg.strategy, cfg.instrument)
        # Feed Asian session bars (20:00 - 00:00 NY) to form ASIA_H (1.1020) and ASIA_L (1.1000), then 00:05 to close Asian range
        st.on_bar(ny_bar("2026-06-02 20:30", 1.1005, 1.1020, 1.1000, 1.1010))
        st.on_bar(ny_bar("2026-06-03 00:05", 1.1010, 1.1015, 1.1005, 1.1010))
        # Set unqualified CBDR (> 40 pips on EURUSD: 55 pips)
        st._cbdr = (1.1055, 1.1000)
        levels = st._cbdr_levels()
        names = [lv.name for lv in levels]
        self.assertTrue(all(n.startswith("ASIA") for n in names), names)
        self.assertEqual(len(levels), 6)

    def test_backtester_seeds_daily_bars(self):
        cfg = simple_config(model="nonarrative", flatten_time=None)
        base = datetime(2026, 4, 1, 0, 0, tzinfo=timezone.utc)
        daily_bars = [
            Bar(
                time=base + timedelta(days=i),
                open=1.0900 + i * 0.0005,
                high=1.0950 + i * 0.0005,
                low=1.0880 + i * 0.0005,
                close=1.0920 + i * 0.0005,
            )
            for i in range(40)
        ]
        intraday = [
            ny_bar("2026-06-03 02:00", 1.1035, 1.1040, 1.1030, 1.1038),
            ny_bar("2026-06-03 02:05", 1.1038, 1.1041, 1.1025, 1.1039),
        ]
        res = Backtester(cfg).run(intraday, daily_bars=daily_bars)
        self.assertEqual(len(res.trades), 0)

    def test_autotrade_effective_risk_pct_reentry_and_stepdown(self):
        u = {"id": "u1", "risk_pct": 1.0, "day_start_balance": 10000.0}
        s_normal = {"id": "1", "reasons": ["EN-01: First FVG limit"]}
        s_reentry = {"id": "2", "reasons": ["RE-02: Second entry at half risk after stop-out"]}
        self.assertAlmostEqual(effective_risk_pct(u, 10000.0, s_normal), 1.0)
        self.assertAlmostEqual(effective_risk_pct(u, 10000.0, s_reentry), 0.5)

        # Enable dynamic_risk and simulate 1 loss, then 2 consecutive losses
        u["dynamic_risk"] = True
        u["consecutive_losses"] = 1
        self.assertAlmostEqual(effective_risk_pct(u, 9900.0, s_normal), 0.5)
        u["consecutive_losses"] = 2
        self.assertAlmostEqual(effective_risk_pct(u, 9850.0, s_normal), 0.25)


if __name__ == "__main__":
    unittest.main()
