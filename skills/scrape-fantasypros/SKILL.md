# Skill: scrape-fantasypros
# Description: Scrape FantasyPros dynasty ECR rankings via browser automation

## Usage
Invoke this skill to scrape FantasyPros dynasty rankings.

## What it does
1. Uses OpenClaw browser automation to navigate to FantasyPros
2. Extracts dynasty rankings (ECR = Expert Consensus Ranking)
3. Saves to static/fantasypros_values.json

## URL
https://www.fantasypros.com/nfl/rankings/dynasty-overall.php

## Output
- static/fantasypros_values.json
- Format: [{"rank": 1, "name": "Ja'Marr Chase", "pos": "WR", "ecr": 1.0}, ...]

## Notes
- Uses browser automation (CDP) to handle JavaScript rendering
- Shows ECR (rank), not trade values
- Can be combined with KTC/DynastyProcess for multi-source blend
- Run weekly via cron
