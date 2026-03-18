# Skill: scrape-all-values
# Description: Scrape all dynasty player value sources

## Usage
Run: `scrape-all-values` or invoke this skill to update all player values.

## What it does
1. Scrapes KTC (KeepTradeCut.com) - dynasty rankings
2. Fetches DynastyProcess values from GitHub CSV
3. Saves both to static/ JSON files
4. Returns count of players from each source

## Sources
- **KTC**: keeptradecut.com - crowdsourced values (0-9999)
- **DynastyProcess**: GitHub CSV - expert values (0-10000)

## Cron Schedule
Run weekly:
```
0 6 * * 0 cd ~/.openclaw/workspace && python3 skills/scrape-all-values/scrape_all.py
```

## Output
- static/ktc_values.json
- static/dynastyprocess_values.json
