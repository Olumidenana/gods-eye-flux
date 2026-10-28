"""Real-time entries keep the plan: at the touch, at the live price, with the stop and target on their levels."""
import os
import unittest
from datetime import datetime, timedelta, timezone
from unittest import mock

from cryptography.fernet import Fernet

from ict_trader import autotrade as at
from ict_trader import entryguard as eg

NOW = datetime(2026, 10, 7, 14, 0, tzinfo=timezone.utc)
DEMO = [{"id": "VRTC1", "type": "demo", "currency": "USD", "balance": 10000}]
PLAN = {"direction": "long", "entry": 100.0, "stop": 99.0, "target": 103.0, "tp1": 101.5}      # 1R = 1.0, 3R to the target


class CheckTest(unittest.TestCase):
    def test_at_the_entry_the_plan_holds(self):
        c = eg.check(PLAN, 100.0)
        self.assertTrue(c.ok)
        self.assertAlmostEqual(c.rr_now, 3.0)

    def test_deeper_than_the_entry_is_fine_until_the_idea_is_failing(self):
        self.assertTrue(eg.check(PLAN, 99.5).ok)                      # -0.5R: a deeper retrace, more reward left
        self.assertGreater(eg.check(PLAN, 99.5).rr_now, 3.0)
        self.assertIn("failing", eg.check(PLAN, 99.2).reason)         # -0.8R: through the entry toward the stop
        self.assertIn("through the stop", eg.check(PLAN, 98.9).reason)

    def test_price_that_has_already_run_is_not_chased(self):
        self.assertTrue(eg.check(PLAN, 100.2).ok)                     # +0.2R: still the entry
        c = eg.check(PLAN, 100.4)                                     # +0.4R: gone
        self.assertFalse(c.ok)
        self.assertIn("not chasing", c.reason)
        self.assertIn("already past the first target", eg.check(PLAN, 101.6).reason)
        self.assertIn("already at the target", eg.check({**PLAN, "tp1": None}, 103.1).reason)

    def test_a_trade_that_no_longer_pays_the_plans_reward_is_refused(self):
        thin = {**PLAN, "target": 101.4, "tp1": None}                  # 1.4R plan
        self.assertIn("under the 1.5R", eg.check(thin, 100.0).reason)
        self.assertTrue(eg.check(thin, 100.0, min_rr=1.0).ok)

    def test_short_is_the_mirror(self):
        s = {"direction": "short", "entry": 100.0, "stop": 101.0, "target": 97.0, "tp1": 98.5}
        self.assertTrue(eg.check(s, 100.0).ok and eg.check(s, 100.5).ok)
        self.assertIn("not chasing", eg.check(s, 99.6).reason)
        self.assertIn("failing", eg.check(s, 100.8).reason)
        self.assertIn("through the stop", eg.check(s, 101.1).reason)
        self.assertTrue(eg.touched(s, 100.0) and eg.touched(s, 100.3) and not eg.touched(s, 99.9))
        self.assertTrue(eg.touched(PLAN, 100.0) and eg.touched(PLAN, 99.7) and not eg.touched(PLAN, 100.1))


class SizingTest(unittest.TestCase):
    def test_the_stop_and_the_target_stay_on_their_levels_from_the_live_price(self):
        plan = {"entry": 100.0, "stop": 99.0, "target": 103.0}
        at_plan = at.sizing(plan, 100.0, [10, 20, 50, 100], 1)
        low = at.sizing(plan, 100.0, [10, 20, 50, 100], 1, spot=99.5)       # filled deeper: the stop is nearer, the target farther
        self.assertEqual(at_plan["stop_loss"], 100.0)
        self.assertEqual(low["stop_loss"], 100.0)                           # the risk is the risk
        self.assertAlmostEqual(low["take_profit"], 100.0 * (103 - 99.5) / (99.5 - 99.0), places=1)   # 700, not 300
        self.assertGreater(low["take_profit"], at_plan["take_profit"])      # the target level did not move with the entry


class Trader:
    def __init__(self, spot, balance=10000.0):
        self._spot, self.bal, self.placed, self.currency = spot, balance, [], "USD"

    def balance(self):
        return self.bal

    def open_positions(self):
        return 0

    def spot(self, sym):
        return self._spot

    def place(self, s, risk, spot=None):
        self.placed.append((s["id"], risk, spot))
        return {**at.sizing(s, risk, [10, 20, 50, 100], 1, spot), "contract_id": 7}

    def close(self):
        pass

    def open_contracts(self):
        return []


def fill(minutes_ago=2, verdict="TAKE", sid="EU-1", mss=111):
    return {"id": sid, "market": "EU", "label": "EUR/USD", "broker_symbol": "frxEURUSD", "direction": "long", "entry": 100.0, "stop": 99.0,
            "target": 103.0, "rr": 3.0, "quality": {"grade": "A"}, "advice": {"verdict": verdict, "score": 80},
            "time": (NOW - timedelta(minutes=minutes_ago)).isoformat(), "timeframe_minutes": 5, "outcome": {"status": "open"},
            "setup": {"tp1": None, "mss_time": mss}}


def order(placed=111, left=6):
    return {"direction": "long", "entry": 100.0, "stop": 99.0, "tp1": None, "tp2": 103.0, "rr": 3.0, "placed": placed, "candles_left": left,
            "quality": {"grade": "A"}, "advice": {"verdict": "TAKE", "score": 80}}


def report(signals=(), orders=()):
    return {"generated_at": (NOW - timedelta(minutes=1)).isoformat(), "timeframe_minutes": 5,
            "markets": [{"ok": True, "key": "EU", "label": "EUR/USD", "cls": "forex", "broker_symbol": "frxEURUSD", "model": "ict2022",
                         "timeframe_minutes": 5, "today": {"signals": list(signals)}, "models": {"ict2022": {"orders": list(orders), "signals": []}}}]}


class RunTest(unittest.TestCase):
    def setUp(self):
        self.env = mock.patch.dict(os.environ, {"AUTOTRADE_KEY": Fernet.generate_key().decode()})
        self.env.start()
        self.store = at.MemoryStore()
        body = {"token": "tok-123456789", "account_id": "VRTC1", "accept_terms": True, "terms_version": at.TERMS_VERSION, "classes": ["forex"]}
        at.enroll(self.store, body, accounts=lambda t: DEMO, now=NOW)

    def tearDown(self):
        self.env.stop()

    def go(self, rep, spot, only_armed=False, t=None):
        t = t or Trader(spot)
        out = at.run(self.store, rep, trader=lambda u, tok: t, now=NOW, only_armed=only_armed)
        return out, t

    def test_a_fill_is_entered_at_the_live_price_when_the_plan_still_holds(self):
        out, t = self.go(report([fill()]), 100.1)
        self.assertEqual(out["placed"], 1)
        self.assertEqual(t.placed[0][2], 100.1)                       # sized from where it really starts

    def test_a_fill_price_has_run_away_from_is_not_chased_and_says_why(self):
        out, t = self.go(report([fill()]), 100.6)
        self.assertEqual((out["placed"], out["skipped"]), (0, 1))
        self.assertTrue(any("not chasing" in x["message"] for x in self.store.log))
        out2, t2 = self.go(report([fill()]), 100.6)                   # and it is not retried on the next run
        self.assertEqual(out2["placed"], 0)

    def test_only_a_pull_the_trigger_verdict_is_traded(self):
        out, t = self.go(report([fill(verdict="CAUTION")]), 100.0)
        self.assertEqual(out["placed"], 0)
        with mock.patch.dict(os.environ, {"AUTOTRADE_MIN_VERDICT": "CAUTION"}):
            out, t = self.go(report([fill(verdict="CAUTION", sid="EU-2")]), 100.0)
            self.assertEqual(out["placed"], 1)

    def test_a_resting_limit_is_entered_the_moment_price_touches_it_not_at_the_close(self):
        rep = report(orders=[order()])
        before = len(self.store.log)
        out, t = self.go(rep, 100.4, only_armed=True)                 # not reached: nothing happens, nothing is logged
        self.assertEqual((out["placed"], out["skipped"], len(self.store.log)), (0, 0, before))
        out, t = self.go(rep, 99.95, only_armed=True)                 # reached
        self.assertEqual(out["placed"], 1)
        self.assertEqual(t.placed[0][0], "armed:EU:111")
        out, t = self.go(rep, 99.9, only_armed=True)                  # and only once
        self.assertEqual(out["placed"], 0)

    def test_the_fill_of_an_order_already_entered_at_the_touch_is_the_same_trade(self):
        self.go(report(orders=[order()]), 99.95, only_armed=True)
        out, t = self.go(report([fill(mss=111)]), 100.0)              # the candle closes and the fill shows up
        self.assertEqual(out["placed"], 0)

    def test_an_order_that_is_expired_or_from_an_old_scan_is_not_armed(self):
        self.assertEqual(eg.armed_orders(report(orders=[order(left=0)]), NOW), [])
        self.assertEqual(eg.armed_orders(report(orders=[order(left=1)]), NOW + timedelta(minutes=10)), [])   # its one candle has run out
        old = report(orders=[order()])
        old["generated_at"] = (NOW - timedelta(minutes=200)).isoformat()
        self.assertEqual(eg.armed_orders(old, NOW), [])
        self.assertEqual(len(eg.armed_orders(report(orders=[order()]), NOW)), 1)

    def test_a_failing_idea_is_logged_once_and_not_entered(self):
        out, t = self.go(report(orders=[order()]), 99.1, only_armed=True)      # touched, but 0.9R through the entry
        self.assertEqual((out["placed"], out["skipped"]), (0, 1))
        self.assertTrue(any("failing" in x["message"] for x in self.store.log))


if __name__ == "__main__":
    unittest.main()


class FeedTest(unittest.TestCase):
    def test_the_live_price_comes_from_the_public_feed_and_tries_the_next_endpoint(self):
        import json as _json

        class WS:
            def __init__(self, prices):
                self.sent, self.prices, self.closed = [], prices, False

            def send(self, data):
                self.sent.append(_json.loads(data))

            def recv(self):
                req = self.sent[-1]
                return _json.dumps({"req_id": req["req_id"], "history": {"prices": self.prices}} if self.prices else {"req_id": req["req_id"], "error": {"message": "bad"}})

            def close(self):
                self.closed = True
        urls = []

        def connect(u):
            urls.append(u)
            if "api.derivws.com" in u:
                raise OSError("down")                  # the first endpoint is unreachable: the second is used
            return WS([1.1, 1.2345])
        f = eg.PublicFeed(connect)
        self.assertEqual(f.price("frxEURUSD"), 1.2345)
        self.assertEqual(len(urls), 2)
        f.close()
        bad = eg.PublicFeed(lambda u: WS([]))
        with self.assertRaises(RuntimeError):
            bad.price("x")
