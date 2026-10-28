import os
import tempfile
import unittest
from datetime import datetime, time, timedelta, timezone
from dataclasses import replace

from ict_trader.broker.base import Broker, BrokerPosition, SymbolSpec
from ict_trader.config import Config, InstrumentConfig, LiveConfig, StrategyConfig
from ict_trader.live import Journal
from ict_trader.notifier import Notifier, NotifierConfig
from ict_trader.portfolio import PortfolioRunner
from ict_trader.sessions import Bar, Level, utc
from ict_trader.strategy import LONG, SHORT, Signal

from tests.helpers import ny_bar, pdh_sweep, prior_day, quiet_open, simple_config


class FakePortfolioBroker(Broker):
    def __init__(self, symbol: str, bars: list[Bar]):
        self.symbol = symbol
        self.bars = bars
        self.visible = len(bars)
        self.orders: list[tuple[int, float, float, float]] = []
        self.positions: list[BrokerPosition] = []

    def connect(self) -> None:
        pass

    def is_real_account(self) -> bool:
        return False

    def closed_bars(self, count: int) -> list[Bar]:
        return self.bars[: self.visible][-count:]

    def equity(self) -> float:
        return 50000.0

    def symbol_spec(self) -> SymbolSpec:
        return SymbolSpec(bid=1.1044, ask=1.10448, value_per_price_unit_per_lot=100000, volume_step=0.01, min_lots=0.01, max_lots=10.0, digits=5)

    def open_positions(self) -> list[BrokerPosition]:
        return list(self.positions)

    def market_order(self, direction: int, lots: float, stop: float, target: float, comment: str) -> int:
        ticket = len(self.orders) + 100
        self.orders.append((direction, lots, stop, target))
        self.positions.append(BrokerPosition(ticket, direction, lots, 1.1044, stop, target, utc(2026, 6, 3, 7, 5)))
        return ticket

    def close_position(self, position: BrokerPosition, comment: str) -> None:
        self.positions = [p for p in self.positions if p.ticket != position.ticket]

    def realized_pnl(self, ticket: int) -> float | None:
        return 150.0


class NotifierTests(unittest.TestCase):
    def test_notifier_dispatches_cleanly_without_network_credentials(self):
        notifier = Notifier(NotifierConfig(enabled=True))
        sig = Signal(
            time=utc(2026, 6, 3, 7, 5),
            direction=SHORT,
            entry_ref=1.3235,
            stop=1.3250,
            target=1.3195,
            rr=2.67,
            level=Level("PDH", 1.3230, "high"),
            killzone="london",
            reasons=("KZ-1 inside london killzone", "TP-3 swept PDH", "FV-01 confirmed FVG"),
        )
        # Verify no unhandled exceptions when tokens are None
        notifier.signal_detected("GBPUSD", sig)
        notifier.order_executed("GBPUSD", 101, SHORT, 0.10, 1.3234, 1.3250, 1.3195, 100.0, "Test Order")
        notifier.position_trimmed("GBPUSD", 101, "50% Target Reached", 1.3242)
        notifier.trade_closed("GBPUSD", 101, 267.0, "TP hit")


class PortfolioRunnerTests(unittest.TestCase):
    def test_portfolio_multi_symbol_warmup_and_poll(self):
        with tempfile.TemporaryDirectory() as tmp:
            journal_path = os.path.join(tmp, "portfolio_journal.sqlite")
            journal = Journal(journal_path)

            bars1 = prior_day() + quiet_open() + [pdh_sweep()]
            bars2 = prior_day() + quiet_open()

            cfg1 = replace(
                simple_config(),
                instrument=InstrumentConfig(symbol="GBPUSD"),
                live=LiveConfig(kill_switch_file=os.path.join(tmp, "STOP")),
            )
            cfg2 = replace(
                simple_config(),
                instrument=InstrumentConfig(symbol="EURUSD"),
                live=LiveConfig(kill_switch_file=os.path.join(tmp, "STOP")),
            )

            broker1 = FakePortfolioBroker("GBPUSD", bars1)
            broker1.visible = 2  # warmup on prior day and quiet open only
            broker2 = FakePortfolioBroker("EURUSD", bars2)
            broker2.visible = 2

            brokers = {
                "GBPUSD": broker1,
                "EURUSD": broker2,
            }

            now = [bars1[2].time + timedelta(minutes=5, seconds=3)]
            runner = PortfolioRunner(
                configs=[cfg1, cfg2],
                broker_factory=lambda c: brokers[c.instrument.symbol],
                news=None,
                journal=journal,
                dry_run=False,
                clock=lambda: now[0],
                max_portfolio_open_positions=2,
            )

            try:
                runner.start(warmup_bars=2)
                self.assertEqual(len(runner.contexts), 2)

                # Reveal the sweep bar to broker1 and poll
                broker1.visible = 3
                self.assertTrue(runner.poll())

                # GBPUSD has pdh_sweep so it should execute a trade
                self.assertGreaterEqual(len(broker1.orders), 1)

                # Test Kill Switch halts and flattens entire portfolio
                open(os.path.join(tmp, "STOP"), "w").close()
                self.assertFalse(runner.poll())
                self.assertEqual(broker1.positions, [])
            finally:
                runner.close()


if __name__ == "__main__":
    unittest.main()
