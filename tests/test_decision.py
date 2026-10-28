"""One decision system: the grade, the verdict and the checklist come from ICT's three required conditions, and the new reads
(weekly profile, room in the day's range, depth in the range) feed it."""

import unittest
from datetime import datetime, timezone

from ict_trader import advisor, analysis, aplus, narrative
from ict_trader.scanner import _grade_sig, _judge
from ict_trader.sessions import NY, Bar

STRONG = {"dir": 1, "bias": 1, "wbias": 1, "level": "PDL", "rr": 3.5, "pd": 1.0, "pd20": None, "obstacles": 0, "body_mult": 3, "gap_ratio": 0.7,
          "target": "PWH", "timed": False}


def ny_bar(day, hour, price):
    return Bar(datetime(2026, 6, day, hour, 0, tzinfo=NY).astimezone(timezone.utc), price, price + 1, price - 1, price)


class Stub:
    """The little of a strategy the weekly profile reads."""

    def __init__(self, day, hour, price, weekly=1, timed=True, wopen=100.0):
        self._bars = [ny_bar(day, hour, price)]
        self._days = {datetime(2026, 6, 1).date(): [wopen, wopen + 3, wopen - 3, wopen]}
        self._w, self._t = weekly, timed

    def _time_based(self): return self._t
    def weekly_bias(self): return self._w, "x"
    def daily_bias(self): return 0, "x"
    def _fmt(self, p): return f"{p:.2f}"


class VerdictTests(unittest.TestCase):
    def test_all_three_required_conditions_is_a_plus_and_pull_the_trigger(self):
        a = advisor.assess(STRONG)
        self.assertEqual((a["verdict"], aplus.quality(a)["grade"]), ("TAKE", "A+"))

    def test_one_required_condition_missing_can_never_be_a_plain_take_however_well_it_scores(self):
        for tweak in ({"wbias": 0}, {"obstacles": 1}, {"body_mult": 1.0, "gap_ratio": 0.1}, {"target": "SW_H"}):
            a = advisor.assess({**STRONG, **tweak})
            self.assertEqual(a["verdict"], "CAUTION", tweak)
            self.assertEqual(aplus.quality(a)["grade"], "B", tweak)
            self.assertIn("Missing:", a["summary"])

    def test_two_missing_is_stand_down_and_c(self):
        a = advisor.assess({**STRONG, "wbias": 0, "obstacles": 1})
        self.assertEqual((a["verdict"], aplus.quality(a)["grade"], a["call"]), ("SKIP", "C", "STAND DOWN"))

    def test_reward_size_is_not_a_reason_to_take_a_trade(self):
        far, near = advisor.assess({**STRONG, "rr": 6.0, "wbias": 0, "obstacles": 1}), advisor.assess({**STRONG, "rr": 1.6})
        self.assertEqual(far["verdict"], "SKIP")           # a 6R target does not rescue a trade with two conditions missing
        self.assertEqual(near["verdict"], "TAKE")          # a modest reward with all three conditions is still the trade
        self.assertIn(aplus.quality(near)["grade"], ("A", "A+"))
        self.assertGreater(aplus.GRADES_ORDER.index(aplus.quality(far)["grade"]), aplus.GRADES_ORDER.index(aplus.quality(near)["grade"]))

    def test_a_model_that_cannot_read_the_required_conditions_is_never_better_than_b(self):
        js = {"direction": "long", "rr": 4.0, "time": "2026-03-03T14:00:00+00:00", "level": "PDL", "reasons": ["RL-05 daily bias"], "cls": "synthetic"}
        a = _judge(js)
        self.assertNotEqual(a["verdict"], "TAKE")
        self.assertIn(aplus.quality(a)["grade"], ("B", "C"))

    def test_the_signals_grade_is_the_checklists(self):
        js = {"direction": "long", "rr": 3.5, "reasons": ["RL-05 daily bias", "KZ-01 midnight"], "advice": advisor.assess({**STRONG, "wbias": 0, "obstacles": 1})}
        _grade_sig(js)
        self.assertEqual(js["quality"]["grade"], "C")      # the old points (3.5R, bias, midnight) would have said A+
        self.assertEqual(js["quality"]["score"], js["advice"]["aplus"]["ticked"])

    def test_the_rules_trail_carries_the_grade_the_lab_reads(self):
        a = advisor.assess({**STRONG, "wbias": 0})
        self.assertEqual(aplus.parse_grade(aplus.line(a)), "B")
        self.assertIs(aplus.parse(aplus.line(advisor.assess(STRONG))), True)


class DayAndWeekTests(unittest.TestCase):
    def test_room_in_the_days_range(self):
        ok = aplus.checklist(advisor.assess({**STRONG, "adr": (10.0, 3.0), "entry_price": 100, "target_price": 105}))
        spent = aplus.checklist(advisor.assess({**STRONG, "adr": (10.0, 10.0), "entry_price": 100, "target_price": 106}))
        self.assertTrue(next(b for b in ok["boxes"] if b["key"] == "room")["ok"])
        self.assertFalse(next(b for b in spent["boxes"] if b["key"] == "room")["ok"])
        self.assertNotIn("room", [b["key"] for b in aplus.checklist(advisor.assess(STRONG))["boxes"]])   # no daily range yet: no box

    def test_depth_in_the_range_is_scored(self):
        deep = advisor.assess({**STRONG, "pd": 0.8})["rows"][1]
        shallow = advisor.assess({**STRONG, "pd": 0.2})["rows"][1]
        self.assertGreater(deep["points"], shallow["points"])
        self.assertIn("outer quadrant", deep["why"])

    def test_weekly_profile_by_day(self):
        tue = narrative.weekly_profile(Stub(2, 10, 98.0), 1)          # Tuesday, a bullish week, below the weekly open: the classic buy
        self.assertEqual((tue["day"], tue["phase"], tue["fit"]), ("Tuesday", "manipulation", 1))
        self.assertIn("below the weekly open", tue["text"])
        self.assertEqual(narrative.weekly_profile(Stub(2, 10, 102.0), 1)["fit"], 0)       # right day, wrong side of the weekly open
        self.assertEqual(narrative.weekly_profile(Stub(2, 10, 98.0), -1)["fit"], -1)      # against the week
        self.assertEqual(narrative.weekly_profile(Stub(5, 14, 98.0), 1)["fit"], -1)       # Friday afternoon
        self.assertEqual(narrative.weekly_profile(Stub(1, 10, 98.0), 1)["fit"], 0)        # Monday: be selective
        self.assertIsNone(narrative.weekly_profile(Stub(2, 10, 98.0, timed=False), 1))    # a synthetic index has no week
        self.assertIsNone(narrative.weekly_profile(Stub(6, 10, 98.0), 1))                 # Saturday: closed

    def test_the_day_of_the_week_moves_the_clock_row(self):
        base = {**STRONG, "timed": True, "window": "london", "weekday": 1, "hour": 10, "midnight_ok": True}
        fits = advisor.assess({**base, "profile": {"fit": 1, "day": "Tuesday", "week": "bullish", "phase": "manipulation"}})["rows"][-1]
        misfit = advisor.assess({**base, "profile": {"fit": -1, "day": "Friday", "week": "bullish", "phase": "distribution"}})["rows"][-1]
        self.assertGreater(fits["points"], misfit["points"])
        self.assertIn("does not fit the weekly profile", misfit["why"])

    def test_the_ipda_ranges_are_named_for_the_chart(self):
        self.assertEqual(analysis._level_label("IPDA20_H"), "20-day range high (IPDA)")
        self.assertEqual(analysis._level_label("IPDA60_L"), "60-day range low (IPDA)")
        self.assertEqual(analysis._level_label("PDH"), "Prior-day high")


class PageTests(unittest.TestCase):
    def test_the_chart_letters_ipda_and_the_draw_and_the_page_says_what_to_take(self):
        with open("web/template.html", encoding="utf-8") as f:
            html = f.read()
        for needle in ("const lvShort =", "◎ DRAW", "htf ? 'accent'", "function decisionHtml()", "What to take now", "Where are we in the week?", "js-decision", "function rsAdvice()", "What works best for each instrument"):
            self.assertIn(needle, html, needle)


if __name__ == "__main__":
    unittest.main()


class MarketStateTests(unittest.TestCase):
    def test_what_the_market_is_doing(self):
        from ict_trader import conditions
        up = [100 + i * 0.5 for i in range(60)]                                   # a straight leg, still going
        pull = up[:48] + [up[47] - j * 0.6 for j in range(1, 13)]                 # the leg, then a pullback in the last 12 candles
        chop = [100 + (0.3 if i % 2 else -0.3) for i in range(60)]                # going nowhere
        self.assertEqual(conditions.label_state(up), "expansion")
        self.assertEqual(conditions.label_state(pull), "retracement")
        self.assertEqual(conditions.label_state(chop), "consolidation")
        self.assertIsNone(conditions.label_state(up[:10]))
        self.assertIn("state", conditions.DIMENSIONS)
        self.assertEqual(conditions.parse([conditions.tag({"trend": "trending", "state": "expansion", "vol": "normal"})])["state"], "expansion")


class EnvironmentChoosesTheModelTests(unittest.TestCase):
    """The reading of the environment decides where each model applies; no model is removed."""

    def rank(self, **conds):
        from ict_trader import selector
        out = selector.recommend(conds, ["ict2022", "ote", "sweep", "judas_swing", "sdt", "stack_trend"], evidence={}, top=6)
        return [r["model"] for r in out["ranked"]]

    def test_an_expansion_is_not_faded_and_a_consolidation_is_traded_at_its_extremes(self):
        exp, cons = self.rank(state="expansion"), self.rank(state="consolidation")
        self.assertLess(exp.index("stack_trend"), exp.index("sweep"))      # trend-following ahead of the fade
        self.assertEqual(cons[0], "sweep")                                  # the false break at the range's edge
        self.assertLess(cons.index("sweep"), cons.index("ote"))

    def test_a_retracement_looks_for_the_array_it_pulls_back_into(self):
        self.assertEqual(self.rank(state="retracement")[0], "ote")

    def test_every_model_stays_available_whatever_the_state(self):
        for st in ("expansion", "retracement", "consolidation", "mixed"):
            self.assertEqual(len(self.rank(state=st)), 6)


class ArrayDimensionTests(unittest.TestCase):
    def test_the_entry_array_and_the_higher_timeframe_point_ride_on_the_trade_for_the_lab(self):
        from ict_trader import conditions
        c = {"trend": "trending", "state": "retracement", "array": "ob", "poi": "1h fvg"}
        self.assertEqual(conditions.parse([conditions.tag(c)]), {k: c[k] for k in c})
        self.assertIn("array", conditions.DIMENSIONS)
        self.assertIn("poi", conditions.DIMENSIONS)


class SecondTryTests(unittest.TestCase):
    """RE-01: a re-entry after a stop-out is ICT's idea, but never a plain PULL THE TRIGGER."""

    def test_a_take_becomes_size_down_and_says_why(self):
        from ict_trader import advisor
        a = {"verdict": "TAKE", "call": "PULL THE TRIGGER", "score": 80, "summary": "All three of ICT's required conditions are met and the rest agree. Best: reward. Weakest: time (x)."}
        b = advisor.second_try(a)
        self.assertEqual((b["verdict"], b["call"], b["reentry"]), ("CAUTION", "SIZE DOWN", True))
        self.assertTrue(b["summary"].startswith("Second try:"))
        self.assertNotIn("All three", b["summary"])               # the old line would contradict the new call
        self.assertIn("Best: reward.", b["summary"])
        self.assertEqual(a["verdict"], "TAKE")                    # the original is not changed

    def test_a_weaker_call_keeps_its_own_ruling_and_its_own_words(self):
        from ict_trader import advisor
        for v, call in (("CAUTION", "SIZE DOWN"), ("SKIP", "STAND DOWN")):
            b = advisor.second_try({"verdict": v, "call": call, "score": 40, "summary": "Mixed: trade it smaller. Best: x."})
            self.assertEqual((b["verdict"], b["call"]), (v, call))
            self.assertIn("Mixed: trade it smaller.", b["summary"])
            self.assertTrue(b["summary"].startswith("Second try:"))
