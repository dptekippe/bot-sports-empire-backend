"""
Actual Points CFR Analysis

Compare ADP-based drafting to ACTUAL 2025 fantasy points.
This creates meaningful variance for RL training.

Key insight:
- Draft-time: Use ADP/VORP (blind preseason)
- Terminal reward: Use ACTUAL 2025 pts (post-mortem truth)
- CFR regret: Use actual pts to find missed opportunities
"""

import json
import random
from typing import Dict, List
from draft_env import DraftEnv
from rl_reward import proj_pts, vorp, need_score, final_score, ROSTER_TARGETS


def load_actual_pts() -> Dict[str, float]:
    """Load actual 2025 fantasy points"""
    with open('fantasy_points_2025.json') as f:
        return {p['name']: p.get('fpts_ppr', 0) for p in json.load(f)}


def load_positions() -> Dict[str, str]:
    """Load player positions"""
    with open('fantasy_points_2025.json') as f:
        return {p['name']: p.get('position', 'WR') for p in json.load(f)}


def calculate_cfr_regret_actual(
    draft_log: List[Dict], 
    team_id: int,
    actual_pts: Dict[str, float],
    pos_lookup: Dict[str, str]
) -> float:
    """
    Calculate CFR regret using ACTUAL points.
    
    This measures: "Could I have drafted a better player at the 
    same position who actually performed better in 2025?"
    
    Args:
        draft_log: All picks in draft
        team_id: Team to analyze
        actual_pts: Actual 2025 fantasy points
        pos_lookup: Player positions
    
    Returns:
        Total regret (in actual points)
    """
    team_picks = [p for p in draft_log if p.get('team') == team_id]
    team_picks.sort(key=lambda x: x.get('pick', 0))
    
    total_regret = 0
    
    for pick in team_picks:
        pick_num = pick.get('pick', 0)
        drafted_name = pick.get('player', '')
        
        drafted_actual = actual_pts.get(drafted_name, 0)
        
        # Find later picks
        later_picks = [p for p in draft_log if p.get('pick', 0) > pick_num]
        
        # Same position only
        drafted_pos = pos_lookup.get(drafted_name, 'WR')
        same_pos_later = []
        
        for later in later_picks:
            later_name = later.get('player', '')
            later_pos = pos_lookup.get(later_name, 'WR')
            
            if later_pos == drafted_pos:
                later_actual = actual_pts.get(later_name, 0)
                same_pos_later.append(later_actual)
        
        if same_pos_later:
            best_later = max(same_pos_later)
            regret = max(0, best_later - drafted_actual)
            total_regret += regret
    
    return total_regret


def run_adp_baseline(n_slots: int = 10) -> Dict:
    """
    Run ADP-based drafting from multiple slots.
    
    Returns:
        Dict with actual_pts, projected_pts, regret per slot
    """
    actual_pts = load_actual_pts()
    pos_lookup = load_positions()
    
    results = []
    
    for slot in range(1, n_slots + 1):
        env = DraftEnv()
        env.reset(roger_slot=slot)
        
        # Run ADP draft
        while True:
            t = env.teams[env.current_team_idx]
            action = env.bot_pick()
            state, reward, done, info = env.step(action)
            if done:
                break
        
        team = env.teams[slot - 1]
        
        # Calculate actual points
        actual_total = sum(actual_pts.get(p.name, 0) for p in team.roster)
        
        # Calculate projected (ADP-based) points
        proj_total = 0
        for p in team.roster:
            pos = pos_lookup.get(p.name, 'WR')
            proj_total += proj_pts(p.adp, pos)
        
        # Calculate CFR regret using actual points
        regret = calculate_cfr_regret_actual(
            env.draft_log, slot, actual_pts, pos_lookup
        )
        
        results.append({
            'slot': slot,
            'actual': actual_total,
            'projected': proj_total,
            'regret': regret
        })
    
    return results


def main():
    print("="*60)
    print("ACTUAL POINTS CFR ANALYSIS")
    print("="*60)
    print("\nADP Drafting → Scored on ACTUAL 2025 Fantasy Points\n")
    
    results = run_adp_baseline(10)
    
    # Print results
    print(f"{'Slot':<6} {'Actual':>8} {'Projected':>10} {'Regret':>8}")
    print("-"*40)
    
    for r in results:
        print(f"{r['slot']:<6} {r['actual']:>8.0f} {r['projected']:>10.0f} {r['regret']:>8.0f}")
    
    # Summary
    avg_actual = sum(r['actual'] for r in results) / len(results)
    avg_proj = sum(r['projected'] for r in results) / len(results)
    avg_regret = sum(r['regret'] for r in results) / len(results)
    
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    print(f"Avg Actual Points:    {avg_actual:.0f}")
    print(f"Avg Projected (ADP): {avg_proj:.0f}")
    print(f"Avg CFR Regret:      {avg_regret:.0f}")
    print(f"\nGap: {avg_actual - avg_proj:+.0f} points")
    print("\n→ RL can learn to minimize this regret!")
    
    return results


if __name__ == '__main__':
    main()
