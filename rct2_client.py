#!/usr/bin/env python3
"""
RCT2 RL Environment - Python Client for OpenRCT2 Bridge

This module provides a Python client to connect to the OpenRCT2 JSON Action Bridge
(zmq_bridge.js) and execute actions like ridedemolish.

Protocol:
- TCP connection to localhost:11752
- Send: {"action": "action_name", "param1": value1, ...}\n
- Receive: {"status": "ok|error", "result": {...} or "error": ...}\n
"""

import socket
import json
import time
from typing import Dict, Any, Optional, List


class RCT2Client:
    """Python client for OpenRCT2 JSON Action Bridge."""
    
    def __init__(self, host: str = "localhost", port: int = 11752, timeout: float = 10.0):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.socket: Optional[socket.socket] = None
    
    def connect(self) -> bool:
        """Establish TCP connection to the bridge."""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(self.timeout)
            self.socket.connect((self.host, self.port))
            print(f"[RCT2Client] Connected to {self.host}:{self.port}")
            return True
        except Exception as e:
            print(f"[RCT2Client] Connection failed: {e}")
            self.socket = None
            return False
    
    def disconnect(self):
        """Close the TCP connection."""
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
            self.socket = None
            print("[RCT2Client] Disconnected")
    
    def send_action(self, action: str, **kwargs) -> Dict[str, Any]:
        """
        Send an action to the bridge and return the response.
        
        Args:
            action: The action name (e.g., "ridedemolish", "get_ride_info")
            **kwargs: Additional parameters for the action
            
        Returns:
            Response dict with status and result/error
        """
        if not self.socket:
            raise RuntimeError("Not connected. Call connect() first.")
        
        # Build the request message
        msg = {"action": action}
        msg.update(kwargs)
        
        # Send the message (newline-delimited JSON)
        json_str = json.dumps(msg) + "\n"
        self.socket.sendall(json_str.encode('utf-8'))
        print(f"[RCT2Client] Sent: {json_str.strip()}")
        
        # Receive the response
        response_data = b""
        while True:
            try:
                chunk = self.socket.recv(4096)
                if not chunk:
                    break
                response_data += chunk
                # Check if we have a complete JSON message
                decoded = response_data.decode('utf-8')
                if '\n' in decoded:
                    lines = decoded.split('\n')
                    response_data = lines[1].encode() if len(lines) > 1 else b""
                    response_str = lines[0]
                    break
            except socket.timeout:
                break
        
        if response_data:
            response_str = response_data.decode('utf-8').strip()
            if not response_str:
                return {"status": "error", "message": "Empty response"}
            response = json.loads(response_str)
            print(f"[RCT2Client] Received: {response}")
            return response
        else:
            return {"status": "error", "message": "No response received"}
    
    def get_ride_info(self) -> Dict[str, Any]:
        """Get information about all rides in the park."""
        return self.send_action("get_ride_info")
    
    def demolish_ride(self, ride_id: int) -> Dict[str, Any]:
        """
        Demolish a ride by its ID.
        
        Args:
            ride_id: The ID of the ride to demolish
            
        Returns:
            Response dict indicating success/failure
        """
        return self.send_action("ridedemolish", id=ride_id)
    
    def pause_toggle(self) -> Dict[str, Any]:
        """Toggle the pause state of the game."""
        return self.send_action("pausetoggle")
    
    def get_surface_height(self, x: int, y: int) -> Dict[str, Any]:
        """
        Get the surface height at a given tile coordinate.
        
        Args:
            x: Tile X coordinate
            y: Tile Y coordinate
        """
        return self.send_action("get_surface_height", x=x, y=y)
    
    def check_area_owned(self, x1: int, y1: int, x2: int, y2: int) -> Dict[str, Any]:
        """
        Check if an area is owned by the park.
        
        Args:
            x1, y1: First corner tile coordinates
            x2, y2: Second corner tile coordinates
        """
        return self.send_action("check_area_owned", x1=x1, y1=y1, x2=x2, y2=y2)


def test_basic_connection():
    """Test basic connectivity to the bridge."""
    print("\n" + "="*60)
    print("TEST: Basic Connection")
    print("="*60)
    
    client = RCT2Client()
    
    if not client.connect():
        print("[FAIL] Could not connect to bridge")
        return False
    
    print("[PASS] Connected successfully")
    client.disconnect()
    return True


def test_get_rides():
    """Test getting ride information."""
    print("\n" + "="*60)
    print("TEST: Get Ride Info")
    print("="*60)
    
    client = RCT2Client()
    
    if not client.connect():
        print("[FAIL] Could not connect to bridge")
        return False
    
    response = client.get_ride_info()
    
    if response.get("status") == "ok":
        rides = response.get("result", {}).get("rides", [])
        print(f"[PASS] Retrieved {len(rides)} rides")
        for ride in rides:
            print(f"  - Ride {ride.get('id')}: type={ride.get('type')}, "
                  f"classification={ride.get('classification')}, "
                  f"status={ride.get('status')}")
        return rides
    else:
        print(f"[FAIL] Failed to get rides: {response}")
        return []


def test_demolish_ride(ride_id: int):
    """
    Test demolishing a specific ride.
    
    Args:
        ride_id: The ID of the ride to demolish
    """
    print("\n" + "="*60)
    print(f"TEST: Demolish Ride {ride_id}")
    print("="*60)
    
    client = RCT2Client()
    
    if not client.connect():
        print("[FAIL] Could not connect to bridge")
        return False
    
    # Try to demolish the ride
    response = client.demolish_ride(ride_id)
    
    if response.get("status") == "ok":
        print(f"[PASS] Demolish action succeeded")
        print(f"  Response: {response}")
        return True
    else:
        print(f"[FAIL] Demolish action failed")
        print(f"  Response: {response}")
        return False


def test_rl_loop(num_steps: int = 3):
    """
    Test a minimal RL loop: observe -> action -> observe.
    
    Args:
        num_steps: Number of demolish actions to attempt
    """
    print("\n" + "="*60)
    print("TEST: Minimal RL Loop")
    print("="*60)
    
    client = RCT2Client()
    
    if not client.connect():
        print("[FAIL] Could not connect to bridge")
        return False
    
    for step in range(num_steps):
        print(f"\n--- Step {step + 1} ---")
        
        # OBSERVE: Get current state
        print("[OBSERVE] Getting current ride list...")
        response = client.get_ride_info()
        
        if response.get("status") != "ok":
            print(f"[OBSERVE] Failed: {response}")
            continue
            
        rides = response.get("result", {}).get("rides", [])
        print(f"[OBSERVE] Current state: {len(rides)} rides")
        
        if not rides:
            print("[OBSERVE] No rides to demolish. Creating a test ride first...")
            # We can't create rides without knowing the object IDs
            # Just skip this step
            print(f"[OBSERVE] Skipping step - no rides available")
            continue
        
        # ACTION: Demolish the first ride
        ride_to_demolish = rides[0]
        ride_id = ride_to_demolish.get("id")
        print(f"[ACTION] Demolishing ride {ride_id} ({ride_to_demolish.get('classification')})...")
        
        demolish_response = client.demolish_ride(ride_id)
        
        if demolish_response.get("status") == "ok":
            print(f"[ACTION] Demolish succeeded")
        else:
            print(f"[ACTION] Demolish failed: {demolish_response}")
        
        # Small delay to let the game process
        time.sleep(0.5)
        
        # OBSERVE: Get new state
        print("[OBSERVE] Getting new ride list...")
        new_response = client.get_ride_info()
        
        if new_response.get("status") == "ok":
            new_rides = new_response.get("result", {}).get("rides", [])
            print(f"[OBSERVE] New state: {len(new_rides)} rides")
            
            # Check if the ride was actually removed
            ride_ids = [r.get("id") for r in new_rides]
            if ride_id not in ride_ids:
                print(f"[REWARD] +1 Ride successfully demolished!")
            else:
                print(f"[REWARD] 0 Ride still exists (demolish may have failed silently)")
        else:
            print(f"[OBSERVE] Failed to get new state: {new_response}")
    
    client.disconnect()
    print("\n[RL LOOP] Test complete")


def discover_available_actions():
    """Try to discover what actions are available on the bridge."""
    print("\n" + "="*60)
    print("TEST: Discover Available Actions")
    print("="*60)
    
    client = RCT2Client()
    
    if not client.connect():
        print("[FAIL] Could not connect to bridge")
        return
    
    # List of actions to try (common OpenRCT2 actions)
    actions_to_try = [
        "pausetoggle",
        "ridedemolish",
        "ridecreate",
        "get_ride_info",
        "get_surface_height",
        "check_area_owned",
        "get_park_info",
        "get_finance_info",
        "get_guest_info",
        "loadsave",
        "map",
    ]
    
    print("\nTesting known special actions:")
    for action in ["get_ride_info", "get_surface_height", "check_area_owned"]:
        print(f"\n  Testing '{action}'...")
        response = client.send_action(action)
        if response.get("status") == "ok":
            print(f"    [OK] {action}: {list(response.get('result', {}).keys())}")
        else:
            print(f"    [ERROR] {action}: {response.get('error', 'unknown')}")
    
    print("\nTesting game actions (will modify game state - be careful!):")
    for action in ["pausetoggle", "ridedemolish"]:
        print(f"\n  Testing '{action}'...")
        if action == "ridedemolish":
            # Need a ride ID for demolish
            response = client.send_action(action, rideId=0)
        else:
            response = client.send_action(action)
        print(f"    Response: {response}")
    
    client.disconnect()


def main():
    """Run all tests."""
    print("="*60)
    print("RCT2 RL Environment - OpenRCT2 Bridge Test Client")
    print("="*60)
    
    # Test 1: Basic connection
    if not test_basic_connection():
        print("\n[ERROR] Bridge connection failed. Is OpenRCT2 running with the plugin?")
        return
    
    # Test 2: Get ride info
    rides = test_get_rides()
    
    # Test 3: Discover available actions
    discover_available_actions()
    
    # Test 4: Minimal RL loop (only if we have rides)
    if rides:
        print(f"\n[INFO] Found {len(rides)} rides. Running RL loop test...")
        test_rl_loop(num_steps=min(3, len(rides)))
    else:
        print("\n[INFO] No rides found. Skipping RL loop test.")
        print("[INFO] The park may be empty or the game is still loading.")
    
    print("\n" + "="*60)
    print("All tests complete!")
    print("="*60)


if __name__ == "__main__":
    main()