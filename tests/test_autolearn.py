import unittest
from datetime import datetime, time, timezone
from pathlib import Path
from ict_trader import autolearn
from ict_trader.config import Config, InstrumentConfig, StrategyConfig, Window
from ict_trader.ict2022 import Decision
from ict_trader.sessions import Bar


class TestAutoLearn(unittest.TestCase):
    def setUp(self):
        self.temp_state = Path("tests/test_adaptive_state.json")
        self.engine = autolearn.SelfCorrectionEngine(state_file=self.temp_state)

    def tearDown(self):
        if self.temp_state.exists():
            self.temp_state.unlink()

    def test_it_reports_what_it_sees_but_never_changes_a_configuration(self):
        cfg = Config(
            instrument=InstrumentConfig("GBPUSD", pip_size=0.0001),
            strategy=StrategyConfig(
                daily_bias_filter=True, narrative_filter=True, fvg_in_premium_discount=True, sd_targets=False,
                killzones=(Window("new_york", time(7, 0), time(10, 0)),),
                reference_ranges=(Window("asia", time(20, 0), time(0, 0)),),
            ),
        )
        decisions = [
            Decision(time=datetime.now(timezone.utc), rule="RL-05", message="LONDON_L sweep ignored: not toward the daily draw"),
            Decision(time=datetime.now(timezone.utc), rule="FV-02", message="ASIA_H setup rejected: gap is in discount, wrong side of the leg's 50%"),
            Decision(time=datetime.now(timezone.utc), rule="TP-01", message="LONDON_L setup rejected: no opposing liquidity to target"),
        ]
        out, anomalies = self.engine.audit_and_correct("GBPUSD", [], decisions, [], cfg)
        self.assertGreaterEqual(len(anomalies), 3)                       # it sees them, and says what it would propose
        self.assertTrue(all("never applied automatically" in a.proposed_remedy for a in anomalies))
        self.assertIs(out, cfg)                                          # but the rules are exactly as they were
        self.assertTrue(out.strategy.daily_bias_filter and out.strategy.narrative_filter and out.strategy.fvg_in_premium_discount)
        self.assertFalse(out.strategy.sd_targets)
        self.assertIs(autolearn.heal_config(cfg, "GBPUSD", [], decisions, []), cfg)

    def test_nothing_is_written_next_to_the_code_unless_a_file_is_named(self):
        self.assertIsNone(autolearn.STATE_PATH)

    def test_engine_status_reporting(self):
        status = autolearn.get_engine_status()
        self.assertEqual(status["status"], "report-only")
        self.assertEqual(status["anomalies_corrected"], 0)
        self.assertIn("total_audits", status)


if __name__ == "__main__":
    unittest.main()
