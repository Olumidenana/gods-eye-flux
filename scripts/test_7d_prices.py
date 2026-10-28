import sys
import json
from ict_trader.research import research

MARKETS = [
    ("frxEURUSD", "EUR/USD", "ict", 5),
    ("frxGBPUSD", "GBP/USD", "ict", 5),
    ("frxUSDJPY", "USD/JPY", "ict", 5),
    ("R_10", "Volatility 10 Index", "allday", 5),
    ("R_25", "Volatility 25 Index", "allday", 5),
    ("R_50", "Volatility 50 Index", "allday", 5),
]

MODELS = ["sweep", "ict2022", "ote", "unicorn"]

all_trades = []

print("=== 7-DAY EMPIRICAL TESTING ON DERIV PRICE FEED ===", flush=True)

for sym, label, mode, tf in MARKETS:
    for m in MODELS:
        try:
            res = research(sym, tf_minutes=tf, days=7, mode=mode, model=m)
            trades = res.get("trades", [])
            stats = res.get("stats", {})
            cnt = len(trades)
            if cnt > 0:
                print(f"[FOUND] {label} ({sym}) - Model: {m} -> {cnt} trades | Win Rate: {stats.get('win_rate_pct')}% | Exp R: {stats.get('expectancy_r')}", flush=True)
                for t in trades:
                    all_trades.append({
                        "market": label,
                        "symbol": sym,
                        "model": m,
                        "time": t.get("time"),
                        "direction": t.get("dir"),
                        "entry": t.get("entry"),
                        "exit": t.get("exit"),
                        "r": t.get("r"),
                        "reason": t.get("exit_reason")
                    })
            else:
                print(f"[CLEAR] {label} ({sym}) - Model: {m} -> 0 setups executed in past 7d", flush=True)
        except Exception as e:
            print(f"[ERROR] {sym} {m}: {e}", flush=True)

print(f"\nTotal trades across 7-day test: {len(all_trades)}", flush=True)
with open("scripts/7d_empirical_results.json", "w") as f:
    json.dump(all_trades, f, indent=2)
print("Saved to scripts/7d_empirical_results.json", flush=True)
