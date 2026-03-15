"""QuestionGym - Probing weak points in reasoning"""

import gymnasium as gym
from gymnasium import spaces
import numpy as np
from typing import Tuple

class QuestionGym(gym.Env):
    metadata = {'render_modes': ['human']}
    
    def __init__(self):
        self.observation_space = spaces.Box(low=0, high=1, shape=(1,), dtype=np.float32)
        self.action_space = spaces.Discrete(3)
        self.action_names = ["probe_assumption", "probe_evidence", "probe_alternative"]
        
    def reset(self, seed=None, options=None):
        self.conf_score = np.random.uniform(0.3, 0.95)
        return np.array([self.conf_score], dtype=np.float32), {}
    
    def step(self, action):
        reward = 0.0
        if action == 0:  # probe_assumption
            reward = self.conf_score * 0.3
        elif action == 1:  # probe_evidence
            reward = self.conf_score * 0.4
        elif action == 2:  # probe_alternative
            reward = (1 - self.conf_score) * 0.5
        
        done = True
        return np.array([self.conf_score], dtype=np.float32), reward, done, False, {"action": self.action_names[action]}

if __name__ == '__main__':
    env = QuestionGym()
    for i in range(5):
        obs, _ = env.reset()
        action = env.action_space.sample()
        obs, reward, _, _, info = env.step(action)
        print(f"Conf: {obs[0]:.2f} | Action: {info['action']} | Reward: {reward:.2f}")
