import unittest
from datetime import datetime, timedelta, timezone

from ict_trader.sessions import Bar
from ict_trader.smt import detect_smt_divergence
from ict_trader.strategy import LONG, SHORT

T0 = datetime(2026, 10, 14, 9, 30, tzinfo=timezone.utc)


def make_bar(i: int, o: float, h: float, l: float, c: float) -> Bar:
    return Bar(T0 + timedelta(minutes=i * 5), o, h, l, c, 100)


class SMTTest(unittest.TestCase):
    def test_correlated_bullish_smt(self):
        # Asset A (ES): Swing Low 1 at bar 1 (low=100), Swing Low 2 at bar 4 (low=95) -> Lower Low
        # Asset B (NQ): Swing Low 1 at bar 1 (low=200), Swing Low 2 at bar 4 (low=205) -> Higher Low (Divergence!)
        bars_a = [
            make_bar(0, 102, 103, 101, 102),
            make_bar(1, 102, 102.5, 100, 101),   # Swing low 1: 100
            make_bar(2, 101, 106, 100.5, 105),
            make_bar(3, 105, 105.5, 102, 103),
            make_bar(4, 103, 103.5, 95, 97),     # Swing low 2: 95 (Lower Low)
            make_bar(5, 97, 102, 96.5, 101),
        ]
        bars_b = [
            make_bar(0, 202, 203, 201, 202),
            make_bar(1, 202, 202.5, 200, 201),   # Swing low 1: 200
            make_bar(2, 201, 210, 200.5, 208),
            make_bar(3, 208, 208.5, 206, 207),
            make_bar(4, 207, 207.5, 205, 206),   # Swing low 2: 205 (Higher Low - Divergence!)
            make_bar(5, 206, 212, 205.5, 211),
        ]

        smt = detect_smt_divergence(bars_a, bars_b, "US500", "NAS100")
        self.assertIsNotNone(smt)
        assert smt is not None
        self.assertEqual(smt.direction, LONG)
        self.assertIn("Bullish SMT", smt.description)

    def test_correlated_bearish_smt(self):
        # Asset A (ES): Swing High 1 at 105, Swing High 2 at 110 -> Higher High
        # Asset B (NQ): Swing High 1 at 210, Swing High 2 at 205 -> Lower High (Divergence!)
        bars_a = [
            make_bar(0, 100, 101, 99, 100),
            make_bar(1, 100, 105, 99.5, 104),   # Swing high 1: 105
            make_bar(2, 104, 104.5, 101, 102),
            make_bar(3, 102, 106, 101.5, 105),
            make_bar(4, 105, 110, 104.5, 109),  # Swing high 2: 110 (Higher High)
            make_bar(5, 109, 109.5, 106, 107),
        ]
        bars_b = [
            make_bar(0, 200, 201, 199, 200),
            make_bar(1, 200, 210, 199.5, 208),  # Swing high 1: 210
            make_bar(2, 208, 208.5, 201, 202),
            make_bar(3, 202, 204, 201.5, 203),
            make_bar(4, 203, 205, 202.5, 204),  # Swing high 2: 205 (Lower High - Divergence!)
            make_bar(5, 204, 204.5, 201, 202),
        ]

        smt = detect_smt_divergence(bars_a, bars_b, "US500", "NAS100")
        self.assertIsNotNone(smt)
        assert smt is not None
        self.assertEqual(smt.direction, SHORT)
        self.assertIn("Bearish SMT", smt.description)


if __name__ == "__main__":
    unittest.main()
