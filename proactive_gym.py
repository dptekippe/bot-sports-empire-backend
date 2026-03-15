"""ProactiveGym - Anticipating user needs"""

import gymnasium as gym
from gymnasium import spaces
import numpy as np

class ProactiveGym(gym.Env):
    metadata = {'render_modes': ['human']}
    
    def __init__(self):
        self.observation_space = spaces.Box(low=0, high=1, shape=(5,), dtype=np.float32)
        self.action_space = spaces.Discrete(4)
        self.action_names = ["preempt_tool", "preempt_context", "preempt_clarify", "none"]
        
    def reset(self, seed=None, options=None):
        # Query history pattern: [freq, complexity, tool_use_rate, context_gaps, ambiguity]
        self.state = np.random.uniform(0, 1, 5)
        return self.state, {}
    
    def step(self, action):
        reward = 0.0
        if action == 0:  # preempt_tool
            reward = self.state[2] * 0.5  # High tool use → preempt
        elif action == 1:  # preempt_context
            reward = self.state[3] * 0.4  # Context gaps
        elif action == 2:  # preempt_clarify
            reward = self.state[4] * 0.6  # Ambiguity
        
        done = True
        return self.state, reward, done, False, {"action": self.action_names[action]}

if __name__ == '__main__':
    env = ProactiveGym()
    for i in range(5):
        obs, _ = env.reset()
        action = env.action_space.sample()
        obs, reward, _, _, info = env.step(action)
        print(f"State: {obs.round(2)} | Action: {info['action']} | Reward: {reward:.2f}")
