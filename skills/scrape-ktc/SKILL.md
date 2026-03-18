# Skill: scrape-ktc
# Description: Scrape dynasty values from KeepTradeCut.com

## Usage
Run: `scrape-ktc` or invoke this skill when you need fresh KTC values.

## What it does
1. Fetches KTC dynasty rankings from keeptradecut.com
2. Parses player names, positions, teams, values
3. Saves to static/ktc_values.json
4. Returns count of players scraped

## Output
- File: static/ktc_values.json
- Format: [{"id": "1", "name": "Josh Allen", "pos": "QB", "value": 9999, "team": "BUF"}, ...]

## Notes
- KTC uses 0-9999 scale
- Values are crowdsourced
- Run weekly via cron for fresh data
