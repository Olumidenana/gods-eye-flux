import io
import os
import unittest
from datetime import datetime, timedelta, timezone
from unittest import mock

from cryptography.fernet import Fernet

from ict_trader import access
from ict_trader import autotrade as at

NOW = datetime(2026, 10, 7, 14, 0, tzinfo=timezone.utc)


class Codes:
    def __init__(self, *rows):
        self.rows = {r["code"].upper(): r for r in rows}
        self.touched = []

    def get(self, code):
        return self.rows.get(code.upper())

    def touch(self, code, now):
        self.touched.append(code)


CODES = Codes({"code": "TUNDE-OCT", "name": "Tunde", "expires_at": (NOW + timedelta(days=30)).isoformat(), "enabled": True},
              {"code": "OLD-1", "name": "Ade", "expires_at": (NOW - timedelta(days=1)).isoformat(), "enabled": True},
              {"code": "OFF-1", "name": "Bola", "expires_at": None, "enabled": False})


class FakeHandler:
    def __init__(self, path, headers=None):
        self.path, self.headers, self.wfile, self.status, self.sent = path, headers or {}, io.BytesIO(), None, {}

    def send_response(self, s):
        self.status = s

    def send_header(self, k, v):
        self.sent[k] = v

    def end_headers(self):
        pass


class AccessTest(unittest.TestCase):
    def setUp(self):
        self.env = mock.patch.dict(os.environ, {"ACCESS_REQUIRED": "1", "AUTOTRADE_KEY": Fernet.generate_key().decode(), "OWNER_CODE": "BOSS-1"})
        self.env.start()

    def tearDown(self):
        self.env.stop()

    def test_codes_open_until_they_end_or_are_switched_off(self):
        p = access.redeem("tunde-oct", CODES, NOW)  # not case sensitive
        self.assertEqual(p["name"], "Tunde")
        self.assertEqual(access.verify(p["token"], NOW.timestamp())["c"], "TUNDE-OCT")
        with self.assertRaisesRegex(PermissionError, "ended"):
            access.redeem("OLD-1", CODES, NOW)
        with self.assertRaisesRegex(PermissionError, "not valid"):
            access.redeem("OFF-1", CODES, NOW)
        with self.assertRaisesRegex(PermissionError, "not valid"):
            access.redeem("NOPE-9", CODES, NOW)
        with self.assertRaisesRegex(PermissionError, "not valid"):
            access.redeem("bad code%", CODES, NOW)
        self.assertEqual(access.redeem("boss-1", None, NOW)["name"], "Owner")  # owner needs no table

    def test_pass_cannot_be_forged_and_never_outlives_the_code(self):
        p = access.redeem("TUNDE-OCT", CODES, NOW)
        body, sig = p["token"].split(".")
        with self.assertRaises(PermissionError):
            access.verify(body + "x." + sig, NOW.timestamp())
        with self.assertRaises(PermissionError):
            access.verify(p["token"], NOW.timestamp() + access.PASS_TTL + 1)
        short = Codes({"code": "SOON-1", "name": "S", "expires_at": (NOW + timedelta(hours=1)).isoformat(), "enabled": True})
        self.assertEqual(access.redeem("SOON-1", short, NOW)["pass_expires"], int((NOW + timedelta(hours=1)).timestamp()))

    def test_gate_refuses_without_a_pass_and_lets_internal_and_valid_requests_through(self):
        h = FakeHandler("/api/scan?tf=5")
        self.assertFalse(access.gate(h))
        self.assertEqual((h.status, h.sent.get("X-Access-Required")), (401, "1"))
        self.assertTrue(access.gate(FakeHandler(f"/api/scan?tf=5&_int={access.internal_key()}")))
        tok = access.issue("TUNDE-OCT", "Tunde", "pro", None, NOW.timestamp())["token"]
        with mock.patch.object(access.time, "time", return_value=NOW.timestamp()):
            self.assertTrue(access.gate(FakeHandler("/api/deriv?op=accounts", {"X-Access": tok}), proxy=False))
        with mock.patch.dict(os.environ, {"ACCESS_REQUIRED": "0"}):
            self.assertTrue(access.gate(FakeHandler("/api/scan")))

    def test_gate_answers_from_the_shared_internal_url(self):
        tok = access.issue("TUNDE-OCT", "Tunde", "pro", None, NOW.timestamp())["token"]
        seen = {}

        class Resp(io.BytesIO):
            status = 200
            headers = {"Content-Type": "text/plain"}

            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

        def fake_open(req, timeout):
            seen["url"] = req.full_url
            return Resp(b"ICTFLUX1|1\n")
        h = FakeHandler(f"/api/scan?format=mt5&access={tok}", {"host": "ict-trader.vercel.app"})
        with mock.patch.object(access.time, "time", return_value=NOW.timestamp()), mock.patch.object(access.urllib.request, "urlopen", fake_open):
            self.assertFalse(access.gate(h))
        self.assertEqual(h.wfile.getvalue(), b"ICTFLUX1|1\n")
        self.assertIn("format=mt5", seen["url"])
        self.assertIn(f"_int={access.internal_key()}", seen["url"])
        self.assertNotIn(tok, seen["url"])  # the pass never reaches the shared cache key
        self.assertEqual(h.sent["Cache-Control"], "private, no-store")

    def test_always_on_bot_stops_when_the_code_ends(self):
        store = at.MemoryStore()
        body = {"token": "tok-123456789", "account_id": "VRTC1", "accept_terms": True, "terms_version": at.TERMS_VERSION, "access_code": "OLD-1"}
        e = at.enroll(store, body, accounts=lambda t: [{"id": "VRTC1", "type": "demo", "currency": "USD", "balance": 1}], now=NOW)
        sig = {"id": "S1", "label": "EUR/USD", "broker_symbol": "frxEURUSD", "direction": "long", "entry": 1.1, "stop": 1.099, "target": 1.103,
               "rr": 3.0, "quality": {"grade": "A"}, "advice": {"verdict": "TAKE", "score": 80}, "time": (NOW - timedelta(minutes=2)).isoformat(), "timeframe_minutes": 5, "outcome": {"status": "open"}}
        report = {"markets": [{"ok": True, "cls": "forex", "today": {"signals": [sig]}}]}

        def trader(u, tok):
            raise AssertionError("must not trade on an ended code")
        out = at.run(store, report, trader=trader, now=NOW, codes=CODES)
        self.assertEqual(out["skipped"], 1)
        self.assertIn("ended", store.get_user(e["id"])["paused_reason"])


if __name__ == "__main__":
    unittest.main()


class SecureByDefaultTests(unittest.TestCase):
    """A deployment that forgot the setting must not be open to the whole internet."""

    def test_the_data_is_locked_unless_the_owner_turns_the_lock_off_on_purpose(self):
        for env, want in (({}, False), ({"ACCESS_REQUIRED": "1"}, True), ({"ACCESS_REQUIRED": ""}, False), ({"ACCESS_REQUIRED": "0"}, False),
                          ({"ACCESS_REQUIRED": "false"}, False), ({"ACCESS_REQUIRED": "off"}, False)):
            with mock.patch.dict(os.environ, env, clear=True):
                self.assertEqual(access.required(), want, env)

    def test_an_invite_list_locks_the_data_even_with_the_lock_switched_off(self):
        with mock.patch.dict(os.environ, {"ACCESS_REQUIRED": "0", "ALLOWED_EMAILS": "a@b.com"}, clear=True):
            self.assertTrue(access.required())
