import subprocess
import os
import sys
from pathlib import Path
import imageio_ffmpeg
import yt_dlp

ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
print(f"Using ffmpeg: {ffmpeg_exe}")

TARGET_DIR = Path(r"C:\Users\giant\Documents\ict-trader\docs\references\video_frames")
TARGET_DIR.mkdir(parents=True, exist_ok=True)

ARTIFACT_DIR = Path(r"C:\Users\giant\.gemini\antigravity\brain\b07f65d1-8dcb-4241-bae9-45fc96e41752")

FRAMES_TO_EXTRACT = [
    {
        "filename": "ep01_23m13s_live_funded_execution.png",
        "url": "https://www.youtube.com/watch?v=kt6V4ai60fI",
        "timestamp": "00:23:13",
        "title": "Ep 01 [23:13] Live Funded Account & 2m ES Execution"
    },
    {
        "filename": "ep02_18m10s_fair_value_gap_anatomy.png",
        "url": "https://www.youtube.com/watch?v=tmeCWULSTHc",
        "timestamp": "00:18:10",
        "title": "Ep 02 [18:10] Fair Value Gap (FVG) Anatomy & Imbalance Box"
    },
    {
        "filename": "ep03_08m20s_swing_structure_ranges.png",
        "url": "https://www.youtube.com/watch?v=nQfHZ2DEJ8c",
        "timestamp": "00:08:20",
        "title": "Ep 03 [08:20] 3-Candle Swing Definition & Dealing Ranges"
    },
    {
        "filename": "ep04_05m30s_liquidity_pools_runs.png",
        "url": "https://www.youtube.com/watch?v=L-ReMHiavPM",
        "timestamp": "00:05:30",
        "title": "Ep 04 [05:30] High-Probability Liquidity Pools & Draws"
    },
    {
        "filename": "ep05_21m00s_market_structure_shift_fvg.png",
        "url": "https://www.youtube.com/watch?v=N29ZJ-o31xs",
        "timestamp": "00:21:00",
        "title": "Ep 05 [21:00] Market Structure Shift (MSS) with Displacement"
    },
    {
        "filename": "ep08_08m15s_morning_session_killzones.png",
        "url": "https://www.youtube.com/watch?v=7rbV8aWkcqY",
        "timestamp": "00:08:15",
        "title": "Ep 08 [08:15] 09:30 Judas Swing & AM Session Killzones"
    },
    {
        "filename": "ep12_10m30s_daily_bias_pdh_pdl.png",
        "url": "https://www.youtube.com/watch?v=8GkQfdAXZP0",
        "timestamp": "00:10:30",
        "title": "Ep 12 [10:30] Daily Bias & Prior Day High/Low (PDH/PDL)"
    },
    {
        "filename": "ep22_09m15s_day_trading_model_execution.png",
        "url": "https://www.youtube.com/watch?v=QKc_i90chVg",
        "timestamp": "00:09:15",
        "title": "Ep 22 [09:15] Day Trading Model & 5m FVG Entry Trigger"
    },
    {
        "filename": "ep25_27m10s_midnight_open_purging.png",
        "url": "https://www.youtube.com/watch?v=CnTXwAuDi9Y",
        "timestamp": "00:27:10",
        "title": "Ep 25 [27:10] NY Midnight Open Anchor & Liquidity Purging"
    },
    {
        "filename": "ep35_07m15s_smt_divergence_es_nq.png",
        "url": "https://www.youtube.com/watch?v=MdYrslpUezU",
        "timestamp": "00:07:15",
        "title": "Ep 35 [07:15] SMT Divergence (ES vs NQ Line Comparison)"
    },
    {
        "filename": "ep41_04m30s_master_model_review.png",
        "url": "https://www.youtube.com/watch?v=2XhDi5GoNUI",
        "timestamp": "00:04:30",
        "title": "Ep 41 [04:30] Mentorship Model Concluding Review & Risk"
    }
]

ydl_opts = {
    'format': 'bestvideo[height<=720]/best[height<=720]',
    'quiet': True,
    'no_warnings': True,
}

print(f"Starting extraction of {len(FRAMES_TO_EXTRACT)} key video frames...")

for idx, item in enumerate(FRAMES_TO_EXTRACT, start=1):
    fn = item["filename"]
    out_file = TARGET_DIR / fn
    if out_file.exists() and out_file.stat().st_size > 10000:
        print(f"[{idx}/{len(FRAMES_TO_EXTRACT)}] Already exists: {fn}")
        # Copy to artifact dir as well
        art_file = ARTIFACT_DIR / fn
        if not art_file.exists():
            art_file.write_bytes(out_file.read_bytes())
        continue

    print(f"\n[{idx}/{len(FRAMES_TO_EXTRACT)}] Fetching stream for {item['title']}...")
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(item["url"], download=False)
            stream_url = info['url']
        
        print(f"  Extracting frame at {item['timestamp']} via ffmpeg...")
        cmd = [
            ffmpeg_exe,
            "-ss", item["timestamp"],
            "-i", stream_url,
            "-vframes", "1",
            "-q:v", "2",
            "-y",
            str(out_file)
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if out_file.exists() and out_file.stat().st_size > 0:
            size_kb = out_file.stat().st_size // 1024
            print(f"  -> Extracted: {fn} ({size_kb} KB)")
            # Copy to artifact dir
            (ARTIFACT_DIR / fn).write_bytes(out_file.read_bytes())
        else:
            print(f"  -> Error capturing frame: {res.stderr[:200]}")
    except Exception as e:
        print(f"  -> Exception extracting {fn}: {e}")

print("\nFinished video frame extraction!")
