"""Sign in with Google in the page (Google's own button + Supabase's ID-token grant), so Google's screen shows ictflux.app and not the
Supabase address. The redirect flow stays as the fallback. The behaviour in a browser was checked with stubbed Google and Supabase endpoints."""
import json
import os
import unittest
from pathlib import Path
from unittest import mock

from ict_trader import accounts

ROOT = Path(__file__).resolve().parents[1]
HEADERS = {h["key"]: h["value"] for block in json.loads((ROOT / "vercel.json").read_text())["headers"] if block["source"] == "/(.*)" for h in block["headers"]}


class GoogleSignInTest(unittest.TestCase):
    def test_the_client_id_is_offered_to_the_page_only_when_set(self):
        with mock.patch.dict(os.environ, {"GOOGLE_CLIENT_ID": " 123.apps.googleusercontent.com "}):
            self.assertEqual(accounts.public_config()["google_client_id"], "123.apps.googleusercontent.com")
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("GOOGLE_CLIENT_ID", None)
            self.assertEqual(accounts.public_config()["google_client_id"], "")

    def test_the_security_headers_let_googles_sign_in_through_and_nothing_else(self):
        csp = HEADERS["Content-Security-Policy"]
        for part in ("script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://accounts.google.com/gsi/client", "https://accounts.google.com/gsi/style"):
            self.assertIn(part, csp)
        self.assertRegex(csp, r"connect-src [^;]*https://accounts\.google\.com/gsi/")
        self.assertRegex(csp, r"frame-src [^;]*https://accounts\.google\.com/gsi/")
        self.assertNotIn("https://accounts.google.com;", csp)          # only Google's sign-in paths, not the whole host
        self.assertIn("frame-ancestors 'none'", csp)                    # our own page is still not framable
        self.assertEqual(HEADERS["Cross-Origin-Opener-Policy"], "same-origin-allow-popups")   # a popup may talk back; other sites still cannot

    def test_the_page_trades_the_google_token_for_a_session_and_falls_back(self):
        html = (ROOT / "web" / "template.html").read_text(encoding="utf-8")
        for needle in ("grant_type=id_token", "google.accounts.id.renderButton", "https://accounts.google.com/gsi/client", "crypto.subtle.digest('SHA-256'"):
            self.assertIn(needle, html)
        self.assertIn("signInGoogle();", html[html.index("async function gsiCallback"):html.index("async function mountGoogle")])   # a failure runs the old flow
        built = (ROOT / "index.html").read_text(encoding="utf-8")
        self.assertIn("grant_type=id_token", built)

    def test_the_service_worker_leaves_googles_script_alone(self):
        self.assertIn("accounts.google.com", (ROOT / "sw.js").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
