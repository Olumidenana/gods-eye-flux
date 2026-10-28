"""Export ICT Research Lab backtest dossiers, trades, and chart replays.

Usage:
    python scripts/export_research.py --symbols frxXAUUSD,frxEURUSD,R_75 --timeframes 5,15 --models ict2022
"""

import argparse
import csv
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# Ensure root package can be imported
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ict_trader.research import (
    DEFAULT_DAYS,
    MARKETS,
    MODELS,
    SYNTHETICS,
    TIMEFRAMES,
    research,
)


def resolve_market_meta(sym: str) -> tuple[str, str, str]:
    """Returns (broker_symbol, label, cls)."""
    s = sym.strip()
    upper = s.upper()
    if upper in ("XAUUSD", "GOLD"):
        return "frxXAUUSD", "Gold", "metal"
    if upper in ("EURUSD", "GBPUSD", "USDJPY", "USDCHF", "AUDUSD", "USDCAD", "NZDUSD"):
        return f"frx{upper}", f"{upper[:3]}/{upper[3:]}", "forex"
    if upper.startswith("FRX"):
        plain = upper[3:]
        label = "Gold" if plain == "XAUUSD" else f"{plain[:3]}/{plain[3:]}" if len(plain) == 6 else s
        cls = "metal" if plain == "XAUUSD" else "forex"
        return s, label, cls
    if s in SYNTHETICS:
        return s, SYNTHETICS[s], "synthetic"
    return s, s, "synthetic" if (s.startswith("R_") or "HZ" in s) else "forex"


def export_csv(trades_data: list[dict], out_path: Path):
    fieldnames = [
        "trade_num",
        "market",
        "label",
        "timeframe_m",
        "direction",
        "entry_time_ny",
        "entry_time_utc",
        "exit_time_ny",
        "exit_time_utc",
        "entry_price",
        "stop_loss",
        "take_profit",
        "exit_price",
        "rr_ratio",
        "status",
        "net_r",
        "exit_reason",
        "killzone",
        "level_swept",
        "reasons",
    ]
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for i, t in enumerate(trades_data, 1):
            outcome = t.get("outcome", {}) or {}
            r_val = outcome.get("r", 0)
            writer.writerow({
                "trade_num": i,
                "market": t.get("market"),
                "label": t.get("label"),
                "timeframe_m": t.get("timeframe_minutes"),
                "direction": t.get("direction", "").upper(),
                "entry_time_ny": t.get("time_ny"),
                "entry_time_utc": t.get("time"),
                "exit_time_ny": t.get("exit_time_ny"),
                "exit_time_utc": t.get("exit_time"),
                "entry_price": t.get("entry"),
                "stop_loss": t.get("stop"),
                "take_profit": t.get("target"),
                "exit_price": t.get("exit"),
                "rr_ratio": t.get("rr"),
                "status": outcome.get("status", "").upper(),
                "net_r": r_val,
                "exit_reason": outcome.get("label", ""),
                "killzone": t.get("killzone", ""),
                "level_swept": t.get("level", ""),
                "reasons": " | ".join(t.get("reasons", [])),
            })


def export_html_charts(test_data: dict, out_path: Path):
    """Generates a self-contained offline visual trade replay viewer."""
    title = f"{test_data.get('label')} ({test_data.get('timeframe_minutes')}m - {test_data.get('model')}) Trade Replays"
    charts_json = json.dumps(test_data.get("trade_charts", []), separators=(",", ":"))
    stats_json = json.dumps(test_data.get("stats", {}), separators=(",", ":"))
    
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>{title}</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #0b0f19; color: #e2e8f0; margin: 0; padding: 20px; }}
    h1, h2, h3 {{ color: #f8fafc; margin: 0 0 6px; }}
    .stats-bar {{ display: flex; gap: 14px; background: #131b2e; padding: 14px 18px; border-radius: 8px; margin-bottom: 20px; border: 1px solid #1e293b; flex-wrap: wrap; }}
    .stat {{ display: flex; flex-direction: column; }}
    .stat small {{ font-size: 11px; text-transform: uppercase; color: #94a3b8; font-weight: 600; }}
    .stat b {{ font-size: 18px; font-family: monospace; color: #38bdf8; }}
    .trade-card {{ background: #131b2e; border: 1px solid #1e293b; border-radius: 8px; padding: 16px; margin-bottom: 24px; }}
    .trade-head {{ display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #1e293b; padding-bottom: 10px; margin-bottom: 12px; flex-wrap: wrap; gap: 8px; }}
    .badge {{ padding: 3px 8px; border-radius: 4px; font-weight: 700; font-size: 12px; text-transform: uppercase; }}
    .badge.win {{ background: #064e3b; color: #34d399; }}
    .badge.loss {{ background: #7f1d1d; color: #f87171; }}
    .badge.buy {{ background: #0369a1; color: #7dd3fc; }}
    .badge.sell {{ background: #831843; color: #f472b6; }}
    .levels {{ display: flex; gap: 16px; margin-bottom: 12px; font-family: monospace; font-size: 13px; }}
    .chart-box {{ width: 100%; height: 260px; background: #070a13; border: 1px solid #1e293b; border-radius: 6px; position: relative; overflow: hidden; }}
    svg {{ width: 100%; height: 100%; }}
  </style>
</head>
<body>
  <h1>{title}</h1>
  <p style="color:#94a3b8;margin-bottom:16px">Tested {test_data.get('candles', 0):,} candles from {test_data.get('from', '')[:10]} to {test_data.get('to', '')[:10]}</p>
  <div class="stats-bar" id="statsBar"></div>
  <div id="tradesList"></div>

  <script>
    const charts = {charts_json};
    const stats = {stats_json};
    
    document.getElementById('statsBar').innerHTML = `
      <div class="stat"><small>Trades</small><b>${{stats.trades || 0}}</b></div>
      <div class="stat"><small>Win Rate</small><b>${{(stats.win_rate_pct || 0).toFixed(1)}}%</b></div>
      <div class="stat"><small>Expectancy</small><b style="color:${{stats.expectancy_r >= 0 ? '#34d399':'#f87171'}}">${{(stats.expectancy_r >= 0 ? '+' : '') + (stats.expectancy_r || 0).toFixed(2)}}R</b></div>
      <div class="stat"><small>Profit Factor</small><b>${{(stats.profit_factor || 0).toFixed(2)}}</b></div>
      <div class="stat"><small>Max Drawdown</small><b>${{(stats.max_drawdown_pct || 0).toFixed(1)}}%</b></div>
    `;

    function renderCandlesSvg(candles, entry, stop, target, exitPrice) {{
      if (!candles || !candles.length) return '';
      const highs = candles.map(c => c[2]), lows = candles.map(c => c[3]);
      const minP = Math.min(...lows, stop, target), maxP = Math.max(...highs, stop, target);
      const spanP = (maxP - minP) || 1;
      const W = 900, H = 240, pad = 10;
      const yOf = p => H - pad - ((p - minP) / spanP) * (H - 2 * pad);
      const step = W / candles.length;
      
      let sv = `<svg viewBox="0 0 ${{W}} ${{H}}" preserveAspectRatio="none">`;
      sv += `<line x1="0" y1="${{yOf(entry)}}" x2="${{W}}" y2="${{yOf(entry)}}" stroke="#38bdf8" stroke-width="1.5" stroke-dasharray="4"/>`;
      sv += `<line x1="0" y1="${{yOf(stop)}}" x2="${{W}}" y2="${{yOf(stop)}}" stroke="#ef4444" stroke-width="1.5"/>`;
      sv += `<line x1="0" y1="${{yOf(target)}}" x2="${{W}}" y2="${{yOf(target)}}" stroke="#10b981" stroke-width="1.5"/>`;
      
      candles.forEach((c, i) => {{
        const x = i * step + step / 2;
        const o = c[1], h = c[2], l = c[3], cl = c[4];
        const bull = cl >= o;
        const color = bull ? '#10b981' : '#ef4444';
        const top = Math.min(yOf(o), yOf(cl)), hgt = Math.max(2, Math.abs(yOf(o) - yOf(cl)));
        sv += `<line x1="${{x}}" y1="${{yOf(h)}}" x2="${{x}}" y2="${{yOf(l)}}" stroke="${{color}}" stroke-width="1"/>`;
        sv += `<rect x="${{x - step*0.35}}" y="${{top}}" width="${{step*0.7}}" height="${{hgt}}" fill="${{color}}"/>`;
      }});
      sv += '</svg>';
      return sv;
    }}

    document.getElementById('tradesList').innerHTML = charts.map((t, idx) => {{
      const outcome = t.outcome || {{}};
      const isWin = outcome.r > 0.05;
      const candles = t.candles || [];
      return `
        <div class="trade-card">
          <div class="trade-head">
            <div>
              <span class="badge ${{t.direction === 'long' ? 'buy' : 'sell'}}">${{t.direction === 'long' ? 'BUY' : 'SELL'}}</span>
              <b style="margin-left:8px">${{t.label}}</b>
              <span style="color:#94a3b8;font-size:13px;margin-left:6px">${{t.time_ny}} NY</span>
            </div>
            <div>
              <span class="badge ${{isWin ? 'win' : 'loss'}}">${{outcome.status}} (${{(outcome.r >= 0 ? '+' : '') + (outcome.r || 0).toFixed(2)}}R)</span>
              <span style="color:#94a3b8;font-size:12px;margin-left:8px">${{t.killzone || ''}}</span>
            </div>
          </div>
          <div class="levels">
            <span>Entry: <b>${{t.entry}}</b></span>
            <span>Stop: <b style="color:#ef4444">${{t.stop}}</b></span>
            <span>Target: <b style="color:#10b981">${{t.target}}</b></span>
            <span>Exit: <b>${{t.exit}}</b> (${{outcome.label || ''}})</span>
            <span>R:R: <b>${{t.rr}}</b></span>
          </div>
          <div class="chart-box">${{renderCandlesSvg(candles, t.entry, t.stop, t.target, t.exit)}}</div>
        </div>
      `;
    }}).join('') || '<p style="color:#94a3b8">No visual trade replays available in this batch.</p>';
  </script>
</body>
</html>
"""
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)


def run_exports(symbols: list[str], timeframes: list[int], models: list[str], days: int | None, mode: str, out_dir: Path):
    out_dir.mkdir(parents=True, exist_ok=True)
    summary_rows = []

    print(f"=== Starting ICT Research Lab Export ===", flush=True)
    print(f"Symbols: {symbols}", flush=True)
    print(f"Timeframes: {timeframes}", flush=True)
    print(f"Models: {models}", flush=True)
    print(f"Mode: {mode}", flush=True)
    print(f"Destination: {out_dir}\n", flush=True)

    for raw_sym in symbols:
        broker_sym, label, cls = resolve_market_meta(raw_sym)
        for tf in timeframes:
            for mod in models:
                tag = f"{broker_sym}_{tf}m_{mod}_{mode}"
                print(f"-> Backtesting {label} ({broker_sym}) | {tf}m | {mod} | {mode}...", flush=True)
                try:
                    res = research(broker_sym, tf_minutes=tf, days=days, mode=mode, model=mod, label=label, cls=cls)
                except Exception as e:
                    print(f"   [!] Failed {broker_sym} {tf}m: {e}", flush=True)
                    continue

                stats = res.get("stats", {}) or {}
                trade_charts = res.get("trade_charts", []) or []
                
                # 1. Full JSON Dossier
                json_path = out_dir / f"dossier_{tag}.json"
                with open(json_path, "w", encoding="utf-8") as f:
                    json.dump(res, f, indent=2)

                # 2. Complete Trades CSV
                csv_path = out_dir / f"trades_{tag}.csv"
                export_csv(trade_charts, csv_path)

                # 3. Interactive HTML Visual Chart Replayer
                html_path = out_dir / f"charts_{tag}.html"
                export_html_charts(res, html_path)

                verdict_obj = res.get("verdict")
                verdict_str = (
                    verdict_obj.get("code")
                    if isinstance(verdict_obj, dict)
                    else (verdict_obj[0] if isinstance(verdict_obj, (list, tuple)) else str(verdict_obj))
                )

                summary_rows.append({
                    "symbol": broker_sym,
                    "label": res.get("label"),
                    "timeframe": f"{tf}m",
                    "model": mod,
                    "mode": mode,
                    "days": round(res.get("calendar_days", 0), 1),
                    "candles": res.get("candles", 0),
                    "trades": stats.get("trades", 0),
                    "win_rate_pct": stats.get("win_rate_pct", 0),
                    "expectancy_r": stats.get("expectancy_r", 0),
                    "total_r": stats.get("expectancy_r", 0) * stats.get("trades", 0),
                    "profit_factor": stats.get("profit_factor", 0),
                    "max_drawdown_pct": stats.get("max_drawdown_pct", 0),
                    "t_stat": stats.get("expectancy_t_stat", 0),
                    "verdict": verdict_str,
                    "csv_file": csv_path.name,
                    "json_file": json_path.name,
                    "charts_file": html_path.name,
                })
                print(f"   [OK] {stats.get('trades', 0)} trades | WinRate: {stats.get('win_rate_pct', 0):.1f}% | Exp: {stats.get('expectancy_r', 0):+.2f}R", flush=True)

    # Master Summary CSV
    if summary_rows:
        sum_path = out_dir / "research_master_summary.csv"
        with open(sum_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(summary_rows[0].keys()))
            writer.writeheader()
            writer.writerows(summary_rows)
        print(f"\n[Done] Master Summary written to: {sum_path}", flush=True)


def main():
    parser = argparse.ArgumentParser(description="Export ICT Research Lab backtests to CSV, JSON, and HTML.")
    parser.add_argument("--symbols", default="frxXAUUSD,frxEURUSD,R_75", help="Comma-separated symbols")
    parser.add_argument("--timeframes", default="5", help="Comma-separated timeframes in minutes")
    parser.add_argument("--models", default="ict2022", help="Comma-separated models (ict2022, silver_bullet, etc.)")
    parser.add_argument("--days", type=int, default=30, help="Days of history")
    parser.add_argument("--mode", default="ict", choices=["ict", "all"], help="Time mode: ict killzones or all day")
    parser.add_argument("--out", default="exports/research", help="Output directory")
    args = parser.parse_args()

    syms = [s.strip() for s in args.symbols.split(",") if s.strip()]
    tfs = [int(t.strip()) for t in args.timeframes.split(",") if t.strip()]
    mods = [m.strip() for m in args.models.split(",") if m.strip()]
    out_dir = Path(args.out)

    run_exports(syms, tfs, mods, args.days, args.mode, out_dir)


if __name__ == "__main__":
    main()
