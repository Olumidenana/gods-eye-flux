import hashlib
import hmac
import json
import os
import unittest
from datetime import datetime, timedelta, timezone
from unittest import mock

from ict_trader import access, accounts

NOW = datetime(2026, 10, 10, 12, 0, tzinfo=timezone.utc)
ENV = {"ACCESS_SECRET": "x", "OWNER_EMAILS": "boss@example.com", "PAYSTACK_SECRET_KEY": "sk_test_1",
       "PRO_MONTH_NGN": "5000", "PRO_YEAR_NGN": "50000", "TRIAL_DAYS": "7"}


class FakeStore:
    def __init__(self, users):
        self.users, self.profiles, self.payments, self.visits = users, {}, {}, []

    def user_from_token(self, token):
        if token not in self.users:
            raise PermissionError("Your sign-in has expired. Please sign in again.")
        return self.users[token]

    def profile(self, uid):
        return self.profiles.get(uid)

    def create_profile(self, row):
        return self.profiles.setdefault(row["user_id"], dict(row))

    def update_profile(self, uid, fields):
        self.profiles[uid].update(fields)

    def count_visit(self, uid, day):
        self.visits.append((uid, day))

    def add_payment(self, row):
        if row["reference"] in self.payments:
            return False
        self.payments[row["reference"]] = row
        return True

    def all_profiles(self):
        return list(self.profiles.values())

    def all_payments(self):
        return list(self.payments.values())

    def usage(self, since):
        return []


def user(uid, email):
    return {"id": uid, "email": email, "email_confirmed_at": "2026-01-01T00:00:00Z", "user_metadata": {"full_name": email.split("@")[0].title()}}


class AccountsTest(unittest.TestCase):
    def setUp(self):
        self.env = mock.patch.dict(os.environ, ENV)
        self.env.start()
        self.store = FakeStore({"t1": user("u1", "ada@example.com"), "t0": user("u0", "boss@example.com")})

    def tearDown(self):
        self.env.stop()

    def test_first_sign_in_starts_a_seven_day_trial_with_a_pass(self):
        out = accounts.me("t1", self.store, NOW)
        self.assertEqual(out["plan"]["plan"], "trial")
        self.assertEqual(out["plan"]["days_left"], 7)
        self.assertEqual(access.verify(out["pass"]["token"], NOW.timestamp())["c"], "u:u1")  # works on every gated endpoint
        self.assertEqual(self.store.visits, [("u1", "2026-10-10")])
        later = accounts.me("t1", self.store, NOW + timedelta(days=8))
        self.assertEqual(later["plan"]["plan"], "free")
        self.assertNotIn("pass", later)  # trial over: no pass, so signals, alerts and bots are locked
        with self.assertRaises(PermissionError):
            accounts.me("bad-token", self.store, NOW)

    def test_invite_only_gives_nothing_to_anyone_not_listed(self):
        with mock.patch.dict(os.environ, {"ALLOWED_EMAILS": "friend@example.com, Ada@Example.com"}):
            out = accounts.me("t1", self.store, NOW)                       # ada@example.com is listed (any case)
            self.assertEqual(out["plan"]["plan"], "trial")
            self.assertIn("pass", out)
            self.store.users["t9"] = user("u9", "stranger@example.com")
            blocked = accounts.me("t9", self.store, NOW)
            self.assertEqual((blocked["plan"]["plan"], blocked["plan"]["active"], blocked["invite_only"]), ("invite", False, True))
            self.assertNotIn("pass", blocked)
            self.assertNotIn("u9", self.store.profiles)                    # no profile, so no trial clock either
            self.assertEqual(accounts.me("t0", self.store, NOW)["plan"]["plan"], "owner")  # the owner is always in
            self.assertTrue(accounts.public_config()["invite_only"])
            self.assertTrue(access.required())                             # an invite list always locks the data
        self.assertFalse(accounts.public_config()["invite_only"])

    def test_owner_is_always_in(self):
        out = accounts.me("t0", self.store, NOW + timedelta(days=400))
        self.assertEqual(out["plan"]["plan"], "owner")
        self.assertIn("pass", out)

    def test_payments_extend_pro_once_and_only_at_full_price(self):
        accounts.me("t1", self.store, NOW)
        tx = {"status": "success", "reference": "ifx-1", "amount": 500000, "currency": "NGN", "paid_at": NOW.isoformat(),
              "metadata": {"user_id": "u1", "period": "month"}, "customer": {"email": "ada@example.com"}}
        self.assertTrue(accounts.apply_payment(tx, self.store, NOW)["applied"])
        self.assertFalse(accounts.apply_payment(tx, self.store, NOW)["applied"])  # the webhook and the return both arrive: credited once
        until = datetime.fromisoformat(self.store.profiles["u1"]["pro_until"])
        self.assertEqual(until, NOW + timedelta(days=30))
        accounts.apply_payment({**tx, "reference": "ifx-2", "amount": 5000000, "metadata": {"user_id": "u1", "period": "year"}}, self.store, NOW)
        self.assertEqual(datetime.fromisoformat(self.store.profiles["u1"]["pro_until"]), NOW + timedelta(days=395))  # stacks on top
        self.assertEqual(accounts.me("t1", self.store, NOW + timedelta(days=100))["plan"]["plan"], "pro")
        for bad in ({**tx, "reference": "x1", "amount": 100}, {**tx, "reference": "x2", "status": "failed"},
                    {**tx, "reference": "x3", "metadata": {"period": "month"}}):
            with self.assertRaises(ValueError):
                accounts.apply_payment(bad, self.store, NOW)
        with self.assertRaises(ValueError):
            accounts.apply_payment({**tx, "reference": "x4"}, self.store, NOW, expect_user="someone-else")

    def test_payment_guards(self):
        tx = {"status": "success", "reference": "g1", "amount": 500000, "currency": "NGN", "paid_at": NOW.isoformat(),
              "metadata": {"user_id": "u1", "period": "month"}, "customer": {"email": "ada@example.com"}}
        accounts.me("t1", self.store, NOW)
        with mock.patch.dict(os.environ, {"PAYSTACK_SECRET_KEY": "sk_live_1"}):
            for bad in ({**tx, "currency": None}, {**tx, "currency": "USD"}, {**tx, "domain": "test"}):
                with self.assertRaises(ValueError):
                    accounts.apply_payment({**bad, "reference": "g-bad"}, self.store, NOW)
        # a failed grant is not recorded, so a retry can still credit it
        real = self.store.update_profile
        self.store.delete_payment = lambda ref: self.store.payments.pop(ref, None)
        self.store.update_profile = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("db down"))
        with self.assertRaises(RuntimeError):
            accounts.apply_payment(tx, self.store, NOW)
        self.assertNotIn("g1", self.store.payments)
        self.store.update_profile = real
        self.assertTrue(accounts.apply_payment(tx, self.store, NOW)["applied"])

    def test_unverified_email_is_never_the_owner_or_invited(self):
        self.store.users["tx"] = {"id": "ux", "email": "boss@example.com", "user_metadata": {}}  # not confirmed
        self.assertNotEqual(accounts.me("tx", self.store, NOW)["plan"]["plan"], "owner")

    def test_checkout_return_url_only_uses_our_own_hosts(self):
        self.assertEqual(accounts.app_url("ictflux.app"), "https://ictflux.app")
        self.assertEqual(accounts.app_url("evil.example"), "https://ictflux.app")
        self.assertEqual(accounts.app_url("ict-trader.vercel.app:443"), "https://ict-trader.vercel.app")

    def test_webhook_signature(self):
        raw = json.dumps({"event": "charge.success"}).encode()
        sig = hmac.new(b"sk_test_1", raw, hashlib.sha512).hexdigest()
        self.assertTrue(accounts.webhook_ok(raw, sig))
        self.assertFalse(accounts.webhook_ok(raw, "0" * 128))
        self.assertFalse(accounts.webhook_ok(raw, "é" * 64))  # a non-ASCII header is refused, not a crash

    def test_checkout_asks_paystack_for_the_plan_price(self):
        sent = {}

        def fake(method, url, body=None, headers=None, timeout=10):
            sent.update(url=url, body=body, auth=headers["Authorization"])
            return 200, {"status": True, "data": {"authorization_url": "https://checkout.paystack.com/abc"}}
        with mock.patch.object(accounts, "_http", fake):
            out = accounts.checkout({"id": "u1-uuid", "email": "ada@example.com"}, "year", "https://ictflux.app/?paid=1")
        self.assertEqual(out["url"], "https://checkout.paystack.com/abc")
        self.assertEqual((sent["body"]["amount"], sent["body"]["currency"]), (5000000, "NGN"))
        self.assertEqual(sent["body"]["metadata"]["period"], "year")
        self.assertEqual(sent["auth"], "Bearer sk_test_1")
        with self.assertRaises(ValueError):
            accounts.checkout({"id": "u", "email": "e"}, "week", "x")

    def test_owner_numbers(self):
        class S(FakeStore):
            def all_profiles(self):
                return [{"user_id": "a", "email": "a@x", "created_at": NOW.isoformat(), "trial_ends_at": (NOW + timedelta(days=3)).isoformat()},
                        {"user_id": "b", "email": "b@x", "created_at": (NOW - timedelta(days=40)).isoformat(), "pro_until": (NOW + timedelta(days=9)).isoformat()},
                        {"user_id": "c", "email": "c@x", "created_at": (NOW - timedelta(days=20)).isoformat(), "trial_ends_at": (NOW - timedelta(days=13)).isoformat()}]

            def all_payments(self):
                return [{"reference": "r", "amount_kobo": 500000, "paid_at": (NOW - timedelta(days=2)).isoformat()}]

            def usage(self, since):
                return [{"user_id": "a", "day": "2026-10-10"}, {"user_id": "b", "day": "2026-10-10"}, {"user_id": "b", "day": "2026-10-05"}]
        st = accounts.stats(S({}), NOW)
        self.assertEqual((st["users"], st["on_trial"], st["pro"], st["free"]), (3, 1, 1, 1))
        self.assertEqual((st["active_today"], st["active_7d"], st["revenue_30d_ngn"]), (2, 2, 5000))
        self.assertEqual(len(st["signups_by_day"]), 30)

    def test_signout_marks_user_as_offline(self):
        store = FakeStore({"t1": user("u1", "ada@example.com")})
        # First verify user is online when active
        accounts.me("t1", store=store, now=NOW)
        st_online = accounts.stats(store, now=NOW)
        self.assertTrue(st_online["recent_users"][0]["is_online"])
        # Now sign out
        ok = accounts.signout("t1", store=store, now=NOW)
        self.assertTrue(ok)
        st_offline = accounts.stats(store, now=NOW)
        self.assertFalse(st_offline["recent_users"][0]["is_online"])
        self.assertGreaterEqual(st_offline["recent_users"][0]["seconds_ago"], 600)

    def test_dedupe_profiles_by_email(self):
        profs = [
            {"user_id": "u1", "email": "trader@example.com", "name": "Trader", "created_at": "2026-10-01T10:00:00Z", "visits": 2, "plan": "free"},
            {"user_id": "u2", "email": "TRADER@EXAMPLE.COM", "name": "Real Name", "created_at": "2026-09-20T10:00:00Z", "visits": 5, "plan": "pro"},
            {"user_id": "u3", "email": "other@example.com", "name": "Other", "created_at": "2026-10-05T10:00:00Z", "visits": 1, "plan": "trial"}
        ]
        res = accounts.dedupe_profiles(profs)
        self.assertEqual(len(res), 2)
        t = next(p for p in res if p["email"].lower() == "trader@example.com")
        self.assertEqual(t["name"], "Real Name")
        self.assertEqual(t["created_at"], "2026-09-20T10:00:00Z")
        self.assertEqual(t["visits"], 5)
        self.assertEqual(t["plan"], "pro")


if __name__ == "__main__":
    unittest.main()
