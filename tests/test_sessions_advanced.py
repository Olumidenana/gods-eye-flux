import unittest
from datetime import datetime
from zoneinfo import ZoneInfo

from ict_trader.sessions_advanced import get_amd_phase, in_macro

NY = ZoneInfo("America/New_York")


class SessionsAdvancedTest(unittest.TestCase):
    def test_in_macro(self):
        # 08:55 NY time is inside ny_am_open_macro (08:50 - 09:10)
        dt_macro1 = datetime(2026, 10, 14, 8, 55, tzinfo=NY)
        m1 = in_macro(dt_macro1)
        self.assertIsNotNone(m1)
        assert m1 is not None
        self.assertEqual(m1.name, "ny_am_open_macro")

        # 09:55 NY time is inside ny_am_mid_macro (09:50 - 10:10)
        dt_macro2 = datetime(2026, 10, 14, 9, 55, tzinfo=NY)
        m2 = in_macro(dt_macro2)
        self.assertIsNotNone(m2)
        assert m2 is not None
        self.assertEqual(m2.name, "ny_am_mid_macro")

        # 12:00 NY time is not inside any macro
        dt_none = datetime(2026, 10, 14, 12, 0, tzinfo=NY)
        self.assertIsNone(in_macro(dt_none))

    def test_get_amd_phase(self):
        # 21:00 NY is Asian accumulation
        self.assertEqual(get_amd_phase(datetime(2026, 10, 14, 21, 0, tzinfo=NY)), "accumulation")

        # 03:30 NY is London manipulation (Judas swing)
        self.assertEqual(get_amd_phase(datetime(2026, 10, 14, 3, 30, tzinfo=NY)), "manipulation")

        # 09:30 NY is NY AM distribution
        self.assertEqual(get_amd_phase(datetime(2026, 10, 14, 9, 30, tzinfo=NY)), "distribution")

        # 12:15 NY is lunch consolidation
        self.assertEqual(get_amd_phase(datetime(2026, 10, 14, 12, 15, tzinfo=NY)), "lunch_consolidation")

        # 14:15 NY is PM distribution
        self.assertEqual(get_amd_phase(datetime(2026, 10, 14, 14, 15, tzinfo=NY)), "pm_distribution")


if __name__ == "__main__":
    unittest.main()
