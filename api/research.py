"""API Endpoint: GET /api/research — Institutional Research Lab & Walk-Forward Validator."""

from __future__ import annotations

import json
import os
import sys
from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from flux_engine.research import run_multi_market_benchmark, run_research_backtest


class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self) -> None:
        q = parse_qs(urlparse(self.path).query)
        tf = int(q.get("tf", ["5"])[0])
        days = int(q.get("days", ["45"])[0])
        mode = q.get("mode", ["ict"])[0]
        bench = q.get("benchmark", ["0"])[0] == "1"
        symbol = q.get("symbol", ["XAUUSD"])[0].upper()

        try:
            if bench:
                payload = run_multi_market_benchmark(tf_minutes=tf, days=days)
            else:
                payload = run_research_backtest(symbol=symbol, tf_minutes=tf, days=days, mode=mode)
            body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Cache-Control", "public, s-maxage=120, stale-while-revalidate=600")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        except Exception as e:
            err = json.dumps({"ok": False, "error": f"{type(e).__name__}: {e}"}).encode("utf-8")
            self.send_response(400)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Content-Length", str(len(err)))
            self.end_headers()
            self.wfile.write(err)
