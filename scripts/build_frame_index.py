"""Publish the ICT reference images to the website and index them by rule ID.

docs/ is not deployed (see .vercelignore), so this copies the 60 mentorship video
frames and the 5 rule diagrams into refs/ as web-sized JPEGs, and writes
refs/frames.json: one entry per image with its episode, timestamp, the chart it
really shows, a caption and the RULES.md IDs it visibly illustrates, all taken from
the frame-by-frame checks in docs/references/verified/. scripts/build_web.py embeds that index in the
site, so the Playbook, the signal lessons and the trade review can show the image
that reflects each rule.

Run after adding frames:  python scripts/build_frame_index.py && python scripts/build_web.py
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "docs" / "references"
OUT = ROOT / "refs"

# What each image actually shows, checked frame by frame (docs/references/verified/).
# The archive README's instrument/timeframe/concept columns are wrong for most frames,
# so captions and rule tags come only from these checks.
VERIFIED = ROOT / "docs" / "references" / "verified"
CHART_IDS = {
    "01_ict_fvg_consequent_encroachment": "CHART-01", "02_ict_liquidity_sweep_judas_swing": "CHART-02",
    "03_ict_order_of_purging_rule_sw02": "CHART-03", "04_ict_silver_bullet_execution_window": "CHART-04",
    "05_ict_inversion_fvg_support_flip": "CHART-05",
}


def load_verified():
    out = {}
    for f in sorted(VERIFIED.glob("batch*.json")):
        out.update(json.loads(f.read_text(encoding="utf-8")))
    return out


def _key(stem):
    m = re.match(r"(ep\d+_(?:ex\d+_)?\d+m\d+s)", stem)
    k = m.group(1) if m else stem
    return re.sub(r"_\d+m\d+s$", "", k) if "_ex" in k else k


def parse_readme():
    rows = {}
    for line in (SRC / "README.md").read_text(encoding="utf-8").splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) == 5 and cells[2].startswith("[`ep"):
            fname = re.search(r"`([^`]+\.png)`", cells[2]).group(1)
            rows[Path(fname).stem] = {"ep": int(re.sub(r"\D", "", cells[0])), "ts": cells[1].strip("`"),
                                      "asset": cells[3], "caption": re.sub(r"[`*]", "", cells[4].replace("$\\to$", "→"))}
        if len(cells) == 5 and cells[0].startswith("**CHART-"):
            fname = re.search(r"`([^`]+\.png)`", cells[1]).group(1)
            rows[Path(fname).stem] = {"caption": re.sub(r"[*`]", "", cells[4])}
    return rows


def convert(src: Path, dst: Path):
    from PIL import Image  # pip install pillow

    im = Image.open(src).convert("RGB")
    if im.width > 1280:
        im = im.resize((1280, round(im.height * 1280 / im.width)))
    im.save(dst, "JPEG", quality=82, optimize=True, progressive=True)


def _entry(k, src, kind, row, v):
    return {"id": k, "src": src, "kind": kind, "ep": row.get("ep"), "ts": row.get("ts"),
            "asset": v["asset"], "date": v.get("date"), "caption": v["caption"], "note": v.get("mismatch"),
            # usable: a real chart that visibly shows at least one rule; only these are offered
            # as rule examples beside trades and in the Playbook.
            "usable": bool(v["chart"] and v["rules"]), "rules": v["rules"]}


def main():
    rows, seen = parse_readme(), load_verified()
    (OUT / "frames").mkdir(parents=True, exist_ok=True)
    (OUT / "charts").mkdir(parents=True, exist_ok=True)
    index = []
    for p in sorted((SRC / "video_frames").glob("*.png")):
        dst = OUT / "frames" / (p.stem + ".jpg")
        if not dst.exists() or dst.stat().st_mtime < p.stat().st_mtime:
            convert(p, dst)
        k = _key(p.stem)
        if k not in seen:
            raise SystemExit(f"{k} has not been checked: add it to docs/references/verified/")
        index.append(_entry(k, f"refs/frames/{dst.name}", "video", rows.get(p.stem, {}), seen[k]))
    for p in sorted((SRC / "ict_charts").glob("*.png")):
        dst = OUT / "charts" / (p.stem + ".jpg")
        if not dst.exists() or dst.stat().st_mtime < p.stat().st_mtime:
            convert(p, dst)
        k = CHART_IDS[p.stem]
        index.append(_entry(k, f"refs/charts/{dst.name}", "diagram", {}, seen[k]))
    (OUT / "frames.json").write_text(json.dumps(index, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"indexed {len(index)} images, {sum(f['usable'] for f in index)} usable as rule examples")


if __name__ == "__main__":
    main()
