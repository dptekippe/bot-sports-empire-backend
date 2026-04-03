#!/usr/bin/env python3
"""
RCT2 RL Environment - Minimal Gymnasium-style Interface

A minimal RL environment wrapper for OpenRCT2 that provides:
- State observation (park metrics, rides)
- Action execution (demolish, etc.)
- Reward signal (based on park metrics changes)

This is a proof-of-concept implementation focused on the demolish action.
"""

import socket
import json
import time
from typing import Dict, Any, Tuple, Optional, List


class RCT2Env:
    """
    Minimal RL environment for OpenRCT2.
    
    Currently supports:
    - Actions: demolish (remove a ride)
    - Observation: park metrics (rating, cash, guests) + ride list
    
    Example usage:
        env = RCT2Env()
        obs = env.reset()
        action = env.action_space.sample()  # demolish a random ride
        next_obs, reward, done, info = env.step(action)
    """
    
    def __init__(self, host: str = "localhost", port: int = 11752):
        self.host = host
        self.port = port
        self.socket: Optional[socket.socket] = None
        
        # Track state for reward calculation
        self._prev_park_rating = 0
        self._prev_park_cash = 0
        self._prev_park_guests = 0
        self._prev_num_rides = 0
        
        # Action space definition
        # Currently we only support demolish actions
        self.action_space = ActionSpace()
        
        # Observation space (simplified)
        self.observation_space = {
            "park_rating": (0, 1000),
            "park_cash": (-1000000, 10000000),
            "park_guests": (0, 100000),
            "num_rides": (0, 100),
        }
    
    def connect(self) -> bool:
        """Establish connection to the OpenRCT2 bridge."""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(10.0)
            self.socket.connect((self.host, self.port))
            print(f"[RCT2Env] Connected to {self.host}:{self.port}")
            return True
        except Exception as e:
            print(f"[RCT2Env] Connection failed: {e}")
            self.socket = None
            return False
    
    def disconnect(self):
        """Close connection."""
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
            self.socket = None
            print("[RCT2Env] Disconnected")
    
    def _send_action(self, action: str, **kwargs) -> Dict[str, Any]:
        """Send an action and get the response."""
        if not self.socket:
            raise RuntimeError("Not connected. Call connect() first.")
        
        msg = {"action": action}
        msg.update(kwargs)
        
        json_str = json.dumps(msg) + "\n"
        self.socket.sendall(json_str.encode('utf-8'))
        
        # Receive response
        response_data = b""
        while True:
            try:
                chunk = self.socket.recv(4096)
                if not chunk:
                    break
                response_data += chunk
                decoded = response_data.decode('utf-8')
                if '\n' in decoded:
                    response_str = decoded.split('\n')[0]
                    break
            except socket.timeout:
                break
        
        if response_data:
            return json.loads(response_data.decode('utf-8').strip())
        return {"status": "error", "message": "No response"}
    
    def _get_observation(self) -> Dict[str, Any]:
        """Get current state observation."""
        response = self._send_action("get_ride_info")
        
        if response.get("status") != "ok":
            return {
                "park_rating": 0,
                "park_cash": 0,
                "park_guests": 0,
                "num_rides": 0,
                "rides": []
            }
        
        rides = response.get("result", {}).get("rides", [])
        
        # TODO: Get actual park metrics from a special action or park object
        # For now, estimate from rides
        return {
            "park_rating": 600,  # Placeholder - would need get_park_info action
            "park_cash": 10000,  # Placeholder
            "park_guests": 100,  # Placeholder
            "num_rides": len(rides),
            "rides": rides
        }
    
    def reset(self) -> Dict[str, Any]:
        """
        Reset the environment and return initial observation.
        
        Returns:
            Initial observation dict
        """
        if not self.socket:
            if not self.connect():
                raise RuntimeError("Could not connect to OpenRCT2")
        
        obs = self._get_observation()
        
        # Store initial state for reward calculation
        self._prev_park_rating = obs["park_rating"]
        self._prev_park_cash = obs["park_cash"]
        self._prev_park_guests = obs["park_guests"]
        self._prev_num_rides = obs["num_rides"]
        
        return obs
    
    def step(self, action: Dict[str, Any]) -> Tuple[Dict[str, Any], float, bool, Dict[str, Any]]:
        """
        Execute an action and return (observation, reward, done, info).
        
        Args:
            action: Dict with 'type' and parameters (e.g., {"type": "demolish", "ride_id": 0})
            
        Returns:
            Tuple of (next_obs, reward, done, info)
        """
        action_type = action.get("type", "")
        result = {"success": False, "error": None}
        
        if action_type == "demolish":
            ride_id = action.get("ride_id")
            if ride_id is not None:
                response = self._send_action("ridedemolish", id=ride_id)
                result["success"] = response.get("status") == "ok"
                result["response"] = response
            else:
                result["error"] = "Missing ride_id"
        
        # Small delay to let game process
        time.sleep(0.1)
        
        # Get new observation
        obs = self._get_observation()
        
        # Calculate reward
        reward = self._calculate_reward(obs, result)
        
        # Update previous state
        self._prev_park_rating = obs["park_rating"]
        self._prev_park_cash = obs["park_cash"]
        self._prev_park_guests = obs["park_guests"]
        self._prev_num_rides = obs["num_rides"]
        
        # Done when no more rides to demolish
        done = obs["num_rides"] == 0
        
        info = {
            "action_result": result,
            "rides_remaining": obs["num_rides"]
        }
        
        return obs, reward, done, info
    
    def _calculate_reward(self, obs: Dict[str, Any], action_result: Dict[str, Any]) -> float:
        """
        Calculate reward based on state change and action result.
        
        Reward strategy:
        - +10 if demolish succeeded and ride count decreased
        - +5 if park rating increased
        - -1 if action failed
        - 0 otherwise
        """
        reward = 0.0
        
        if action_result.get("success"):
            # Check if ride count actually decreased
            if obs["num_rides"] < self._prev_num_rides:
                reward += 10.0  # Successful demolish
            else:
                reward += 1.0  # Action claimed success but no change
            
            # Bonus for positive park rating change
            if obs["park_rating"] > self._prev_park_rating:
                reward += 5.0 * (obs["park_rating"] - self._prev_park_rating) / 100.0
        else:
            reward -= 1.0  # Penalty for failed action
        
        return reward
    
    def close(self):
        """Clean up resources."""
        self.disconnect()


class ActionSpace:
    """
    Simple action space for RCT2 demolish actions.
    
    In a full implementation, this would support multiple action types.
    For now, it's focused on demolish.
    """
    
    def __init__(self):
        self.n = 1  # Number of action types
    
    def sample(self) -> Dict[str, Any]:
        """Return a random demolish action (will be configured with actual ride ID)."""
        return {"type": "demolish", "ride_id": 0}  # ride_id should be set by caller


def test_env():
    """Test the RCT2 environment."""
    print("="*60)
    print("RCT2 Environment Test")
    print("="*60)
    
    env = RCT2Env()
    
    # Connect
    if not env.connect():
        print("[FAIL] Could not connect to OpenRCT2")
        return
    
    try:
        # Reset and get initial observation
        print("\n[RESET] Getting initial observation...")
        obs = env.reset()
        print(f"[RESET] Initial observation: {obs}")
        
        if not obs["rides"]:
            print("\n[FAIL] No rides found in park")
            return
        
        # Try to demolish each ride
        rides = obs["rides"]
        print(f"\n[TEST] Found {len(rides)} rides to potentially demolish...")
        
        total_reward = 0
        for i, ride in enumerate(rides):
            ride_id = ride.get("id")
            print(f"\n[STEP {i+1}] Demolishing ride {ride_id}...")
            
            action = {"type": "demolish", "ride_id": ride_id}
            next_obs, reward, done, info = env.step(action)
            
            print(f"[STEP {i+1}] Reward: {reward}, Done: {done}")
            print(f"[STEP {i+1}] Info: {info}")
            
            total_reward += reward
            
            if done:
                print("[DONE] No more rides to demolish")
                break
        
        print(f"\n[RESULT] Total reward: {total_reward}")
        
    finally:
        env.close()
    
    print("\n" + "="*60)
    print("Environment test complete")
    print("="*60)


if __name__ == "__main__":
    test_env()