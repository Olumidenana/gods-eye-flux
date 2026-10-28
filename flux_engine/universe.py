"""Market Universe & Configuration for God's Eye Flux (Zero Synthetics).

Strictly institutional, session-driven markets with real order flow:
- Forex Majors & Crosses
- Precious & Industrial Metals
- Energy & Commodities
- Global Equity Indices
- Institutional Large-Cap Stocks
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import time


@dataclass(frozen=True)
class TimeWindow:
    name: str
    start: time
    end: time

    def contains(self, t: time) -> bool:
        if self.start <= self.end:
            return self.start <= t < self.end
        return t >= self.start or t < self.end


@dataclass(frozen=True)
class MarketSpec:
    key: str
    label: str
    asset_class: str          # "forex" | "metal" | "commodity" | "index" | "stock"
    deriv_symbol: str         # Deriv symbol; "" when Deriv does not list the market (oil, gas, stocks)
    yahoo_symbol: str         # Yahoo Finance ticker fallback / stock primary
    pip_size: float
    typical_spread_pips: float
    decimals: int
    smt_partner: str          # Correlated triad/dyad partner key for SMT divergence
    region: str = "us"        # "us" | "eu" | "asia" | "global"


# Strict Institutional Universe — Zero Synthetic / RNG Indices
UNIVERSE: tuple[MarketSpec, ...] = (
    # --- Precious & Industrial Metals ---
    MarketSpec("XAUUSD", "Gold (XAU/USD)", "metal", "frxXAUUSD", "GC=F", 0.1, 2.0, 2, "XAGUSD", "global"),
    MarketSpec("XAGUSD", "Silver (XAG/USD)", "metal", "frxXAGUSD", "SI=F", 0.01, 2.0, 3, "XAUUSD", "global"),
    MarketSpec("XPTUSD", "Platinum (XPT/USD)", "metal", "frxXPTUSD", "PL=F", 0.1, 3.5, 2, "XAUUSD", "global"),
    MarketSpec("XCUUSD", "Copper (HG)", "metal", "frxXCUUSD", "HG=F", 0.001, 2.5, 4, "XAUUSD", "global"),

    # --- Forex Majors & Institutional Crosses ---
    MarketSpec("EURUSD", "EUR/USD", "forex", "frxEURUSD", "EURUSD=X", 0.0001, 0.7, 5, "GBPUSD", "global"),
    MarketSpec("GBPUSD", "GBP/USD", "forex", "frxGBPUSD", "GBPUSD=X", 0.0001, 0.9, 5, "EURUSD", "global"),
    MarketSpec("USDJPY", "USD/JPY", "forex", "frxUSDJPY", "JPY=X", 0.01, 0.8, 3, "EURJPY", "global"),
    MarketSpec("USDCHF", "USD/CHF", "forex", "frxUSDCHF", "CHF=X", 0.0001, 1.0, 5, "EURUSD", "global"),
    MarketSpec("AUDUSD", "AUD/USD", "forex", "frxAUDUSD", "AUDUSD=X", 0.0001, 0.9, 5, "NZDUSD", "global"),
    MarketSpec("NZDUSD", "NZD/USD", "forex", "frxNZDUSD", "NZDUSD=X", 0.0001, 1.1, 5, "AUDUSD", "global"),
    MarketSpec("USDCAD", "USD/CAD", "forex", "frxUSDCAD", "CAD=X", 0.0001, 1.0, 5, "WTI", "global"),
    MarketSpec("EURJPY", "EUR/JPY", "forex", "frxEURJPY", "EURJPY=X", 0.01, 1.2, 3, "GBPJPY", "global"),
    MarketSpec("GBPJPY", "GBP/JPY", "forex", "frxGBPJPY", "GBPJPY=X", 0.01, 1.6, 3, "EURJPY", "global"),
    MarketSpec("EURGBP", "EUR/GBP", "forex", "frxEURGBP", "EURGBP=X", 0.0001, 0.9, 5, "EURUSD", "eu"),

    # --- Global Equity Indices ---
    MarketSpec("NAS100", "Nasdaq 100 (USTEC)", "index", "OTC_NDX", "NQ=F", 0.25, 1.2, 2, "US500", "us"),
    MarketSpec("US500", "S&P 500 (US500)", "index", "OTC_SPC", "ES=F", 0.25, 0.6, 2, "NAS100", "us"),
    MarketSpec("US30", "Dow Jones 30 (US30)", "index", "OTC_DJI", "YM=F", 1.0, 1.5, 1, "US500", "us"),
    MarketSpec("DE40", "DAX 40 (GER40)", "index", "OTC_GDAXI", "^GDAXI", 0.5, 1.4, 2, "UK100", "eu"),
    MarketSpec("UK100", "FTSE 100 (UK100)", "index", "OTC_FTSE", "^FTSE", 0.5, 1.2, 2, "DE40", "eu"),
    MarketSpec("JP225", "Nikkei 225 (JP225)", "index", "OTC_N225", "NIY=F", 5.0, 2.0, 1, "US500", "asia"),

    # --- Energy & Commodities ---
    MarketSpec("WTI", "WTI Crude Oil", "commodity", "frxXTIUSD", "CL=F", 0.01, 2.5, 2, "BRENT", "us"),
    MarketSpec("BRENT", "Brent Crude Oil", "commodity", "frxXBRUSD", "BZ=F", 0.01, 2.5, 2, "WTI", "global"),
    MarketSpec("NATGAS", "Natural Gas", "commodity", "NG=F", "NG=F", 0.001, 3.0, 3, "WTI", "us"),

    # --- Institutional Stocks (US RTH Session Leaders) ---
    MarketSpec("NVDA", "NVIDIA Corp", "stock", "OTC_NVDA", "NVDA", 0.01, 2.0, 2, "NAS100", "us"),
    MarketSpec("AAPL", "Apple Inc", "stock", "OTC_AAPL", "AAPL", 0.01, 1.5, 2, "NAS100", "us"),
    MarketSpec("MSFT", "Microsoft Corp", "stock", "OTC_MSFT", "MSFT", 0.01, 1.8, 2, "NAS100", "us"),
    MarketSpec("TSLA", "Tesla Inc", "stock", "OTC_TSLA", "TSLA", 0.01, 2.5, 2, "NAS100", "us"),
    MarketSpec("META", "Meta Platforms", "stock", "OTC_META", "META", 0.01, 2.2, 2, "NAS100", "us"),
    MarketSpec("AMZN", "Amazon.com Inc", "stock", "OTC_AMZN", "AMZN", 0.01, 1.8, 2, "NAS100", "us"),
)

BY_KEY: dict[str, MarketSpec] = {m.key: m for m in UNIVERSE}

ASSET_CLASSES: dict[str, str] = {
    "metal": "Metals",
    "forex": "Forex",
    "index": "Indices",
    "commodity": "Commodities",
    "stock": "Stocks",
}


def killzones_for(spec: MarketSpec) -> tuple[TimeWindow, ...]:
    """Institutional Killzone windows in New York time."""
    if spec.asset_class == "stock":
        # US Equities trade RTH 09:30 - 16:00 NY; primary institutional expansion is Opening Drive & PM
        return (
            TimeWindow("NY_RTH_OPEN", time(9, 30), time(11, 30)),
            TimeWindow("NY_PM_CLOSE", time(13, 30), time(15, 30)),
        )
    if spec.asset_class == "index":
        if spec.region == "eu":
            return (
                TimeWindow("LONDON_OPEN", time(2, 0), time(5, 30)),
                TimeWindow("NY_AM", time(8, 30), time(11, 30)),
            )
        if spec.region == "asia":
            return (
                TimeWindow("TOKYO_OPEN", time(19, 0), time(22, 0)),
                TimeWindow("NY_AM", time(8, 30), time(11, 30)),
            )
        return (
            TimeWindow("LONDON_OPEN", time(2, 0), time(5, 0)),
            TimeWindow("NY_AM_EQUITY", time(8, 30), time(11, 30)),
            TimeWindow("NY_PM", time(13, 30), time(15, 30)),
        )
    # Forex, Metals, Commodities: classic London Open, NY AM, and NY PM Silver Bullet / Macro windows
    return (
        TimeWindow("LONDON_OPEN", time(2, 0), time(5, 30)),
        TimeWindow("NY_AM", time(7, 0), time(11, 0)),
        TimeWindow("NY_PM", time(13, 30), time(15, 0)),
    )


def is_macro_window(ny_t: time) -> bool:
    """ICT Algorithmic Time Macros:
    - XX:50 to XX:10 around every hour in London & NY
    - 09:50-10:10, 10:50-11:10, 13:50-14:10, 15:15-15:45 NY
    """
    m = ny_t.minute
    if m >= 50 or m <= 10:
        return True
    if ny_t.hour == 15 and 15 <= m <= 45:
        return True
    return False
