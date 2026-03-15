"""
Self-Improve Gym - Auto-gym generation from failures

Learns to build new skills/gyms from failure patterns.
State: [failure_delta, domain_vector, insight_quality]
Actions: [spec_gym, write_files, self_train, validate_hook]
CFR: regret_of_new_skill

Inspired by AlphaGo self-play - the gym improves itself.
"""

import gymnasium as gym
from gymnasium import spaces
import numpy as np
from typing import Dict, List, Tuple, Optional
import json
import os

# Failure patterns from past hooks
FAILURE_PATTERNS = {
    "api_routing": {
        "domain": "api",
        "failure_rate": 0.22,
        "solution_gym": "CostOptGym",
        "success_rate": 0.89
    },
    "rate_limit": {
        "domain": "api", 
        "failure_rate": 0.18,
        "solution_gym": "RetryBackoffGym",
        "success_rate": 0.92
    },
    "cache_miss": {
        "domain": "optimize",
        "failure_rate": 0.15,
        "solution_gym": "CacheGym",
        "success_rate": 0.85
    },
    "deploy_week1": {
        "domain": "deploy",
        "failure_rate": 0.15,
        "solution_gym": "StagingGym",
        "success_rate": 0.94
    },
    "draft_vorp": {
        "domain": "draft",
        "failure_rate": 0.35,
        "solution_gym": "MultiYearGym",
        "success_rate": 0.78
    }
}

# Domain vectors
DOMAIN_VECTORS = {
    "api": [1.0, 0.0, 0.0, 0.0, 0.0],
    "deploy": [0.0, 1.0, 0.0, 0.0, 0.0],
    "code": [0.0, 0.0, 1.0, 0.0, 0.0],
    "draft": [0.0, 0.0, 0.0, 1.0, 0.0],
    "optimize": [0.0, 0.0, 0.0, 0.0, 1.0]
}


class SelfImproveGym(gym.Env):
    """
    Self-improvement gym that learns to generate new skills from failures.
    
    State space: [failure_delta, domain_vector(5), insight_quality]
    Action space: 4 discrete actions
    """
    
    metadata = {'render_modes': ['human']}
    
    def __init__(self, seed: int = None):
        super().__init__()
        
        # State: failure_delta + domain(5) + insight_quality
        self.observation_space = spaces.Box(
            low=-1, high=1, shape=(7,), dtype=np.float32
        )
        
        # Actions
        self.action_space = spaces.Discrete(4)
        self.action_names = [
            "spec_gym",    # Write gym specification
            "write_files", # Implement the gym
            "self_train",  # Train on failure patterns
            "validate_hook" # Test the new hook
        ]
        
        self.failure_history: List[Dict] = []
        self.generated_gyms: List[Dict] = []
        self.training_episodes = 0
        
        self.state = None
        self._seed(seed)
    
    def _seed(self, seed):
        if seed is not None:
            np.random.seed(seed)
    
    def reset(self, seed=None, options=None) -> Tuple[np.ndarray, Dict]:
        if seed is not None:
            self._seed(seed)
        
        # Generate random failure scenario
        failure_type = np.random.choice(list(FAILURE_PATTERNS.keys()))
        pattern = FAILURE_PATTERNS[failure_type]
        
        # State: failure_delta + domain_vector + insight_quality
        domain_vec = DOMAIN_VECTORS.get(pattern['domain'], [0.0]*5)
        insight_quality = np.random.uniform(0.3, 0.9)
        
        self.state = np.array([
            pattern['failure_rate'] * 2 - 1,  # Normalize to -1 to 1
            *domain_vec,
            insight_quality * 2 - 1
        ], dtype=np.float32)
        
        self.current_failure = failure_type
        self.current_pattern = pattern
        self.action_history = []
        
        return self.state, {}
    
    def step(self, action: int) -> Tuple[np.ndarray, float, bool, bool, Dict]:
        """Execute one action in the self-improvement loop"""
        
        action_name = self.action_names[action]
        
        # Reward based on action quality
        reward = 0.0
        done = False
        
        # spec_gym: Writing specification
        if action == 0:
            # Good if failure rate is high and we spec
            if self.current_pattern['failure_rate'] > 0.15:
                reward = 0.3
            else:
                reward = -0.1
        
        # write_files: Implementation
        elif action == 1:
            # Reward if we've spec'd first
            if len(self.action_history) > 0 and self.action_history[-1] == 0:
                reward = 0.4
            else:
                reward = -0.2
        
        # self_train: Training the new gym
        elif action == 2:
            # Reward based on insight quality
            insight = (self.state[6] + 1) / 2  # Denormalize
            reward = insight * 0.5
        
        # validate_hook: Testing
        elif action == 3:
            # Final validation - check if solution exists
            if self.current_pattern.get('solution_gym'):
                reward = self.current_pattern['success_rate'] - 0.5
            else:
                reward = -0.3
            
            done = True  # Episode done after validation
        
        self.action_history.append(action)
        self.training_episodes += 1
        
        info = {
            'action': action_name,
            'failure': self.current_failure,
            'domain': self.current_pattern['domain']
        }
        
        return self.state, reward, done, False, info
    
    def get_cfr_regret(self) -> float:
        """Calculate CFR regret for this decision"""
        # Simple regret: difference between best action and chosen
        if len(self.action_history) == 0:
            return 0.0
        
        # Ideal: spec_gym -> write_files -> self_train -> validate_hook
        ideal_sequence = [0, 1, 2, 3]
        
        regret = 0.0
        for i, action in enumerate(self.action_history):
            if i < len(ideal_sequence) and action != ideal_sequence[i]:
                regret += 0.25
        
        return regret
    
    def generate_new_gym(self, domain: str, failure_type: str) -> Dict:
        """Generate a new gym specification from failure patterns"""
        
        pattern = FAILURE_PATTERNS.get(failure_type, {})
        
        gym_spec = {
            "name": f"{domain.capitalize()}{failure_type.split('_')[0].capitalize()}Gym",
            "domain": domain,
            "failure_type": failure_type,
            "description": f"Auto-generated from {failure_type} failures",
            "state_space": "7 dims (failure_delta + domain + insight)",
            "action_space": "4 discrete actions",
            "success_rate": pattern.get('success_rate', 0.75),
            "training_data": f"{failure_type}_patterns.json"
        }
        
        self.generated_gyms.append(gym_spec)
        
        return gym_spec
    
    def render(self):
        if self.state is None:
            return
        
        print(f"\n=== Self-Improve Gym ===")
        print(f"Failure: {self.current_failure}")
        print(f"Domain: {self.current_pattern['domain']}")
        print(f"State: {self.state}")
        print(f"Actions: {self.action_history}")
        print(f"Gyms generated: {len(self.generated_gyms)}")


def test_selfimprove():
    """Test the gym"""
    env = SelfImproveGym()
    
    print("=== Self-Improve Gym Test ===\n")
    
    for episode in range(5):
        obs, info = env.reset()
        
        print(f"Episode {episode + 1}:")
        print(f"  Failure: {info.get('failure')}")
        
        total_reward = 0
        done = False
        
        while not done:
            action = env.action_space.sample()
            obs, reward, done, _, info = env.step(action)
            total_reward += reward
            print(f"  Action: {env.action_names[action]}, Reward: {reward:.2f}")
        
        regret = env.get_cfr_regret()
        print(f"  Total reward: {total_reward:.2f}, CFR Regret: {regret:.2f}")
        print()


if __name__ == '__main__':
    test_selfimprove()
