import unittest
from datetime import datetime, timedelta, timezone

from ict_trader.pd_arrays import (
    PDArray,
    detect_breaker_blocks,
    detect_fvgs,
    detect_inversion_fvgs,
    detect_order_blocks,
    detect_volume_imbalances,
    scan_pd_arrays,
)
from ict_trader.sessions import Bar
from ict_trader.strategy import LONG, SHORT

T0 = datetime(2026, 10, 14, 9, 30, tzinfo=timezone.utc)


def make_bar(i: int, o: float, h: float, l: float, c: float) -> Bar:
    return Bar(T0 + timedelta(minutes=i * 5), o, h, l, c, 100)


class PDArraysTest(unittest.TestCase):
    def test_order_block_detection(self):
        # Setup: small bars, then a down candle (OB), followed by a massive up displacement candle breaking high
        bars = [
            make_bar(0, 100.0, 100.5, 99.8, 100.2),
            make_bar(1, 100.2, 100.4, 99.9, 100.1),
            make_bar(2, 100.1, 100.3, 99.0, 99.2),  # down-close OB (open 100.1, close 99.2, body 0.9)
            make_bar(3, 99.2, 103.0, 99.1, 102.8),  # massive displacement up, breaks 100.3
            make_bar(4, 102.8, 103.5, 102.5, 103.2),
        ]
        obs = detect_order_blocks(bars, min_displacement_mult=1.0)
        self.assertTrue(any(ob.direction == LONG and ob.kind == "order_block" for ob in obs))
        ob = [o for o in obs if o.direction == LONG][0]
        # Mean Threshold of body: 99.2 + (100.1 - 99.2) * 0.5 = 99.65
        self.assertAlmostEqual(ob.midpoint, 99.65)
        self.assertEqual(ob.top, 100.3)
        self.assertEqual(ob.bottom, 99.0)

    def test_fvg_and_consequent_encroachment(self):
        # Bullish FVG: Bar 0 High is strictly below Bar 2 Low
        bars = [
            make_bar(0, 100.0, 101.0, 99.8, 100.8),  # High = 101.0
            make_bar(1, 100.9, 104.5, 100.9, 104.2),  # Displacement bar
            make_bar(2, 104.2, 105.0, 102.5, 104.8),  # Low = 102.5 -> Gap is (101.0, 102.5)
        ]
        fvgs = detect_fvgs(bars)
        self.assertEqual(len(fvgs), 1)
        fvg = fvgs[0]
        self.assertEqual(fvg.direction, LONG)
        self.assertAlmostEqual(fvg.bottom, 101.0)
        self.assertAlmostEqual(fvg.top, 102.5)
        # CE is 50%: (101.0 + 102.5) / 2 = 101.75
        self.assertAlmostEqual(fvg.midpoint, 101.75)

    def test_inversion_fvg(self):
        # Create FVG, then later a candle closes right through it
        bars = [
            make_bar(0, 100.0, 101.0, 99.8, 100.8),  # High = 101.0
            make_bar(1, 100.9, 104.5, 100.9, 104.2),
            make_bar(2, 104.2, 105.0, 102.5, 104.8),  # Gap is (101.0, 102.5)
            make_bar(3, 104.8, 105.2, 103.5, 103.8),
            make_bar(4, 103.8, 104.0, 99.5, 100.2),   # Closes at 100.2, below 101.0 (inverts FVG!)
        ]
        fvgs = detect_fvgs(bars)
        ifvgs = detect_inversion_fvgs(bars, fvgs)
        self.assertEqual(len(ifvgs), 1)
        self.assertEqual(ifvgs[0].direction, SHORT)  # flipped to resistance
        self.assertEqual(ifvgs[0].kind, "ifvg")

    def test_breaker_block_detection(self):
        # Bearish Breaker: Low A (bar 1) -> High B (bar 3) -> Higher High C (bar 5) -> Break below Low A (bar 7)
        bars = [
            make_bar(0, 102.0, 103.0, 101.0, 101.5),
            make_bar(1, 101.5, 102.0, 100.0, 100.5),  # Swing Low A at 100.0
            make_bar(2, 100.5, 103.5, 100.2, 103.0),
            make_bar(3, 103.0, 105.0, 102.8, 104.5),  # Swing High B at 105.0
            make_bar(4, 104.5, 104.8, 102.0, 102.5),
            make_bar(5, 102.5, 106.5, 102.2, 106.0),  # Higher High C at 106.5 (liquidity purge)
            make_bar(6, 106.0, 106.2, 101.0, 101.2),
            make_bar(7, 101.2, 101.5, 98.5, 98.8),    # Closes below 100.0 (displacement break!)
        ]
        breakers = detect_breaker_blocks(bars)
        self.assertTrue(len(breakers) >= 1)
        bb = breakers[0]
        self.assertEqual(bb.direction, SHORT)
        self.assertEqual(bb.kind, "breaker")

    def test_scan_pd_arrays_unified(self):
        bars = [
            make_bar(0, 100.0, 101.0, 99.8, 100.8),
            make_bar(1, 100.9, 104.5, 100.9, 104.2),
            make_bar(2, 104.2, 105.0, 102.5, 104.8),
        ]
        res = scan_pd_arrays(bars)
        self.assertTrue(len(res) > 0)


if __name__ == "__main__":
    unittest.main()
