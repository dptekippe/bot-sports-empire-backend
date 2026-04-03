#!/usr/bin/env python3
"""
RCT2 Action Tester - Tests action execution via OpenRCT2 JSON Action Bridge

Connects to the zmq_bridge.js plugin running inside OpenRCT2.
Protocol: TCP with newline-delimited JSON messages.

Usage:
    python rct2_action_tester.py
"""

import socket
import json
import time

BRIDGE_HOST = "localhost"
BRIDGE_PORT = 11752

def send_action(sock, action, **kwargs):
    """Send an action to the bridge and return the response."""
    msg = {"action": action}
    msg.update(kwargs)
    
    print(f">>> Sending: {json.dumps(msg)}")
    sock.sendall((json.dumps(msg) + "\n").encode())
    
    # Receive response
    response = b""
    sock.settimeout(5.0)
    while True:
        try:
            chunk = sock.recv(4096)
            if not chunk:
                break
            response += chunk
            # Try to parse - if we get a complete JSON object, we're done
            try:
                decoded = json.loads(response.decode().strip())
                print(f"<<< Received: {json.dumps(decoded, indent=2)}")
                return decoded
            except json.JSONDecodeError:
                # Not complete yet, keep receiving
                continue
        except socket.timeout:
            break
    
    if response:
        print(f"<<< Received: {response.decode().strip()}")
        return json.loads(response.decode().strip())
    return None

def connect():
    """Create a connection to the bridge."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((BRIDGE_HOST, BRIDGE_PORT))
    print(f"Connected to {BRIDGE_HOST}:{BRIDGE_PORT}")
    return sock

def get_ride_info(sock):
    """Get list of rides - special action."""
    return send_action(sock, "get_ride_info")

def demolish_ride(sock, ride_id):
    """Demolish a ride by ID - game action."""
    return send_action(sock, "ridedemolish", id=ride_id)

def pause_toggle(sock):
    """Toggle pause state."""
    return send_action(sock, "pausetoggle")

def get_surface_height(sock, x, y):
    """Get terrain height at coordinates - special action."""
    return send_action(sock, "get_surface_height", x=x, y=y)

def main():
    print("=" * 60)
    print("RCT2 Action Tester")
    print("=" * 60)
    
    try:
        sock = connect()
        
        # Test 1: Get ride info (special action)
        print("\n--- TEST 1: Get Ride Info ---")
        result = get_ride_info(sock)
        if result and result.get("status") == "ok":
            rides = result.get("result", {}).get("rides", [])
            print(f"Found {len(rides)} rides")
            for ride in rides:
                print(f"  Ride {ride.get('id')}: type={ride.get('type')}, status={ride.get('status')}")
        else:
            print(f"Failed to get ride info: {result}")
        
        # Test 2: Try demolish action with rideId 0
        if result and result.get("status") == "ok":
            rides = result.get("result", {}).get("rides", [])
            if rides:
                ride_to_demolish = rides[0]
                ride_id = ride_to_demolish.get("id")
                print(f"\n--- TEST 2: Demolish Ride {ride_id} ---")
                demolish_result = demolish_ride(sock, ride_id)
                print(f"Demolish result: {demolish_result}")
                
                # Verify the ride was removed
                print("\n--- VERIFY: Get Ride Info After Demolish ---")
                verify_result = get_ride_info(sock)
                if verify_result and verify_result.get("status") == "ok":
                    remaining_rides = verify_result.get("result", {}).get("rides", [])
                    print(f"Remaining rides: {len(remaining_rides)}")
                    if ride_id not in [r.get("id") for r in remaining_rides]:
                        print(f"SUCCESS: Ride {ride_id} was demolished!")
                    else:
                        print(f"FAILURE: Ride {ride_id} still exists")
            else:
                print("No rides to demolish")
        else:
            print("Skipping demolish test - could not get ride info")
        
        # Test 3: Get surface height (special action)
        print("\n--- TEST 3: Get Surface Height ---")
        height_result = get_surface_height(sock, 50, 50)
        
        sock.close()
        print("\nConnection closed")
        
    except ConnectionRefusedError:
        print(f"ERROR: Could not connect to {BRIDGE_HOST}:{BRIDGE_PORT}")
        print("Is OpenRCT2 running with the zmq_bridge.js plugin loaded?")
    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    main()
