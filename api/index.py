"""Unified WSGI Application & Serverless Dispatcher for God's Eye x ICT Flux."""

from __future__ import annotations

import json
import mimetypes
import os
import sys
from pathlib import Path
from urllib.parse import parse_qs

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from flux_engine.research import run_multi_market_benchmark, run_research_backtest
from flux_engine.scanner import scan_live_radar

WEB_DIR = ROOT / "web"


def _send_json(start_response, status_code: int, data: dict, cache_seconds: int = 15):
    status_text = "200 OK" if status_code == 200 else f"{status_code} Error"
    body = json.dumps(data, separators=(",", ":")).encode("utf-8")
    headers = [
        ("Content-Type", "application/json; charset=utf-8"),
        ("Access-Control-Allow-Origin", "*"),
        ("Access-Control-Allow-Methods", "GET, OPTIONS"),
        ("Access-Control-Allow-Headers", "Content-Type"),
        ("Cache-Control", f"public, s-maxage={cache_seconds}, stale-while-revalidate=60"),
        ("Content-Length", str(len(body))),
    ]
    start_response(status_text, headers)
    return [body]


def _serve_file(start_response, file_path: Path):
    if not file_path.exists() or not file_path.is_file():
        status = "404 Not Found"
        body = b"404 Not Found"
        headers = [
            ("Content-Type", "text/plain; charset=utf-8"),
            ("Content-Length", str(len(body))),
        ]
        start_response(status, headers)
        return [body]

    mime, _ = mimetypes.guess_type(str(file_path))
    if not mime:
        if file_path.name.endswith(".js"):
            mime = "application/javascript"
        elif file_path.name.endswith(".html"):
            mime = "text/html"
        else:
            mime = "application/octet-stream"

    body = file_path.read_bytes()
    headers = [
        ("Content-Type", f"{mime}; charset=utf-8" if ("text" in mime or "javascript" in mime or "json" in mime) else mime),
        ("Cache-Control", "public, max-age=3600"),
        ("Content-Length", str(len(body))),
    ]
    start_response("200 OK", headers)
    return [body]


def app(environ, start_response):
    path = environ.get("PATH_INFO", "/").strip()
    query_string = environ.get("QUERY_STRING", "")
    method = environ.get("REQUEST_METHOD", "GET").upper()

    if method == "OPTIONS":
        headers = [
            ("Access-Control-Allow-Origin", "*"),
            ("Access-Control-Allow-Methods", "GET, OPTIONS"),
            ("Access-Control-Allow-Headers", "Content-Type"),
            ("Content-Length", "0"),
        ]
        start_response("204 No Content", headers)
        return [b""]

    # 1. Root and index.html
    if path in ("", "/", "/index.html"):
        return _serve_file(start_response, WEB_DIR / "index.html")

    # 2. API: /api/scan
    if path == "/api/scan" or path.endswith("/scan"):
        q = parse_qs(query_string)
        tf = int(q.get("tf", ["5"])[0])
        days = int(q.get("days", ["12"])[0])
        symbols_raw = q.get("symbols", [""])[0]
        keys = [s.strip().upper() for s in symbols_raw.split(",") if s.strip()] if symbols_raw else None
        try:
            res = scan_live_radar(tf_minutes=tf, keys=keys, days=days)
            return _send_json(start_response, 200, res, cache_seconds=10)
        except Exception as e:
            return _send_json(start_response, 500, {"ok": False, "error": f"{type(e).__name__}: {e}"})

    # 3. API: /api/research
    if path == "/api/research" or path.endswith("/research"):
        q = parse_qs(query_string)
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
            return _send_json(start_response, 200, res, cache_seconds=120)
        except Exception as e:
            return _send_json(start_response, 400, {"ok": False, "error": f"{type(e).__name__}: {e}"})

    # 4. Static assets (e.g. lightweight-charts.standalone.production.js)
    sub_path = path.lstrip("/")
    if sub_path.startswith("web/"):
        sub_path = sub_path[4:]
    target_file = WEB_DIR / sub_path
    if target_file.exists() and target_file.is_file():
        return _serve_file(start_response, target_file)

    # 5. Default fallback to index.html
    return _serve_file(start_response, WEB_DIR / "index.html")


handler = app
