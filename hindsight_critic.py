"""
Hindsight Critic: Analyze draft regret and opportunity costs

This module evaluates completed drafts to identify the worst team and calculate
their "regret" - the opportunity cost of each pick.

Used for:
- RL training signals (negative regret = reward)
- Draft autopsy reports
- Identifying draft strategy flaws
"""

import json
import argparse
from typing import Dict, List, Tuple
from draft_env import DraftEnv
from rl_reward import proj_pts, vorp, need_score, final_score, ROSTER_TARGETS


def load_player_positions():
    """Load player positions from fantasy_points file"""
    try:
        with open('fantasy_points_2025.json', 'r') as f:
            players = json.load(f)
        return {p['name']: p.get('position', 'WR') for p in players}
    except FileNotFoundError:
        import os
        path = os.path.expanduser('~/.openclaw/workspace/fantasy_points_2025.json')
        with open(path, 'r') as f:
            players = json.load(f)
        return {p['name']: p.get('position', 'WR') for p in players}


def calculate_vorp_for_player(player_name: str, adp: float, position: str) -> float:
    """Calculate VORP for a single player"""
    pts = proj_pts(adp, position)
    return vorp(pts, position)


def analyze_draft_regret(draft_log: List[Dict], teams: List, roger_slot: int = None) -> Dict:
    """
    Analyze a completed draft for regret.
    
    Args:
        draft_log: List of pick dicts with keys: pick, team, player, position, adp
        teams: List of Team objects with rosters
        roger_slot: Optional Roger slot to focus analysis on
    
    Returns:
        Dict with worst_team_id, regret_analysis, total_regret
    """
    pos_lookup = load_player_positions()
    
    # Calculate scores for all teams
    team_scores = {}
    for i, team in enumerate(teams):
        team_id = team.team_id
        roster = team.roster
        
        # Sum projected points
        total_proj = 0
        for player in roster:
            pos = pos_lookup.get(player.name, 'WR')
            pts = proj_pts(player.adp, pos)
            total_proj += pts
        
        # Calculate penalty
        counts = {'QB': 0, 'RB': 0, 'WR': 0, 'TE': 0}
        for player in roster:
            pos = pos_lookup.get(player.name, 'WR')
            if pos in counts:
                counts[pos] += 1
        
        # Roster penalty
        penalty = 0
        for pos, target in ROSTER_TARGETS.items():
            over = max(0, counts.get(pos, 0) - target - 2)
            penalty -= over ** 2 * 20
        
        team_scores[team_id] = {
            'total_proj': total_proj,
            'penalty': penalty,
            'score': total_proj + penalty,
            'counts': counts
        }
    
    # Find worst team
    worst_team_id = min(team_scores.keys(), key=lambda t: team_scores[t]['score'])
    
    # Get that team's picks
    team_picks = [p for p in draft_log if p['team'] == worst_team_id]
    team_picks.sort(key=lambda x: x['pick'])
    
    # For each pick, find regret
    regret_analysis = []
    cumulative_regret = 0
    
    for pick_idx, pick in enumerate(team_picks):
        pick_num = pick['pick']
        drafted_name = pick['player']
        drafted_adp = pick.get('adp', 100)
        
        # Get drafted player's VORP
        drafted_pos = pos_lookup.get(drafted_name, 'WR')
        drafted_vorp = calculate_vorp_for_player(drafted_name, drafted_adp, drafted_pos)
        
        # Find all players drafted AFTER this pick (by any team)
        later_picks = [p for p in draft_log if p['pick'] > pick_num]
        
        # Find best opportunity missed
        best_missed = None
        best_missed_vorp = -float('inf')
        
        for later_pick in later_picks:
            later_name = later_pick['player']
            later_adp = later_pick.get('adp', 100)
            later_pos = pos_lookup.get(later_name, 'WR')
            later_vorp = calculate_vorp_for_player(later_name, later_adp, later_pos)
            
            if later_vorp > best_missed_vorp:
                best_missed_vorp = later_vorp
                best_missed = {
                    'name': later_name,
                    'pick': later_pick['pick'],
                    'vorp': later_vorp,
                    'position': later_pos,
                    'adp': later_adp
                }
        
        # Calculate regret
        regret = max(0, best_missed_vorp - drafted_vorp) if best_missed else 0
        cumulative_regret += regret
        
        regret_analysis.append({
            'pick_num': pick_num,
            'drafted': {
                'name': drafted_name,
                'position': drafted_pos,
                'adp': drafted_adp,
                'vorp': drafted_vorp
            },
            'missed': best_missed,
            'regret': regret,
            'cumulative_regret': cumulative_regret
        })
    
    return {
        'worst_team_id': worst_team_id,
        'worst_score': team_scores[worst_team_id]['score'],
        'regret_analysis': regret_analysis,
        'total_regret': cumulative_regret,
        'all_team_scores': team_scores
    }


def generate_autopsy_report(draft_log: List[Dict], teams: List, roger_slot: int = None) -> str:
    """Generate a human-readable autopsy report"""
    
    analysis = analyze_draft_regret(draft_log, teams, roger_slot)
    
    lines = []
    lines.append("=" * 70)
    lines.append("DRAFT AUTOPSY REPORT")
    lines.append("=" * 70)
    lines.append("")
    lines.append(f"Worst Team: {analysis['worst_team_id']}")
    lines.append(f"Team Score: {analysis['worst_score']:.1f}")
    lines.append(f"Total Draft Regret: {analysis['total_regret']:.1f}")
    lines.append("")
    lines.append("-" * 70)
    lines.append(f"{'Pick':<6} {'Drafted':<22} {'VORP':>6} {'Better Alternative':<22} {'VORP':>6} {'Regret':>8}")
    lines.append("-" * 70)
    
    for item in analysis['regret_analysis']:
        pick = item['pick_num']
        drafted = item['drafted']
        missed = item['missed']
        regret = item['regret']
        
        drafted_str = f"{drafted['name'][:20]:<20} ({drafted['position']})"
        drafted_vorp_str = f"{drafted['vorp']:>6.1f}"
        
        if missed:
            missed_str = f"{missed['name'][:20]:<20} (P{missed['pick']})"
            missed_vorp_str = f"{missed['vorp']:>6.1f}"
        else:
            missed_str = "None available"
            missed_vorp_str = "------"
        
        regret_str = f"{regret:>8.1f}"
        
        lines.append(f"{pick:<6} {drafted_str} {drafted_vorp_str:>6} {missed_str} {missed_vorp_str:>6} {regret_str}")
    
    lines.append("-" * 70)
    lines.append(f"{'Cumulative Regret:':<50} {analysis['total_regret']:>8.1f}")
    lines.append("")
    
    # Top 3 regrets
    sorted_regrets = sorted(analysis['regret_analysis'], key=lambda x: -x['regret'])[:3]
    lines.append("TOP 3 BIGGEST MISTAKES:")
    for i, item in enumerate(sorted_regrets):
        if item['regret'] > 0:
            lines.append(f"  {i+1}. Pick {item['pick_num']}: Drafted {item['drafted']['name']} ({item['drafted']['vorp']:.1f})")
            lines.append(f"      Missed {item['missed']['name']} at pick {item['missed']['pick']} ({item['missed']['vorp']:.1f})")
            lines.append(f"      Regret: {item['regret']:.1f}")
    
    return "\n".join(lines)


def run_test_draft():
    """Run a test draft and analyze it"""
    print("Running test draft...")
    
    env = DraftEnv()
    state = env.reset(roger_slot=5)
    
    # Run draft with bot picks
    while True:
        t = env.teams[env.current_team_idx]
        action = env.bot_pick()
        state, reward, done, info = env.step(action)
        if done:
            break
    
    # Generate autopsy report
    print("\n" + generate_autopsy_report(env.draft_log, env.teams))
    
    return env


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Hindsight Critic for Draft Analysis')
    parser.add_argument('--draft-log', type=str, help='Path to draft log JSON')
    parser.add_argument('--test', action='store_true', help='Run test draft')
    
    args = parser.parse_args()
    
    if args.test or (not args.draft_log):
        run_test_draft()
    else:
        # Load and analyze provided draft
        with open(args.draft_log, 'r') as f:
            draft_log = json.load(f)
        
        # Would need teams too - this is a placeholder
        print("Draft log analysis not yet implemented without teams")
