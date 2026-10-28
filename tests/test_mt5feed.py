import unittest
from datetime import datetime, timedelta, timezone

from ict_trader.mt5feed import feed, mt5_symbol

NOW = datetime(2026, 10, 7, 14, 0, tzinfo=timezone.utc)


def sig(sid, bs, label, minutes_ago=2, status="open", direction="short"):
    return {"id": sid, "label": label, "broker_symbol": bs, "direction": direction, "entry": 1.1, "stop": 1.101, "target": 1.097,
            "rr": 3.0, "quality": {"grade": "A"}, "time": (NOW - timedelta(minutes=minutes_ago)).isoformat(), "timeframe_minutes": 5,
            "outcome": {"status": status}, "setup": {"tp1": 1.099}}


class Mt5FeedTest(unittest.TestCase):
    def test_symbol_names(self):
        self.assertEqual(mt5_symbol({"broker_symbol": "frxEURUSD", "label": "EUR/USD"}), "EURUSD")
        self.assertEqual(mt5_symbol({"broker_symbol": "cryBTCUSD", "label": "BTC/USD"}), "BTCUSD")
        self.assertEqual(mt5_symbol({"broker_symbol": "R_75", "label": "Volatility 75 Index"}), "Volatility 75 Index")

    def test_feed_lists_recent_open_signals_only(self):
        report = {"markets": [
            {"ok": True, "cls": "synthetic", "today": {"signals": [sig("V75-1", "R_75", "Volatility 75 Index"),
                                                                  sig("OLD", "R_75", "Volatility 75 Index", minutes_ago=90),
                                                                  sig("DONE", "R_75", "Volatility 75 Index", status="win")]}},
            {"ok": False, "cls": "forex"}]}
        lines = feed(report, NOW).strip().split("\n")
        self.assertEqual(lines[0], f"ICTFLUX1|{int(NOW.timestamp())}")
        self.assertEqual(len(lines), 2)
        f = lines[1].split("|")
        self.assertEqual(len(f), 14)
        self.assertEqual(f[:5], ["V75-1", "synthetic", "Volatility 75 Index", "Volatility 75 Index", "sell"])
        self.assertEqual((f[7], f[10], int(f[11])), ("1.099", "A", int((NOW - timedelta(minutes=2)).timestamp())))


if __name__ == "__main__":
    unittest.main()
