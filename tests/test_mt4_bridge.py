"""Exercises the MT4 file bridge against a fake EA that mimics ICTBridge.mq4."""

import os
import tempfile
import threading
import time
import unittest
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

from ict_trader.broker.base import BrokerError
from ict_trader.broker.mt4 import MT4BridgeBroker
from ict_trader.config import Config, LiveConfig
from ict_trader.strategy import LONG, SHORT

# 2026-06-03 10:00 server time (NY+7) = 03:00 NY = 07:00 UTC.
SERVER_EPOCH = int(datetime(2026, 6, 3, 10, 0, tzinfo=timezone.utc).timestamp())
NOW = datetime(2026, 6, 3, 7, 0, 5, tzinfo=timezone.utc)


class FakeEA:
    def __init__(self, folder: Path, reply: str | None = "OK 555"):
        self.folder, self.reply, self.commands = folder, reply, []
        self._stop = threading.Event()
        self.write("account.txt", "\n".join([
            "symbol=EURUSD", "timeframe_minutes=5", "equity=10250.50", "demo=1", "trade_allowed=1",
            "bid=1.10440", "ask=1.10448", "tick_value=1.0", "tick_size=0.00001",
            "lot_step=0.01", "min_lot=0.01", "max_lot=100", "digits=5",
            f"gmt_time={int(NOW.timestamp())}", f"server_time={SERVER_EPOCH}",
        ]))
        self.write("bars.csv", "time,open,high,low,close,volume\n"
                   f"{SERVER_EPOCH - 300},1.1040,1.1056,1.1038,1.1045,120\n{SERVER_EPOCH},1.1045,1.1046,1.1040,1.1042,80\n")
        self.write("positions.csv", f"ticket,type,lots,open_price,sl,tp,open_time\n777,1,0.41,1.1045,1.1057,1.1021,{SERVER_EPOCH}\n")
        self.write("history.csv", "ticket,pnl,close_time\n555,-49.87,0\n")

    def write(self, name: str, content: str) -> None:
        (self.folder / f"ictb_EURUSD_{name}").write_text(content)

    def serve(self) -> None:
        while not self._stop.is_set():
            for cmd in self.folder.glob("ictb_EURUSD_cmd_*.txt"):
                lines = cmd.read_text().splitlines()
                cmd.unlink()
                self.commands.append(lines)
                if self.reply is not None:
                    self.write(f"res_{lines[0]}.txt", self.reply + "\n")
            time.sleep(0.02)

    def __enter__(self):  # type: ignore[no-untyped-def]
        self.thread = threading.Thread(target=self.serve, daemon=True)
        self.thread.start()
        return self

    def __exit__(self, *exc):  # type: ignore[no-untyped-def]
        self._stop.set()
        self.thread.join()


class MT4BridgeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.folder = Path(self.tmp.name)
        self.config = replace(Config(), live=LiveConfig(platform="mt4", bridge_dir=self.tmp.name, bridge_timeout_seconds=2))

    def tearDown(self):
        self.tmp.cleanup()

    def broker(self) -> MT4BridgeBroker:
        return MT4BridgeBroker(self.config, clock=lambda: NOW)

    def test_reads_state_published_by_ea(self):
        FakeEA(self.folder)
        b = self.broker()
        b.connect()
        self.assertFalse(b.is_real_account())
        self.assertEqual(b.equity(), 10250.50)
        bars = b.closed_bars(10)
        self.assertEqual(bars[0].time, datetime(2026, 6, 3, 6, 55, tzinfo=timezone.utc))
        spec = b.symbol_spec()
        self.assertAlmostEqual(spec.value_per_price_unit_per_lot, 100_000)
        (pos,) = b.open_positions()
        self.assertEqual((pos.ticket, pos.direction, pos.stop), (777, SHORT, 1.1057))
        self.assertEqual(b.realized_pnl(555), -49.87)
        self.assertIsNone(b.realized_pnl(1))

    def test_stale_heartbeat_refuses_to_connect(self):
        FakeEA(self.folder)
        b = MT4BridgeBroker(self.config, clock=lambda: NOW.replace(minute=5))
        with self.assertRaisesRegex(BrokerError, "heartbeat"):
            b.connect()

    def test_wrong_timeframe_refuses_to_connect(self):
        FakeEA(self.folder)
        cfg = replace(self.config, strategy=replace(self.config.strategy, timeframe_minutes=15))
        with self.assertRaisesRegex(BrokerError, "M5"):
            MT4BridgeBroker(cfg, clock=lambda: NOW).connect()

    def test_order_round_trip(self):
        with FakeEA(self.folder) as ea:
            ticket = self.broker().market_order(LONG, 0.41, 1.1030, 1.1080, "ICT PDL")
        self.assertEqual(ticket, 555)
        _, action, direction, lots, sl, tp, comment = ea.commands[0]
        self.assertEqual((action, direction, lots, sl, tp, comment), ("OPEN", "1", "0.41", "1.103", "1.108", "ICT PDL"))
        self.assertEqual(list(self.folder.glob("*res_*")), [])

    def test_rejection_raises(self):
        with FakeEA(self.folder, reply="ERR 134 not enough money"):
            with self.assertRaisesRegex(BrokerError, "not enough money"):
                self.broker().market_order(SHORT, 1.0, 1.2, 1.0, "x")

    def test_timeout_raises(self):
        with FakeEA(self.folder, reply=None):
            with self.assertRaisesRegex(BrokerError, "No reply"):
                self.broker().close_position(self.broker().open_positions()[0], "EX-1")

    def test_missing_bridge_dir(self):
        with self.assertRaises(BrokerError):
            MT4BridgeBroker(Config())
        self.assertFalse(os.path.exists(os.path.join(self.tmp.name, "ictb_EURUSD_cmd.txt")))


if __name__ == "__main__":
    unittest.main()
