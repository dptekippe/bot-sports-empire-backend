#!/usr/bin/env python3
"""
RCT2 Demolish Action Test - Multiple Parameter Formats

Tests different parameter formats for the ridedemolish action to find
which one works with the OpenRCT2 bridge.
"""

import socket
import json
import sys
import time


def send_tcp_message(host: str, port: int, message: dict, timeout: float = 5.0) -> dict:
    """
    Send a JSON message via TCP and return the response.
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    
    try:
        sock.connect((host, port))
        
        json_str = json.dumps(message) + "\n"
        sock.sendall(json_str.encode('utf-8'))
        print(f"  SENT: {json_str.strip()}")
        
        response_data = b""
        sock.settimeout(timeout)
        while True:
            try:
                chunk = sock.recv(4096)
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
            response_str = response_data.decode('utf-8').strip()
            if response_str:
                response = json.loads(response_str)
                print(f"  RECV: {response}")
                return response
        
        return {"status": "error", "message": "Empty response"}
        
    except Exception as e:
        return {"status": "error", "message": str(e)}
    finally:
        sock.close()


def get_rides(port: int = 11752) -> list:
    """Get list of rides."""
    print(f"\n[GET RIDES] Port {port}...")
    response = send_tcp_message("localhost", port, {"action": "get_ride_info"})
    
    if response.get("status") == "ok":
        rides = response.get("result", {}).get("rides", [])
        print(f"  Found {len(rides)} rides:")
        for ride in rides:
            print(f"    - ID {ride.get('id')}: {ride.get('classification')} ({ride.get('status')})")
        return rides
    print(f"  Error: {response}")
    return []


def test_demolish_formats(ride_id: int, port: int = 11752):
    """
    Test different demolish parameter formats.
    
    Formats to try:
    1. rideId (as used in the original zmq_bridge code comments)
    2. id (OpenRCT2's standard ride ID parameter)
    3. ride_id (Python convention)
    """
    print(f"\n[TEST FORMATS] Ride ID: {ride_id}")
    
    formats = [
        ("rideId", {"action": "ridedemolish", "rideId": ride_id}),
        ("id", {"action": "ridedemolish", "id": ride_id}),
        ("ride_id", {"action": "ridedemolish", "ride_id": ride_id}),
    ]
    
    for name, msg in formats:
        print(f"\n  Testing format: {name}")
        response = send_tcp_message("localhost", port, msg)
        
        if response.get("status") == "ok":
            print(f"  [SUCCESS] {name} format worked!")
            return name, response
        
        time.sleep(0.2)
    
    return None, None


def main():
    port = 11752
    
    if len(sys.argv) > 1:
        port = int(sys.argv[1])
    
    print("="*60)
    print("RCT2 Demolish Action Format Test")
    print(f"Target: localhost:{port}")
    print("="*60)
    
    # Get current rides
    rides = get_rides(port)
    
    if not rides:
        print("\n[ERROR] No rides found.")
        return
    
    first_ride = rides[0]
    ride_id = first_ride.get('id')
    
    # Test different parameter formats
    print(f"\n[TEST] Attempting to demolish ride {ride_id}...")
    working_format, response = test_demolish_formats(ride_id, port)
    
    if working_format:
        print(f"\n[RESULT] Format '{working_format}' works!")
        
        # Verify ride was removed
        time.sleep(0.5)
        remaining = get_rides(port)
        remaining_ids = [r.get('id') for r in remaining]
        
        if ride_id not in remaining_ids:
            print(f"\n[VERIFIED] Ride {ride_id} successfully demolished!")
        else:
            print(f"\n[WARNING] Ride {ride_id} still exists - demolish may have been cosmetic")
    else:
        print("\n[RESULT] No format worked. Check OpenRCT2 console for errors.")
    
    print("\n" + "="*60)


if __name__ == "__main__":
    main()