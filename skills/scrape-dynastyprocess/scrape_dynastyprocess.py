#!/usr/bin/env python3
"""
Scrape DynastyProcess values from GitHub
Usage: python scrape_dynastyprocess.py
"""

import urllib.request
import csv
import json
import os

DYNASTYPROCESS_URL = "https://raw.githubusercontent.com/dynastyprocess/data/master/files/values-players.csv"
OUTPUT_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static", "dynastyprocess_values.json")

def main():
    print(f"Fetching DynastyProcess values from GitHub...")
    
    # Download CSV
    with urllib.request.urlopen(DYNASTYPROCESS_URL) as response:
        content = response.read().decode('utf-8')
    
    # Parse CSV
    reader = csv.DictReader(content.splitlines())
    players = []
    
    for i, row in enumerate(reader):
        players.append({
            "id": str(i + 1),
            "name": row["player"],
            "pos": row["pos"],
            "team": row["team"],
            "value": int(float(row["value_2qb"]))  # Superflex values
        })
    
    # Save to JSON
    with open(OUTPUT_FILE, "w") as f:
        json.dump(players, f, indent=2)
    
    print(f"✓ Saved {len(players)} players to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
