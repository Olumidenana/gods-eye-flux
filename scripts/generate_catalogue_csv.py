import os
import sys
import json
import re
import csv
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "research" / "ict-videos"
PLAYLISTS_CACHE = OUTPUT_DIR / ".playlists_cache.json"
VIDEOS_CACHE = OUTPUT_DIR / ".videos_cache.json"
STREAMS_CACHE = OUTPUT_DIR / ".streams_cache.json"
EP_LOG = Path(r"C:\Users\giant\.gemini\antigravity\brain\b07f65d1-8dcb-4241-bae9-45fc96e41752\.system_generated\tasks\task-2029.log")
CATALOGUE_CSV = OUTPUT_DIR / "catalogue.csv"

# 1. Parse Mentorship Dates from task-2029.log
mentorship_dates = {}
if EP_LOG.exists():
    text = EP_LOG.read_text(encoding="utf-8", errors="replace")
    for line in text.splitlines():
        line = line.strip()
        if "|" in line and not line.startswith("WARNING"):
            parts = line.split("|")
            if len(parts) == 2 and len(parts[0]) == 11 and len(parts[1]) == 8:
                mentorship_dates[parts[0]] = parts[1]

print(f"Loaded {len(mentorship_dates)} mentorship dates from log.")

# 2. Load caches
with open(PLAYLISTS_CACHE, "r", encoding="utf-8") as f:
    playlists_raw = json.load(f)
with open(VIDEOS_CACHE, "r", encoding="utf-8") as f:
    videos_raw = json.load(f)
with open(STREAMS_CACHE, "r", encoding="utf-8") as f:
    streams_raw = json.load(f)

# Map video_id to list of playlists
video_to_playlists = {}
playlist_order = {}
for p_idx, p in enumerate(playlists_raw):
    pl_title = p.get("title", "")
    for item in p.get("items", []):
        vid_id = item["id"]
        if vid_id not in video_to_playlists:
            video_to_playlists[vid_id] = []
        video_to_playlists[vid_id].append(pl_title)

# Merge all items preserving chronological upload order index
# videos_raw is in reverse chronological order (newest = index 0)
# streams_raw is in reverse chronological order (newest = index 0)
all_items = {}

for idx, v in enumerate(videos_raw):
    vid_id = v["id"]
    all_items[vid_id] = {
        "id": vid_id,
        "title": (v.get("title") or "").strip(),
        "duration": v.get("duration") or 0,
        "url": f"https://www.youtube.com/watch?v={vid_id}",
        "source": "video",
        "video_index": idx,
        "stream_index": 999999
    }

for idx, s in enumerate(streams_raw):
    vid_id = s["id"]
    if vid_id in all_items:
        all_items[vid_id]["stream_index"] = idx
    else:
        all_items[vid_id] = {
            "id": vid_id,
            "title": (s.get("title") or "").strip(),
            "duration": s.get("duration") or 0,
            "url": f"https://www.youtube.com/watch?v={vid_id}",
            "source": "stream",
            "video_index": 999999,
            "stream_index": idx
        }

for p in playlists_raw:
    pl_title = p.get("title", "")
    for item in p.get("items", []):
        vid_id = item["id"]
        if vid_id not in all_items:
            all_items[vid_id] = {
                "id": vid_id,
                "title": (item.get("title") or "").strip(),
                "duration": item.get("duration") or 0,
                "url": f"https://www.youtube.com/watch?v={vid_id}",
                "source": "playlist_only",
                "video_index": 999999,
                "stream_index": 999999
            }

print(f"Total merged items: {len(all_items)}")

# 3. Filter shorts under 3 minutes
# "Skip Shorts under 3 minutes unless the title names a market or model."
MARKET_OR_MODEL_KEYWORDS = [
    r'\bes\b', r'\bnq\b', r'\bym\b', r'\brty\b', r'\bcl\b', r'\bgc\b', r'\bsi\b',
    r'\beurusd\b', r'\bgbpusd\b', r'\busdjpy\b', r'\busdcad\b', r'\baudusd\b',
    r'\bdxy\b', r'\bdollar\b', r'\bgold\b', r'\bsilver\b', r'\boil\b', r'\bcrude\b',
    r'\bbtc\b', r'\bbitcoin\b', r'\bforex\b', r'\bfutures\b', r'\be-mini\b', r'\bemini\b',
    r'\bs&p\b', r'\bnasdaq\b', r'\bdow\b', r'\bbonds\b',
    r'silver\s*bullet', r'judas', r'\bote\b', r'optimal\s*trade\s*entry',
    r'unicorn', r'turtle\s*soup', r'fair\s*value\s*gap', r'\bfvg\b',
    r'order\s*block', r'\bob\b', r'breaker', r'\bsmt\b', r'liquidity',
    r'bias', r'setup', r'model', r'market\s*maker', r'mentorship', r'scalping',
    r'execution', r'tape\s*reading', r'kill\s*zone', r'killzone', r'asian\s*session',
    r'london', r'new\s*york', r'macro', r'inversion', r'ipda'
]
KW_REGEX = re.compile('|'.join(MARKET_OR_MODEL_KEYWORDS), re.IGNORECASE)

filtered_items = {}
skipped_count = 0
for vid_id, item in all_items.items():
    dur = item["duration"]
    # If duration is known and > 0 and < 180 seconds
    if 0 < dur < 180:
        if not KW_REGEX.search(item["title"]):
            skipped_count += 1
            continue
    filtered_items[vid_id] = item

print(f"Filtered {skipped_count} shorts without market/model. Remaining: {len(filtered_items)}")

# 4. Helper to extract date from title or assign known date
MONTHS = {
    "january": "01", "february": "02", "march": "03", "april": "04",
    "may": "05", "june": "06", "july": "07", "august": "08",
    "september": "09", "october": "10", "november": "11", "december": "12"
}

def parse_date_from_title(title: str):
    # Pattern: MM/DD/YYYY or MM/DD/YY
    m = re.search(r'\b(0?[1-9]|1[0-2])[/-](0?[1-9]|[12]\d|3[01])[/-](20\d{2}|\d{2})\b', title)
    if m:
        mo, da, yr = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if yr < 100:
            yr += 2000
        return f"{yr:04d}{mo:02d}{da:02d}"
    
    # Pattern: Month DD, YYYY
    m = re.search(r'\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2}),?\s+(20\d{2})\b', title, re.IGNORECASE)
    if m:
        mo = MONTHS[m.group(1).lower()]
        da = int(m.group(2))
        yr = int(m.group(3))
        return f"{yr:04d}{mo}{da:02d}"

    # Pattern: Month YYYY
    m = re.search(r'\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+(20\d{2})\b', title, re.IGNORECASE)
    if m:
        mo = MONTHS[m.group(1).lower()]
        yr = int(m.group(2))
        return f"{yr:04d}{mo}01"

    # Pattern: Year YYYY
    m = re.search(r'\b(201[6-9]|202[0-6])\b', title)
    if m:
        return f"{m.group(1)}0101"

    return None

# 5. Classify into Tiers:
# Tier 1: 2022 ICT Mentorship episodes
# Tier 2: Silver Bullet / model-specific videos
# Tier 3: Newest videos (2023 to today, newest first)
# Tier 4: Everything older

# Find 2022 Mentorship playlist items
mentorship_2022_items = []
for p in playlists_raw:
    if p.get("title") == "2022 ICT Mentorship":
        mentorship_2022_items = [it["id"] for it in p.get("items", [])]
        break

print(f"2022 Mentorship playlist items count: {len(mentorship_2022_items)}")

tier1 = []
tier2 = []
tier3 = []
tier4 = []

# Model specific regex for Tier 2
MODEL_SPECIFIC_REGEX = re.compile(
    r'(silver\s*bullet|optimal\s*trade\s*entry|\bote\b|judas(\s*swing)?|unicorn|breaker(\s*block)?|turtle\s*soup|market\s*maker\s*(primer|series|model|reversal)|mastering\s*high\s*probability\s*scalping)',
    re.IGNORECASE
)

MODEL_SPECIFIC_PLAYLISTS = {
    "ICT Pattern Recognition - Optimal Trade Entry",
    "ICT OTE Pattern Recognition Series",
    "ICT Market Maker Forex Series",
    "ICT - Mastering High Probability Scalping Volumes 1 - 3",
    "ICT Forex - Market Maker Primer Course"
}

RECENT_PLAYLISTS = {
    "2026 ICT Smart Money Concept Lecture",
    "2025 Shotgun Saturday",
    "2025 Lecture Series",
    "ICT 2024 Mentorship",
    "2023 ICT Mentorship",
    "2023 Forex Reviews"
}

# Process each filtered item
for vid_id in mentorship_2022_items:
    if vid_id in filtered_items:
        item = filtered_items[vid_id]
        # Assign date from mentorship_dates if known
        item["upload_date"] = mentorship_dates.get(vid_id) or "20220101"
        item["playlist"] = "2022 ICT Mentorship"
        tier1.append(item)

# Build remaining items
remaining_ids = set(filtered_items.keys()) - set(mentorship_2022_items)

for vid_id in remaining_ids:
    item = filtered_items[vid_id]
    title = item["title"]
    pls = video_to_playlists.get(vid_id, [])
    pl_str = "; ".join(pls) if pls else ("Live Streams" if item["source"] == "stream" else "Uploads")
    item["playlist"] = pl_str
    
    # Try date
    parsed_date = parse_date_from_title(title)
    if not parsed_date:
        # Check playlist names for year
        for pl in pls:
            m_yr = re.search(r'\b(201[6-9]|202[0-6])\b', pl)
            if m_yr:
                parsed_date = f"{m_yr.group(1)}0101"
                break
    
    # If still None, check video upload index:
    # 0 is Oct 2026, ~200 is 2024, ~400 is 2023, ~600 is 2022, etc.
    item["upload_date"] = parsed_date or "NA"
    
    # Check if Tier 2 (Model specific)
    is_tier2 = False
    if MODEL_SPECIFIC_REGEX.search(title):
        is_tier2 = True
    elif any(p in MODEL_SPECIFIC_PLAYLISTS for p in pls):
        is_tier2 = True
    
    if is_tier2:
        tier2.append(item)
        continue
    
    # Check if Tier 3 (Newest: 2023 to today)
    is_tier3 = False
    # Check if in recent playlists
    if any(p in RECENT_PLAYLISTS for p in pls):
        is_tier3 = True
    elif parsed_date and parsed_date >= "20230101":
        is_tier3 = True
    elif item["video_index"] < 450: # Videos from 2023 to 2026 on this channel are indices 0 to ~450
        is_tier3 = True
    elif item["stream_index"] < 120: # Recent streams
        is_tier3 = True
        
    if is_tier3:
        tier3.append(item)
    else:
        tier4.append(item)

print(f"Tier 1 (2022 Mentorship): {len(tier1)}")
print(f"Tier 2 (Silver Bullet / Models): {len(tier2)}")
print(f"Tier 3 (Newest 2023+): {len(tier3)}")
print(f"Tier 4 (Older content): {len(tier4)}")

# Sort each tier:
# Tier 1 is already in exact episode order (Episode 1 to 41)
# Tier 2: Sort by title or date
tier2.sort(key=lambda x: (x.get("upload_date") if x.get("upload_date") != "NA" else "19000101", x["title"]), reverse=True)
# Tier 3: Newest first (by video_index or stream_index or date)
tier3.sort(key=lambda x: (x["video_index"], x["stream_index"]))
# Tier 4: Older content
tier4.sort(key=lambda x: (x["video_index"], x["stream_index"]))

ordered_catalogue = tier1 + tier2 + tier3 + tier4
print(f"Total catalogue rows: {len(ordered_catalogue)}")

# Write to catalogue.csv
# Columns: id,title,upload_date,duration_min,playlist,url,status
with open(CATALOGUE_CSV, "w", encoding="utf-8", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["id", "title", "upload_date", "duration_min", "playlist", "url", "status"])
    for row in ordered_catalogue:
        dur_min = round(row["duration"] / 60) if row["duration"] else 0
        # Clean title of any raw newlines or tabs
        clean_title = re.sub(r'\s+', ' ', row["title"]).strip()
        clean_playlist = re.sub(r'\s+', ' ', row["playlist"]).strip()
        writer.writerow([
            row["id"],
            clean_title,
            row.get("upload_date", "NA"),
            dur_min,
            clean_playlist,
            row["url"],
            "todo"
        ])

print(f"Successfully generated {CATALOGUE_CSV} with {len(ordered_catalogue)} entries!")
