import os
import sys
import json
import re
import csv
from pathlib import Path
import yt_dlp

CHANNEL_HANDLE = "@InnerCircleTrader"
BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "research" / "ict-videos"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

PLAYLISTS_CACHE = OUTPUT_DIR / ".playlists_cache.json"
VIDEOS_CACHE = OUTPUT_DIR / ".videos_cache.json"
STREAMS_CACHE = OUTPUT_DIR / ".streams_cache.json"
CATALOGUE_CSV = OUTPUT_DIR / "catalogue.csv"

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

def has_market_or_model(title: str) -> bool:
    return bool(KW_REGEX.search(title))

def fetch_flat(url: str, description: str):
    print(f"Fetching {description}: {url}...")
    ydl_opts = {
        'extract_flat': True,
        'quiet': True,
        'ignoreerrors': True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        return info

def get_playlists():
    if PLAYLISTS_CACHE.exists():
        print(f"Loading playlists from cache: {PLAYLISTS_CACHE}")
        with open(PLAYLISTS_CACHE, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    url = f"https://www.youtube.com/{CHANNEL_HANDLE}/playlists"
    info = fetch_flat(url, "Channel Playlists")
    playlists_data = []
    
    ydl_opts = {
        'extract_flat': True,
        'quiet': True,
        'ignoreerrors': True,
    }
    
    for entry in info.get('entries', []):
        pl_id = entry.get('id')
        pl_title = entry.get('title')
        if not pl_id:
            continue
        print(f"Fetching playlist entries: '{pl_title}' ({pl_id})...")
        pl_url = f"https://www.youtube.com/playlist?list={pl_id}"
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            pl_info = ydl.extract_info(pl_url, download=False)
            items = []
            if pl_info and 'entries' in pl_info:
                for item in pl_info['entries']:
                    if item:
                        items.append({
                            'id': item.get('id'),
                            'title': item.get('title'),
                            'duration': item.get('duration'),
                            'url': item.get('url') or f"https://www.youtube.com/watch?v={item.get('id')}"
                        })
            playlists_data.append({
                'id': pl_id,
                'title': pl_title,
                'items': items
            })
            
    with open(PLAYLISTS_CACHE, 'w', encoding='utf-8') as f:
        json.dump(playlists_data, f, indent=2, ensure_ascii=False)
    print(f"Saved {len(playlists_data)} playlists to {PLAYLISTS_CACHE}")
    return playlists_data

def get_videos():
    if VIDEOS_CACHE.exists():
        print(f"Loading videos from cache: {VIDEOS_CACHE}")
        with open(VIDEOS_CACHE, 'r', encoding='utf-8') as f:
            return json.load(f)
            
    url = f"https://www.youtube.com/{CHANNEL_HANDLE}/videos"
    info = fetch_flat(url, "Channel Videos")
    entries = []
    for item in info.get('entries', []):
        if item:
            entries.append({
                'id': item.get('id'),
                'title': item.get('title'),
                'duration': item.get('duration'),
                'url': item.get('url') or f"https://www.youtube.com/watch?v={item.get('id')}"
            })
    with open(VIDEOS_CACHE, 'w', encoding='utf-8') as f:
        json.dump(entries, f, indent=2, ensure_ascii=False)
    print(f"Saved {len(entries)} videos to {VIDEOS_CACHE}")
    return entries

def get_streams():
    if STREAMS_CACHE.exists():
        print(f"Loading streams from cache: {STREAMS_CACHE}")
        with open(STREAMS_CACHE, 'r', encoding='utf-8') as f:
            return json.load(f)
            
    url = f"https://www.youtube.com/{CHANNEL_HANDLE}/streams"
    info = fetch_flat(url, "Channel Live Streams")
    entries = []
    for item in info.get('entries', []):
        if item:
            entries.append({
                'id': item.get('id'),
                'title': item.get('title'),
                'duration': item.get('duration'),
                'url': item.get('url') or f"https://www.youtube.com/watch?v={item.get('id')}"
            })
    with open(STREAMS_CACHE, 'w', encoding='utf-8') as f:
        json.dump(entries, f, indent=2, ensure_ascii=False)
    print(f"Saved {len(entries)} streams to {STREAMS_CACHE}")
    return entries

if __name__ == '__main__':
    playlists = get_playlists()
    videos = get_videos()
    streams = get_streams()
    print(f"Summary: {len(playlists)} playlists, {len(videos)} videos, {len(streams)} streams.")
