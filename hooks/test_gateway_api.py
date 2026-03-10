#!/usr/bin/env python3
"""
Test OpenClaw Gateway API for tool calling
"""

import os
import sys
import json
import http.client
import urllib.parse

print("=" * 60)
print("OpenClaw Gateway API Test")
print("=" * 60)

# Get gateway connection info from environment
gateway_port = os.getenv('OPENCLAW_GATEWAY_PORT', '18789')
gateway_token = os.getenv('OPENCLAW_GATEWAY_TOKEN', '')

print(f"Gateway Port: {gateway_port}")
print(f"Gateway Token: {'[REDACTED]' if gateway_token else 'Not found'}")

if not gateway_token:
    print("❌ No gateway token found")
    sys.exit(1)

# Try to connect to gateway
try:
    print(f"\nAttempting to connect to gateway on port {gateway_port}...")
    
    # Create HTTP connection
    conn = http.client.HTTPConnection('localhost', int(gateway_port))
    
    # Test endpoint - try to get status
    headers = {
        'Authorization': f'Bearer {gateway_token}',
        'Content-Type': 'application/json'
    }
    
    # Try to call a simple endpoint
    conn.request('GET', '/status', headers=headers)
    response = conn.getresponse()
    
    print(f"Response status: {response.status}")
    print(f"Response headers: {dict(response.getheaders())}")
    
    body = response.read().decode('utf-8')
    print(f"Response body: {body[:200]}...")
    
    conn.close()
    
except Exception as e:
    print(f"❌ Gateway connection failed: {e}")
    print("\nThis suggests tools are called differently.")

# Alternative: Check if there's a local socket
print("\n" + "=" * 60)
print("Alternative Approach: Local Socket")
print("=" * 60)

socket_path = f"/tmp/openclaw-gateway-{gateway_port}.sock"
print(f"Checking for Unix socket: {socket_path}")

if os.path.exists(socket_path):
    print(f"✅ Socket exists: {socket_path}")
    
    # Try to connect to Unix socket
    try:
        import socket
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.connect(socket_path)
        print("✅ Socket connection successful")
        sock.close()
    except Exception as e:
        print(f"❌ Socket connection failed: {e}")
else:
    print("❌ Socket not found")

print("\n" + "=" * 60)
print("Research Conclusion:")
print("=" * 60)
print("OpenClaw tools are likely called via:")
print("1. Gateway HTTP API (localhost:{port})")
print("2. Unix socket (/tmp/openclaw-gateway-*.sock)")
print("3. With authentication token from environment")
print("\nNext step: Find API documentation for tool calls.")