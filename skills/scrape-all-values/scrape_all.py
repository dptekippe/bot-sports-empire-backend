#!/usr/bin/env python3
"""
Scrape all dynasty player values
Usage: python scrape_all.py
"""

import urllib.request
import csv
import json
import subprocess
import os
import sys

# Add skills directory to path
SKILLS_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(os.path.dirname(SKILLS_DIR), "static")

KTC_URL = "https://keeptradecut.com/dynasty-rankings"
DP_URL = "https://raw.githubusercontent.com/dynastyprocess/data/master/files/values-players.csv"

def scrape_ktc():
    """Scrape KTC values"""
    print("Fetching KTC...")
    
    # Use scrapling
    result = subprocess.run(
        ["~/.local/bin/scrapling", "extract", "get", KTC_URL, "/tmp/ktc_raw.html"],
        capture_output=True, text=True
    )
    
    if result.returncode != 0:
        print(f"  KTC fetch error: {result.stderr}")
        return 0
    
    # Parse - look for patterns in text
    import re
    with open("/tmp/ktc_raw.html", "r") as f:
        content = f.read()
    
    players = []
    for line in content.split("\n"):
        match = re.search(r'(\d+)\s+([A-Za-z\.\'\-]+ [A-Za-z\.\'\-]+)\s+(QB|RB|WR|TE|PICK)\s+([A-Z]{2,3})\s+(\d{3,4})', line)
        if match:
            players.append({
                "id": match.group(1),
                "name": match.group(2).strip(),
                "pos": match.group(3),
                "team": match.group(4),
                "value": int(match.group(5))
            })
    
    if players:
        with open(os.path.join(STATIC_DIR, "ktc_values.json"), "w") as f:
            json.dump(players, f, indent=2)
        print(f"  ✓ KTC: {len(players)} players")
    return len(players)

def scrape_dynastyprocess():
    """Fetch DynastyProcess values from GitHub"""
    print("Fetching DynastyProcess...")
    
    try:
        with urllib.request.urlopen(DP_URL) as response:
            content = response.read().decode('utf-8')
        
        reader = csv.DictReader(content.splitlines())
        players = []
        
        for i, row in enumerate(reader):
            players.append({
                "id": str(i + 1),
                "name": row["player"],
                "pos": row["pos"],
                "team": row["team"],
                "value": int(float(row["value_2qb"]))
            })
        
        with open(os.path.join(STATIC_DIR, "dynastyprocess_values.json"), "w") as f:
            json.dump(players, f, indent=2)
        
        print(f"  ✓ DynastyProcess: {len(players)} players")
        return len(players)
    except Exception as e:
        print(f"  ✗ DynastyProcess error: {e}")
        return 0

def main():
    print("=" * 50)
    print("Scraping dynasty values...")
    print("=" * 50)
    
    ktc_count = scrape_ktc()
    dp_count = scrape_dynastyprocess()
    
    print("=" * 50)
    print(f"Total: {ktc_count + dp_count} player values updated")
    print("=" * 50)

if __name__ == "__main__":
    main()
