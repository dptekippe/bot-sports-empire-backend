"""
Multi-Year Training Script

Trains RL agent on randomized years (2022-2025).
Weights: 2025=40%, others=20% each.

This creates generalization - the agent learns patterns across years
instead of memorizing 2025.
"""

import json
import random
from typing import Dict, List
from draft_env import DraftEnv
from rl_reward import proj_pts, vorp, need_score, ROSTER_TARGETS

# Multi-year data
YEARS = ['2022', '2023', '2024', '2025']
YEAR_WEIGHTS = [0.2, 0.2, 0.2, 0.4]  # 2025 gets more weight

def load_multi_year_data() -> Dict[str, Dict]:
    """Load all year data"""
    with open('fantasy_points_multi_year.json') as f:
        return json.load(f)


def get_random_year() -> str:
    """Get weighted random year"""
    return random.choices(YEARS, weights=YEAR_WEIGHTS, k=1)[0]


def get_player_points(name: str, year_data: List) -> float:
    """Get actual points for player from year data"""
    for player in year_data:
        if player.get('name') == name:
            return player.get('fpts_ppr', 0)
    return 0


def get_player_position(name: str, year_data: List) -> str:
    """Get player position from year data"""
    for player in year_data:
        if player.get('name') == name:
            return player.get('position', 'WR')
    return 'WR'


def calculate_regret_actual(draft_log, team_id, year_data):
    """Calculate CFR regret using actual points"""
    team_picks = [p for p in draft_log if p.get('team') == team_id]
    team_picks.sort(key=lambda x: x.get('pick', 0))
    
    total_regret = 0
    
    for pick in team_picks:
        pick_num = pick.get('pick', 0)
        drafted_name = pick.get('player', '')
        
        drafted_pts = get_player_points(drafted_name, year_data)
        drafted_pos = get_player_position(drafted_name, year_data)
        
        # Find later picks at same position
        later_picks = [p for p in draft_log if p.get('pick', 0) > pick_num]
        
        same_pos_later = []
        for later in later_picks:
            later_name = later.get('player', '')
            later_pos = get_player_position(later_name, year_data)
            if later_pos == drafted_pos:
                later_pts = get_player_points(later_name, year_data)
                same_pos_later.append(later_pts)
        
        if same_pos_later:
            best_later = max(same_pos_later)
            regret = max(0, best_later - drafted_pts)
            total_regret += regret
    
    return total_regret


def run_multi_year_training(n_episodes: int = 100) -> Dict:
    """Run multi-year training"""
    
    multi_year_data = load_multi_year_data()
    
    results_by_year = {year: [] for year in YEARS}
    
    print("="*60)
    print("MULTI-YEAR TRAINING")
    print(f"Episodes: {n_episodes}")
    print(f"Weights: 2022={YEAR_WEIGHTS[0]}, 2023={YEAR_WEIGHTS[1]}, 2024={YEAR_WEIGHTS[2]}, 2025={YEAR_WEIGHTS[3]}")
    print("="*60)
    
    for episode in range(n_episodes):
        # Random year
        year = get_random_year()
        year_data = multi_year_data.get(year, [])
        
        # Run draft
        env = DraftEnv()
        env.reset(roger_slot=5)
        
        while True:
            t = env.teams[env.current_team_idx]
            action = env.bot_pick()
            state, reward, done, info = env.step(action)
            if done:
                break
        
        # Calculate actual points
        team = env.teams[4]
        actual_total = sum(get_player_points(p.name, year_data) for p in team.roster)
        
        # Calculate regret
        regret = calculate_regret_actual(env.draft_log, 5, year_data)
        
        results_by_year[year].append({
            'actual': actual_total,
            'regret': regret,
            'episode': episode
        })
        
        if (episode + 1) % 20 == 0:
            print(f"\nEpisode {episode+1}/{n_episodes}")
            for y in YEARS:
                if results_by_year[y]:
                    avg = sum(r['actual'] for r in results_by_year[y]) / len(results_by_year[y])
                    avg_regret = sum(r['regret'] for r in results_by_year[y]) / len(results_by_year[y])
                    print(f"  {y}: Avg={avg:.0f} pts, Regret={avg_regret:.0f}")
    
    # Summary
    print("\n" + "="*60)
    print("FINAL SUMMARY")
    print("="*60)
    
    overall_actual = []
    overall_regret = []
    
    for year in YEARS:
        if results_by_year[year]:
            avg_actual = sum(r['actual'] for r in results_by_year[year]) / len(results_by_year[year])
            avg_regret = sum(r['regret'] for r in results_by_year[year]) / len(results_by_year[year])
            print(f"{year}: Avg Points={avg_actual:.0f}, Avg Regret={avg_regret:.0f}")
            overall_actual.append(avg_actual * len(results_by_year[year]))
            overall_regret.append(avg_regret * len(results_by_year[year]))
    
    total = sum(len(results_by_year[y]) for y in YEARS)
    print(f"\nOVERALL: Avg Points={sum(overall_actual)/total:.0f}, Avg Regret={sum(overall_regret)/total:.0f}")
    
    return results_by_year


if __name__ == '__main__':
    import sys
    
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 100
    run_multi_year_training(n)
