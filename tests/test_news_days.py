import unittest
from datetime import datetime
from zoneinfo import ZoneInfo

from ict_trader.config import InstrumentConfig, NewsConfig
from ict_trader.news import NewsFilter, parse_ff

NY = ZoneInfo("America/New_York")
EVENTS = parse_ff([
    {"title": "Non-Farm Employment Change", "country": "USD", "date": "2026-06-05T08:30:00-04:00", "impact": "High"},
    {"title": "Federal Funds Rate", "country": "USD", "date": "2026-06-17T14:00:00-04:00", "impact": "High"},
    {"title": "Memorial Day", "country": "USD", "date": "2026-05-25T00:00:00-04:00", "impact": "Holiday"},
])


def at(s):
    return datetime.fromisoformat(s).replace(tzinfo=NY)


class NoTradeDayTest(unittest.TestCase):
    def setUp(self):
        self.f = NewsFilter(NewsConfig(), InstrumentConfig(symbol="EURUSD"), EVENTS)

    def test_nfp_week_stops_wednesday_noon(self):
        self.assertIsNone(self.f.no_trade(at("2026-06-03T10:00")))            # Wednesday morning
        self.assertTrue(self.f.no_trade(at("2026-06-03T12:30")).startswith("NF-04"))
        self.assertTrue(self.f.no_trade(at("2026-06-04T03:00")).startswith("NF-04"))  # Thursday
        self.assertIsNone(self.f.no_trade(at("2026-06-08T03:00")))            # next week

    def test_fomc_day_has_no_afternoon(self):
        self.assertIsNone(self.f.no_trade(at("2026-06-17T09:00")))
        self.assertTrue(self.f.no_trade(at("2026-06-17T13:30")).startswith("NF-03"))

    def test_holiday_and_the_friday_before(self):
        self.assertTrue(self.f.no_trade(at("2026-05-25T03:00")).startswith("NF-05"))
        self.assertTrue(self.f.no_trade(at("2026-05-22T13:00")).startswith("NF-05"))
        self.assertIsNone(self.f.no_trade(at("2026-05-22T09:00")))

    def test_markets_without_usd_news_are_unaffected(self):
        f = NewsFilter(NewsConfig(), InstrumentConfig(symbol="EURGBP"), EVENTS)
        self.assertIsNone(f.no_trade(at("2026-06-04T03:00")))


if __name__ == "__main__":
    unittest.main()
