import glob
import re
import csv
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
RESEARCH_DIR = BASE_DIR / "research" / "ict-videos"
SUMMARY_CSV = RESEARCH_DIR / "summary.csv"

def extract_symbols(raw_text: str):
    symbols = []
    if re.search(r'\b(ES|ESH\d{2}|E-MINI S&P|S&P 500)\b', raw_text, re.IGNORECASE):
        symbols.append("ES")
    if re.search(r'\b(MES|MICRO E-MINI S&P)\b', raw_text, re.IGNORECASE):
        symbols.append("MES")
    if re.search(r'\b(NQ|NQH\d{2}|E-MINI NASDAQ|NASDAQ-100|NASDAQ)\b', raw_text, re.IGNORECASE):
        symbols.append("NQ")
    if re.search(r'\b(MNQ|MICRO E-MINI NASDAQ)\b', raw_text, re.IGNORECASE):
        symbols.append("MNQ")
    if re.search(r'\b(YM|DOW)\b', raw_text, re.IGNORECASE):
        symbols.append("YM")
    if re.search(r'\b(EUR/JPY|EURJPY)\b', raw_text, re.IGNORECASE):
        symbols.append("EURJPY")
    if re.search(r'\b(EUR/AUD|EURAUD)\b', raw_text, re.IGNORECASE):
        symbols.append("EURAUD")
    if re.search(r'\b(EUR/USD|EURUSD)\b', raw_text, re.IGNORECASE):
        symbols.append("EURUSD")
    if re.search(r'\b(GBP/USD|GBPUSD)\b', raw_text, re.IGNORECASE):
        symbols.append("GBPUSD")
    if re.search(r'\b(6E|EURO FUTURES)\b', raw_text, re.IGNORECASE):
        symbols.append("6E")
    if re.search(r'\b(6J|YEN FUTURES)\b', raw_text, re.IGNORECASE):
        symbols.append("6J")
    if re.search(r'\b(DXY|DOLLAR INDEX|US DOLLAR)\b', raw_text, re.IGNORECASE):
        symbols.append("DXY")
    if re.search(r'\b(CL|CRUDE OIL)\b', raw_text, re.IGNORECASE):
        symbols.append("CL")
    if re.search(r'\b(GC|GOLD|XAUUSD)\b', raw_text, re.IGNORECASE):
        symbols.append("GC")
    if re.search(r'\b(SI|SILVER|XAGUSD)\b', raw_text, re.IGNORECASE):
        symbols.append("SI")
    if re.search(r'\b(USD/CAD|USDCAD)\b', raw_text, re.IGNORECASE):
        symbols.append("USDCAD")
    if re.search(r'\b(AUD/USD|AUDUSD)\b', raw_text, re.IGNORECASE):
        symbols.append("AUDUSD")
    if re.search(r'\b(NZD/USD|NZDUSD)\b', raw_text, re.IGNORECASE):
        symbols.append("NZDUSD")
    if re.search(r'\b(USD/JPY|USDJPY)\b', raw_text, re.IGNORECASE):
        symbols.append("USDJPY")
    if re.search(r'\b(USD/CHF|USDCHF|SWISSY)\b', raw_text, re.IGNORECASE):
        symbols.append("USDCHF")
    if re.search(r'\b(ZB|BONDS|TREASURY BONDS|30-YEAR BOND|T-BONDS)\b', raw_text, re.IGNORECASE):
        symbols.append("ZB")
    if re.search(r'\b(6M|MEXICAN PESO|PESO FUTURES)\b', raw_text, re.IGNORECASE):
        symbols.append("6M")
    return symbols

NON_TIMEFRAMES = {"web browser", "slides", "economic calendar", "barchart.com", "n/a", "none"}

def normalize_timeframe(tf: str) -> str:
    tf_clean = tf.strip().lower()
    if tf_clean in NON_TIMEFRAMES or not tf_clean:
        return ""
    if tf_clean in ["1m", "1-minute", "1-minute (1m)", "1 minute"]:
        return "1m"
    if tf_clean in ["2m", "2-minute", "2-minute (2m)", "2 minute"]:
        return "2m"
    if tf_clean in ["3m", "3-minute", "3-minute (3m)", "3 minute"]:
        return "3m"
    if tf_clean in ["4m", "4-minute", "4-minute (4m)", "4 minute"]:
        return "4m"
    if tf_clean in ["5m", "5-minute", "5-minute (5m)", "5 minute"]:
        return "5m"
    if tf_clean in ["15m", "15-minute", "15-minute (15m)", "15 minute"]:
        return "15m"
    if tf_clean in ["1h", "1-hour", "hourly", "1 hour"]:
        return "1h"
    if tf_clean in ["4h", "4-hour", "4 hour"]:
        return "4h"
    if tf_clean in ["daily", "daily (1d)", "1d", "day"]:
        return "Daily"
    if tf_clean in ["weekly", "1w", "week"]:
        return "Weekly"
    return tf.strip()

def normalize_session(sess: str) -> str:
    s = sess.strip()
    s_low = s.lower()
    if "london" in s_low:
        return "London"
    if "asia" in s_low:
        return "Asia"
    if "pm" in s_low or "afternoon" in s_low:
        return "NY PM"
    if "am" in s_low or "morning" in s_low or "killzone" in s_low or "news" in s_low or "08:30" in s_low:
        return "NY AM"
    if "pre-market" in s_low or "overnight" in s_low:
        return "Pre-market / Overnight"
    return s

def parse_section_table(markdown_text: str, section_title: str):
    pattern = rf"## {re.escape(section_title)}\s*\n(.*?)(?=\n## |\Z)"
    match = re.search(pattern, markdown_text, re.DOTALL)
    if not match:
        return []
    rows = []
    lines = match.group(1).strip().splitlines()
    for line in lines:
        line = line.strip()
        if not line.startswith("|"):
            continue
        cols = [c.strip() for c in line.split("|")[1:-1]]
        if not cols or "Timestamp" in cols[0] or "---" in cols[0]:
            continue
        rows.append(cols)
    return rows

def build_summary():
    files = sorted(RESEARCH_DIR.glob("*.md"))
    symbols_data = {}

    for f in files:
        content = f.read_text(encoding="utf-8")
        date_m = re.search(r"date:\s*(\d+)", content)
        date_str = date_m.group(1) if date_m else "NA"
        vid_m = re.search(r"id:\s*([a-zA-Z0-9_-]+)", content)
        vid_id = vid_m.group(1) if vid_m else f.stem

        def ensure_symbol(sym):
            if sym not in symbols_data:
                symbols_data[sym] = {
                    "videos": set(),
                    "trades": 0,
                    "models": set(),
                    "timeframes": set(),
                    "sessions": set(),
                    "first_seen": date_str,
                    "last_seen": date_str
                }
            if date_str != "NA":
                if symbols_data[sym]["first_seen"] == "NA" or date_str < symbols_data[sym]["first_seen"]:
                    symbols_data[sym]["first_seen"] = date_str
                if symbols_data[sym]["last_seen"] == "NA" or date_str > symbols_data[sym]["last_seen"]:
                    symbols_data[sym]["last_seen"] = date_str

        # 1. Charts shown
        chart_rows = parse_section_table(content, "Charts shown")
        for cols in chart_rows:
            if len(cols) >= 5:
                raw_sym, tf_str, session_str = cols[1], cols[2], cols[4]
                syms = extract_symbols(raw_sym)
                for s in syms:
                    ensure_symbol(s)
                    symbols_data[s]["videos"].add(vid_id)
                    for tf in tf_str.split("/"):
                        tf_norm = normalize_timeframe(tf)
                        if tf_norm:
                            symbols_data[s]["timeframes"].add(tf_norm)
                    for sess in session_str.split("/"):
                        sess_norm = normalize_session(sess)
                        if sess_norm:
                            symbols_data[s]["sessions"].add(sess_norm)

        # 2. Trades taken or shown
        trade_rows = parse_section_table(content, "Trades taken or shown")
        for cols in trade_rows:
            if len(cols) >= 9:
                raw_sym, model_str, entry_tf = cols[1], cols[3], cols[4]
                syms = extract_symbols(raw_sym)
                for s in syms:
                    ensure_symbol(s)
                    symbols_data[s]["videos"].add(vid_id)
                    symbols_data[s]["trades"] += 1
                    if model_str:
                        symbols_data[s]["models"].add(model_str)
                    if entry_tf:
                        for tf in entry_tf.split("/"):
                            tf_norm = normalize_timeframe(tf)
                            if tf_norm:
                                symbols_data[s]["timeframes"].add(tf_norm)

    rows = []
    for sym, data in sorted(symbols_data.items()):
        models_str = "; ".join(sorted(data["models"])) if data["models"] else "Analysis / SMT only"
        # Sort timeframes logically: Daily, Weekly, 15m, 5m, 4m, 3m, 2m, 1m
        tf_order = {"Weekly": 1, "Daily": 2, "4h": 3, "1h": 4, "15m": 5, "5m": 6, "4m": 7, "3m": 8, "2m": 9, "1m": 10}
        sorted_tfs = sorted(data["timeframes"], key=lambda x: tf_order.get(x, 99))
        tfs_str = ", ".join(sorted_tfs) if sorted_tfs else "N/A"
        sessions_str = ", ".join(sorted(data["sessions"])) if data["sessions"] else "N/A"
        rows.append([
            sym,
            len(data["videos"]),
            data["trades"],
            models_str,
            tfs_str,
            sessions_str,
            data["first_seen"],
            data["last_seen"]
        ])

    with open(SUMMARY_CSV, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["symbol", "videos_shown", "trades_shown", "models_named", "timeframes", "sessions", "first_seen", "last_seen"])
        writer.writerows(rows)

    print(f"Successfully generated clean {SUMMARY_CSV} with {len(rows)} symbols:")
    for r in rows:
        print(f"  {r[0]}: {r[1]} vids, {r[2]} trades, tfs=[{r[4]}], sessions=[{r[5]}]")

if __name__ == "__main__":
    build_summary()
