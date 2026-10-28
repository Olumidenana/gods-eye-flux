"""The Market view: one market read on every timeframe, and whether the timeframes agree."""

import json
import random
import unittest
from datetime import datetime, timedelta, timezone
from ict_trader import mtf
from ict_trader.sessions import Bar

NOW = datetime(2026, 10, 7, 15, 3, tzinfo=timezone.utc)


def walk(tf, n, drift=0.0, seed=3):
    r = random.Random(seed)
    p, out = 1000.0, []
    end = NOW.replace(minute=0, second=0) - timedelta(minutes=tf)
    t0 = end - timedelta(minutes=tf * n)
    for i in range(n):
        o = p
        c = o + drift + r.gauss(0, 0.7)
        out.append(Bar(t0 + timedelta(minutes=tf * i), round(o, 2), round(max(o, c) + abs(r.gauss(0, .3)), 2), round(min(o, c) - abs(r.gauss(0, .3)), 2), round(c, 2)))
        p = c
    return out


def zig(points, step=3):
    """Candles that go through the given turning points: highs and lows a swing detector will find."""
    bars, t = [], NOW - timedelta(minutes=5 * step * len(points))
    for a, b in zip(points, points[1:]):
        for k in range(step):
            lo, hi = sorted((a + (b - a) * k / step, a + (b - a) * (k + 1) / step))
            bars.append(Bar(t, lo, hi + 0.1, lo - 0.1, hi)) if b > a else bars.append(Bar(t, hi, hi + 0.1, lo - 0.1, lo))
            t += timedelta(minutes=5)
    return bars


def row(tf, trend="up", bias="bullish", ok=True):
    return {"tf": tf, "ok": ok, "structure": {"trend": trend}, "analysis": {"story": {"bias": bias, "stand_aside": None}}}


class StructureTests(unittest.TestCase):
    def test_reads_up_down_and_two_sided_swings(self):
        self.assertEqual(mtf.structure(zig([100, 110, 104, 114, 108, 118, 112, 122]))["trend"], "up")
        self.assertEqual(mtf.structure(zig([122, 112, 118, 108, 114, 104, 110, 100]))["trend"], "down")
        self.assertEqual(mtf.structure(zig([100, 110, 104, 114, 100, 118, 98, 122]))["trend"], "range")

    def test_too_few_candles_is_unclear_not_a_guess(self):
        self.assertEqual(mtf.structure(walk(5, 6))["trend"], "unclear")


class AlignmentTests(unittest.TestCase):
    def test_every_timeframe_with_the_story(self):
        a = mtf.alignment([row(240), row(60), row(15), row(5), row(1)])
        self.assertEqual((a["state"], a["side"]), ("agree", 1))
        self.assertIn("buys", a["text"])

    def test_a_lower_timeframe_against_the_story_is_the_pullback_not_a_stop(self):
        a = mtf.alignment([row(240), row(60), row(15, "down"), row(5, "down"), row(1)])
        self.assertEqual((a["state"], a["side"]), ("pullback", 1))
        self.assertIn("pulling back", a["text"])

    def test_a_higher_timeframe_against_the_story_means_stand_aside(self):
        a = mtf.alignment([row(240), row(60, "down"), row(15), row(5)])
        self.assertEqual((a["state"], a["side"]), ("conflict", None))
        self.assertIn("1-hour", a["text"])
        self.assertIn("stand aside", a["text"])

    def test_no_story_no_side(self):
        self.assertEqual(mtf.alignment([row(240, bias="neutral"), row(60, bias="neutral")])["state"], "none")

    def test_nothing_readable(self):
        self.assertEqual(mtf.alignment([row(240, ok=False)])["state"], "unavailable")
        self.assertEqual(mtf.alignment([])["state"], "unavailable")

    def test_only_higher_timeframes_have_a_direction(self):
        self.assertEqual(mtf.alignment([row(240), row(60), row(5, "range"), row(1, "unclear")])["state"], "higher")


ACTIVE = [
    {"underlying_symbol": "R_75", "underlying_symbol_name": "Volatility 75 Index", "market": "synthetic_index", "submarket_display_name": "Continuous Indices"},
    {"underlying_symbol": "BOOM500", "underlying_symbol_name": "Boom 500 Index", "market": "synthetic_index", "submarket_display_name": "Crash/Boom Indices"},
    {"underlying_symbol": "CRASH300N", "underlying_symbol_name": "Crash 300 Index", "market": "synthetic_index", "submarket_display_name": "Crash/Boom Indices"},
    {"underlying_symbol": "JD50", "underlying_symbol_name": "Jump 50 Index", "market": "synthetic_index", "submarket_display_name": "Jump Indices"},
    {"underlying_symbol": "stpRNG", "underlying_symbol_name": "Step Index", "market": "synthetic_index", "submarket_display_name": "Step Indices"},
    {"underlying_symbol": "frxEURUSD", "underlying_symbol_name": "EUR/USD", "market": "forex", "submarket_display_name": "Major Pairs", "exchange_is_open": 0},
    {"underlying_symbol": "frxEURNOK", "underlying_symbol_name": "EUR/NOK", "market": "forex", "submarket_display_name": "Minor Pairs"},
    {"underlying_symbol": "cryBTCUSD", "underlying_symbol_name": "BTC/USD", "market": "cryptocurrency", "submarket_display_name": "Cryptocurrencies"},
    {"underlying_symbol": "OTC_SPC", "underlying_symbol_name": "US 500", "market": "indices", "submarket_display_name": "Americas"},
    {"underlying_symbol": "frxXAUUSD", "underlying_symbol_name": "Gold/USD", "market": "commodities", "submarket": "metals", "submarket_display_name": "Metals"},
    {"underlying_symbol": "R_100", "underlying_symbol_name": "Volatility 100 Index", "market": "synthetic_index", "is_trading_suspended": 1},
    {"underlying_symbol": "odd", "underlying_symbol_name": "Something else", "market": "otc_widgets"},
]


class FakeWS:
    """Deriv's public socket: answers active_symbols and candle requests, and fails the timeframe it is told to."""

    def __init__(self, fail_tf=None):
        self.q, self.sent, self.closed, self.fail_tf = [], [], False, fail_tf

    def send(self, raw):
        req = json.loads(raw)
        self.sent.append(req)
        if "active_symbols" in req:
            self.q.append({"req_id": req["req_id"], "active_symbols": ACTIVE})
            return
        tf = req["granularity"] // 60
        if tf == self.fail_tf:
            self.q.append({"req_id": req["req_id"], "error": {"code": "X", "message": "boom"}})
            return
        self.q.append({"req_id": req["req_id"], "candles": [{"epoch": int(b.time.timestamp()), "open": b.open, "high": b.high, "low": b.low, "close": b.close}
                                                            for b in walk(tf, req["count"])]})

    def recv(self):
        return json.dumps(self.q.pop(0))

    def close(self):
        self.closed = True


class ListTests(unittest.TestCase):
    def setUp(self):
        mtf._active.update(at=0.0, rows=[])

    def test_every_deriv_market_is_listed_and_synthetics_come_first(self):
        out = mtf.listing(ACTIVE)
        syms = [m["symbol"] for m in out]
        for want in ("R_75", "BOOM500", "CRASH300N", "JD50", "stpRNG", "frxEURUSD", "frxEURNOK", "cryBTCUSD", "OTC_SPC", "frxXAUUSD"):
            self.assertIn(want, syms)
        self.assertNotIn("R_100", syms)   # trading suspended
        self.assertNotIn("odd", syms)     # a kind of market the engine does not read
        self.assertEqual({m["cls"] for m in out[:5]}, {"synthetic"})
        self.assertEqual([m["cls"] for m in out].index("forex"), 5)
        self.assertFalse(next(m for m in out if m["symbol"] == "frxEURUSD")["open"])
        self.assertEqual(next(m for m in out if m["symbol"] == "BOOM500")["group"], "Crash/Boom Indices")

    def test_the_picker_list_comes_from_deriv_over_one_connection(self):
        ws = FakeWS()
        out = mtf.deriv_list(connect=lambda url: ws)
        self.assertGreaterEqual(len(out), 10)
        self.assertTrue(ws.closed)
        self.assertEqual(len(ws.sent), 1)


class ReadTests(unittest.TestCase):
    def setUp(self):
        mtf._active.update(at=0.0, rows=[])

    def test_any_synthetic_index_reads_on_every_timeframe_in_top_down_order(self):
        ws = FakeWS()
        out = mtf.read("BOOM500", now=NOW, connect=lambda url: ws)
        self.assertEqual([r["tf"] for r in out["timeframes"]], list(mtf.TFS))
        self.assertTrue(all(r["ok"] for r in out["timeframes"]))
        self.assertEqual((out["key"], out["label"], out["cls"]), ("BOOM500", "Boom 500 Index", "synthetic"))
        r = out["timeframes"][0]
        self.assertEqual(r["role"], "Sets the story")
        self.assertIn(r["structure"]["trend"], ("up", "down", "range", "unclear"))
        self.assertIn("pool_above", r["near"])
        self.assertIn("ict2022", r["models"])
        self.assertNotIn("chart", r)
        self.assertIn(out["alignment"]["state"], ("agree", "pullback", "conflict", "none", "higher"))

    def test_one_connection_asks_for_the_list_every_timeframe_and_the_daily_candles(self):
        ws = FakeWS()
        mtf.read("stpRNG", now=NOW, connect=lambda url: ws)
        self.assertEqual(len(ws.sent), 1 + len(mtf.TFS) + 1)
        self.assertEqual(sorted(q["granularity"] for q in ws.sent if "granularity" in q), sorted([t * 60 for t in mtf.TFS] + [86400]))
        self.assertTrue(ws.closed)

    def test_the_market_list_is_kept_between_reads(self):
        first, second = FakeWS(), FakeWS()
        mtf.read("R_75", now=NOW, connect=lambda url: first)
        mtf.read("JD50", now=NOW, connect=lambda url: second)
        self.assertTrue(any("active_symbols" in q for q in first.sent))
        self.assertFalse(any("active_symbols" in q for q in second.sent))

    def test_forex_and_other_deriv_markets_read_too(self):
        for sym, cls in (("frxEURUSD", "forex"), ("frxEURNOK", "forex"), ("cryBTCUSD", "crypto"), ("OTC_SPC", "index"), ("frxXAUUSD", "metal")):
            mtf._active.update(at=0.0, rows=[])
            out = mtf.read(sym, now=NOW, tfs=(60, 5), connect=lambda url: FakeWS())
            self.assertEqual(out["cls"], cls, sym)
            self.assertTrue(all(r["ok"] for r in out["timeframes"]), (sym, [r.get("error") for r in out["timeframes"]]))

    def test_one_timeframe_failing_does_not_take_the_others_down(self):
        out = mtf.read("R_75", now=NOW, connect=lambda url: FakeWS(fail_tf=1))
        by = {r["tf"]: r for r in out["timeframes"]}
        self.assertFalse(by[1]["ok"])
        self.assertIn("boom", by[1]["error"])
        self.assertTrue(by[5]["ok"] and by[240]["ok"])

    def test_a_market_deriv_does_not_list_is_an_error_not_a_guess(self):
        with self.assertRaises(LookupError):
            mtf.read("NOT_A_MARKET", now=NOW, connect=lambda url: FakeWS())

    def test_a_market_the_engine_does_not_read_is_refused(self):
        with self.assertRaises(LookupError):
            mtf._market({"underlying_symbol": "odd", "market": "otc_widgets"}, ACTIVE)

    def test_the_key_from_a_request_is_checked(self):
        for good in ("R_75", "frxEURUSD", "cryBTCUSD", "1HZ100V", "BOOM500", "stpRNG", "OTC_SPC"):
            self.assertTrue(mtf.valid_key(good), good)
        for bad in ("", "../etc", "R_75;drop", "a b", "x" * 40, None):
            self.assertFalse(mtf.valid_key(bad), bad)


class PageTests(unittest.TestCase):
    """The page and its endpoint stay wired together: a nav item, a view, a route hook, and an endpoint that checks access."""

    def test_the_view_is_in_the_nav_and_the_router(self):
        html = open("web/template.html", encoding="utf-8").read()
        for needle in ('id="v-mtf"', "{ v: 'mtf'", "if (v === 'mtf') mtfOpen();", "/api/market?key=", "/api/markets", 'id="mtfMarket"', 'id="mtfSearch"'):
            self.assertIn(needle, html, needle)

    def test_the_endpoint_is_gated_and_checks_its_input(self):
        src = open("api/market.py", encoding="utf-8").read()
        for needle in ("access.gate(self)", "ratelimit.guard(self", "mtf.valid_key(key)"):
            self.assertIn(needle, src, needle)
        lst = open("api/markets.py", encoding="utf-8").read()
        for needle in ("access.gate(self)", "ratelimit.guard(self", "mtf.deriv_list()"):
            self.assertIn(needle, lst, needle)


if __name__ == "__main__":
    unittest.main()
