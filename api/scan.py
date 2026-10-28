"""API Endpoint: GET /api/scan — Zero-Lag Institutional Radar."""

from __future__ import annotations

import json
import os
import sys
from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flux_engine.scanner import scan_live_radar  # noqa: E402


class handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        q = parse_qs(urlparse(self.path).query)
        tf = int(q.get("tf", ["5"])[0])
        days = int(q.get("days", ["12"])[0])
        symbols_raw = q.get("symbols", [""])[0]
        keys = [s.strip().upper() for s in symbols_raw.split(",") if s.strip()] if symbols_raw else None
        try:
            payload = scan_live_radar(tf_minutes=tf, keys=keys, days=days)
            body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "public, s-maxage=15, stale-while-revalidate=60")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        except Exception as e:
            err = json.dumps({"ok": False, "error": f"{type(e).__name__}: {e}"}).encode("utf-8")
            self.send_response(500)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(err)))
            self.end_headers()
            self.wfile.write(err)
