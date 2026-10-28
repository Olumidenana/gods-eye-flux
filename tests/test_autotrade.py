import os
import unittest
from datetime import datetime, timedelta, timezone
from unittest import mock

from cryptography.fernet import Fernet

from ict_trader import autotrade as at

NOW = datetime(2026, 10, 7, 14, 0, tzinfo=timezone.utc)
DEMO = [{"id": "VRTC1", "type": "demo", "currency": "USD", "balance": 10000}, {"id": "CR9", "type": "real", "currency": "USD", "balance": 50}]


def sig(sid="EURUSD-1", minutes_ago=2, status="open", cls="forex"):
    return {"id": sid, "label": "EUR/USD", "broker_symbol": "frxEURUSD", "direction": "long", "entry": 1.1, "stop": 1.099,
            "target": 1.103, "rr": 3.0, "quality": {"grade": "A"}, "advice": {"verdict": "TAKE", "score": 80}, "time": (NOW - timedelta(minutes=minutes_ago)).isoformat(), "timeframe_minutes": 5,
            "outcome": {"status": status}}


def report(*sigs, cls="forex"):
    return {"markets": [{"ok": True, "cls": cls, "today": {"signals": list(sigs)}}]}


class FakeTrader:
    def __init__(self, balance=10000.0, open_n=0):
        self.bal, self.open_n, self.placed, self.closed, self.currency = balance, open_n, [], False, "USD"

    def balance(self):
        return self.bal

    def open_positions(self):
        return self.open_n

    def place(self, s, risk):
        self.placed.append((s["id"], risk))
        return {**at.sizing(s, risk, [10, 20, 50, 100], 1), "contract_id": 123}

    def close(self):
        self.closed = True

    def open_contracts(self):
        return getattr(self, "contracts", [])

    def update_stop(self, cid, sl, tp):
        self.updates = getattr(self, "updates", []) + [(cid, sl, tp)]


class AutotradeTest(unittest.TestCase):
    def setUp(self):
        self.env = mock.patch.dict(os.environ, {"AUTOTRADE_KEY": Fernet.generate_key().decode()})
        self.env.start()
        self.store = at.MemoryStore()

    def tearDown(self):
        self.env.stop()

    def enroll(self, **kw):
        body = {"token": "tok-123456789", "account_id": "VRTC1", "accept_terms": True, "terms_version": at.TERMS_VERSION, **kw}
        return at.enroll(self.store, body, accounts=lambda t: DEMO, now=NOW)

    def test_enroll_needs_terms_and_real_confirmation(self):
        with self.assertRaises(ValueError):
            at.enroll(self.store, {"token": "tok-123456789", "account_id": "VRTC1"}, accounts=lambda t: DEMO)
        with self.assertRaises(ValueError):
            self.enroll(account_id="CR9")
        self.assertEqual(self.enroll(account_id="CR9", confirm_real="REAL")["account_type"], "real")

    def test_token_is_encrypted_and_never_public(self):
        e = self.enroll()
        u = self.store.get_user(e["id"])
        self.assertNotIn("tok-123456789", str(u))
        self.assertEqual(at.decrypt(u["token_enc"]), "tok-123456789")
        self.assertNotIn("token_enc", at.public(u))
        self.assertNotIn("manage_hash", at.public(u))
        with self.assertRaises(PermissionError):
            at.authorize(self.store, e["id"], "wrong-key")
        self.assertEqual(at.authorize(self.store, e["id"], e["manage_key"])["id"], e["id"])

    def test_settings_are_bounded(self):
        with self.assertRaises(ValueError):
            self.enroll(risk_pct=5)
        with self.assertRaises(ValueError):
            self.enroll(classes=["nonsense"])

    def test_run_places_fresh_signals_once_with_risk_sized_stake(self):
        self.enroll(risk_pct=1)
        t = FakeTrader()
        out = at.run(self.store, report(sig(), sig("OLD", minutes_ago=30), sig("DONE", status="win")), trader=lambda u, tok: t, now=NOW)
        self.assertEqual(out["placed"], 1)
        self.assertEqual(t.placed, [("EURUSD-1", 100.0)])  # 1% of 10,000
        self.assertTrue(t.closed)
        again = FakeTrader()
        at.run(self.store, report(sig()), trader=lambda u, tok: again, now=NOW + timedelta(minutes=1))
        self.assertEqual(again.placed, [])  # never placed twice

    def test_limits_and_market_groups(self):
        self.enroll(max_open=1, classes=["index"])
        t = FakeTrader()
        at.run(self.store, report(sig()), trader=lambda u, tok: t, now=NOW)
        self.assertEqual(t.placed, [])  # forex not chosen
        self.store = at.MemoryStore()
        self.enroll(max_open=1)
        t = FakeTrader(open_n=1)
        out = at.run(self.store, report(sig()), trader=lambda u, tok: t, now=NOW)
        self.assertEqual((out["placed"], out["skipped"]), (0, 1))

    def test_daily_loss_limit_pauses_for_the_day(self):
        e = self.enroll(day_loss_pct=2)
        at.run(self.store, report(), trader=lambda u, tok: FakeTrader(10000), now=NOW)  # records the day's start balance
        t = FakeTrader(9790)
        out = at.run(self.store, report(sig()), trader=lambda u, tok: t, now=NOW)
        self.assertEqual(t.placed, [])
        self.assertEqual(out["skipped"], 1)
        self.assertEqual(self.store.get_user(e["id"])["paused_reason"], "Daily loss limit reached")

    def test_rejected_token_disables_and_says_why(self):
        e = self.enroll()

        def bad(u, tok):
            raise PermissionError("invalid token")
        at.run(self.store, report(sig()), trader=bad, now=NOW)
        u = self.store.get_user(e["id"])
        self.assertFalse(u["enabled"])
        self.assertIn("reconnect", u["paused_reason"])

    def test_tp1_partial_is_a_second_half_size_contract(self):
        self.enroll(risk_pct=1)
        t = FakeTrader()
        s = {**sig(), "setup": {"tp1": 1.1015}}
        out = at.run(self.store, report(s), trader=lambda u, tok: t, now=NOW)
        self.assertEqual(out["placed"], 1)
        self.assertEqual([r for _, r in t.placed], [50.0, 50.0])  # half the risk on each leg

    def test_quality_filters_skip_low_rr_and_low_grade(self):
        self.enroll(min_rr=3, min_grade="A")
        t = FakeTrader()
        good = {**sig("GOOD"), "rr": 3.5, "quality": {"grade": "A+"}}
        low_rr = {**sig("LOWRR"), "rr": 2.0, "quality": {"grade": "A+"}}
        low_g = {**sig("LOWG"), "rr": 4.0, "quality": {"grade": "B"}}
        at.run(self.store, report(good, low_rr, low_g), trader=lambda u, tok: t, now=NOW)
        self.assertEqual([i for i, _ in t.placed], ["GOOD"])
        with self.assertRaises(ValueError):
            self.enroll(min_grade="Z")

    def test_demo_accounts_are_recognised_like_the_browser_bot(self):
        rows = [{"account_id": "DOT93185437", "currency": "USD"}, {"account_id": "ROT91882629"},
                {"loginid": "VRTC1"}, {"id": "CR1", "type": "Demo"}, {"id": "CR2", "account_type": "real"}]
        with mock.patch.object(at, "_http", return_value={"data": rows}):
            kinds = [a["type"] for a in at.deriv_accounts("tok")]
        self.assertEqual(kinds, ["demo", "real", "demo", "demo", "real"])

    def test_database_errors_say_why_and_how_to_fix(self):
        msg = at._db_error(400, b'{"code":"PGRST204","message":"Could not find the \'min_rr\' column"}')
        self.assertIn("PGRST204", msg)
        self.assertIn("db/autotrade.sql", msg)
        self.assertIn("SUPABASE_SERVICE_KEY", at._db_error(401, b'{"message":"Invalid API key"}'))

    def test_stop_steps_follow_ict(self):
        self.assertIsNone(at.stop_step(40, 100, 50, 50, trim=True))           # 40% of the way: nothing yet
        self.assertEqual(at.stop_step(55, 100, 50, 50, trim=True), 37.5)      # halfway: risk cut 25%
        self.assertIsNone(at.stop_step(55, 100, 50, 50, trim=False))          # plan without SL-04
        self.assertEqual(at.stop_step(80, 100, 37.5, 50, trim=True), 2.5)     # 75%: near entry
        self.assertIsNone(at.stop_step(80, 100, 2.5, 50, trim=True))          # never loosens or repeats

    def test_open_trades_get_their_stops_moved(self):
        self.enroll(risk_pct=1)
        t = FakeTrader()
        s = {**sig(), "management": {"partial": 0.0, "trim_50": True}}
        at.run(self.store, report(s), trader=lambda u, tok: t, now=NOW)
        t2 = FakeTrader()
        t2.contracts = [{"contract_id": "123", "profit": 160.0, "take_profit": 300.0, "stop_loss": 100.0}]  # 53% of the way
        out = at.run(self.store, report(), trader=lambda u, tok: t2, now=NOW + timedelta(minutes=5))
        self.assertEqual(t2.updates, [("123", 75.0, 300.0)])
        self.assertEqual(out.get("managed"), 1)

    def test_sizing_loses_the_risk_at_the_stop(self):
        p = at.sizing({"entry": 1.1, "stop": 1.099, "target": 1.103}, 100, [10, 20, 50, 100, 200], 1)
        loss_at_stop = p["stake"] * p["multiplier"] * (0.001 / 1.1)
        self.assertAlmostEqual(loss_at_stop, 100, delta=0.5)
        self.assertEqual(p["stop_loss"], 100)
        self.assertAlmostEqual(p["take_profit"], 300, delta=0.01)


if __name__ == "__main__":
    unittest.main()


class RunnerBreakevenTest(unittest.TestCase):
    """TP-04: once the TP1 leg is banked the runner's stop goes to entry, whatever its own progress to the target."""

    def setUp(self):
        self.store = at.MemoryStore()
        self.u = {"id": "u1"}
        for leg, cid in (("TP1", "11"), ("TP2", "22")):
            self.store.add_log({"user_id": "u1", "kind": "placed", "signal_id": "sig-1", "market": "Volatility 75", "contract_id": cid,
                                "message": f"Buy Volatility 75 {leg} · on the fill · stake 10 x100 · SL 20.0 / TP 40.0 USD · stop plan: trim 25% halfway, entry at 75%"})

    def run_it(self, contracts):
        t = FakeTrader()
        t.contracts = contracts
        summary = {}
        at.manage_stops(self.store, self.u, t, summary)
        return t, summary

    def test_the_runner_goes_to_entry_when_the_tp1_leg_has_closed(self):
        t, summary = self.run_it([{"contract_id": "22", "profit": 6.0, "stop_loss": 20.0, "take_profit": 40.0}])   # only 15% of the way to TP2
        self.assertEqual(t.updates, [("22", 1.0, 40.0)])
        self.assertEqual(summary["managed"], 1)
        self.assertIn("TP1 banked", self.store.logs("u1", 10, kind="managed")[0]["message"])

    def test_the_runner_keeps_its_stop_while_the_tp1_leg_is_still_open(self):
        t, _ = self.run_it([{"contract_id": "11", "profit": 3.0, "stop_loss": 20.0, "take_profit": 15.0},
                            {"contract_id": "22", "profit": 3.0, "stop_loss": 20.0, "take_profit": 40.0}])
        self.assertFalse(hasattr(t, "updates"))

    def test_a_stop_already_at_entry_is_left_alone(self):
        t, _ = self.run_it([{"contract_id": "22", "profit": 6.0, "stop_loss": 1.0, "take_profit": 40.0}])
        self.assertFalse(hasattr(t, "updates"))
