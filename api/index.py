"""Unified Vercel Serverless Function Dispatcher for God's Eye x ICT Flux."""

from __future__ import annotations

import json
import os
import sys
from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse

# Ensure root directory is on Python path so flux_engine imports cleanly
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from flux_engine.research import run_multi_market_benchmark, run_research_backtest
from flux_engine.scanner import scan_live_radar


class handler(BaseHTTPRequestHandler):
    def _send_json(self, status: int, data: dict, cache_seconds: int = 15) -> None:
        raw = json.dumps(data, separators=(",", ":")).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Cache-Control", f"public, s-maxage={cache_seconds}, stale-while-revalidate=60")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/")
        q = parse_qs(parsed.query)

        # 1. /api/scan endpoint
        if path.endswith("/scan") or path == "/api/scan":
            tf = int(q.get("tf", ["5"])[0])
            days = int(q.get("days", ["12"])[0])
            symbols_raw = q.get("symbols", [""])[0]
            keys = [s.strip().upper() for s in symbols_raw.split(",") if s.strip()] if symbols_raw else None
            try:
                res = scan_live_radar(tf_minutes=tf, keys=keys, days=days)
                self._send_json(200, res, cache_seconds=10)
            except Exception as e:
                self._send_json(500, {"ok": False, "error": f"{type(e).__name__}: {e}"})
            return

        # 2. /api/research endpoint
        if path.endswith("/research") or path == "/api/research":
            tf = int(q.get("tf", ["5"])[0])
            days = int(q.get("days", ["45"])[0])
            mode = q.get("mode", ["ict"])[0]
            bench = q.get("benchmark", ["0"])[0] == "1"
            symbol = q.get("symbol", ["XAUUSD"])[0].upper()
            try:
                if bench:
                    res = run_multi_market_benchmark(tf_minutes=tf, days=days)
                else:
                    res = run_research_backtest(symbol=symbol, tf_minutes=tf, days=days, mode=mode)
                self._send_json(200, res, cache_seconds=120)
            except Exception as e:
                self._send_json(400, {"ok": False, "error": f"{type(e).__name__}: {e}"})
            return

        # 3. Health check / Root API fallback
        self._send_json(200, {
            "ok": True,
            "service": "God's Eye x ICT Flux API",
            "endpoints": ["/api/scan", "/api/research"]
        })
