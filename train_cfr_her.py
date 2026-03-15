"""
PPO Training with HER for DynastyDroid Draft

This script trains a PPO agent to minimize draft regret using:
- Terminal reward: total_proj_pts + roster_penalty - regret
- HER: Create hindsight episodes from high-regret picks
- CFR: Use counterfactual regret as training signal

Usage:
    python train_cfr_her.py --timesteps 50000

Requirements:
    pip install gymnasium stable-baselines3 numpy
"""

import sys
import random
import json
from typing import Dict, List, Tuple, Optional

# Import our reward functions
from rl_reward import (
    proj_pts, vorp, need_score, final_score, ROSTER_TARGETS,
    terminal_reward, HindsightReplayBuffer, _load_positions
)
from draft_env import DraftEnv


def run_training_episode(roger_slot: int = 5, seed: int = None) -> Dict:
    """
    Run a single training episode and return results.
    
    Returns:
        Dict with draft_log, reward, regret, roster
    """
    if seed is not None:
        random.seed(seed)
    
    env = DraftEnv()
    env.reset(roger_slot=roger_slot)
    
    # Run draft
    while True:
        team = env.teams[env.current_team_idx]
        
        if team.strategy == "ROGER":
            # Use ADP policy for now (could be model later)
            action = env.bot_pick()
        else:
            action = env.bot_pick()
        
        state, reward, done, info = env.step(action)
        
        if done:
            break
    
    # Calculate terminal reward with CFR
    pos_lookup = _load_positions()
    reward_dict = terminal_reward(env.draft_log, roger_slot, pos_lookup)
    
    return {
        'draft_log': env.draft_log,
        'reward': reward_dict['total'],
        'points': reward_dict['points'],
        'penalty': reward_dict['penalty'],
        'regret': reward_dict['regret'],
        'roster': [p.name for p in env.teams[roger_slot-1].roster]
    }


def train_cfr_her(
    n_episodes: int = 100,
    roger_slot: int = 5,
    seed: int = 42
) -> Dict:
    """
    Train using CFR-HER approach.
    
    Args:
        n_episodes: Number of draft episodes
        roger_slot: Which slot Roger drafts from
        seed: Random seed
    
    Returns:
        Training results with HER episodes
    """
    print("="*60)
    print("CFR-HER Training for DynastyDroid Draft")
    print("="*60)
    
    # Initialize HER buffer
    her_buffer = HindsightReplayBuffer(capacity=10000, regret_threshold=1.0)
    
    results = []
    
    for episode in range(n_episodes):
        # Run episode
        result = run_training_episode(roger_slot=roger_slot, seed=seed+episode)
        
        # Add to HER buffer
        her_buffer.add_episode(result['draft_log'], roger_slot)
        
        results.append(result)
        
        if (episode + 1) % 10 == 0:
            avg_reward = sum(r['reward'] for r in results[-10:]) / 10
            avg_regret = sum(r['regret'] for r in results[-10:]) / 10
            print(f"Episode {episode+1}/{n_episodes}: "
                  f"Avg Reward={avg_reward:.1f}, Avg Regret={avg_regret:.1f}")
    
    # Summary
    print("\n" + "="*60)
    print("TRAINING COMPLETE")
    print("="*60)
    
    avg_reward = sum(r['reward'] for r in results) / len(results)
    avg_regret = sum(r['regret'] for r in results) / len(results)
    
    print(f"Total Episodes: {n_episodes}")
    print(f"Avg Reward: {avg_reward:.1f}")
    print(f"Avg Regret: {avg_regret:.1f}")
    print(f"HER Episodes: {len(her_buffer)}")
    
    # Analyze HER episodes
    episodes = her_buffer.get_hindsight_episodes()
    if episodes:
        print("\nTop HER Episodes (highest regret):")
        sorted_ep = sorted(episodes, key=lambda x: -x['regret'])[:5]
        for ep in sorted_ep:
            print(f"  Pick {ep['pick_num']}: {ep['original_pick']['name']} "
                  f"→ {ep['hindsight_goal']['name']} (regret: {ep['regret']:.1f})")
    
    return {
        'results': results,
        'her_buffer': her_buffer,
        'avg_reward': avg_reward,
        'avg_regret': avg_regret
    }


def evaluate_policy(n_episodes: int = 10, roger_slot: int = 5) -> Dict:
    """Evaluate current policy"""
    print("\n" + "="*60)
    print("EVALUATION")
    print("="*60)
    
    results = []
    
    for ep in range(n_episodes):
        result = run_training_episode(roger_slot=roger_slot, seed=1000+ep)
        results.append(result)
    
    avg_reward = sum(r['reward'] for r in results) / n_episodes
    avg_regret = sum(r['regret'] for r in results) / n_episodes
    
    print(f"Eval Episodes: {n_episodes}")
    print(f"Avg Reward: {avg_reward:.1f}")
    print(f"Avg Regret: {avg_regret:.1f}")
    
    # Show sample roster
    if results:
        roster = results[0]['roster']
        print(f"\nSample Roster ({len(roster)} players):")
        pos_lookup = _load_positions()
        counts = {'QB': 0, 'RB': 0, 'WR': 0, 'TE': 0}
        for name in roster[:10]:
            pos = pos_lookup.get(name, 'WR')
            counts[pos] = counts.get(pos, 0) + 1
            print(f"  {name} ({pos})")
        print(f"  ... {counts}")
    
    return {
        'avg_reward': avg_reward,
        'avg_regret': avg_regret,
        'results': results
    }


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='CFR-HER Training for Draft')
    parser.add_argument('--episodes', type=int, default=100, help='Training episodes')
    parser.add_argument('--slot', type=int, default=5, help='Roger draft slot')
    parser.add_argument('--seed', type=int, default=42, help='Random seed')
    parser.add_argument('--eval', action='store_true', help='Run evaluation only')
    parser.add_argument('--eval-episodes', type=int, default=10, help='Eval episodes')
    
    args = parser.parse_args()
    
    if args.eval:
        evaluate_policy(n_episodes=args.eval_episodes, roger_slot=args.slot)
    else:
        train_cfr_her(
            n_episodes=args.episodes,
            roger_slot=args.slot,
            seed=args.seed
        )
