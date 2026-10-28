import re
import os
import sys
import subprocess
import json
import time
from pathlib import Path
import imageio_ffmpeg
import yt_dlp

TARGET_DIR = Path(r"C:\Users\giant\Documents\ict-trader\docs\references\video_frames")
TARGET_DIR.mkdir(parents=True, exist_ok=True)

ARTIFACT_DIR = Path(r"C:\Users\giant\.gemini\antigravity\brain\b07f65d1-8dcb-4241-bae9-45fc96e41752")
RULES_DIR = Path(r"C:\Users\giant\Documents\ict-trader\rules")

ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
print(f"Using FFmpeg: {ffmpeg_exe}")

def parse_time_str(s):
    if not s:
        return None
    # Matches hh:mm:ss or mm:ss or m:ss, handles brackets, approx ~
    m = re.search(r'(\d{1,2}):(\d{2})(?::(\d{2}))?', s)
    if m:
        if m.group(3):
            h, mm, ss = int(m.group(1)), int(m.group(2)), int(m.group(3))
        else:
            h, mm, ss = 0, int(m.group(1)), int(m.group(2))
        return f"{h:02d}:{mm:02d}:{ss:02d}", f"{h*60 + mm}m{ss:02d}s"
    return None

def is_frame_already_present(ep_num, ts_slug, filename):
    # Check exact filename
    target = TARGET_DIR / filename
    if target.exists() and target.stat().st_size >= 10000:
        return target
    # Check existing frames with same episode and timestamp
    for f in TARGET_DIR.glob(f"ep{ep_num:02d}_*"):
        if ts_slug in f.name and f.stat().st_size >= 10000:
            return f
    return None

def collect_chart_tasks():
    ep_files = sorted(RULES_DIR.glob("episode-*.md"))
    tasks = []
    
    for f in ep_files:
        txt = f.read_text(encoding="utf-8")
        url_m = re.search(r"https://www\.youtube\.com/watch\?v=([a-zA-Z0-9_-]+)", txt)
        if not url_m:
            continue
        url = url_m.group(0)
        ep_m = re.search(r"episode-(\d+)", f.name)
        if not ep_m:
            continue
        ep_num = int(ep_m.group(1))

        lines = txt.splitlines()
        in_chart_section = False
        ex_idx = 0
        cur_ts = None
        cur_inst = "chart"
        cur_desc = ""

        def push_task():
            nonlocal cur_ts, cur_inst, cur_desc, ex_idx
            if cur_ts:
                parsed = parse_time_str(cur_ts)
                if parsed:
                    ts_fmt, ts_slug = parsed
                    clean_inst = re.sub(r'[^a-zA-Z0-9]+', '_', cur_inst.lower()).strip('_')[:15] or "chart"
                    clean_desc = re.sub(r'[^a-zA-Z0-9]+', '_', cur_desc.lower()).strip('_')[:20] if cur_desc else clean_inst
                    fn = f"ep{ep_num:02d}_ex{ex_idx:02d}_{ts_slug}_{clean_desc}.png"
                    tasks.append({
                        "ep": ep_num,
                        "ex_idx": ex_idx,
                        "url": url,
                        "ts_raw": cur_ts,
                        "ts_fmt": ts_fmt,
                        "ts_slug": ts_slug,
                        "inst": cur_inst,
                        "desc": cur_desc,
                        "filename": fn
                    })
                cur_ts = None
                cur_inst = "chart"
                cur_desc = ""

        for line in lines:
            if "## Chart Examples" in line:
                in_chart_section = True
                continue
            if in_chart_section and line.startswith("## ") and "Chart Examples" not in line:
                in_chart_section = False
                push_task()
                break

            if in_chart_section:
                if line.strip().startswith("### Chart Example") or line.strip().startswith("### Example") or (line.strip().startswith("*   **Timestamp:**") and cur_ts is not None):
                    push_task()
                    ex_idx += 1
                    if "### " in line:
                        cur_desc = line.replace("###", "").replace("Chart Example", "").strip(" :1234567890-()")

                if "**Timestamp:**" in line or "Timestamp:" in line:
                    parts = line.split("Timestamp:", 1)[-1]
                    t_val = parse_time_str(parts)
                    if t_val and not cur_ts:
                        cur_ts = parts.strip()
                elif "Instrument:" in line:
                    cur_inst = line.split("Instrument:", 1)[-1].strip()
                elif "Timeframe:" in line and not cur_desc:
                    cur_desc = line.split("Timeframe:", 1)[-1].strip()

        push_task()

    return tasks

def fetch_stream_url_with_retry(ydl_opts, url, retries=3):
    for attempt in range(1, retries + 1):
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                stream_url = info.get("url")
                if stream_url:
                    return stream_url
        except Exception as e:
            print(f"    [Attempt {attempt}/{retries}] Notice: {e}")
            time.sleep(2 * attempt)
    return None

def main():
    tasks = collect_chart_tasks()
    print(f"Total chart example tasks discovered across episodes: {len(tasks)}")

    by_url = {}
    for t in tasks:
        by_url.setdefault(t["url"], []).append(t)

    ydl_opts = {
        'format': 'bestvideo[height<=720]/best[height<=720]',
        'quiet': True,
        'no_warnings': True,
    }

    successful = 0
    skipped = 0
    failed = 0

    print(f"Processing {len(by_url)} unique YouTube videos...")
    video_idx = 0

    for url, ep_tasks in sorted(by_url.items(), key=lambda x: x[1][0]["ep"]):
        video_idx += 1
        ep_num = ep_tasks[0]["ep"]
        print(f"\n[{video_idx}/{len(by_url)}] Episode {ep_num:02d}: {len(ep_tasks)} frame(s) to process")

        # Check if all tasks for this video already exist
        needed = []
        for t in ep_tasks:
            existing = is_frame_already_present(ep_num, t["ts_slug"], t["filename"])
            if existing:
                art_file = ARTIFACT_DIR / existing.name
                if not art_file.exists():
                    art_file.write_bytes(existing.read_bytes())
                skipped += 1
            else:
                needed.append(t)

        if not needed:
            print(f"  All {len(ep_tasks)} frames for Ep {ep_num:02d} already exist.")
            continue

        print(f"  Fetching stream URL for Episode {ep_num:02d}...")
        time.sleep(1.5)  # Respect rate limit
        stream_url = fetch_stream_url_with_retry(ydl_opts, url)

        if not stream_url:
            print(f"  Could not get stream URL for Ep {ep_num:02d}")
            failed += len(needed)
            continue

        for t in needed:
            out_file = TARGET_DIR / t["filename"]
            art_file = ARTIFACT_DIR / t["filename"]

            print(f"  -> Capturing Ex {t['ex_idx']} at {t['ts_fmt']} -> {t['filename']}...")
            cmd = [
                ffmpeg_exe,
                "-ss", t["ts_fmt"],
                "-i", stream_url,
                "-vframes", "1",
                "-q:v", "2",
                "-y",
                str(out_file)
            ]
            try:
                res = subprocess.run(cmd, capture_output=True, timeout=25)
                if out_file.exists() and out_file.stat().st_size >= 5000:
                    art_file.write_bytes(out_file.read_bytes())
                    print(f"     OK: {out_file.stat().st_size // 1024} KB")
                    successful += 1
                else:
                    print(f"     Failed (size={out_file.stat().st_size if out_file.exists() else 0})")
                    failed += 1
            except subprocess.TimeoutExpired:
                print(f"     Timeout extracting {t['ts_fmt']}")
                failed += 1
            except Exception as e:
                print(f"     Error: {e}")
                failed += 1

        time.sleep(1.0)

    print("\n" + "="*50)
    print(f"Batch Extraction Summary:")
    print(f"  Total Tasks: {len(tasks)}")
    print(f"  Successful:  {successful}")
    print(f"  Skipped:     {skipped}")
    print(f"  Failed:      {failed}")
    print("="*50)

if __name__ == "__main__":
    main()
