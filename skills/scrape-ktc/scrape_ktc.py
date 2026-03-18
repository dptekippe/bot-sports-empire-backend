#!/usr/bin/env python3
"""
Scrape KTC dynasty values
Usage: python scrape_ktc.py
"""

import subprocess
import json
import re
import os

KTC_URL = "https://keeptradecut.com/dynasty-rankings"
OUTPUT_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static", "ktc_values.json")

def main():
    print(f"Fetching KTC rankings from {KTC_URL}...")
    
    # Use scrapling to fetch
    result = subprocess.run(
        ["~/.local/bin/scrapling", "extract", "get", KTC_URL, "/tmp/ktc_scrape.html"],
        capture_output=True, text=True
    )
    
    if result.returncode != 0:
        print(f"Error fetching: {result.stderr}")
        return
    
    # Parse the HTML
    with open("/tmp/ktc_scrape.html", "r") as f:
        content = f.read()
    
    # Extract player data from text
    players = []
    lines = content.split("\n")
    
    for line in lines:
        # Look for patterns like: "1 Josh Allen QB BUF 9999"
        match = re.search(r'(\d+)\s+([A-Za-z\.\'\-]+ [A-Za-z\.\'\-]+)\s+(QB|RB|WR|TE|PICK)\s+([A-Z]{2,3})\s+(\d{3,4})', line)
        if match:
            rank = int(match.group(1))
            name = match.group(2).strip()
            pos = match.group(3)
            team = match.group(4)
            value = int(match.group(5))
            players.append({
                "id": str(rank),
                "name": name,
                "pos": pos,
                "team": team,
                "value": value
            })
    
    # Save to JSON
    with open(OUTPUT_FILE, "w") as f:
        json.dump(players, f, indent=2)
    
    print(f"✓ Saved {len(players)} players to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
