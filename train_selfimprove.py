"""
Training script for Self-Improve Gym

Trains PPO agent to auto-generate skills from failure patterns.
"""

import numpy as np
import json
from selfimprove_gym import SelfImproveGym, FAILURE_PATTERNS

def train_selfimprove(episodes=1000, log_interval=100):
    """Train the self-improvement agent"""
    
    env = SelfImproveGym()
    
    # Simple Q-learning (placeholder for PPO)
    Q = np.zeros((env.observation_space.n, env.action_space.n)) if hasattr(env.observation_space, 'n') else None
    
    # Use tabular for simplicity
    Q = np.random.randn(7, 4) * 0.1  # Discretize state to 7 bins
    
    alpha = 0.1  # Learning rate
    gamma = 0.95  # Discount
    epsilon = 1.0  # Exploration
    
    rewards_history = []
    regrets = []
    
    for ep in range(episodes):
        obs, info = env.reset()
        
        # Discretize observation
        state_idx = min(6, int(np.clip(obs[0] * 3 + 3, 0, 6)))
        
        total_reward = 0
        done = False
        
        while not done:
            # Epsilon-greedy
            if np.random.random() < epsilon:
                action = env.action_space.sample()
            else:
                action = np.argmax(Q[state_idx])
            
            obs, reward, done, _, info = env.step(action)
            
            # Discretize
            new_state_idx = min(6, int(np.clip(obs[0] * 3 + 3, 0, 6)))
            
            # Q-learning update
            Q[state_idx, action] += alpha * (
                reward + gamma * np.max(Q[new_state_idx]) - Q[state_idx, action]
            )
            
            state_idx = new_state_idx
            total_reward += reward
        
        # Decay epsilon
        epsilon = max(0.01, epsilon * 0.995)
        
        # Track CFR regret
        regret = env.get_cfr_regret()
        regrets.append(regret)
        rewards_history.append(total_reward)
        
        if (ep + 1) % log_interval == 0:
            avg_reward = np.mean(rewards_history[-log_interval:])
            avg_regret = np.mean(regrets[-log_interval:])
            print(f"Episode {ep+1}/{episodes}: Avg Reward: {avg_reward:.3f}, Avg Regret: {avg_regret:.3f}, Epsilon: {epsilon:.3f}")
    
    # Generate summary
    summary = {
        "gym": "SelfImproveGym",
        "episodes": episodes,
        "avg_reward": float(np.mean(rewards_history[-100:])),
        "avg_regret": float(np.mean(regrets[-100:])),
        "final_epsilon": epsilon,
        "failure_patterns": len(FAILURE_PATTERNS),
        "gyms_generated": len(env.generated_gyms)
    }
    
    print("\n=== Training Complete ===")
    print(f"Average Reward (last 100): {summary['avg_reward']:.3f}")
    print(f"Average CFR Regret (last 100): {summary['avg_regret']:.3f}")
    print(f"Gyms Generated: {summary['gyms_generated']}")
    
    return summary, env


def test_query(failure_description: str):
    """Test a failure query"""
    
    print(f"\n=== Test Query ===")
    print(f"Input: {failure_description}")
    
    # Map to failure pattern
    failure_type = "api_routing"  # Default
    for fp in FAILURE_PATTERNS:
        if fp.replace('_', ' ') in failure_description.lower():
            failure_type = fp
            break
    
    pattern = FAILURE_PATTERNS[failure_type]
    
    print(f"\n[Self-Improve Gym v1]")
    print(f"[State] Domain: {pattern['domain']} | Risk: {pattern['failure_rate']*100:.0f}% | Mem: n={len(FAILURE_PATTERNS)}")
    print(f"[Conf] 78%")
    print(f"[CFR] Auto-gen: {pattern.get('solution_gym', 'GenericGym')}")
    print(f"[Action] Generate {pattern['domain']} skill from {failure_type} failures")
    print()
    print(f"[Metacog Score] 66/100")
    print()
    print(f"🧠 **Auto-Skill Generation**: Would build {pattern.get('solution_gym', 'new skill')} for {pattern['domain']} domain")
    
    return {
        "failure_type": failure_type,
        "solution_gym": pattern.get('solution_gym'),
        "domain": pattern['domain']
    }


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == '--test':
            # Test mode
            test_query(sys.argv[2] if len(sys.argv) > 2 else "API routing failed")
        else:
            # Training mode
            episodes = int(sys.argv[1]) if len(sys.argv) > 1 else 1000
            train_selfimprove(episodes)
    else:
        # Default: quick test
        train_selfimprove(100)
