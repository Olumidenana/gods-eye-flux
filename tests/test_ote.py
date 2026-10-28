import unittest

from ict_trader.ote import find_dealing_range
from ict_trader.strategy import LONG, SHORT


class OTETest(unittest.TestCase):
    def test_bullish_ote_and_projections(self):
        # Bullish impulse leg from 100 to 200
        dr = find_dealing_range(swing_low=100.0, swing_high=200.0, direction=LONG)
        self.assertIsNotNone(dr)
        assert dr is not None

        # Equilibrium
        self.assertEqual(dr.equilibrium, 150.0)
        self.assertTrue(dr.is_discount(140.0))
        self.assertFalse(dr.is_discount(160.0))

        # OTE levels for Long: retracement downwards from 200
        self.assertAlmostEqual(dr.ote_shallow, 138.2)     # 200 - 0.618 * 100
        self.assertAlmostEqual(dr.ote_sweet_spot, 129.5)  # 200 - 0.705 * 100
        self.assertAlmostEqual(dr.ote_deep, 121.0)        # 200 - 0.790 * 100
        self.assertEqual(dr.invalidation, 100.0)

        # In OTE zone
        self.assertTrue(dr.is_in_ote(130.0))
        self.assertTrue(dr.is_in_ote(125.0))
        self.assertFalse(dr.is_in_ote(155.0))
        self.assertFalse(dr.is_in_ote(115.0))

        # SD Targets for Long: expansions above 200
        self.assertEqual(dr.standard_deviation_target(1.0), 300.0)
        self.assertEqual(dr.standard_deviation_target(1.5), 350.0)
        self.assertEqual(dr.standard_deviation_target(2.0), 400.0)
        self.assertEqual(dr.standard_deviation_target(4.0), 600.0)

    def test_bearish_ote_and_projections(self):
        # Bearish impulse leg from 200 down to 100
        dr = find_dealing_range(swing_low=100.0, swing_high=200.0, direction=SHORT)
        self.assertIsNotNone(dr)
        assert dr is not None

        self.assertEqual(dr.equilibrium, 150.0)
        self.assertTrue(dr.is_premium(160.0))
        self.assertFalse(dr.is_premium(140.0))

        # OTE levels for Short: retracement upwards from 100
        self.assertAlmostEqual(dr.ote_shallow, 161.8)     # 100 + 0.618 * 100
        self.assertAlmostEqual(dr.ote_sweet_spot, 170.5)  # 100 + 0.705 * 100
        self.assertAlmostEqual(dr.ote_deep, 179.0)        # 100 + 0.790 * 100
        self.assertEqual(dr.invalidation, 200.0)

        # In OTE zone
        self.assertTrue(dr.is_in_ote(170.0))
        self.assertFalse(dr.is_in_ote(150.0))

        # SD Targets for Short: expansions below 100
        self.assertEqual(dr.standard_deviation_target(1.0), 0.0)
        self.assertEqual(dr.standard_deviation_target(2.0), -100.0)


if __name__ == "__main__":
    unittest.main()
