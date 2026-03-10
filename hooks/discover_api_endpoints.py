#!/usr/bin/env python3
"""
Discover OpenClaw Gateway API endpoints for tool calling
"""

import os
import sys
import json
import http.client
import urllib.parse

print("=" * 60)
print("OpenClaw Gateway API Discovery")
print("=" * 60)

# Get gateway connection info
gateway_port = os.getenv('OPENCLAW_GATEWAY_PORT', '18789')
gateway_token = os.getenv('OPENCLAW_GATEWAY_TOKEN', '')

if not gateway_token:
    print("❌ No gateway token found")
    sys.exit(1)

# Common API endpoint patterns to try
api_patterns = [
    # Tool-related endpoints
    '/api/tools',
    '/api/v1/tools',
    '/tools',
    '/v1/tools',
    
    # Agent/tool endpoints
    '/api/agent/tools',
    '/api/v1/agent/tools',
    
    # Session/tool endpoints
    '/api/session/tools',
    '/api/v1/session/tools',
    
    # Generic endpoints that might list available tools
    '/api',
    '/api/v1',
    '/openapi.json',
    '/swagger.json',
    '/docs',
    '/redoc',
]

def test_endpoint(method, path, data=None):
    """Test a single API endpoint"""
    try:
        conn = http.client.HTTPConnection('localhost', int(gateway_port))
        headers = {
            'Authorization': f'Bearer {gateway_token}',
            'Content-Type': 'application/json'
        }
        
        if data:
            body = json.dumps(data)
            conn.request(method, path, body, headers)
        else:
            conn.request(method, path, headers=headers)
        
        response = conn.getresponse()
        status = response.status
        body = response.read().decode('utf-8')
        conn.close()
        
        return status, body
        
    except Exception as e:
        return None, str(e)

print(f"\nTesting API endpoints on port {gateway_port}...")

# First, try to get API documentation
print("\n1. Looking for API documentation:")
doc_endpoints = ['/docs', '/redoc', '/swagger', '/openapi']
for endpoint in doc_endpoints:
    status, body = test_endpoint('GET', endpoint)
    if status == 200:
        print(f"  ✅ {endpoint}: Found documentation (status {status})")
        # Check if it's HTML (likely documentation)
        if '<html' in body.lower() or '<!doctype' in body.lower():
            print(f"    Looks like HTML documentation")
        break
else:
    print("  ❌ No documentation endpoints found")

# Try common API root endpoints
print("\n2. Testing API root endpoints:")
for endpoint in ['/api', '/api/v1', '/v1/api']:
    status, body = test_endpoint('GET', endpoint)
    if status == 200:
        print(f"  ✅ {endpoint}: Found API root (status {status})")
        try:
            data = json.loads(body)
            print(f"    Response: {json.dumps(data, indent=2)[:200]}...")
        except:
            print(f"    Response: {body[:200]}...")
        break
else:
    print("  ❌ No API root found")

# Try tool-related endpoints
print("\n3. Testing tool endpoints:")
for endpoint in api_patterns:
    status, body = test_endpoint('GET', endpoint)
    if status == 200:
        print(f"  ✅ {endpoint}: Found (status {status})")
        try:
            data = json.loads(body)
            print(f"    JSON response keys: {list(data.keys())}")
        except:
            print(f"    Response: {body[:200]}...")
    elif status == 404:
        # Expected for many endpoints
        pass
    elif status:
        print(f"  ⚠️  {endpoint}: Status {status}")
    else:
        # Connection error
        pass

# Try to discover by making a tool call
print("\n4. Attempting tool call discovery:")

# Try common tool call patterns
tool_call_patterns = [
    ('POST', '/api/tools/exec', {'tool': 'exec', 'command': 'echo test'}),
    ('POST', '/api/v1/tools/exec', {'tool': 'exec', 'command': 'echo test'}),
    ('POST', '/tools/exec', {'tool': 'exec', 'command': 'echo test'}),
    ('POST', '/api/agent/tool', {'tool': 'exec', 'command': 'echo test'}),
]

for method, endpoint, data in tool_call_patterns:
    print(f"  Testing {method} {endpoint}...")
    status, body = test_endpoint(method, endpoint, data)
    
    if status == 200:
        print(f"    ✅ Success! Status {status}")
        try:
            result = json.loads(body)
            print(f"    Response: {json.dumps(result, indent=2)[:200]}...")
            print(f"\n🎉 DISCOVERED TOOL CALLING ENDPOINT: {endpoint}")
            break
        except:
            print(f"    Response: {body[:200]}...")
    elif status == 400 or status == 401 or status == 403:
        print(f"    ⚠️  Status {status} - Endpoint exists but rejected call")
        print(f"    Response: {body[:200]}...")
    elif status == 404:
        # Endpoint doesn't exist
        pass
    elif status:
        print(f"    ⚠️  Status {status}")
    else:
        # Connection error
        pass

print("\n" + "=" * 60)
print("Discovery Complete")
print("=" * 60)

print("\nIf no endpoint was discovered, alternative approaches:")
print("1. Check OpenClaw source code for API routes")
print("2. Look for existing Python examples in community")
print("3. Check if tools are injected into agent context")
print("4. Look for WebSocket/RPC patterns instead of HTTP")

print("\nNext step: Based on discovery results, implement real tool calls.")