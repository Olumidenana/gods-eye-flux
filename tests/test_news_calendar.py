"""The economic calendar in the app: the digest, the blackout banner, the pre-news alert."""
import unittest
from datetime import datetime, timedelta, timezone

from ict_trader import news, scanner, tiers
from ict_trader.news import NewsEvent

NOW = datetime(2026, 10, 7, 12, 20, tzinfo=timezone.utc)   # Wed 08:20 NY
MARKETS = [{"key": "EURUSD", "label": "EUR/USD", "cls": "forex"}, {"key": "GBPJPY", "label": "GBP/JPY", "cls": "forex"},
           {"key": "NAS100", "label": "Nasdaq 100", "cls": "index"}, {"key": "R_75", "label": "Volatility 75", "cls": "synthetic"}]


def cal():
    at = lambda **kw: NOW + timedelta(**kw)  # noqa: E731
    return [NewsEvent(at(minutes=10), "USD", "high", "Non-Farm Employment Change"),
            NewsEvent(at(minutes=10), "USD", "high", "Unemployment Rate"),
            NewsEvent(at(hours=3), "EUR", "medium", "German Factory Orders"),
            NewsEvent(at(hours=5), "GBP", "low", "Something small"),
            NewsEvent(at(days=2), "JPY", "high", "BOJ Press Conference"),
            NewsEvent(at(days=12), "USD", "high", "Too far ahead"),
            NewsEvent(at(hours=-5), "USD", "high", "Already past")]


class DigestTest(unittest.TestCase):
    def setUp(self):
        self.d = news.digest(cal(), MARKETS, NOW)

    def test_keeps_the_events_that_move_markets_inside_the_window(self):
        titles = [e["title"] for e in self.d["events"]]
        self.assertEqual(titles, ["Non-Farm Employment Change", "Unemployment Rate", "German Factory Orders", "BOJ Press Conference"])
        self.assertEqual(self.d["events"][0]["minutes"], 10)

    def test_each_currency_names_the_markets_it_touches_and_synthetics_none(self):
        m = self.d["markets_by_currency"]
        self.assertEqual(m["USD"], ["EUR/USD", "Nasdaq 100"])
        self.assertEqual(m["JPY"], ["GBP/JPY"])
        self.assertTrue(all("Volatility 75" not in v for v in m.values()))

    def test_blackout_covers_the_thirty_minutes_either_side(self):
        self.assertEqual([b["title"] for b in self.d["blackout"]], ["Non-Farm Employment Change", "Unemployment Rate"])
        self.assertEqual(self.d["blackout"][0]["markets"], ["EUR/USD", "Nasdaq 100"])
        later = news.digest(cal(), MARKETS, NOW + timedelta(hours=1))
        self.assertEqual(later["blackout"], [])
        self.assertEqual(later["next_high"]["title"], "BOJ Press Conference")

    def test_a_calendar_that_could_not_be_fetched_says_so(self):
        d = news.digest(None, MARKETS, NOW)
        self.assertFalse(d["ok"])
        self.assertTrue(d["error"])

    def test_fomc_day_note_in_the_afternoon(self):
        ev = [NewsEvent(datetime(2026, 10, 7, 18, 0, tzinfo=timezone.utc), "USD", "high", "FOMC Statement")]
        d = news.digest(ev, MARKETS, datetime(2026, 10, 7, 17, 0, tzinfo=timezone.utc))   # 13:00 NY
        self.assertTrue(any("FOMC" in n["note"] for n in d["day_notes"]), d["day_notes"])


class AlertTest(unittest.TestCase):
    def report(self, now=NOW):
        return {"generated_at": now.isoformat(), "markets": [], "news": news.digest(cal(), MARKETS, now)}

    def test_one_heads_up_for_the_release_with_every_title(self):
        evs = scanner.pending_events(self.report())
        n = [e for e in evs if e["kind"] == "news"]
        self.assertEqual(len(n), 1)
        self.assertIn("10 min", n[0]["title"])
        self.assertIn("Non-Farm Employment Change", n[0]["title"])
        self.assertIn("Unemployment Rate", n[0]["title"])
        self.assertIn("pause", n[0]["body"])

    def test_not_before_the_lead_time_or_after_the_release(self):
        self.assertEqual([e for e in scanner.pending_events(self.report(NOW - timedelta(minutes=20))) if e["kind"] == "news"], [])
        self.assertEqual([e for e in scanner.pending_events(self.report(NOW + timedelta(minutes=11))) if e["kind"] == "news"], [])

    def test_the_same_release_has_the_same_id_every_minute(self):
        a = [e["id"] for e in scanner.pending_events(self.report()) if e["kind"] == "news"]
        b = [e["id"] for e in scanner.pending_events(self.report(NOW + timedelta(minutes=1))) if e["kind"] == "news"]
        self.assertEqual(a, b)

    def test_a_plus_only_phones_stay_quiet_for_news(self):
        ev = {"kind": "news", "grade": None}
        self.assertEqual([tiers.allows(t, ev) for t in ("aplus", "a", "b")], [False, True, True])

    def test_scan_attaches_the_digest(self):
        import os
        from unittest import mock
        with mock.patch.object(scanner, "_run", return_value=[{"ok": True, "key": "EURUSD", "label": "EUR/USD", "cls": "forex", "today": {"signals": []}}]), \
             mock.patch.dict(os.environ, {"NEWS_FILTER": "1"}):
            env = scanner.scan(fetch=None, now=NOW, calendar=cal())
        self.assertTrue(env["news"]["ok"])
        self.assertEqual(env["news"]["next_high"]["title"], "Non-Farm Employment Change")


if __name__ == "__main__":
    unittest.main()
