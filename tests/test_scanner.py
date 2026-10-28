import json
import os
import unittest
from datetime import datetime, timedelta, timezone
from unittest import mock

from ict_trader import scanner
from ict_trader.data import synthetic_bars
from ict_trader.sessions import Bar

NOW = datetime(2026, 6, 10, 15, 0, tzinfo=timezone.utc)
FX = scanner.Market("EURUSD", "EUR/USD", "FAKE", "test feed", "config.example.toml", 5)
AUTO = scanner.Market("NZDCAD", "NZD/CAD", "FAKE", "test feed", "", 5, "NZD_CAD", "forex")
IDX = scanner.Market("DE40", "DAX 40", "FAKE", "test feed", "", 0, "DE30_EUR", "index", "eu")


def fake_fetch(ticker, range_="41d"):
    days = 5 if range_ == "5d" else 41
    return synthetic_bars(NOW - timedelta(days=days - 1), days, price=1.1, seed=3)


def report_with_signal(status="open", r=None):
    sig = {
        "id": "EURUSD-20260610T0735Z", "direction": "long", "rr": 2.5, "entry": 1.1, "stop": 1.099,
        "target": 1.1025, "killzone": "london", "level": "ASIA_L", "time_ny": "Wed 10 Jun 03:35",
        "fill": 1.10008, "exit": 1.1025, "exit_time_ny": "06:10",
        "outcome": {"status": status, "label": "Target hit", "r": r},
    }
    return {"markets": [{"ok": True, "label": "EUR/USD", "today": {"signals": [sig], "decisions": []}}]}


_ENV = None


def setUpModule():
    # These tests are about scanning mechanics on hand-built series, which have no completed days to build a story from: the main
    # model is the ICT 2022 machinery without the narrative gate (the narrative has its own tests in test_narrative.py).
    global _ENV
    _ENV = mock.patch.dict(os.environ, {"SIGNAL_MODEL": "nonarrative", "SCAN_MODELS": "core"})
    _ENV.start()


def tearDownModule():
    _ENV.stop()


class ScannerTest(unittest.TestCase):
    def test_scan_market_reports_stats_and_never_sees_forming_bar(self):
        out = scanner.scan_market(FX, fake_fetch, NOW, "history")
        self.assertTrue(out["ok"], out.get("error"))
        self.assertEqual(out["stale_minutes"], 0)
        for key in ("trades", "wins", "losses", "win_rate", "total_r"):
            self.assertIn(key, out["stats"])
        json.dumps(out)  # must be serialisable for the API

    def test_live_mode_reports_today(self):
        out = scanner.scan_market(FX, fake_fetch, NOW, "live")
        self.assertTrue(out["ok"], out.get("error"))
        self.assertIn("signals", out["today"])
        self.assertNotIn("stats", out)

    def test_auto_config_scales_to_market_volatility(self):
        bars = fake_fetch("x", "5d")
        cfg = scanner.auto_config(AUTO, bars, None)
        rng = sorted(b.high - b.low for b in bars[-864:])[432] / cfg.instrument.pip_size
        self.assertAlmostEqual(cfg.strategy.min_stop_pips, rng, delta=rng * 0.05)
        self.assertGreater(cfg.strategy.max_stop_pips, cfg.strategy.min_stop_pips)
        self.assertEqual(cfg.strategy.killzones[0].name, "london")

    def test_index_markets_scale_and_use_their_session(self):
        scaled = [Bar(b.time, b.open * 20000, b.high * 20000, b.low * 20000, b.close * 20000) for b in fake_fetch("x", "5d")]
        out = scanner.scan_market(IDX, lambda t, r: scaled, NOW, "history")
        self.assertTrue(out["ok"], out.get("error"))
        cfg = scanner.auto_config(IDX, scaled, None)
        self.assertEqual(cfg.instrument.pip_size, 1.0)
        self.assertEqual([k.name for k in cfg.strategy.killzones], ["london", "ny_am"])

    def test_data_source_and_universe(self):
        with mock.patch.dict("os.environ", {}, clear=True):
            self.assertEqual(scanner.data_source(), "deriv")
            self.assertEqual(len(scanner.universe()), len(scanner.MARKETS))
        with mock.patch.dict("os.environ", {"OANDA_API_TOKEN": "t"}, clear=True):
            self.assertEqual(scanner.data_source(), "oanda")
            self.assertGreater(len(scanner.universe()), 50)
        with mock.patch.dict("os.environ", {"DATA_SOURCE": "yahoo"}, clear=True):
            self.assertEqual({m.key for m in scanner.universe()}, {"XAUUSD", "GBPUSD", "EURUSD", "US500", "NAS100"})

    def test_deriv_symbols_resolved_by_code_and_by_name(self):
        active = [{"underlying_symbol": "frxEURUSD", "underlying_symbol_name": "EUR/USD"}, {"symbol": "OTC_SPC", "display_name": "US 500"},
                  {"symbol": "cryBTCUSD", "display_name": "BTC/USD"}]
        got = scanner.deriv_resolve(active, scanner.MARKETS)
        self.assertEqual(got["EURUSD"], "frxEURUSD")
        self.assertEqual(got["US500"], "OTC_SPC")
        self.assertEqual(got["BTCUSD"], "cryBTCUSD")
        self.assertNotIn("CORN", got)

    def test_deriv_bulk_over_one_socket(self):
        bars = fake_fetch("x", "5d")
        candles = [{"epoch": int(b.time.timestamp()), "open": b.open, "high": b.high, "low": b.low, "close": b.close} for b in bars]

        class FakeWS:
            def __init__(self):
                self.out = []
            def send(self, raw):
                req = json.loads(raw)
                if "active_symbols" in req:
                    self.out.append({"req_id": req["req_id"], "msg_type": "active_symbols",
                                     "active_symbols": [{"symbol": "frxEURUSD", "display_name": "EUR/USD"},
                                                        {"symbol": "frxGBPUSD", "display_name": "GBP/USD"}]})
                elif req["ticks_history"] == "frxGBPUSD":
                    self.out.append({"req_id": req["req_id"], "error": {"code": "MarketIsClosed", "message": "closed"}})
                else:
                    self.out.append({"req_id": req["req_id"], "msg_type": "candles", "candles": candles})
            def recv(self):
                return json.dumps(self.out.pop(0))
            def close(self):
                pass

        mk = tuple(m for m in scanner.MARKETS if m.key in ("EURUSD", "GBPUSD", "CORN"))
        urls = []

        def connect(url):
            urls.append(url)
            if "derivws.com/trading" in url:
                raise OSError("new endpoint down")
            return FakeWS()

        res = scanner.fetch_deriv_bulk(mk, "live", connect=connect)
        self.assertEqual(len(urls), 2)  # new public endpoint first, legacy as fallback
        self.assertEqual(res["EURUSD"][1], "frxEURUSD")
        self.assertEqual(len(res["EURUSD"][0]), len(bars))
        self.assertIsInstance(res["GBPUSD"], RuntimeError)
        self.assertIsInstance(res["CORN"], LookupError)
        out = scanner.scan_market(mk[0] if mk[0].key == "EURUSD" else mk[1], now=NOW, pre=res["EURUSD"], daily=res.get("__daily__", {}).get("EURUSD", []))
        self.assertTrue(out["ok"], out.get("error"))
        self.assertTrue(out["realtime"])
        self.assertIn("Deriv", out["feed"])

    def test_every_deriv_market_is_discovered(self):
        active = [{"underlying_symbol": "R_75", "underlying_symbol_name": "Volatility 75 Index", "market": "synthetic_index"},
                  {"underlying_symbol": "JD10", "underlying_symbol_name": "Jump 10 Index", "market": "synthetic_index"},
                  {"underlying_symbol": "BOOM1000", "underlying_symbol_name": "Boom 1000 Index", "market": "synthetic_index"},
                  {"underlying_symbol": "frxAUDNZD", "underlying_symbol_name": "AUD/NZD", "market": "forex"},
                  {"underlying_symbol": "OTC_N225", "underlying_symbol_name": "Japan 225", "market": "indices"},
                  {"underlying_symbol": "frxXPDUSD", "underlying_symbol_name": "Palladium/USD", "market": "commodities", "submarket": "metals"},
                  {"underlying_symbol": "STOP", "underlying_symbol_name": "Suspended", "market": "synthetic_index", "is_trading_suspended": 1}]
        known = tuple(m for m in scanner.MARKETS if m.key in ("R_75", "XPDUSD"))
        found = {m.key: (m.cls, m.region, sym) for m, sym in scanner.discover_markets(active, known, {"R_75", "frxXPDUSD"})}
        self.assertEqual(found["JD10"], ("synthetic", "us", "JD10"))
        self.assertIn("BOOM1000", found)
        self.assertEqual(found["AUDNZD"][0], "forex")
        self.assertEqual(found["OTC_N225"][:2], ("index", "asia"))
        self.assertNotIn("R_75", found)      # already in the fixed list
        self.assertNotIn("STOP", found)      # suspended
        self.assertEqual(list(found)[:2], ["JD10", "BOOM1000"])  # synthetics first

    def test_unavailable_instrument_is_flagged_not_failed(self):
        def missing(t, r):
            raise LookupError("not available on this OANDA account")
        out = scanner.scan_market(AUTO, missing, NOW)
        self.assertFalse(out["ok"])
        self.assertTrue(out["unavailable"])

    def test_closed_bars_drops_the_bar_still_forming(self):
        t = NOW - timedelta(minutes=3)
        bars = [Bar(NOW - timedelta(minutes=8), 1, 1, 1, 1), Bar(t, 1, 1, 1, 1)]
        self.assertEqual(len(scanner._closed_bars(bars, NOW, 5)), 1)

    def test_feed_failure_is_reported_not_raised(self):
        def broken(ticker, range_):
            raise OSError("network down")
        out = scanner.scan_market(FX, broken, NOW)
        self.assertFalse(out["ok"])
        self.assertIn("network down", out["error"])

    def test_closed_trade_produces_signal_and_result_events(self):
        self.assertEqual([e["id"] for e in scanner.pending_events(report_with_signal())], ["EURUSD-20260610T0735Z"])
        ids = [e["id"] for e in scanner.pending_events(report_with_signal("win", 2.5))]
        self.assertEqual(ids, ["EURUSD-20260610T0735Z", "EURUSD-20260610T0735Z-closed"])

    def test_notify_skips_events_already_in_ntfy_history(self):
        history = json.dumps({"event": "message", "tags": ["chart", "id-EURUSD-20260610T0735Z"]}).encode()
        posted = []

        def fake_http(url, data=None, headers=None, timeout=8):
            if data is None:
                return history
            posted.append(headers["Tags"])
            return b"{}"

        with mock.patch.object(scanner, "_http", fake_http):
            res = scanner.notify(report_with_signal("win", 2.5))
        self.assertEqual(res["sent"], ["EURUSD-20260610T0735Z-closed"])
        self.assertEqual(len(posted), 1)

    def test_notify_sends_nothing_if_history_unreadable(self):
        def fail(url, data=None, headers=None, timeout=8):
            if data is None:
                raise OSError("down")
            raise AssertionError("must not post without de-duplication")

        with mock.patch.object(scanner, "_http", fail):
            res = scanner.notify(report_with_signal())
        self.assertEqual(res["sent"], [])
        self.assertIn("error", res)

    def test_oanda_candles_parsed_and_forming_candle_dropped(self):
        payload = json.dumps({"candles": [
            {"complete": True, "time": "2026-06-10T07:35:00.000000000Z", "volume": 12,
             "mid": {"o": "1.10010", "h": "1.10050", "l": "1.10000", "c": "1.10040"}},
            {"complete": False, "time": "2026-06-10T07:40:00.000000000Z", "volume": 3,
             "mid": {"o": "1.10040", "h": "1.10060", "l": "1.10030", "c": "1.10050"}},
        ]}).encode()

        class Resp:
            def __enter__(self): return self
            def __exit__(self, *a): return False
            def read(self, *a): return payload

        with mock.patch.dict("os.environ", {"OANDA_API_TOKEN": "t"}), \
                mock.patch.object(scanner.urllib.request, "urlopen", lambda req, timeout: Resp()):
            bars, spread = scanner.fetch_oanda("EUR_USD")
        self.assertEqual(len(bars), 1)
        self.assertIsNone(spread)
        self.assertEqual(bars[0].time, datetime(2026, 6, 10, 7, 35, tzinfo=timezone.utc))
        self.assertEqual(bars[0].close, 1.1004)


    def test_delayed_fallback_is_off_by_default(self):
        with mock.patch.dict("os.environ", {}, clear=True):
            out = scanner.scan_market(AUTO, None, NOW, pre=LookupError("not offered on Deriv"))
        self.assertFalse(out["ok"])
        self.assertTrue(out["unavailable"])

    def test_history_attaches_real_candles_for_replays(self):
        out = scanner.history(fetch=fake_fetch, now=NOW, markets=(FX,))
        recent = out["markets"][0]["recent"]
        with_candles = [s for s in recent if "candles" in s]
        for s in with_candles:
            self.assertIn(s["signal_bar"], [c[0] for c in s["candles"]])

    def test_trade_review_lists_every_trade_and_loads_any_one_with_candles(self):
        def fake_fetch(ticker, range_):  # a series on which the strict model trades twice
            return synthetic_bars(NOW - timedelta(days=40), 41, price=1.1, seed=12)
        out = scanner.history(fetch=fake_fetch, now=NOW, markets=(FX,))
        recent = out["markets"][0]["recent"]
        self.assertGreaterEqual(len(recent), 2)
        self.assertEqual([s["time"] for s in recent], sorted((s["time"] for s in recent), reverse=True))
        oldest = recent[-1]
        self.assertIsNotNone(oldest["setup"])
        self.assertEqual(len(oldest["setup"]["fvg"]), 2)
        with mock.patch.object(scanner, "universe", return_value=(FX,)):
            one = scanner.trade_detail("EURUSD", oldest["id"], 5, fetch=fake_fetch, now=NOW)
            with self.assertRaises(LookupError):
                scanner.trade_detail("EURUSD", "nope", 5, fetch=fake_fetch, now=NOW)
        times = [c[0] for c in one["candles"]]
        self.assertIn(one["signal_bar"], times)
        self.assertIn(one["setup"]["fvg_time"], times)

    def test_live_scan_reports_every_model_for_the_desk(self):
        out = scanner.scan_market(AUTO, fake_fetch, NOW, "live")
        self.assertEqual(set(out["models"]), set(__import__("ict_trader.models", fromlist=["LIVE_MODELS"]).LIVE_MODELS))
        for name, m in out["models"].items():
            self.assertTrue(m["available"], name)
            self.assertIn(m["stage"], ("in_trade", "order", "trigger", "forming", "idle"))
            for key in ("orders", "forming", "triggers", "signals"):
                self.assertIsInstance(m[key], list)
        swing = scanner.scan_market(AUTO, lambda t, r: synthetic_bars(NOW - timedelta(days=40), 41, timeframe_minutes=60, price=1.1, seed=3), NOW, "live", tf=60)
        self.assertFalse(swing["models"]["silver_bullet"]["available"])  # no time windows on 1h

    def test_past_day_replay_sees_only_that_day_but_knows_the_outcome(self):
        bars = synthetic_bars(NOW - timedelta(days=40), 41, price=1.1, seed=12)
        f = lambda t, r: bars  # noqa: E731
        hist = scanner.scan_market(FX, f, NOW, "history")
        trade = hist["recent"][-1]
        day_end = datetime.fromisoformat(trade["time"]).replace(hour=21, minute=0)
        if day_end < datetime.fromisoformat(trade["time"]):
            day_end += timedelta(days=1)
        past = scanner.scan_market(FX, f, NOW, "live", as_of=day_end, light=True)
        self.assertEqual(past["as_of"], day_end.isoformat())
        ids = [s["id"] for s in past["today"]["signals"]]
        self.assertIn(trade["id"], ids)
        self.assertTrue(all(datetime.fromisoformat(s["time"]) <= day_end for s in past["today"]["signals"]))
        replayed = next(s for s in past["today"]["signals"] if s["id"] == trade["id"])
        self.assertEqual(replayed["outcome"], trade["outcome"])  # the result, known with hindsight
        self.assertLessEqual(past["analysis"]["as_of"], int(day_end.timestamp()))
        with self.assertRaises(ValueError):
            scanner.scan(fetch=f, now=NOW, markets=(FX,), as_of=NOW - timedelta(days=30))

    def test_news_blackout_blocks_the_entry_and_shows_in_the_read(self):
        from ict_trader.news import NewsEvent, parse_ff
        ev = parse_ff([{"title": "CPI m/m", "country": "USD", "date": "2026-06-05T08:30:00-04:00", "impact": "High"},
                       {"title": "Bank holiday", "country": "EUR", "date": "bad"}])
        self.assertEqual((len(ev), ev[0].currency, ev[0].impact), (1, "USD", "high"))
        bars = synthetic_bars(NOW - timedelta(days=40), 41, price=1.1, seed=12)
        f = lambda t, r: bars  # noqa: E731
        hist = scanner.scan_market(FX, f, NOW, "history")
        trade = next(s for s in hist["recent"] if s["outcome"]["status"] != "not_taken")
        at = datetime.fromisoformat(trade["time"])
        blocked = scanner.scan_market(FX, f, NOW, "history", news=[NewsEvent(at, "USD", "high", "NFP")])
        same = next(s for s in blocked["recent"] if s["id"] == trade["id"])
        self.assertEqual(same["outcome"]["status"], "not_taken")
        live = scanner.scan_market(FX, f, at + timedelta(minutes=5), "live", news=[NewsEvent(at + timedelta(minutes=20), "USD", "high", "NFP")], light=True)
        self.assertTrue(any(c["rule"] == "NF-01" for c in live["analysis"]["checklist"]))

    def test_smt_divergence_when_the_partner_holds_its_level(self):
        from tests.helpers import ny_bar, simple_config
        cfg = simple_config().strategy
        partner = [ny_bar("2026-06-01 18:00", 1.30, 1.31, 1.29, 1.30),   # partner's prior day: low 1.29
                   ny_bar("2026-06-02 18:00", 1.30, 1.305, 1.295, 1.30),
                   ny_bar("2026-06-03 02:10", 1.30, 1.302, 1.2935, 1.295)]  # holds above 1.29
        t = datetime.fromisoformat("2026-06-03T06:15:00+00:00")  # 02:15 NY
        r = scanner.smt_check(cfg, ("GBP/USD", partner), "PDL", t, 1, 5)
        self.assertTrue(r["divergence"])
        partner[-1] = ny_bar("2026-06-03 02:10", 1.30, 1.302, 1.2880, 1.295)  # partner also ran its low
        self.assertFalse(scanner.smt_check(cfg, ("GBP/USD", partner), "PDL", t, 1, 5)["divergence"])

    def test_notifications_read_like_a_trade_call(self):
        sig = {"id": "EURUSD-1", "direction": "short", "rr": 3.2, "entry": 1.085, "stop": 1.087, "target": 1.08, "killzone": "london",
               "level": "PDH", "time_ny": "Wed 10 Jun 03:35", "fill": 1.085, "exit": None, "exit_time_ny": None,
               "setup": {"tp1": 1.083}, "quality": {"grade": "A+", "score": 4, "confluence": ["3.2R", "daily bias"]},
               "outcome": {"status": "open", "label": "Still open", "r": 0.1}}
        weak = {**sig, "id": "EURUSD-2", "quality": {"grade": "C", "score": 0, "confluence": []}}
        order = {"direction": "long", "entry": 1.1, "stop": 1.099, "tp1": 1.101, "tp2": 1.104, "rr": 4.0, "placed": 1, "candles_left": 3,
                 "quality": {"grade": "A", "score": 3, "confluence": []}}
        report = {"generated_at": "2026-06-10T06:05:00+00:00", "timeframe_minutes": 5,  # 02:05 NY: London just opened
                  "markets": [{"ok": True, "key": "EURUSD", "label": "EUR/USD", "model": "ict2022", "analysis": {"bias": "bearish", "stage": "limit"},
                               "models": {"ict2022": {"orders": [order]}}, "today": {"signals": [sig, weak], "decisions": []}}]}
        ev = {e["id"]: e for e in scanner.pending_events(report)}
        self.assertIn("kz-london-20260610", ev)
        self.assertIn("EUR/USD ▼", ev["kz-london-20260610"]["body"])
        self.assertEqual(ev["EURUSD-1"]["title"], "▼ ICT 2022 Model: SELL EUR/USD · A+ · 3.2R")  # every alert names its model
        self.assertIn("SL 1.087 · TP1 1.083 · TP2 1.08", ev["EURUSD-1"]["body"])
        self.assertNotIn("EURUSD-2", ev)  # grade C is below the default B
        self.assertIn("BUY LIMIT", ev["EURUSD-order-1"]["title"])
        self.assertIn("15 min", ev["EURUSD-order-1"]["body"])

    def test_volatility_indices_ignore_news_and_one_failure_never_breaks_the_scan(self):
        from ict_trader.news import NewsEvent
        vix = scanner.Market("R_75", "Volatility 75 Index", "", "Deriv", "", 0, "", "synthetic")
        bars = synthetic_bars(NOW - timedelta(days=5), 6, price=1000.0, seed=3)
        news = [NewsEvent(NOW - timedelta(hours=1), "USD", "high", "FOMC Statement")]
        out = scanner.scan_market(vix, lambda t, r: bars, NOW, "live", news=news)
        self.assertTrue(out["ok"], out.get("error"))
        self.assertFalse(any(c["rule"].startswith("NF") for c in out["analysis"]["checklist"]))

        def boom(t, r):
            raise ValueError("bad data")
        with mock.patch.object(scanner, "scan_market", side_effect=[RuntimeError("one market broke"), {"key": "B", "ok": True}]):
            res = scanner._run((FX, AUTO), boom, NOW, "live")
        self.assertEqual([r["ok"] for r in res], [False, True])

    def test_every_timeframe_runs_for_every_market_kind(self):
        for tf in (t for t in scanner.TIMEFRAMES if t <= 15):  # 1h/4h covered with longer data below
            def tf_fetch(t, r, tf=tf):
                days = 2 if tf <= 2 else 5
                return synthetic_bars(NOW - timedelta(days=days - 1), days, timeframe_minutes=tf, price=1.1, seed=3)
            for m in (FX, AUTO):
                out = scanner.scan_market(m, tf_fetch, NOW, "live", tf=tf, light=True)
                self.assertTrue(out["ok"], (tf, m.key, out.get("error")))
                self.assertEqual(out["timeframe_minutes"], tf)
                self.assertEqual(out["tuned"], tf == 5 and bool(m.config_file))

    def test_signal_ids_keep_5m_format_and_tag_other_timeframes(self):
        from ict_trader.strategy import Signal
        from ict_trader.sessions import Level
        sig = Signal(datetime(2026, 6, 10, 7, 35, tzinfo=timezone.utc), 1, 1.1, 1.09, 1.12, 2.0, Level("PDL", 1.095, "low"), "london", ())
        self.assertEqual(scanner._signal_id(FX, sig), "EURUSD-20260610T0735Z")
        self.assertEqual(scanner._signal_id(FX, sig, 1), "EURUSD-1m-20260610T0735Z")

    def test_live_window_covers_prior_day_on_every_timeframe(self):
        for tf in scanner.TIMEFRAMES:
            self.assertGreaterEqual(scanner.live_bars(tf) * tf, 3 * 1440)
            self.assertLessEqual(scanner.live_bars(tf), 5000)

    def test_unknown_timeframe_rejected(self):
        with self.assertRaises(ValueError):
            scanner.scan(fetch=fake_fetch, now=NOW, markets=(FX,), tf=4)

    def test_swing_and_long_term_styles(self):
        from ict_trader.config import Config
        cfg = scanner.apply_style(Config(), 60)
        self.assertIsNone(cfg.strategy.flatten_time)
        self.assertEqual(cfg.strategy.level_period, "day")
        self.assertEqual(cfg.strategy.reference_ranges, ())
        cfg = scanner.apply_style(Config(), 240)
        self.assertEqual(cfg.strategy.level_period, "week")
        self.assertEqual(scanner.style_of(1), "scalp")
        self.assertEqual(scanner.style_of(240), "position")
        for tf in (60, 240):
            def hb(t, r, tf=tf):
                return synthetic_bars(NOW - timedelta(days=120), 121, timeframe_minutes=tf, price=1.1, seed=3)
            out = scanner.scan_market(AUTO, hb, NOW, "history", tf=tf)
            self.assertTrue(out["ok"], (tf, out.get("error")))
            live = scanner.scan_market(AUTO, hb, NOW, "live", tf=tf)
            self.assertTrue(live["ok"], (tf, live.get("error")))

    def test_weekly_levels_named_and_built_from_prior_week(self):
        from ict_trader.config import StrategyConfig
        from ict_trader.sessions import LevelTracker
        tr = LevelTracker(StrategyConfig(level_period="week", reference_ranges=()))
        week1 = [b for b in synthetic_bars(datetime(2026, 6, 1, tzinfo=timezone.utc), 5, timeframe_minutes=240, price=1.1, seed=1)]
        for b in week1:
            tr.update(b)
        tr.update(Bar(datetime(2026, 6, 8, 4, tzinfo=timezone.utc), 1.1, 1.1, 1.1, 1.1))
        names = {lv.name: lv.price for lv in tr.levels()}
        self.assertAlmostEqual(names["PWH"], max(b.high for b in week1 if b.time < datetime(2026, 6, 5, 21, tzinfo=timezone.utc)), places=5)

    def test_enrich_with_smt(self):
        from ict_trader.scanner import _enrich_with_smt
        t0 = datetime(2026, 6, 10, 10, 0, tzinfo=timezone.utc)
        def mb(i, o, h, l, c):
            return Bar(t0 + timedelta(minutes=i * 5), o, h, l, c, 100)
        bars_es = [
            mb(0, 100, 101, 99, 100),
            mb(1, 100, 105, 99.5, 104),   # Swing high 1: 105
            mb(2, 104, 104.5, 101, 102),
            mb(3, 102, 106, 101.5, 105),
            mb(4, 105, 110, 104.5, 109),  # Swing high 2: 110 (Higher High)
            mb(5, 109, 109.5, 106, 107),
        ]
        bars_nq = [
            mb(0, 200, 201, 199, 200),
            mb(1, 200, 210, 199.5, 208),  # Swing high 1: 210
            mb(2, 208, 208.5, 201, 202),
            mb(3, 202, 204, 201.5, 203),
            mb(4, 203, 205, 202.5, 204),  # Swing high 2: 205 (Lower High - Divergence!)
            mb(5, 204, 204.5, 201, 202),
        ]
        results = [
            {"key": "US500", "ok": True, "today": {"signals": [{"direction": "short", "reasons": ["KZ-1"]}]}},
            {"key": "NAS100", "ok": True, "today": {"signals": []}},
        ]
        pre = {"US500": (bars_es, "ES"), "NAS100": (bars_nq, "NQ")}
        _enrich_with_smt(results, pre)
        self.assertIn("smt", results[0])
        self.assertTrue(results[0]["smt"]["active"])
        self.assertEqual(results[0]["smt"]["direction"], "short")
        self.assertTrue(any("SMT-01" in r for r in results[0]["today"]["signals"][0]["reasons"]))


if __name__ == "__main__":
    unittest.main()


class TrailingRunnerTest(unittest.TestCase):
    """The live plan trails the runner behind each new swing; the Research lab keeps the plain plan as its baseline."""

    def test_live_management_trails_when_there_is_a_runner(self):
        from dataclasses import replace
        from ict_trader import management
        from ict_trader.config import StrategyConfig
        base = replace(StrategyConfig(), model="ict2022", timeframe_minutes=5)
        self.assertTrue(management.apply(base, 5, live=True).trail_structure)
        self.assertFalse(management.apply(base, 5).trail_structure)                                  # the lab's baseline
        self.assertFalse(management.apply(replace(base, model="silver_bullet"), 5, live=True).trail_structure)   # no partial, no runner
        self.assertIn("trail the stop behind each new swing", management.describe(5, "ict2022")["text"])
        self.assertNotIn("trail", management.describe(5, "ict2022", trail=False)["text"])
        with mock.patch.dict("os.environ", {"TRAIL_RUNNER": "0"}):
            self.assertFalse(management.apply(base, 5, live=True).trail_structure)
            self.assertFalse(management.describe(5, "ict2022")["trail"])
