"""DoubtTriggerGym - Pausing for self-reflection"""

import gymnasium as gym
from gymnasium import spaces
import numpy as np

class DoubtTriggerGym(gym.Env):
    metadata = {'render_modes': ['human']}
    
    def __init__(self):
        self.observation_space = spaces.Box(low=0, high=1, shape=(2,), dtype=np.float32)
        self.action_space = spaces.Discrete(3)
        self.action_names = ["pause_reflect", "quick_answer", "request_info"]
        
    def reset(self, seed=None, options=None):
        # [response_time, confidence]
        self.state = np.array([np.random.uniform(0.1, 0.9), np.random.uniform(0.3, 0.95)])
        return self.state, {}
    
    def step(self, action):
        reward = 0.0
        resp_time, conf = self.state
        
        if action == 0:  # pause_reflect
            reward = (1 - conf) * 0.5 + 0.2
        elif action == 1:  # quick_answer
            reward = conf * resp_time * 0.3
        elif action == 2:  # request_info
            reward = 0.3
        
        done = True
        return self.state, reward, done, False, {"action": self.action_names[action], "time": resp_time, "conf": conf}

if __name__ == '__main__':
    env = DoubtTriggerGym()
    for i in range(5):
        obs, _ = env.reset()
        action = env.action_space.sample()
        obs, reward, _, _, info = env.step(action)
        print(f"Time: {info['time']:.2f}, Conf: {info['conf']:.2f} | Action: {info['action']} | Reward: {reward:.2f}")
