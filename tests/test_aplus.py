"""ICT's A+ checklist: ticked boxes, price-only for synthetics, and it never replaces the grade on its own."""

import unittest

from ict_trader import advisor, aplus
from ict_trader.scanner import _grade_sig, _judge

STRONG = {"dir": 1, "bias": 1, "wbias": 1, "level": "PDL", "rr": 3.5, "pd": 1, "pd20": None, "obstacles": 0,
          "body_mult": 3, "gap_ratio": 0.7, "target": "PWH", "timed": False}
CLOCK = {**STRONG, "timed": True, "window": "london_kz", "weekday": 2, "hour": 9, "midnight_ok": True}


def boxes(a):
    return {b["key"]: b for b in a["aplus"]["boxes"]}


class AplusTests(unittest.TestCase):
    def test_full_house_on_a_synthetic_is_judged_on_price_alone(self):
        a = advisor.assess(STRONG)["aplus"]
        self.assertTrue(a["aplus"])
        self.assertEqual((a["ticked"], a["of"]), (7, 7))
        self.assertNotIn("time", [b["key"] for b in a["boxes"]])    # no clock on a synthetic index

    def test_a_clock_market_adds_the_time_box(self):
        a = advisor.assess(CLOCK)
        self.assertIn("time", boxes(a))
        self.assertEqual(a["aplus"]["of"], 8)
        not_midnight = advisor.assess({**CLOCK, "midnight_ok": False})
        self.assertFalse(boxes(not_midnight)["time"]["ok"])
        self.assertTrue(not_midnight["aplus"]["aplus"])             # one missed box in eight is allowed, the required three are intact

    def test_the_three_required_boxes_cannot_be_traded_for_the_rest(self):
        for tweak, key in (({"wbias": 0}, "htf"), ({"obstacles": 1}, "draw"), ({"target": "SW_H"}, "draw"), ({"body_mult": 1.0, "gap_ratio": 0.1}, "entry")):
            a = advisor.assess({**STRONG, **tweak})
            self.assertFalse(boxes(a)[key]["ok"], key)
            self.assertTrue(boxes(a)[key]["required"])
            self.assertFalse(a["aplus"]["aplus"], key)
            self.assertIn(boxes(a)[key]["label"], a["aplus"]["missing"])

    def test_the_rest_must_reach_three_quarters(self):
        a = advisor.assess({**STRONG, "pd": -1, "rr": 1.6})          # wrong side of the range and a thin reward
        self.assertFalse(a["aplus"]["aplus"])
        self.assertEqual(a["aplus"]["ticked"], 4)

    def test_a_model_with_no_matrix_of_its_own_cannot_be_a_plus(self):
        js = {"direction": "long", "rr": 4.0, "time": "2026-03-03T14:00:00+00:00", "level": "PDL", "reasons": ["RL-05 daily bias"], "cls": "synthetic"}
        a = _judge(js)
        self.assertFalse(a["aplus"]["aplus"])
        self.assertFalse(boxes(a)["entry"]["applies"])
        self.assertLess(a["aplus"]["of"], 7)

    def test_smt_adds_a_box_only_when_a_partner_was_read(self):
        a = advisor.assess(STRONG)
        self.assertNotIn("smt", boxes(a))
        yes = aplus.checklist(a, {"divergence": True, "text": "SMT: GBPUSD did not take its PDL"})
        no = aplus.checklist(a, {"divergence": False, "text": "No SMT"})
        self.assertEqual((yes["of"], yes["ticked"]), (8, 8))
        self.assertEqual((no["of"], no["ticked"]), (8, 7))
        js = {"direction": "long", "rr": 3.5, "reasons": [], "advice": a, "smt": {"divergence": True, "text": "SMT"}}
        _grade_sig(js)
        self.assertIn("smt", boxes(js["advice"]))

    def test_the_checklist_is_in_the_alert_and_the_rules_trail(self):
        a = advisor.assess(STRONG)
        self.assertIn("A+ checklist 7/7 passes", aplus.text(a))
        self.assertIn("✅ HTF", aplus.text(a))
        self.assertEqual(aplus.parse(aplus.line(a)), True)
        weak = advisor.assess({**STRONG, "wbias": 0})
        self.assertIn("⬜ HTF", aplus.text(weak))
        self.assertEqual(aplus.parse(aplus.line(weak)), False)
        self.assertIsNone(aplus.parse(["AD-00 advisor 80/100 TAKE: x"]))
        self.assertEqual(aplus.text(None), "")


if __name__ == "__main__":
    unittest.main()
