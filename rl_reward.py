"""
RL Reward Function for DynastyDroid Draft Optimization

Uses 2025 FantasyPros PPR data for top 164 players.
Falls back to ADP-based estimation for remaining players.

VORP Calibration (v2):
- ProjPts formula scaled up to match historical data
- Position baselines from RP24-30 across positions
- ±20% Monte Carlo variance for uncertainty

CFR Integration:
- Terminal reward = total_proj_pts + roster_penalty - regret
- HER: For each regret > 1.0, create hindsight episode
"""

import json
import math
import random
from typing import Optional, Dict, List, Tuple

# Load top 164 players
TOP164_FILE = 'fantasy_points_2025.json'

# Position multipliers (scarcity adjustment)
POS_MULT = {'QB': 1.4, 'RB': 1.2, 'WR': 1.0, 'TE': 1.1}

# Position baselines (RP24-30 level = replacement level)
BASELINES = {'QB': 220, 'RB': 140, 'WR': 130, 'TE': 110}

# Median points for top-tier players at each position
MEDIAN_POS = {'QB': 260, 'RB': 180, 'WR': 170, 'TE': 140}

# Target roster counts
ROSTER_TARGETS = {'QB': 2, 'RB': 5, 'WR': 7, 'TE': 3}


def load_top164() -> Dict[str, dict]:
    """Load top 164 players with 2025 PPR points"""
    try:
        with open(TOP164_FILE, 'r') as f:
            players = json.load(f)
        return {p['name']: p for p in players}
    except FileNotFoundError:
        import os
        path = os.path.expanduser('~/.openclaw/workspace/fantasy_points_2025.json')
        with open(path, 'r') as f:
            players = json.load(f)
        return {p['name']: p for p in players}


# Global cache
_top164_cache = None


def proj_pts(adp: float, position: str, use_mc: bool = False) -> float:
    """
    Projected fantasy points from ADP using calibrated formula.
    
    Calibrated to:
    - ADP 1 ≈ 300 pts (QB/RB stud)
    - ADP 50 ≈ 130 pts (RB/WR starter)
    - ADP 100 ≈ 90 pts (flex level)
    
    Args:
        adp: Average Draft Position (1-240)
        position: QB/RB/WR/TE
        use_mc: Add Monte Carlo variance (±20%)
    
    Returns:
        Projected PPR fantasy points
    """
    if adp <= 0 or adp > 240:
        return 50
    
    pos_mult = POS_MULT.get(position, 1.0)
    
    # Calibrated formula: 35 * ln(241 - ADP) + 30 * pos_mult - 15
    # Produces: ADP1 RB ~210, ADP100 WR ~140
    base = 35 * math.log(241 - adp) + 30 * pos_mult - 15
    base = max(50, base)
    
    if use_mc:
        variance = base * random.uniform(-0.2, 0.2)
        base += variance
    
    return base


def vorp(projected_pts: float, position: str) -> float:
    """
    Value Over Replacement - how much better than replacement level.
    
    Args:
        projected_pts: ProjPts from formula
        position: QB/RB/WR/TE
    
    Returns:
        VORP score (positive = better than replacement)
    """
    baseline = BASELINES.get(position, 120)
    median = MEDIAN_POS.get(position, 150)
    
    # Stronger stud bonus: +15 for top-tier players
    bonus = 15 * max(0, (projected_pts / median - 1))
    
    # Floor negatives at 0
    return max(0, projected_pts - baseline + bonus)


def need_score(current_count: int, target: int, rounds_left: int) -> float:
    """
    Positional need score - how much we need this position.
    
    Args:
        current_count: How many we currently have
        target: Target count for position
        rounds_left: Rounds remaining in draft
    
    Returns:
        Need score (higher = more urgent)
    """
    if rounds_left <= 0:
        return 0
    diff = max(0, target - current_count)
    return diff / math.sqrt(rounds_left)


def final_score(vorp: float, need: float, pick_num: int) -> float:
    """
    Final selection score combining VORP, need, and draft position.
    
    Early picks have MORE impact (higher weight), not less.
    Pick 1 = highest weight, Pick 240 = lowest weight.
    
    Args:
        vorp: VORP score
        need: Position need score
        pick_num: Current pick number (1-240)
    
    Returns:
        Final score (higher = better pick)
    """
    # Early picks worth more: pick 1 = 1.0, pick 240 = 0.004
    pick_factor = (241 - pick_num) / 240
    return vorp * need * pick_factor


def roster_penalty(counts: Dict[str, int]) -> float:
    """
    Penalty for overloading positions beyond target + 2.
    
    Args:
        counts: Position counts {'QB': n, 'RB': n, ...}
    
    Returns:
        Penalty (negative)
    """
    penalty = 0
    for pos, target in ROSTER_TARGETS.items():
        current = counts.get(pos, 0)
        over = max(0, current - target - 2)
        penalty -= over ** 2 * 20
    return penalty


def get_fpts(player_name: str, adp_position: Optional[int] = None) -> float:
    """Get fantasy points for a player (legacy function)"""
    global _top164_cache
    
    if _top164_cache is None:
        _top164_cache = load_top164()
    
    if player_name in _top164_cache:
        return _top164_cache[player_name]['fpts_ppr']
    
    if adp_position:
        base_est = 500 / (adp_position ** 1.2)
        return base_est * 0.8
    
    return 0.5


def calculate_roster_reward(roster: List[str], league_avg: float = 2500) -> float:
    """Legacy reward calculation"""
    total_pts = sum(get_fpts(p) for p in roster)
    return total_pts - league_avg


def check_roster_legality(roster: List[str]) -> float:
    """Legacy legality check"""
    global _top164_cache
    
    if _top164_cache is None:
        _top164_cache = load_top164()
    
    counts = {'QB': 0, 'RB': 0, 'WR': 0, 'TE': 0}
    for player in roster:
        if player in _top164_cache:
            pos = _top164_cache[player]['position']
            if pos in counts:
                counts[pos] += 1
    
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
    """Legacy full reward"""
    points = sum(get_fpts(p) for p in roster)
    legality = check_roster_legality(roster)
    
    return {
        'points': points,
        'legality_penalty': legality,
        'total': points + legality - league_avg
    }


def calculate_regret(draft_log: List[Dict], team_id: int, pos_lookup: Dict) -> float:
    """
    Calculate position-constrained regret for a team's picks.
    
    Args:
        draft_log: List of pick dicts
        team_id: Team to analyze
        pos_lookup: Position lookup dict
    
    Returns:
        Total regret score
    """
    # Get team's picks
    team_picks = [p for p in draft_log if p.get('team') == team_id]
    team_picks.sort(key=lambda x: x.get('pick', 0))
    
    total_regret = 0
    
    for pick in team_picks:
        pick_num = pick.get('pick', 0)
        drafted_name = pick.get('player', '')
        drafted_adp = pick.get('adp', 100)
        
        drafted_pos = pos_lookup.get(drafted_name, 'WR')
        drafted_vorp = vorp(proj_pts(drafted_adp, drafted_pos), drafted_pos)
        
        # Find later picks
        later_picks = [p for p in draft_log if p.get('pick', 0) > pick_num]
        
        # Same position candidates
        same_pos_candidates = []
        for later in later_picks:
            later_name = later.get('player', '')
            later_pos = pos_lookup.get(later_name, 'WR')
            if later_pos == drafted_pos:
                later_adp = later.get('adp', 100)
                later_vorp = vorp(proj_pts(later_adp, later_pos), later_pos)
                same_pos_candidates.append(later_vorp)
        
        if same_pos_candidates:
            best_later = max(same_pos_candidates)
            regret = max(0, best_later - drafted_vorp)
            total_regret += regret
    
    return total_regret


def terminal_reward(draft_log: List[Dict], team_id: int, pos_lookup: Dict = None) -> Dict[str, float]:
    """
    Calculate terminal reward including CFR regret.
    
    Reward = total_proj_pts + roster_penalty - regret
    
    Args:
        draft_log: List of pick dicts
        team_id: Team to score
        pos_lookup: Optional position lookup
    
    Returns:
        Dict with 'points', 'penalty', 'regret', 'total'
    """
    if pos_lookup is None:
        pos_lookup = _load_positions()
    
    # Get team's picks
    team_picks = [p for p in draft_log if p.get('team') == team_id]
    
    # Calculate projected points
    total_pts = 0
    counts = {'QB': 0, 'RB': 0, 'WR': 0, 'TE': 0}
    
    for pick in team_picks:
        name = pick.get('player', '')
        adp = pick.get('adp', 100)
        pos = pos_lookup.get(name, 'WR')
        pts = proj_pts(adp, pos)
        total_pts += pts
        
        if pos in counts:
            counts[pos] += 1
    
    # Roster penalty
    penalty = roster_penalty(counts)
    
    # CFR Regret
    regret = calculate_regret(draft_log, team_id, pos_lookup)
    
    # Final reward: higher = better
    # Subtract regret to penalize missed opportunities
    total = total_pts + penalty - regret
    
    return {
        'points': total_pts,
        'penalty': penalty,
        'regret': regret,
        'total': total
    }


def _load_positions() -> Dict[str, str]:
    """Load position lookup"""
    try:
        with open(TOP164_FILE, 'r') as f:
            players = json.load(f)
        return {p['name']: p.get('position', 'WR') for p in players}
    except FileNotFoundError:
        import os
        path = os.path.expanduser(f'~/.openclaw/workspace/{TOP164_FILE}')
        with open(path, 'r') as f:
            players = json.load(f)
        return {p['name']: p.get('position', 'WR') for p in players}


class HindsightReplayBuffer:
    """
    HER: Hindsight Experience Replay for draft training.
    
    For each pick with regret > threshold, creates a hindsight episode
    where the "goal" is the best available player at that position.
    """
    
    def __init__(self, capacity: int = 10000, regret_threshold: float = 1.0):
        self.buffer = []
        self.capacity = capacity
        self.regret_threshold = regret_threshold
    
    def add_episode(self, draft_log: List[Dict], team_id: int, pos_lookup: Dict = None):
        """Analyze draft and add hindsight episodes to buffer"""
        
        if pos_lookup is None:
            pos_lookup = _load_positions()
        
        team_picks = [p for p in draft_log if p.get('team') == team_id]
        team_picks.sort(key=lambda x: x.get('pick', 0))
        
        for pick in team_picks:
            pick_num = pick.get('pick', 0)
            drafted_name = pick.get('player', '')
            drafted_adp = pick.get('adp', 100)
            
            drafted_pos = pos_lookup.get(drafted_name, 'WR')
            drafted_vorp = vorp(proj_pts(drafted_adp, drafted_pos), drafted_pos)
            
            # Find later picks at same position
            later_picks = [p for p in draft_log if p.get('pick', 0) > pick_num]
            
            same_pos_candidates = []
            for later in later_picks:
                later_name = later.get('player', '')
                later_pos = pos_lookup.get(later_name, 'WR')
                if later_pos == drafted_pos:
                    later_adp = later.get('adp', 100)
                    later_vorp = vorp(proj_pts(later_adp, later_pos), later_pos)
                    same_pos_candidates.append({
                        'name': later_name,
                        'adp': later_adp,
                        'vorp': later_vorp
                    })
            
            if same_pos_candidates:
                best_later = max(same_pos_candidates, key=lambda x: x['vorp'])
                regret = max(0, best_later['vorp'] - drafted_vorp)
                
                # If regret > threshold, add hindsight episode
                if regret > self.regret_threshold:
                    episode = {
                        'original_pick': {
                            'name': drafted_name,
                            'adp': drafted_adp,
                            'vorp': drafted_vorp
                        },
                        'hindsight_goal': best_later,
                        'regret': regret,
                        'pick_num': pick_num,
                        'position': drafted_pos
                    }
                    
                    if len(self.buffer) >= self.capacity:
                        self.buffer.pop(0)
                    self.buffer.append(episode)
    
    def get_hindsight_episodes(self) -> List[Dict]:
        """Get all hindsight episodes for training"""
        return self.buffer
    
    def __len__(self):
        return len(self.buffer)


# Test VORP calibration
if __name__ == '__main__':
    print("=== VORP Calibration Test ===\n")
    
    test_cases = [
        (5, 'RB'),   # ADP 5 RB
        (1, 'QB'),   # ADP 1 QB
        (20, 'WR'),  # ADP 20 WR
        (50, 'TE'),  # ADP 50 TE
        (100, 'RB'), # ADP 100 RB
    ]
    
    print(f"{'ADP':<6} {'Pos':<4} {'ProjPts':>8} {'VORP':>8} {'Need':>6} {'Score':>8}")
    print("-" * 45)
    
    for adp, pos in test_cases:
        pts = proj_pts(adp, pos)
        v = vorp(pts, pos)
        n = need_score(0, ROSTER_TARGETS[pos], 20)
        s = final_score(v, n, adp)
        print(f"{adp:<6} {pos:<4} {pts:>8.1f} {v:>8.1f} {n:>6.2f} {s:>8.1f}")
    
    print("\n=== Test Roster (8 players) ===")
    test_players = [
        "Josh Allen", "Jonathan Taylor", 
        "Puka Nacua", "Ja'Marr Chase",
        "Trey McBride", "Christian McCaffrey",
        "Bijan Robinson", "Jahmyr Gibbs",
    ]
    
    result = full_reward(test_players)
    print(f"Points: {result['points']:.1f}")
    print(f"Legality: {result['legality_penalty']}")
    print(f"Total: {result['total']:.1f}")
