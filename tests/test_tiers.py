"""Alert tiers: A+ only / A and up / B and up, and the suggestion line on every trade alert."""
import json
import os
import unittest
from unittest import mock

from ict_trader import scanner, tiers
from ict_trader import webpush as wp


def report(grade, advice=None, kind="order"):
    q = {"grade": grade}
    order = {"direction": "long", "entry": 1.1, "stop": 1.099, "tp1": None, "tp2": 1.104, "rr": 4.0, "placed": 1000, "quality": q,
             "candles_left": 5, "advice": advice}
    return {"generated_at": "2026-10-08T14:00:00+00:00", "timeframe_minutes": 5,
            "markets": [{"ok": True, "key": "EU", "label": "EUR/USD", "model": "ict2022", "last_price": 1.1005, "today": {"signals": []},
                         "models": {"ict2022": {"available": True, "orders": [order] if kind == "order" else [], "signals": [],
                                                "forming": [{"direction": "short", "level": "PDH", "level_price": 1.12, "extreme": 1.121, "need": 1.118, "candles_left": 6}]}}}]}


class TierTest(unittest.TestCase):
    def test_a_phone_hears_only_the_grades_its_tier_allows(self):
        ev = lambda g, **k: {"id": "x", "grade": g, **k}  # noqa: E731
        self.assertEqual([tiers.allows("aplus", ev(g)) for g in ("A+", "A", "B")], [True, False, False])
        self.assertEqual([tiers.allows("a", ev(g)) for g in ("A+", "A", "B")], [True, True, False])
        self.assertEqual([tiers.allows("b", ev(g)) for g in ("A+", "A", "B")], [True, True, True])
        self.assertFalse(tiers.allows("b", ev("C")))

    def test_heads_ups_and_cancellations(self):
        for kind in ("headsup", "forming"):
            self.assertEqual([tiers.allows(t, {"kind": kind, "grade": None}) for t in ("aplus", "a", "b")], [False, False, True])
        self.assertEqual([tiers.allows(t, {"kind": "cancel", "grade": None}) for t in ("aplus", "a", "b")], [False, True, True])
        self.assertTrue(tiers.allows("aplus", {"kind": "cancel", "grade": "A+"}))   # the grade it was sent with wins
        self.assertFalse(tiers.allows("aplus", {"kind": "cancel", "grade": "A"}))

    def test_unknown_tier_falls_back_to_the_default(self):
        self.assertEqual((tiers.clean(None), tiers.clean("nonsense"), tiers.clean("A+"), tiers.clean("b")), ("a", "a", "aplus", "b"))
        with mock.patch.dict(os.environ, {"NOTIFY_MIN_GRADE": "A+"}):
            self.assertEqual(tiers.channel_tier(), "aplus")
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("NOTIFY_MIN_GRADE", None)
            self.assertEqual(tiers.channel_tier(), "a")

    def test_the_suggestion_says_the_call_loudly(self):
        take = {"verdict": "TAKE", "score": 82}
        self.assertIn("🎯 PULL THE TRIGGER: A+ trade, adviser says TAKE 82/100", tiers.suggestion("A+", take))
        self.assertIn("⚠️ SIZE DOWN", tiers.suggestion("A+", {"verdict": "CAUTION", "score": 55}))
        self.assertIn("⛔ STAND DOWN", tiers.suggestion("A", {"verdict": "SKIP", "score": 30}))
        self.assertIn("An A+ would rank above it", tiers.suggestion("A", take))
        self.assertIn("3 models agree", tiers.suggestion("A", take, models=3))
        self.assertIn("OPTIONAL", tiers.suggestion("B", take))
        self.assertIn("no adviser verdict yet", tiers.suggestion("A+", None))   # a model that has not kept the matrix
        self.assertIn("Filled", tiers.suggestion("A", take, filled=True))


class AlertFlowTest(unittest.TestCase):
    def test_events_carry_grade_kind_and_the_suggestion(self):
        evs = {e["kind"]: e for e in scanner.pending_events(report("A+", {"verdict": "TAKE", "score": 80}))}
        self.assertEqual((evs["trade"]["grade"], evs["forming"]["grade"]), ("A+", None))
        self.assertTrue(evs["trade"]["body"].startswith("🎯 PULL THE TRIGGER: A+ trade, adviser says TAKE 80/100"), evs["trade"]["body"])
        self.assertIn("\n", evs["trade"]["body"])
        self.assertNotIn("\\n", evs["trade"]["body"])     # real line breaks, not the two characters backslash and n

    def test_a_c_grade_trade_is_never_alerted(self):
        kinds = [e["kind"] for e in scanner.pending_events(report("C"))]
        self.assertNotIn("trade", kinds)

    def test_each_phone_keeps_only_what_its_tier_allows(self):
        subs = [{"endpoint": f"https://{t}", "p256dh": "k", "auth": "a", "tier": t} for t in ("aplus", "a", "b")] + \
               [{"endpoint": "https://old", "p256dh": "k", "auth": "a"}]      # a phone saved before tiers: the default
        got = {}
        evs = [{"id": "A", "title": "t", "body": "b", "grade": "A", "kind": "trade"},
               {"id": "B", "title": "t", "body": "b", "grade": "B", "kind": "trade"},
               {"id": "P", "title": "t", "body": "b", "grade": "A+", "kind": "trade"},
               {"id": "F", "title": "t", "body": "b", "grade": None, "kind": "forming", "priority": "low"}]
        def fake(sub, msg, key, urgency):
            got.setdefault(sub["endpoint"][8:], []).append(msg["tag"])
            return 201
        with mock.patch.dict(os.environ, {"CRON_SECRET": "s"}), mock.patch.object(wp, "subscriptions", return_value=subs), mock.patch.object(wp, "send", side_effect=fake):
            wp.broadcast(evs)
        self.assertEqual(got, {"aplus": ["P"], "a": ["A", "P"], "b": ["A", "B", "P", "F"], "old": ["A", "P"]})

    def test_the_shared_topic_gets_the_channel_tier_and_the_rest_a_silent_log(self):
        posted = []
        def fake_http(url, data=None, headers=None, timeout=8):
            if data is None:
                return b""
            posted.append((url, headers["Tags"]))
            return b""
        rep = report("B", {"verdict": "TAKE", "score": 70})
        with mock.patch.object(scanner, "_http", fake_http), mock.patch.object(scanner, "ntfy_topic", return_value="topic"), \
             mock.patch("ict_trader.webpush.broadcast", return_value={"sent": 0}) as bc:
            os.environ.pop("NOTIFY_MIN_GRADE", None)
            out = scanner.notify(rep)
        self.assertEqual(out["sent"], [])                                   # a B trade does not reach the A-and-up channel...
        self.assertTrue(posted and all(u.endswith("/topic-log") for u, _ in posted), posted)   # ...but is remembered, so it is not re-sent
        self.assertTrue(any("gr-B" in t for _, t in posted))
        self.assertEqual(len(bc.call_args[0][0]), len(posted))               # and the phones saw every event to filter themselves

    def test_a_cancelled_limit_follows_the_grade_it_was_sent_with(self):
        history = json.dumps({"event": "message", "tags": ["x", "id-EU-order-1", "gr-A+"]}).encode()
        with mock.patch.object(scanner, "_http", return_value=history):
            got = scanner.already_sent("topic")
        self.assertEqual(got, {"EU-order-1": "A+"})


if __name__ == "__main__":
    unittest.main()
