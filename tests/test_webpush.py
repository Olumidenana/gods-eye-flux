import json
import os
import unittest
from unittest import mock

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import encode_dss_signature

from ict_trader import webpush as wp


class WebPushTest(unittest.TestCase):
    def test_encryption_matches_rfc8291_example(self):
        # RFC 8291 Appendix A: the exact bytes a push service and browser expect
        as_key = ec.derive_private_key(int.from_bytes(wp.unb64u("yfWPiYE-n46HLnH0KqZOF1fJJU3MYrct3AELtAQ-oRw"), "big"), ec.SECP256R1())
        out = wp.encrypt(b"When I grow up, I want to be a watermelon",
                         "BCVxsr7N_eNgVRqvHtD0zTZsEc6-VV-JvLexhqUzORcxaOzi6-AYWXvTBHm4bjyPjs7Vd8pZGH6SRpkNtoIAiw4",
                         "BTBZMqHH6r4Tts7J_aSIgg", salt=wp.unb64u("DGv6ra1nlYgDCS1FRnbzlw"), server_key=as_key)
        self.assertEqual(wp.b64u(out), "DGv6ra1nlYgDCS1FRnbzlwAAEABBBP4z9KsN6nGRTbVYI_c7VJSPQTBtkgcy27mlmlMoZIIgDll6e3vCYLocInmYWAmS6TlzAC8wEqKK6PBru3jl7A_yl95bQpu6cVPTpK4Mqgkf1CXztLVBSt2Ks3oZwbuwXPXLWyouBWLVWGNWQexSgSxsj_Qulcy4a-fN")

    def test_vapid_key_comes_from_the_cron_secret_and_signs_valid_tokens(self):
        with mock.patch.dict(os.environ, {"CRON_SECRET": "s3cret", "VAPID_PRIVATE_KEY": ""}):
            k1, k2 = wp.vapid_key(), wp.vapid_key()
            self.assertEqual(k1.private_numbers().private_value, k2.private_numbers().private_value)  # stable across runs
            self.assertEqual(len(wp.unb64u(wp.public_key())), 65)
            h = wp.vapid_header("https://fcm.googleapis.com/fcm/send/abc", k1, now=1000)
        jwt, k = h[len("vapid t="):].split(", k=")
        head, claims, sig = jwt.split(".")
        self.assertEqual(json.loads(wp.unb64u(claims))["aud"], "https://fcm.googleapis.com")
        raw = wp.unb64u(sig)
        pub = ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(), wp.unb64u(k))
        pub.verify(encode_dss_signature(int.from_bytes(raw[:32], "big"), int.from_bytes(raw[32:], "big")),
                   f"{head}.{claims}".encode(), ec.ECDSA(hashes.SHA256()))  # raises if the signature is wrong
        with mock.patch.dict(os.environ, {"CRON_SECRET": "", "VAPID_PRIVATE_KEY": ""}):
            self.assertIsNone(wp.public_key())

    def test_subscriptions_are_checked(self):
        ua = ec.generate_private_key(ec.SECP256R1()).public_key().public_bytes(
            __import__("cryptography.hazmat.primitives.serialization", fromlist=["Encoding"]).Encoding.X962,
            __import__("cryptography.hazmat.primitives.serialization", fromlist=["PublicFormat"]).PublicFormat.UncompressedPoint)
        good = {"endpoint": "https://fcm.googleapis.com/x", "keys": {"p256dh": wp.b64u(ua), "auth": wp.b64u(b"0" * 16)}}
        self.assertEqual(wp.valid(good)["endpoint"], good["endpoint"])
        for bad in (None, {**good, "endpoint": "http://evil"}, {**good, "keys": {"p256dh": "x", "auth": "y"}}):
            with self.assertRaises(ValueError):
                wp.valid(bad)

    def test_broadcast_sends_every_alert_and_forgets_phones_that_left(self):
        subs = [{"endpoint": "https://a", "p256dh": "k", "auth": "a"}, {"endpoint": "https://gone", "p256dh": "k", "auth": "a"}]
        codes = {"https://a": 201, "https://gone": 410}
        removed = []
        with mock.patch.dict(os.environ, {"CRON_SECRET": "s"}), \
             mock.patch.object(wp, "subscriptions", return_value=subs), \
             mock.patch.object(wp, "send", side_effect=lambda sub, msg, key, urgency: codes[sub["endpoint"]]), \
             mock.patch.object(wp, "unsubscribe", side_effect=removed.append):
            out = wp.broadcast([{"id": "e1", "title": "t", "body": "b"}, {"id": "e2", "title": "t", "body": "b", "priority": "low"}])
        self.assertEqual((out["sent"], out["removed"]), (2, 1))
        self.assertEqual(removed, ["https://gone"])
        with mock.patch.object(wp, "subscriptions", side_effect=RuntimeError("no table")), mock.patch.dict(os.environ, {"CRON_SECRET": "s"}):
            self.assertIn("error", wp.broadcast([{"id": "e", "title": "t", "body": "b"}]))  # never breaks the alerts


if __name__ == "__main__":
    unittest.main()


class PushApiGateTest(unittest.TestCase):
    """With the lock on (the default), a signed-in phone's POST must reach its op. The gate's shared-GET proxy replays a request
    without its body as a GET, which the push endpoint answers with "unknown op": turning notifications on, the test and the tier all failed."""

    def _post(self, op, body):
        import io
        from api import push
        from ict_trader import access

        class H(push.handler):
            def __init__(self, path, raw):
                self.path, self.headers, self.rfile, self.wfile, self.codes = path, {"Content-Length": str(len(raw)), "Host": "ictflux.app"}, io.BytesIO(raw), io.BytesIO(), []
            def send_response(self, c): self.codes.append(c)
            def send_header(self, *a): pass
            def end_headers(self): pass

        h = H(f"/api/push?op={op}", json.dumps(body).encode())
        with mock.patch.dict(os.environ, {"ACCESS_SECRET": "test-secret"}), mock.patch.object(access, "required", lambda: True), \
                mock.patch.object(access, "holder", lambda handler: None), mock.patch("urllib.request.urlopen", side_effect=AssertionError("the POST was proxied as a GET")):
            h.do_POST()
        return h.codes[0], json.loads(h.wfile.getvalue())

    def test_a_signed_in_post_reaches_its_op_instead_of_being_proxied(self):
        with mock.patch.object(wp, "set_tier") as tier:
            code, out = self._post("tier", {"endpoint": "https://push.example/abc", "tier": "a"})
        self.assertEqual((code, out), (200, {"ok": True}))
        tier.assert_called_once_with("https://push.example/abc", "a")
        with mock.patch.object(wp, "unsubscribe") as un:
            self.assertEqual(self._post("unsubscribe", {"endpoint": "https://push.example/abc"})[0], 200)
        un.assert_called_once()
        self.assertEqual(self._post("nope", {}), (400, {"error": "unknown op"}))   # a genuinely unknown op still says so
