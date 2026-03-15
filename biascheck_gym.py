"""BiasCheckGym - Challenging assumptions"""

import gymnasium as gym
from gymnasium import spaces
import numpy as np

class BiasCheckGym(gym.Env):
    metadata = {'render_modes': ['human']}
    
    def __init__(self):
        self.observation_space = spaces.Box(low=0, high=1, shape=(1,), dtype=np.float32)
        self.action_space = spaces.Discrete(4)
        self.action_names = ["challenge_assumption", "seek_contrary", "verify_source", "accept"]
        
    def reset(self, seed=None, options=None):
        self.metacog = np.random.uniform(0.3, 0.95)
        return np.array([self.metacog], dtype=np.float32), {}
    
    def step(self, action):
        reward = 0.0
        if action == 0:  # challenge_assumption
            reward = (1 - self.metacog) * 0.5
        elif action == 1:  # seek_contrary
            reward = 0.3
        elif action == 2:  # verify_source
            reward = 0.4
        elif action == 3:  # accept
            reward = self.metacog * 0.2
        
        done = True
        return np.array([self.metacog], dtype=np.float32), reward, done, False, {"action": self.action_names[action]}

if __name__ == '__main__':
    env = BiasCheckGym()
    for i in range(5):
        obs, _ = env.reset()
        action = env.action_space.sample()
        obs, reward, _, _, info = env.step(action)
        print(f"Metacog: {obs[0]:.2f} | Action: {info['action']} | Reward: {reward:.2f}")
