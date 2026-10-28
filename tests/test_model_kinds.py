"""Models are trade recipes the judgement matrix rules on; everything else is a building block."""
import unittest

from ict_trader import advisor, scanner
from ict_trader.models import BUILDING_BLOCKS, KIND, LIVE_MODELS, MODEL_INFO, MODELS, TRADE_MODELS, kind_of


class KindsTest(unittest.TestCase):
    def test_every_name_is_a_model_or_a_known_kind_of_building_block(self):
        self.assertEqual(set(TRADE_MODELS) | set(BUILDING_BLOCKS), set(MODELS))
        self.assertFalse(set(TRADE_MODELS) & set(BUILDING_BLOCKS))
        self.assertTrue(set(KIND.values()) <= {"direction", "filter", "zone", "target", "management", "stop"})
        for k in MODELS:
            self.assertEqual(MODEL_INFO[k]["kind"], kind_of(k))

    def test_the_named_trade_recipes_are_models_and_the_parts_are_not(self):
        for k in ("ict2022", "silver_bullet", "judas_swing", "sweep", "ote", "unicorn", "venom", "atm", "mm", "reaper", "osok", "fpfvg", "institutional"):
            self.assertEqual(kind_of(k), "model", k)
        for k in ("nonarrative", "weekly", "dayopen"):
            self.assertEqual(kind_of(k), "direction", k)
        for k in ("ob", "breaker", "ifvg", "cisd", "mitigation", "rejection", "propulsion", "suspension", "vimb", "vacuum"):
            self.assertEqual(kind_of(k), "zone", k)
        self.assertEqual((kind_of("sdt"), kind_of("drawtarget"), kind_of("cbdr")), ("target",) * 3)
        self.assertEqual((kind_of("trail"), kind_of("reentry"), kind_of("tightstop")), ("management", "management", "stop"))
        self.assertEqual(kind_of("custom:entry=ote;stop=zone"), "model")   # a custom build is a whole recipe

    def test_the_live_scan_runs_models_only(self):
        self.assertTrue(LIVE_MODELS and all(kind_of(m) == "model" for m in LIVE_MODELS))
        self.assertTrue(all(kind_of(m) == "model" for m in scanner.NOTIFY_MODELS))


class JudgementTest(unittest.TestCase):
    def test_every_verdict_has_a_plain_call(self):
        self.assertEqual(advisor.CALL, {"TAKE": "PULL THE TRIGGER", "CAUTION": "SIZE DOWN", "SKIP": "STAND DOWN"})
        a = advisor.assess({"dir": 1, "bias": 1, "wbias": 1, "level": "PDL", "rr": 3.5, "pd": 1, "obstacles": 0, "body_mult": 3, "gap_ratio": 0.7, "target": "PDH"})
        self.assertEqual((a["verdict"], a["call"]), ("TAKE", "PULL THE TRIGGER"))

    def test_a_model_that_keeps_no_matrix_is_judged_on_what_its_trade_shows(self):
        js = {"direction": "long", "time": "2026-10-14T13:30:00+00:00", "rr": 3.0, "level": "PDL", "killzone": "ny_am", "cls": "forex",
              "reasons": ["TP-3 swept PDL", "RL-05 not against the daily draw (up)"]}
        a = scanner._judge(js)
        self.assertTrue(a["partial"])
        self.assertEqual([r["name"] for r in a["rows"]], ["Draw on liquidity", "Liquidity taken", "Reward", "Time and day"])
        self.assertIn(a["verdict"], ("TAKE", "CAUTION", "SKIP"))
        sig = dict(js, quality=None)
        scanner._grade_sig(sig)
        self.assertEqual(sig["advice"]["call"], a["call"])           # signals get it on the way out
        keep = {"verdict": "TAKE", "score": 90, "call": "PULL THE TRIGGER", "rows": []}
        sig = dict(js, advice=keep)
        scanner._grade_sig(sig)
        self.assertIs(sig["advice"], keep)                           # a model's own matrix is never replaced
        self.assertIsNone(scanner._judge({"direction": "long"}))      # missing data never raises


if __name__ == "__main__":
    unittest.main()
