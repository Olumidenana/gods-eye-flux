"""Build the static web app (index.html and web/index.html) from web/template.html.

The rule library on the site is generated from RULES.md, so the two never drift.
Run after editing RULES.md or the template:  python scripts/build_web.py
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _clean(s):
    return re.sub(r"[`*]", "", s).strip()


def parse_rules(text):
    rules, cat = [], None
    for line in text.splitlines():
        m = re.match(r"^### 1\.\d+ (.+?)(\s*\(`.*)?$", line)
        if m:
            cat = re.sub(r"\s*\(\d{4}.*\)$", "", m.group(1)).strip()
            continue
        if line.startswith("## 2."):
            break
        if line.startswith("| **") and cat:
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if len(cells) == 5:  # SA-/UM- tables have no Source column
                cells.insert(2, "System design (engine extension)")
            mm = re.match(r"\*\*(.+?):\*\*\s*(.*)", cells[1])
            title, desc = (mm.group(1), mm.group(2)) if mm else (cells[0], cells[1])
            rules.append({
                "id": cells[0].strip("* "), "cat": cat, "title": _clean(title),
                "desc": _clean(desc), "src": _clean(cells[2]), "cfg": _clean(cells[3]),
                "dflt": _clean(cells[4]), "status": _clean(cells[5]),
            })
    return rules


def parse_decisions(text):
    part = text.split("## 3.", 1)[1] if "## 3." in text else ""
    out = []
    for block in re.split(r"^### ", part, flags=re.M)[1:]:
        head, *body = block.strip().splitlines()
        opts = []
        for l in body:
            m = re.match(r"- \*\*(.+?):\*\*\s*(.*)", l)
            if m:
                opts.append({"label": _clean(m.group(1)), "text": _clean(m.group(2))})
        out.append({"title": _clean(re.sub(r"^Decision \d+:\s*", "", head)), "options": opts})
    return out


def main():
    text = (ROOT / "RULES.md").read_text(encoding="utf-8")
    rules, decisions = parse_rules(text), parse_decisions(text)
    html = (ROOT / "web" / "template.html").read_text(encoding="utf-8")
    html = html.replace("__RULES__", json.dumps(rules, ensure_ascii=False, separators=(",", ":")))
    html = html.replace("__DECISIONS__", json.dumps(decisions, ensure_ascii=False, separators=(",", ":")))
    # Reference images indexed by rule (scripts/build_frame_index.py writes refs/frames.json).
    frames = json.loads((ROOT / "refs" / "frames.json").read_text(encoding="utf-8"))
    html = html.replace("__FRAMES__", json.dumps(frames, ensure_ascii=False, separators=(",", ":")))
    # A version id from the page's own content, so the app can tell when a newer one is live.
    import hashlib
    version = hashlib.sha256(html.encode("utf-8")).hexdigest()[:8]
    html = html.replace("__BUILD__", version)
    for out in (ROOT / "index.html", ROOT / "web" / "index.html"):
        out.write_text(html, encoding="utf-8")
    for out in (ROOT / "version.json", ROOT / "web" / "version.json"):
        out.write_text(json.dumps({"version": version}) + "\n", encoding="utf-8")
    # Stamp the build version into sw.js and web/sw.js so mobile/PWA caches bust automatically.
    sw_path = ROOT / "sw.js"
    if sw_path.exists():
        sw_src = sw_path.read_text(encoding="utf-8")
        sw_updated = re.sub(
            r"const CACHE = 'ictflux-[^']+';",
            f"const CACHE = 'ictflux-{version}';",
            sw_src,
        )
        sw_path.write_text(sw_updated, encoding="utf-8")
        (ROOT / "web" / "sw.js").write_text(sw_updated, encoding="utf-8")
    print(f"built site: {len(rules)} rules, {len(decisions)} decisions, {len(frames)} reference images")


if __name__ == "__main__":
    main()
