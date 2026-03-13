# Baseline Mock Draft Process

## Overview
This document describes how to run a realistic dynasty fantasy football mock draft using real ADP data and actual fantasy points.

## Data Sources

### ADP (Average Draft Position)
- **Source:** FantasyPros PPR Consensus ADP
- **URL:** https://www.fantasypros.com/nfl/adp/ppr-overall.php
- **Filter:** Offensive players only (QB, RB, WR, TE) - exclude DST and K
- **Saved file:** `adp_2025_filtered.json` (138 players)

### Fantasy Points
- **Source:** FantasyPros 2025 actual PPR scoring
- **Key:** Player name maps to total season FPTS

## Draft Rules

1. **12 teams, 20 rounds** (240 picks total)
2. **Snake draft order:** Round 1 (1→12), Round 2 (12→1), etc.
3. **Validation:**
   - Player must be in original ADP list
   - Selection must be within ±5 positions of player's ADP vs pick number
   - Player cannot be already drafted (remove after each pick)
4. **By round 12, every team should have 10 starters**

## Files

| File | Description |
|------|-------------|
| `adp_2025_filtered.json` | Real FantasyPros ADP (QB, RB, WR, TE only) |
| `draft_20rounds.json` | Complete draft board with all picks |
| `draft_real_adp.json` | Draft results |

## Running the Draft

```python
import json

# Load ADP
with open('adp_2025_filtered.json', 'r') as f:
    adp_players = json.load(f)

available = [p.copy() for p in adp_players]
draft_board = {f"Team {i}": [] for i in range(1, 13)}

# Snake draft order
def get_pick_order(teams, rounds):
    picks = []
    for rnd in range(1, rounds + 1):
        if rnd % 2 == 1:  # Odd: 1→12
            for i in range(1, len(teams) + 1):
                picks.append((rnd, i, teams[i-1]))
        else:  # Even: 12→1
            for i in range(len(teams), 0, -1):
                picks.append((rnd, i, teams[i-1]))
    return picks

# Find best player within ±5 of pick
def find_best_player(pick_num):
    candidates = [p for p in available if abs(p["adp"] - pick_num) <= 5]
    if candidates:
        candidates.sort(key=lambda x: abs(x["adp"] - pick_num))
        return candidates[0]
    # Expand to ±10 if needed
    candidates = [p for p in available if abs(p["adp"] - pick_num) <= 10]
    if candidates:
        candidates.sort(key=lambda x: abs(x["adp"] - pick_num))
        return candidates[0]
    # Last resort
    available.sort(key=lambda x: x["adp"])
    return available[0] if available else None

# Run draft
for rnd, pick_num, team in pick_order:
    player = find_best_player(pick_num)
    if player:
        player["pick"] = pick_num
        draft_board[team].append(player.copy())
        available = [p for p in available if p["name"] != player["name"]]
```

## Scoring (2025 FPTS)

Roster: 1 QB, 2 RB, 2 WR, 1 TE, 3 FLEX, 1 SUPERFLEX

```python
def calculate_score(roster):
    for p in roster:
        p["fpts"] = fpts_2025.get(p["name"], 0)
    
    qbs = sorted([p for p in roster if p["pos"] == "QB"], key=lambda x: x["fpts"], reverse=True)
    rbs = sorted([p for p in roster if p["pos"] == "RB"], key=lambda x: x["fpts"], reverse=True)
    wrs = sorted([p for p in roster if p["pos"] == "WR"], key=lambda x: x["fpts"], reverse=True)
    tes = sorted([p for p in roster if p["pos"] == "TE"], key=lambda x: x["fpts"], reverse=True)
    
    starters = []
    starters.append(("QB", qbs[0])) if qbs else None
    starters.append(("RB", rbs[0])) if rbs else None
    starters.append(("RB", rbs[1])) if len(rbs) > 1 else None
    starters.append(("WR", wrs[0])) if wrs else None
    starters.append(("WR", wrs[1])) if len(wrs) > 1 else None
    starters.append(("TE", tes[0])) if tes else None
    
    # FLEX (best remaining RB/WR/TE)
    flex = rbs[2:] + wrs[2:] + tes[1:]
    flex.sort(key=lambda x: x["fpts"], reverse=True)
    for f in flex[:3]:
        starters.append(("FLEX", f))
    
    # SUPERFLEX (best remaining)
    remaining = rbs[3:] + wrs[3:] + tes[2:] + qbs[1:]
    remaining.sort(key=lambda x: x["fpts"], reverse=True)
    if remaining:
        starters.append(("SUPERFLEX", remaining[0]))
    
    return sum(p.get("fpts", 0) for slot, p in starters), starters
```

## Key Learnings (Mar 12, 2026)

1. **Use real ADP** - Don't generate ADP data; fetch from FantasyPros
2. **Filter offensive only** - Exclude DST and K from ADP list
3. **Validate picks** - Each pick within ±5 of ADP position
4. **Remove drafted players** - No duplicates in snake draft
5. **Score with actual FPTS** - Use previous season's actual fantasy points
6. **Proper starting lineup** - 1 QB, 2 RB, 2 WR, 1 TE, 3 FLEX, 1 SUPERFLEX

## Updating ADP

To update with new season ADP:
1. Fetch from FantasyPros
2. Filter to QB, RB, WR, TE only
3. Save as `adp_2025_filtered.json`
4. Run draft following above process

---
*Created: March 12, 2026*
