"""Local & Production Multi-Threaded Server for God's Eye × ICT Flux."""

from __future__ import annotations

import json
import mimetypes
import os
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from flux_engine.research import run_multi_market_benchmark, run_research_backtest
from flux_engine.scanner import scan_live_radar

ROOT = Path(__file__).resolve().parent
WEB_DIR = ROOT / "web"


class FluxRequestHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(WEB_DIR), **kwargs)

    def log_message(self, format: str, *args) -> None:
        pass

    def _send_json(self, status: int, data: dict) -> None:
        raw = json.dumps(data, separators=(",", ":")).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        q = parse_qs(parsed.query)

        if parsed.path == "/api/scan":
            tf = int(q.get("tf", ["5"])[0])
            days = int(q.get("days", ["12"])[0])
            symbols_raw = q.get("symbols", [""])[0]
            keys = [s.strip().upper() for s in symbols_raw.split(",") if s.strip()] if symbols_raw else None
            try:
                res = scan_live_radar(tf_minutes=tf, keys=keys, days=days)
                self._send_json(200, res)
            except Exception as e:
                self._send_json(500, {"ok": False, "error": f"{type(e).__name__}: {e}"})
            return

        if parsed.path == "/api/research":
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
                self._send_json(200, res)
            except Exception as e:
                self._send_json(400, {"ok": False, "error": f"{type(e).__name__}: {e}"})
            return

        return super().do_GET()


def main() -> None:
    port = int(os.environ.get("PORT", "8090"))
    server = ThreadingHTTPServer(("127.0.0.1", port), FluxRequestHandler)
    print(f"God's Eye x ICT Flux Live Server running at http://127.0.0.1:{port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
