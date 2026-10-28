import unittest
from datetime import timedelta

from ict_trader.analysis import analyze
from ict_trader.ict2022 import ICT2022Strategy
from tests.helpers import ny_bar
from tests.test_ict2022 import config, scenario


def read(bars):
    cfg = config()
    st = ICT2022Strategy(cfg.strategy, cfg.instrument)
    for b in bars:
        st.on_bar(b)
    return analyze(st, bars, cfg, 5, 5, bars[-1].time + timedelta(minutes=5))


class AnalysisTest(unittest.TestCase):
    def test_staged_limit_is_read_like_ict(self):
        a = read(scenario(fill=False)[:8])
        self.assertEqual(a["stage"], "limit")
        self.assertEqual(a["bias"], "bearish")
        p = a["plan"]
        self.assertEqual((p["direction"], p["entry"], p["stop"], p["tp2"]), ("short", 1.1038, 1.1059, 1.1))
        self.assertEqual(p["tp1"], 1.1015)            # TP-04: the displacement leg's low
        self.assertEqual(p["rr1"], round(0.0023 / 0.0021, 2))
        self.assertEqual(p["fvg"], [1.1038, 1.1042])
        states = {c["rule"]: c["state"] for c in a["checklist"]}
        self.assertEqual(states["SW-01"], "done")
        self.assertEqual(states["MS-02"], "done")
        self.assertEqual(states["EN-01"], "pending")
        pdh = next(lv for lv in a["levels"] if lv["name"] == "PDH")
        self.assertEqual((pdh["status"], pdh["pool"]), ("swept", "BSL"))
        kinds = [e["type"] for e in a["events"]]
        self.assertEqual(kinds[:3], ["sweep", "mss", "staged"])
        self.assertTrue(any("Market structure shift" in n for n in a["narrative"]))
        ob = next(x for x in a["pd_arrays"] if x["kind"] == "ob")
        self.assertEqual((ob["dir"], ob["top"], ob["bottom"]), ("bear", 1.1058, 1.1042))  # last up-close candle before the drop

    def test_waiting_for_the_shift_names_the_swing_to_break(self):
        a = read(scenario()[:6])  # PDH just swept, no displacement yet
        self.assertEqual(a["stage"], "await_mss")
        self.assertEqual(a["need_mss"], 1.1025)
        self.assertIn("1.1025", next(c for c in a["checklist"] if c["rule"] == "MS-02")["detail"])

    def test_sessions_and_gaps_are_marked(self):
        a = read(scenario(fill=False)[:8] + [ny_bar("2026-06-03 02:30", 1.1018, 1.1020, 1.1012, 1.1015)])
        names = [s["name"] for s in a["sessions"]]
        self.assertIn("london", names)
        self.assertTrue(any(g["dir"] == "bear" for g in a["fvgs"]))
        self.assertEqual(a["dealing_range"]["high"], 1.1058)
        pdh = next(lv for lv in a["levels"] if lv["name"] == "PDH")
        hod = next(lv for lv in a["levels"] if lv["name"] == "HOD")
        self.assertIsNotNone(pdh.get("origin_time"))
        self.assertIsNotNone(hod.get("origin_time"))
        self.assertEqual(hod["status"], "developing")
        self.assertIn("swings", a)
        self.assertTrue(any(sw["tier"] in ("LTH", "LTL", "ITH", "ITL", "STH", "STL") for sw in a["swings"]))


if __name__ == "__main__":
    unittest.main()
