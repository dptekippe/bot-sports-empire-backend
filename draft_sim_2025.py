#!/usr/bin/env python3
"""
2025 Dynasty Fantasy Football Simulation
Using actual 2025 PPR ADP and season stats
"""

import json
import random
from collections import defaultdict

# 2025 PPR ADP (top 60 for draft)
ADP_2025 = [
    ("Ja'Marr Chase", "WR", "CIN", 1),
    ("Bijan Robinson", "RB", "ATL", 2),
    ("Saquon Barkley", "RB", "PHI", 3),
    ("Jahmyr Gibbs", "RB", "DET", 4),
    ("CeeDee Lamb", "WR", "DAL", 5),
    ("Justin Jefferson", "WR", "MIN", 6),
    ("Christian McCaffrey", "RB", "SF", 7),
    ("Malik Nabers", "WR", "NYG", 8),
    ("Amon-Ra St. Brown", "WR", "DET", 9),
    ("Derrick Henry", "RB", "BAL", 10),
    ("Ashton Jeanty", "RB", "LV", 11),
    ("Puka Nacua", "WR", "LAR", 12),
    ("Nico Collins", "WR", "HOU", 13),
    ("De'Von Achane", "RB", "MIA", 14),
    ("Brian Thomas Jr.", "WR", "JAC", 15),
    ("Josh Jacobs", "RB", "GB", 16),
    ("Drake London", "WR", "ATL", 17),
    ("Jonathan Taylor", "RB", "IND", 18),
    ("Brock Bowers", "TE", "LV", 19),
    ("Josh Allen", "QB", "BUF", 20),
    ("A.J. Brown", "WR", "PHI", 21),
    ("Chase Brown", "RB", "CIN", 22),
    ("Lamar Jackson", "QB", "BAL", 23),
    ("Bucky Irving", "RB", "TB", 24),
    ("Kyren Williams", "RB", "LAR", 25),
    ("Ladd McConkey", "WR", "LAC", 26),
    ("Trey McBride", "TE", "ARI", 27),
    ("James Cook III", "RB", "BUF", 28),
    ("Jayden Daniels", "QB", "WAS", 29),
    ("Tee Higgins", "WR", "CIN", 30),
    ("Tyreek Hill", "WR", "MIA", 31),
    ("Joe Burrow", "QB", "CIN", 32),
    ("Jaxon Smith-Njigba", "WR", "SEA", 33),
    ("Jalen Hurts", "QB", "PHI", 34),
    ("Omarion Hampton", "RB", "LAC", 35),
    ("Alvin Kamara", "RB", "NO", 36),
    ("George Kittle", "TE", "SF", 37),
    ("Breece Hall", "RB", "NYJ", 38),
    ("Terry McLaurin", "WR", "WAS", 39),
    ("Mike Evans", "WR", "SF", 40),
    ("Garrett Wilson", "WR", "NYJ", 41),
    ("Davante Adams", "WR", "LAR", 42),
    ("Kenneth Walker III", "RB", "KC", 43),
    ("Marvin Harrison Jr.", "WR", "ARI", 44),
    ("TreVeyon Henderson", "RB", "NE", 45),
    ("Chuba Hubbard", "RB", "CAR", 46),
    ("James Conner", "RB", "ARI", 47),
    ("DK Metcalf", "WR", "PIT", 48),
    ("Patrick Mahomes", "QB", "KC", 49),
    ("DJ Moore", "WR", "BUF", 50),
    ("Courtland Sutton", "WR", "DEN", 51),
    ("Sam LaPorta", "TE", "DET", 52),
    ("Xavier Worthy", "WR", "KC", 53),
    ("D'Andre Swift", "RB", "CHI", 54),
    ("DeVonta Smith", "WR", "PHI", 55),
    ("Tetairoa McMillan", "WR", "CAR", 56),
    ("Jameson Williams", "WR", "DET", 57),
    ("David Montgomery", "RB", "HOU", 58),
    ("RJ Harvey", "RB", "DEN", 59),
    ("Isiah Pacheco", "RB", "DET", 60),
]

# Actual 2025 fantasy points (season totals)
ACTUAL_2025_FPTS = {
    # QB
    "Josh Allen": 374.5, "Drake Maye": 359.9, "Matthew Stafford": 358.3,
    "Trevor Lawrence": 350.1, "Caleb Williams": 325.3, "Dak Prescott": 323.8,
    "Bo Nix": 315.8, "Jared Goff": 305.1, "Jalen Hurts": 305.0,
    "Justin Herbert": 299.8, "Patrick Mahomes": 296.7, "Baker Mayfield": 282.9,
    "Sam Darnold": 249.4, "Jaxson Dart": 246.5, "Jordan Love": 241.3,
    # RB
    "Christian McCaffrey": 416.6, "Bijan Robinson": 370.8, "Jahmyr Gibbs": 366.9,
    "Jonathan Taylor": 362.3, "De'Von Achane": 322.8, "James Cook III": 302.2,
    "Chase Brown": 282.6, "Derrick Henry": 279.5, "Kyren Williams": 263.3,
    "Travis Etienne Jr.": 253.9, "Ashton Jeanty": 245.1, "Javonte Williams": 242.8,
    "Josh Jacobs": 237.1, "Saquon Barkley": 232.3, "D'Andre Swift": 228.6,
    # WR
    "Puka Nacua": 375.0, "Jaxon Smith-Njigba": 359.9, "Amon-Ra St. Brown": 324.0,
    "Ja'Marr Chase": 313.6, "George Pickens": 291.9, "Chris Olave": 269.0,
    "Zay Flowers": 243.3, "Nico Collins": 226.2, "Davante Adams": 222.9,
    "Michael Wilson": 220.6, "A.J. Brown": 220.3, "Jameson Williams": 219.9,
    "Courtland Sutton": 219.7, "Wan'Dale Robinson": 217.9, "Tee Higgins": 211.6,
    "Tetairoa McMillan": 211.4, "Stefon Diggs": 210.3, "Michael Pittman Jr.": 202.4,
    "Drake London": 201.9, "DeVonta Smith": 201.8, "Justin Jefferson": 201.5,
    "CeeDee Lamb": 200.9,
    # TE
    "Trey McBride": 315.9, "Kyle Pitts": 210.8, "Travis Kelce": 193.2,
    "Tyler Warren": 188.5, "Jake Ferguson": 188.1, "Harold Fannin Jr.": 186.4,
    "Dallas Goedert": 185.1, "Juwan Johnson": 179.9, "Hunter Henry": 178.8,
    "Dalton Schultz": 177.7, "Brock Bowers": 176.2,
}

# Games played (approximate for per-game calc)
GAMES_PLAYED = 17

def get_player_fpts(player_name):
    """Get per-game fantasy points with randomness"""
    total_fpts = ACTUAL_2025_FPTS.get(player_name, 50)  # default for unknown
    per_game = total_fpts / GAMES_PLAYED
    # Add ±20% randomness for week-to-week variance
    return per_game * random.uniform(0.8, 1.2)

# Team strategies
TEAM_STRATEGIES = {
    "Roger (Balanced)": "Follow ADP strictly, balanced RB/WR/TE",
    "Hero RB": "First 2 picks RB, then value",
    "Zero RB": "Zero RBs first 4 rounds, load up WR",
    "Elite QB": "Prioritize QB early (superflex)",
    "Value WR": "Wait on WR, target value picks",
    "Youth Movement": "Prioritize younger players",
    "Veteran Hunter": "Prioritize proven veterans",
    "Best Player": "Take best available always",
    "PPR Specialist": "Target high-catch WRs",
    "Sleeper Hunter": "Target ADP sleepers",
    "Risk Taker": "High variance, high ceiling",
    "Safe Draft": "High floor players only",
}

def run_draft():
    """Run snake draft"""
    teams = list(TEAM_STRATEGIES.keys())
    random.shuffle(teams)
    
    rosters = {team: [] for team in teams}
    adp_index = 0
    
    # 20 round draft
    for round_num in range(1, 21):
        # Snake order
        if round_num % 2 == 1:
            pick_order = teams
        else:
            pick_order = teams[::-1]
        
        for team in pick_order:
            if adp_index < len(ADP_2025):
                player = ADP_2025[adp_index]
                rosters[team].append({
                    "name": player[0],
                    "pos": player[1],
                    "team": player[2],
                    "adp": player[3]
                })
                adp_index += 1
    
    return rosters

def score_week(rosters, week):
    """Score a week for all teams"""
    scores = {}
    
    for team, roster in rosters.items():
        total = 0
        # Start: 1 QB, 2 RB, 3 WR, 1 TE, 1 FLEX (total 8)
        # For simplicity, score top 8 players
        for player in roster[:8]:
            fpts = get_player_fpts(player["name"])
            total += fpts
        scores[team] = round(total, 1)
    
    return scores

def run_season(rosters):
    """Run 14-week regular season (weeks 1-14)"""
    weekly_results = []
    
    for week in range(1, 15):
        scores = score_week(rosters, week)
        weekly_results.append(scores)
    
    # Calculate standings
    standings = defaultdict(float)
    for week_scores in weekly_results:
        for team, score in week_scores.items():
            standings[team] += score
    
    # Sort by total points
    sorted_standings = sorted(standings.items(), key=lambda x: x[1], reverse=True)
    
    return sorted_standings, weekly_results

def run_playoffs(rosters, regular_standings):
    """Run playoffs weeks 15-17"""
    # Top 6 make playoffs
    playoff_teams = [t[0] for t in regular_standings[:6]]
    
    # Week 15: Semifinals (1v6, 2v5, 3v4) - but for 6 teams: 1v4, 2v3, winner gets bye
    # Simple: 1v4, 2v3, winners play in week 16, champion in week 17
    
    matchups = [
        (playoff_teams[0], playoff_teams[3]),
        (playoff_teams[1], playoff_teams[2]),
    ]
    
    week15_winners = []
    for team1, team2 in matchups:
        score1 = score_week({team1: rosters[team1]}, 15)[team1]
        score2 = score_week({team2: rosters[team2]}, 15)[team2]
        
        if score1 >= score2:
            week15_winners.append(team1)
        else:
            week15_winners.append(team2)
    
    # Week 16: Championship
    score1 = score_week({week15_winners[0]: rosters[week15_winners[0]]}, 16)[week15_winners[0]]
    score2 = score_week({week15_winners[1]: rosters[week15_winners[1]]}, 16)[week15_winners[1]]
    
    if score1 >= score2:
        champion = week15_winners[0]
    else:
        champion = week15_winners[1]
    
    return champion

def main():
    print("=" * 60)
    print("🏈 2025 DYNASTY FANTASY FOOTBALL SIMULATION")
    print("=" * 60)
    
    # Run draft
    print("\n📝 DRAFT RESULTS (Snake, 20 Rounds)")
    print("-" * 40)
    
    random.seed(42)  # For reproducibility
    rosters = run_draft()
    
    # Show first few picks for each team
    for team, roster in rosters.items():
        print(f"\n{team}:")
        for i, p in enumerate(roster[:5]):
            print(f"  {i+1}. {p['name']} ({p['pos']}) - ADP: {p['adp']}")
        print(f"  ... ({len(roster)} total)")
    
    # Run season
    print("\n\n📊 REGULAR SEASON (Weeks 1-14)")
    print("-" * 40)
    
    standings, weekly = run_season(rosters)
    
    print("\nFinal Standings:")
    for i, (team, pts) in enumerate(standings, 1):
        strategy = TEAM_STRATEGIES[team]
        print(f"  {i}. {team}: {pts:.1f} pts - {strategy}")
    
    # Playoffs
    print("\n\n🏆 PLAYOFFS (Weeks 15-17)")
    print("-" * 40)
    
    champion = run_playoffs(rosters, standings)
    
    print(f"\n🎉 CHAMPION: {champion} 🎉")
    print(f"   Strategy: {TEAM_STRATEGIES[champion]}")
    
    # Analysis
    print("\n\n📈 ANALYSIS")
    print("-" * 40)
    print(f"Total Points Scored (Champion): {standings[0][1]:.1f}")
    print(f"Average Weekly Score: {standings[0][1]/14:.1f}")
    
    # Store results for database
    results = {
        "draft": {team: [p["name"] for p in roster] for team, roster in rosters.items()},
        "standings": standings,
        "champion": champion
    }
    
    return results

if __name__ == "__main__":
    main()
