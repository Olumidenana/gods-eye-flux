import unittest
from datetime import datetime, timedelta, timezone
from unittest import mock

from ict_trader import autotrade as at
from ict_trader.mt5feed import feed
from ict_trader.strict import strict_why

# Wednesday 7 Oct 2026, 09:30 NY
WED = datetime(2026, 10, 7, 13, 30, tzinfo=timezone.utc)


def sig(**kw):
    s = {"id": "S", "market": "EURUSD", "timeframe_minutes": 5, "time": WED.isoformat(), "quality": {"grade": "A"}, "rr": 2.5, "advice": {"verdict": "TAKE", "score": 80}}
    s.update(kw)
    return s


class StrictTest(unittest.TestCase):
    def test_ict_setup_qualifies(self):
        self.assertEqual(strict_why(sig()), [])
        self.assertEqual(strict_why(sig(market="NAS100", timeframe_minutes=15, quality={"grade": "A+"})), [])

    def test_rejects_what_ict_would_not_take(self):
        self.assertIn("not a market ICT trades", strict_why(sig(market="R_75")))
        self.assertIn("not a market ICT trades", strict_why(sig(market="GBPNZD")))
        self.assertIn("not a 5m or 15m killzone trade", strict_why(sig(timeframe_minutes=60)))
        self.assertIn("Monday", strict_why(sig(time=(WED - timedelta(days=2)).isoformat())))
        self.assertIn("Friday afternoon", strict_why(sig(time=(WED + timedelta(days=2, hours=4)).isoformat())))
        self.assertEqual(strict_why(sig(time=(WED + timedelta(days=2)).isoformat())), [])  # Friday morning is fine
        self.assertTrue(any("grade B" in w for w in strict_why(sig(quality={"grade": "B"}))))
        self.assertTrue(any("1.8R" in w for w in strict_why(sig(rr=1.8))))

    def test_bots_and_mt5_feed_can_take_strict_only(self):
        good = {**sig(id="GOOD"), "strict": True}
        loose = {**sig(id="LOOSE", market="R_75"), "strict": False}
        for s in (good, loose):
            s.update({"label": s["market"], "broker_symbol": "frxEURUSD", "direction": "long", "entry": 1.1, "stop": 1.099, "target": 1.103,
                      "outcome": {"status": "open"}, "setup": {}})
        report = {"markets": [{"ok": True, "cls": "forex", "today": {"signals": [good, loose]}}]}
        now = WED + timedelta(minutes=2)
        lines = feed(report, now, strict=True).strip().split("\n")[1:]
        self.assertEqual([x.split("|")[0] for x in lines], ["GOOD"])
        self.assertEqual(len(feed(report, now).strip().split("\n")[1:]), 2)

        store, placed = at.MemoryStore(), []

        class T:
            currency = "USD"
            def balance(self): return 10000.0
            def open_positions(self): return 0
            def place(self, s, risk): placed.append(s["id"]); return {"stake": 1, "multiplier": 1, "stop_loss": 1, "take_profit": 1}
            def close(self): pass
        with mock.patch.dict("os.environ", {"AUTOTRADE_KEY": __import__("cryptography.fernet", fromlist=["Fernet"]).Fernet.generate_key().decode()}):
            at.enroll(store, {"token": "tok-123456789", "account_id": "VRTC1", "accept_terms": True, "terms_version": at.TERMS_VERSION,
                              "classes": ["forex", "strict"]}, accounts=lambda t: [{"id": "VRTC1", "type": "demo", "currency": "USD", "balance": 1}], now=now)
            at.run(store, report, trader=lambda u, tok: T(), now=now)
        self.assertEqual(sorted(set(placed)), ["GOOD"])


if __name__ == "__main__":
    unittest.main()


class ManagementTest(unittest.TestCase):
    def test_each_style_and_model_has_its_own_ict_plan(self):
        from ict_trader import management as mg
        self.assertEqual(mg.plan(5, "ict2022"), {"partial_at_tp1": 0.5, "trim_stop_at_50_pct": True, "move_be_at_75_pct": True})
        self.assertEqual(mg.plan(1, "ict2022")["partial_at_tp1"], 0.75)
        self.assertEqual(mg.plan(240, "ict2022")["partial_at_tp1"], 0.25)
        self.assertEqual(mg.plan(5, "silver_bullet")["partial_at_tp1"], 0.0)
        self.assertIn("50%", mg.describe(5, "ict2022")["text"])
        self.assertIn("whole trade", mg.describe(5, "silver_bullet")["text"])


class ModelsTest(unittest.TestCase):
    def test_every_ict_model_is_available_and_resolves(self):
        from dataclasses import replace
        from ict_trader.config import load_config
        from ict_trader.models import BUILDING_BLOCKS, LAB_MODELS, LIVE_MODELS, MODEL_INFO, MODELS, PREVIEW_MODELS, TRADE_MODELS, kind_of, model_available, resolve
        st = load_config("examples/config.example.toml").strategy
        self.assertEqual(set(LIVE_MODELS), set(TRADE_MODELS) - set(PREVIEW_MODELS))  # every trade model is switched on everywhere
        self.assertFalse(set(LIVE_MODELS) & set(BUILDING_BLOCKS))               # building blocks are tested in the lab, never scanned or alerted on
        self.assertEqual(set(TRADE_MODELS) | set(BUILDING_BLOCKS), set(MODELS))
        self.assertEqual([kind_of(m) for m in ("ict2022", "nonarrative", "ob", "sdt", "trail", "tightstop", "custom:entry=ote")], ["model", "direction", "zone", "target", "management", "stop", "model"])
        self.assertEqual(set(MODELS) - set(LAB_MODELS), {"ict2022", "silver_bullet", "judas_swing", "ote", "unicorn", "sweep"})
        self.assertTrue(all(MODEL_INFO[m].get("lab") for m in LAB_MODELS))  # new models are marked until confirmed
        self.assertEqual(resolve(replace(st, model="ifvg")).trigger, "ifvg")
        self.assertEqual(resolve(replace(st, model="breaker")).entry_mode, "breaker")
        # the ICT 2022 family reads the narrative and is ruled by the matrix; the control and the pattern models do not
        spine = resolve(replace(st, model="ict2022"))
        self.assertEqual((spine.narrative_required, spine.htf_context, spine.target_pref, spine.min_score), (True, True, "draw", 40))
        self.assertTrue(resolve(replace(st, model="ote")).narrative_required and resolve(replace(st, model="ob")).narrative_required)
        self.assertFalse(resolve(replace(st, model="nonarrative")).narrative_required)
        self.assertFalse(resolve(replace(st, model="venom")).narrative_required)
        self.assertTrue(resolve(replace(st, model="narrative")).narrative_required)   # the old names are the ICT 2022 model now
        self.assertEqual(MODEL_INFO["sweep"]["label"], "Turtle Soup")
        self.assertEqual([w.name for w in resolve(replace(st, model="judas_swing")).killzones], ["london_open", "ny_open"])
        self.assertEqual(resolve(replace(st, model="ote")).entry_mode, "ote")
        self.assertEqual(resolve(replace(st, model="unicorn")).entry_mode, "unicorn")
        any_hour = replace(st, killzones=(type(st.killzones[0])("any", st.killzones[0].start.replace(hour=0), st.killzones[0].end.replace(hour=23)),))
        self.assertFalse(model_available(any_hour, "judas_swing"))  # a time model needs a clock
        self.assertTrue(model_available(any_hour, "ote"))


class AlertsAndDiscoveryTest(unittest.TestCase):
    def test_discovery_skips_a_market_already_listed_under_another_spelling(self):
        from ict_trader import scanner
        known = (scanner.Market("GBPUSD", "GBP/USD", "", "", "", 0, "", "forex"),)
        active = [{"underlying_symbol": "OTC_GBPUSD", "market": "forex", "display_name": "GBPUSD"},
                  {"underlying_symbol": "frxNZDSGD", "market": "forex", "display_name": "NZD/SGD"}]
        self.assertEqual([m.label for m, _ in scanner.discover_markets(active, known, set())], ["NZD/SGD"])

    def test_every_model_pushes_its_own_setups(self):
        from ict_trader import scanner
        order = {"direction": "short", "entry": 1.1, "stop": 1.101, "tp1": None, "tp2": 1.097, "rr": 3.0, "placed": "t1", "quality": {"grade": "A"}}
        trig = {"direction": "long", "level": "PDL", "level_price": 1.09, "extreme": 1.089, "trigger": "a candle close back above 1.09"}
        report = {"generated_at": "2026-10-03T12:00:00+00:00", "markets": [{"ok": True, "key": "EURUSD", "label": "EUR/USD", "model": "ict2022", "today": {"signals": []},
                  "models": {"ict2022": {"available": True, "orders": []}, "ote": {"available": True, "orders": [order], "triggers": [], "signals": []},
                             "sweep": {"available": True, "orders": [], "triggers": [trig], "signals": []}}}]}
        titles = [e["title"] for e in scanner.pending_events(report)]
        self.assertTrue(any(t.startswith("⏳ OTE: SELL LIMIT EUR/USD") for t in titles), titles)
        self.assertTrue(any("Turtle Soup: EUR/USD BUY setup forming" in t for t in titles), titles)


    def test_alerts_follow_the_trade_with_its_models(self):
        from ict_trader import scanner
        now = "2026-10-08T14:00:00+00:00"
        base = {"direction": "long", "rr": 4.0, "entry": 1.1, "fill": 1.1, "stop": 1.099, "target": 1.104, "time": "2026-10-08T13:00:00+00:00",
                "time_ny": "Thu 08 Oct 09:00", "killzone": "ny_am", "level": "PDL", "setup": {"tp1": 1.1015, "mss_time": 1},
                "quality": {"grade": "A"}, "management": {"partial": 0.5, "trim_50": True, "be_75": True, "text": "Take 50% off at TP1."}}
        open_sig = {**base, "id": "EU-1", "outcome": {"status": "open", "label": "Still open", "r": 1.2, "best_r": 2.1}}
        report = {"generated_at": now, "timeframe_minutes": 5, "markets": [{"ok": True, "key": "EU", "label": "EUR/USD", "model": "ict2022", "last_price": 1.1012,
                  "today": {"signals": [open_sig]},
                  "models": {"ict2022": {"available": True, "orders": [], "signals": []},
                             "ote": {"available": True, "orders": [], "signals": [{**open_sig, "id": "EU-1-ote"}]}}}]}
        ev = {e["id"]: e for e in scanner.pending_events(report)}
        self.assertIn("ICT 2022 Model + OTE", ev["EU-1"]["title"])  # one alert naming both models
        self.assertNotIn("EU-1-ote", ev)
        self.assertEqual([k for k in ev if k.startswith("EU-1-m-")], ["EU-1-m-2r"])  # only the furthest step reached
        self.assertIn("Best so far +2.10R", ev["EU-1-m-2r"]["body"])
        # closed: how long it lasted and how far it got
        lost = {**base, "id": "EU-2", "exit": 1.099, "exit_time": "2026-10-08T13:40:00+00:00", "exit_time_ny": "09:40",
                "outcome": {"status": "loss", "label": "Stop loss hit", "r": -1.0, "best_r": 0.6}}
        report["markets"][0]["today"]["signals"] = [lost]
        ev = {e["id"]: e for e in scanner.pending_events(report)}
        self.assertIn("after 40 min", ev["EU-2-closed"]["body"])
        self.assertIn("+0.60R before the stop", ev["EU-2-closed"]["body"])
        # a limit pushed earlier that vanished without a fill was cancelled
        placed = int(datetime(2026, 10, 8, 13, 30, tzinfo=timezone.utc).timestamp())
        ev = {e["id"]: e for e in scanner.pending_events(report, sent={f"EU-order-{placed}"})}
        self.assertIn(f"EU-order-{placed}-cancelled", ev)
        ev = {e["id"]: e for e in scanner.pending_events(report, sent={"EU-order-1"})}  # an old one: never guessed at
        self.assertNotIn("EU-order-1-cancelled", ev)

class ScanThrottleTest(unittest.TestCase):
    def test_cron_scans_once_per_five_minute_candle(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location("scan_api", "api/scan.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        due = [m for m in range(60) if mod.scan_due(datetime(2026, 10, 8, 14, m, 20, tzinfo=timezone.utc))]
        self.assertEqual(due, [1, 6, 11, 16, 21, 26, 31, 36, 41, 46, 51, 56])
        with mock.patch.dict("os.environ", {"SCAN_EVERY": "1"}):
            self.assertTrue(mod.scan_due(datetime(2026, 10, 8, 14, 3, tzinfo=timezone.utc)))

    def test_readers_get_the_saved_scan_without_running_the_engine(self):
        import importlib.util
        import io
        spec = importlib.util.spec_from_file_location("scan_api2", "api/scan.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        saved = '{"generated_at": "x", "markets": []}'

        def call(path):
            h = mod.handler.__new__(mod.handler)
            h.path, h.headers, h.wfile = path, {}, io.BytesIO()
            h.send_response = lambda code: setattr(h, "code", code)
            h.send_header = lambda k, v: setattr(h, "cc", v) if k == "Cache-Control" else None
            h.end_headers = lambda: None
            h.do_GET()
            return h
        with mock.patch.dict("os.environ", {"ACCESS_REQUIRED": "0"}), mock.patch.object(mod.snapshot, "load", return_value=saved), \
             mock.patch("ict_trader.scanner.scan", side_effect=AssertionError("the engine must not run")):
            h = call("/api/scan?tf=5")
            self.assertEqual(h.wfile.getvalue().decode(), saved)
            self.assertIn("stale-while-revalidate", h.cc)
            self.assertTrue(call("/api/scan?tf=5&format=mt5").wfile.getvalue().startswith(b"ICTFLUX1|"))
        from ict_trader import snapshot
        with mock.patch.dict("os.environ", {"SUPABASE_URL": "", "SUPABASE_SERVICE_KEY": ""}):
            self.assertIsNone(snapshot.load("scan-5", 60))  # not set up: quietly nothing
            self.assertFalse(snapshot.save("scan-5", {}))
