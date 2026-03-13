"""
RL Reward Function for DynastyDroid Draft Optimization

Uses 2025 FantasyPros PPR data for top 164 players.
Falls back to ADP-based estimation for remaining players.
"""

import json
import math
from typing import Optional, Dict, List

# Load top 164 players
TOP164_FILE = 'fantasy_points_2025.json'

def load_top164() -> Dict[str, dict]:
    """Load top 164 players with 2025 PPR points"""
    try:
        with open(TOP164_FILE, 'r') as f:
            players = json.load(f)
        return {p['name']: p for p in players}
    except FileNotFoundError:
        # Fallback: try workspace path
        import os
        path = os.path.expanduser('~/.openclaw/workspace/fantasy_points_2025.json')
        with open(path, 'r') as f:
            players = json.load(f)
        return {p['name']: p for p in players}

# Global cache
_top164_cache = None

def get_fpts(player_name: str, adp_position: Optional[int] = None) -> float:
    """
    Get fantasy points for a player.
    
    Args:
        player_name: Player's full name
        adp_position: ADP rank (if known) for estimation
        
    Returns:
        PPR fantasy points (2025 season)
    """
    global _top164_cache
    
    if _top164_cache is None:
        _top164_cache = load_top164()
    
    # Check top 164 first
    if player_name in _top164_cache:
        return _top164_cache[player_name]['fpts_ppr']
    
    # Fallback: ADP-based estimation using power law
    # fpts = 500 / (adp_position ** 1.2)
    # Also apply 20% bench penalty
    if adp_position:
        base_est = 500 / (adp_position ** 1.2)
        return base_est * 0.8  # 20% bench penalty
    
    # Unknown player with no ADP = minimal value
    return 0.5


def calculate_roster_reward(roster: List[str], league_avg: float = 2500) -> float:
    """
    Calculate reward for a full roster.
    
    Args:
        roster: List of player names
        league_avg: Average points across league (default 2500)
        
    Returns:
        reward = sum(fpts) - league_avg
    """
    total_pts = sum(get_fpts(p) for p in roster)
    return total_pts - league_avg


def check_roster_legality(roster: List[str]) -> float:
    """
    Check if roster has required starters.
    
    Penalties:
    - Missing QB: -50
    - Missing 2nd RB: -50
    - Missing 2nd WR: -50
    - Missing TE: -50
    
    Returns:
        Penalty (negative) or 0 if legal
    """
    global _top164_cache
    
    if _top164_cache is None:
        _top164_cache = load_top164()
    
    # Count positions
    counts = {'QB': 0, 'RB': 0, 'WR': 0, 'TE': 0}
    for player in roster:
        if player in _top164_cache:
            pos = _top164_cache[player]['position']
            if pos in counts:
                counts[pos] += 1
    
    # Check requirements: 1 QB, 2 RB, 2 WR, 1 TE
    penalty = 0
    if counts['QB'] < 1:
        penalty -= 50
    if counts['RB'] < 2:
        penalty -= 50
    if counts['WR'] < 2:
        penalty -= 50
    if counts['TE'] < 1:
        penalty -= 50
    
    return penalty


def full_reward(roster: List[str], league_avg: float = 2500) -> Dict[str, float]:
    """
    Calculate full reward with legality check.
    
    Returns:
        Dict with 'points', 'legality_penalty', 'total'
    """
    points = sum(get_fpts(p) for p in roster)
    legality = check_roster_legality(roster)
    
    return {
        'points': points,
        'legality_penalty': legality,
        'total': points + legality - league_avg
    }


# Test
if __name__ == '__main__':
    # Test reward function
    test_players = [
        "Josh Allen",
        "Jonathan Taylor", 
        "Puka Nacua",
        "Ja'Marr Chase",
        "Trey McBride",
        "Christian McCaffrey",
        "Bijan Robinson",
        "Jahmyr Gibbs",
    ]
    
    result = full_reward(test_players)
    print(f"Test Roster (8 players):")
    print(f"  Points: {result['points']:.1f}")
    print(f"  Legality: {result['legality_penalty']}")
    print(f"  Total Reward: {result['total']:.1f}")
