"""
Bestball Simulation with REAL 2025 Data
=========================================
100 simulations, 12 teams, 17-round snake draft.
Strategies: BPA, Zero-RB, Late-QB, and varied random.
"""

import json
import random
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Tuple

# ---------------------------------------------------------------------------
# Load real data
# ---------------------------------------------------------------------------

ADP_FILE = "/Users/danieltekippe/.openclaw/workspace/adp_2025_filtered.json"
FPTS_FILE = "/Users/danieltekippe/.openclaw/workspace/fantasy_points_2025.json"

with open(ADP_FILE) as f:
    adp_data = json.load(f)

with open(FPTS_FILE) as f:
    fpts_data = json.load(f)

# Build fpts lookup by player name
fpts_lookup: Dict[str, float] = {}
for p in fpts_data:
    fpts_lookup[p["name"]] = p["fpts_ppr"]

# Build player list from ADP, annotate with real fpts
@dataclass(frozen=True, slots=True)
class Player:
    name: str
    position: str
    adp: float
    fpts_ppr: float
    team: str = ""

    def tier(self) -> int:
        if self.adp <= 12:   return 1
        if self.adp <= 36:   return 2
        if self.adp <= 72:   return 3
        if self.adp <= 144:  return 4
        return 5

players: List[Player] = []
for p in adp_data:
    name = p["name"]
    fpts = fpts_lookup.get(name, 0.0)
    pos = p.get("pos") or p.get("position", "UNK")
    team = p.get("team", "")
    players.append(Player(
        name=name,
        position=pos,
        adp=float(p["adp"]),
        fpts_ppr=fpts,
        team=team,
    ))

# Sort by ADP
players.sort(key=lambda p: p.adp)
print(f"Loaded {len(players)} players from ADP, {len(fpts_lookup)} from fantasy points")

# Count players with actual fpts
with_fpts = sum(1 for p in players if p.fpts_ppr > 0)
print(f"Players with real fpts_ppr: {with_fpts}")

# ---------------------------------------------------------------------------
# Strategy functions
# ---------------------------------------------------------------------------

def get_top_available_by_adp(available: List[Player], n: int = 1, pos: str = None) -> List[Player]:
    src = available if pos is None else [p for p in available if p.position == pos]
    return sorted(src, key=lambda p: p.adp)[:n]

def get_top_available_by_fpts(available: List[Player], n: int = 1, pos: str = None) -> List[Player]:
    src = available if pos is None else [p for p in available if p.position == pos]
    return sorted(src, key=lambda p: p.fpts_ppr, reverse=True)[:n]

# BPA: best player available by ADP
def strategy_bpa(available: List[Player], roster: List[Player]) -> Player:
    return get_top_available_by_adp(available, 1)[0]

# Zero-RB: skip RB in first 3 rounds (positions taken)
def strategy_zerorb(available: List[Player], roster: List[Player], picks_taken: int) -> Player:
    rounds_taken = picks_taken // 12
    if rounds_taken < 3:
        # Avoid RB
        non_rb = [p for p in available if p.position != "RB"]
        if non_rb:
            return get_top_available_by_adp(non_rb, 1)[0]
    return get_top_available_by_adp(available, 1)[0]

# Late-QB: wait on QB
def strategy_lateqb(available: List[Player], roster: List[Player], picks_taken: int) -> Player:
    rounds_taken = picks_taken // 12
    if rounds_taken < 5:
        non_qb = [p for p in available if p.position != "QB"]
        if non_qb:
            return get_top_available_by_adp(non_qb, 1)[0]
    return get_top_available_by_adp(available, 1)[0]

# Random: pick random available player
def strategy_random(available: List[Player], roster: List[Player]) -> Player:
    return random.choice(available)

# Balanced: prefer position needs (2 RB, 3 WR early then fill)
def strategy_balanced(available: List[Player], roster: List[Player], picks_taken: int) -> Player:
    pos_counts = defaultdict(int)
    for p in roster:
        pos_counts[p.position] += 1
    # Need 2 RB, 3 WR, 1 TE minimum before filling other positions
    if pos_counts["RB"] < 2:
        rb_avail = [p for p in available if p.position == "RB"]
        if rb_avail:
            return get_top_available_by_adp(rb_avail, 1)[0]
    if pos_counts["WR"] < 3:
        wr_avail = [p for p in available if p.position == "WR"]
        if wr_avail:
            return get_top_available_by_adp(wr_avail, 1)[0]
    if pos_counts["TE"] < 1:
        te_avail = [p for p in available if p.position == "TE"]
        if te_avail:
            return get_top_available_by_adp(te_avail, 1)[0]
    return get_top_available_by_adp(available, 1)[0]

# Elite-Stack: stack top WRs and a QB
def strategy_elitestack(available: List[Player], roster: List[Player], picks_taken: int) -> Player:
    pos_counts = defaultdict(int)
    for p in roster:
        pos_counts[p.position] += 1
    # Prioritize WR in first 6 rounds
    rounds_taken = picks_taken // 12
    if rounds_taken < 6 and pos_counts["WR"] < 3:
        wr_avail = [p for p in available if p.position == "WR"]
        if wr_avail:
            return get_top_available_by_adp(wr_avail, 1)[0]
    # Grab a QB after round 8
    if rounds_taken >= 8 and pos_counts["QB"] < 1:
        qb_avail = [p for p in available if p.position == "QB"]
        if qb_avail:
            return get_top_available_by_adp(qb_avail, 1)[0]
    return get_top_available_by_adp(available, 1)[0]

# Robust-Flex: build around TE and WR
def strategy_robustflex(available: List[Player], roster: List[Player], picks_taken: int) -> Player:
    pos_counts = defaultdict(int)
    for p in roster:
        pos_counts[p.position] += 1
    if pos_counts["TE"] < 1:
        te_avail = [p for p in available if p.position == "TE"]
        if te_avail:
            return get_top_available_by_adp(te_avail, 1)[0]
    if pos_counts["RB"] < 2:
        rb_avail = [p for p in available if p.position == "RB"]
        if rb_avail:
            return get_top_available_by_adp(rb_avail, 1)[0]
    return get_top_available_by_adp(available, 1)[0]

# Hero-RB: take RB first, then best available
def strategy_herorb(available: List[Player], roster: List[Player]) -> Player:
    pos_counts = defaultdict(int)
    for p in roster:
        pos_counts[p.position] += 1
    if pos_counts["RB"] < 2:
        rb_avail = [p for p in available if p.position == "RB"]
        if rb_avail:
            return get_top_available_by_adp(rb_avail, 1)[0]
    return get_top_available_by_adp(available, 1)[0]

# Late-RB: load up on RBs in middle/late rounds
def strategy_laterb(available: List[Player], roster: List[Player], picks_taken: int) -> Player:
    rounds_taken = picks_taken // 12
    pos_counts = defaultdict(int)
    for p in roster:
        pos_counts[p.position] += 1
    # In rounds 5-12, prioritize RB
    if 5 <= rounds_taken <= 12 and pos_counts["RB"] < 4:
        rb_avail = [p for p in available if p.position == "RB"]
        if rb_avail:
            return get_top_available_by_adp(rb_avail, 1)[0]
    return get_top_available_by_adp(available, 1)[0]

# Spread: prioritize all positions evenly (no heavy stacking)
def strategy_spread(available: List[Player], roster: List[Player]) -> Player:
    pos_counts = defaultdict(int)
    for p in roster:
        pos_counts[p.position] += 1
    # Pick whichever position we have least of
    for pos in ["QB", "RB", "WR", "TE"]:
        if pos_counts[pos] == 0:
            avail = [p for p in available if p.position == pos]
            if avail:
                return get_top_available_by_adp(avail, 1)[0]
    return get_top_available_by_adp(available, 1)[0]

# Zero-WR: skip WR first 4 rounds
def strategy_zerowr(available: List[Player], roster: List[Player], picks_taken: int) -> Player:
    rounds_taken = picks_taken // 12
    if rounds_taken < 4:
        non_wr = [p for p in available if p.position != "WR"]
        if non_wr:
            return get_top_available_by_adp(non_wr, 1)[0]
    return get_top_available_by_adp(available, 1)[0]

# ---------------------------------------------------------------------------
# Draft simulation
# ---------------------------------------------------------------------------

STRATEGIES = [
    "BPA",
    "Zero-RB",
    "Late-QB",
    "Random",
    "Balanced",
    "Elite-Stack",
    "Robust-Flex",
    "Hero-RB",
    "Late-RB",
    "Spread",
    "Zero-WR",
    "Random",
]

def run_draft(seed: int) -> Tuple[List[Tuple[str, List[Player]]], List[int]]:
    random.seed(seed)
    available = list(players)
    rosters: List[List[Player]] = [[] for _ in range(12)]
    
    # Shuffle strategy assignment each draft
    strats = STRATEGIES.copy()
    random.shuffle(strats)
    
    # Build snake order
    draft_order: List[int] = []
    for r in range(17):
        if r % 2 == 0:
            draft_order.extend(range(12))
        else:
            draft_order.extend(range(11, -1, -1))
    
    for pick_idx, team_id in enumerate(draft_order):
        strat = strats[team_id]
        roster = rosters[team_id]
        
        if strat == "BPA":
            player = strategy_bpa(available, roster)
        elif strat == "Zero-RB":
            player = strategy_zerorb(available, roster, pick_idx)
        elif strat == "Late-QB":
            player = strategy_lateqb(available, roster, pick_idx)
        elif strat == "Elite-Stack":
            player = strategy_elitestack(available, roster, pick_idx)
        elif strat == "Robust-Flex":
            player = strategy_robustflex(available, roster, pick_idx)
        elif strat == "Hero-RB":
            player = strategy_herorb(available, roster)
        elif strat == "Late-RB":
            player = strategy_laterb(available, roster, pick_idx)
        elif strat == "Spread":
            player = strategy_spread(available, roster)
        elif strat == "Zero-WR":
            player = strategy_zerowr(available, roster, pick_idx)
        elif strat == "Balanced":
            player = strategy_balanced(available, roster, pick_idx)
        else:  # Random
            player = strategy_random(available, roster)
        
        rosters[team_id].append(player)
        available.remove(player)
    
    return [(strats[i], rosters[i]) for i in range(12)], draft_order

def calc_bestball_score(roster: List[Player]) -> float:
    """Bestball: sum of top 9 players by fpts_ppr"""
    sorted_roster = sorted(roster, key=lambda p: p.fpts_ppr, reverse=True)
    top9 = sorted_roster[:9]
    return sum(p.fpts_ppr for p in top9)

def calc_standings(rosters_with_strats: List[Tuple[str, List[Player]]]) -> List[Tuple[str, float, List[Player]]]:
    results = []
    for strat, roster in rosters_with_strats:
        score = calc_bestball_score(roster)
        results.append((strat, score, roster))
    results.sort(key=lambda x: x[1], reverse=True)
    return results

# ---------------------------------------------------------------------------
# Run 100 simulations
# ---------------------------------------------------------------------------

NUM_SIMS = 100

win_counts: Dict[str, int] = defaultdict(int)
total_scores: Dict[str, float] = defaultdict(float)
win_details: List[Dict] = []
player_win_contributions: Dict[str, float] = defaultdict(float)

for sim_idx in range(NUM_SIMS):
    seed = sim_idx * 42 + 7
    rosters_with_strats, draft_order = run_draft(seed)
    standings = calc_standings(rosters_with_strats)
    
    winner_strat = standings[0][0]
    win_counts[winner_strat] += 1
    
    for strat, score, roster in standings:
        total_scores[strat] += score
    
    # Track player contributions on winning rosters
    winner_roster = standings[0][2]
    winner_score = standings[0][1]
    for p in winner_roster:
        if p.fpts_ppr > 0:
            # Contribution = what % of team's bestball score came from this player
            contrib = p.fpts_ppr / winner_score if winner_score > 0 else 0
            player_win_contributions[p.name] += contrib
    
    if sim_idx < 5:  # Save first 5 drafts for analysis
        win_details.append({
            "sim": sim_idx,
            "standings": [(s, round(sc, 1)) for s, sc, r in standings],
            "winner": winner_strat,
        })

# ---------------------------------------------------------------------------
# Compute final stats
# ---------------------------------------------------------------------------

avg_scores = {strat: total_scores[strat] / NUM_SIMS for strat in total_scores}
win_rates = {strat: win_counts[strat] / NUM_SIMS * 100 for strat in win_counts}

# Sort strategies by win rate
sorted_by_wr = sorted(win_rates.items(), key=lambda x: x[1], reverse=True)
sorted_by_score = sorted(avg_scores.items(), key=lambda x: x[1], reverse=True)

# Top players by win contributions
top_players = sorted(player_win_contributions.items(), key=lambda x: x[1], reverse=True)[:20]

# ---------------------------------------------------------------------------
# Print summary
# ---------------------------------------------------------------------------

print("\n" + "="*60)
print("BESTBALL SIMULATION RESULTS - 100 SIMULATIONS, REAL 2025 DATA")
print("="*60)
print(f"\nPlayers: {len(players)} (ADP order), {with_fpts} with real fpts_ppr")
print(f"Scoring: Bestball (top 9 of 17 players by fpts_ppr)")
print(f"Roster: 12 teams × 17 rounds = 204 picks per draft")

print("\n--- WIN RATES BY STRATEGY ---")
for strat, wr in sorted_by_wr:
    avg = avg_scores[strat]
    wins = win_counts[strat]
    print(f"  {strat:15s}: {wins:3d} wins ({wr:5.1f}%) | Avg Score: {avg:.1f}")

print("\n--- AVERAGE SCORES BY STRATEGY ---")
for strat, avg in sorted_by_score:
    wr = win_rates[strat]
    print(f"  {strat:15s}: {avg:7.1f} avg pts | {wr:5.1f}% win rate")

print("\n--- TOP 20 PLAYERS BY WIN CONTRIBUTION ---")
print("  (Total contribution % across all 100 winning rosters)")
for name, contrib in top_players:
    print(f"  {name:30s}: {contrib:7.2f}")

# ---------------------------------------------------------------------------
# Save results
# ---------------------------------------------------------------------------

results = {
    "num_simulations": NUM_SIMS,
    "total_players": len(players),
    "players_with_real_fpts": with_fpts,
    "win_rates": win_rates,
    "avg_scores": avg_scores,
    "win_counts": dict(win_counts),
    "top_players_by_contribution": dict(top_players),
    "sample_drafts": win_details,
    "strategy_summary": {
        strat: {
            "wins": win_counts[strat],
            "win_rate_pct": round(win_rates[strat], 2),
            "avg_score": round(avg_scores[strat], 1),
        }
        for strat in set(list(win_counts.keys()) + STRATEGIES)
    },
}

out_path = "/Users/danieltekippe/.openclaw/workspace/bestball-swarm/results_real_100.json"
with open(out_path, "w") as f:
    json.dump(results, f, indent=2)

print(f"\nResults saved to: {out_path}")
