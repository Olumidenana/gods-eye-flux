import sys
from ict_trader.research import research

synthetics = ['R_10', 'R_25', 'R_50', 'R_75', 'R_100', '1HZ10V']
print("Testing Turtle Soup on Synthetics (30 days)...", flush=True)

for sym in synthetics:
    try:
        res = research(sym, tf_minutes=5, days=30, mode='allday', model='sweep')
        trades = res.get("trades", [])
        stats = res.get("stats", {})
        print(f"[{sym}]: {len(trades)} trades | Win rate: {stats.get('win_rate_pct')}% | Exp R: {stats.get('expectancy_r')}", flush=True)
    except Exception as e:
        print(f"[{sym}] ERROR: {e}", flush=True)
