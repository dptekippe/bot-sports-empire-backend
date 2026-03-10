#!/usr/bin/env python3
"""
Test the production deployment of bot registration API.
"""
import requests
import json
import sys

# Production URL
BASE_URL = "https://bot-sports-empire.onrender.com"
API_PREFIX = "/api/v1"

def test_production_endpoints():
    """Test production endpoints."""
    print("=" * 60)
    print("Testing Production Deployment")
    print("=" * 60)
    
    # Test 1: Health check
    print(f"\n1. Testing health check: GET {BASE_URL}/health")
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=10)
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            print("   ✅ Health check passed")
        else:
            print(f"   ❌ Health check failed: {response.text}")
    except Exception as e:
        print(f"   ❌ Health check error: {e}")
    
    # Test 2: Root endpoint
    print(f"\n2. Testing root endpoint: GET {BASE_URL}/")
    try:
        response = requests.get(BASE_URL, timeout=10)
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ API is running: {data.get('message')}")
            print(f"   📚 Docs: {BASE_URL}{data.get('docs')}")
        else:
            print(f"   ❌ Root endpoint failed: {response.text}")
    except Exception as e:
        print(f"   ❌ Root endpoint error: {e}")
    
    # Test 3: Bot registration endpoint (quick test)
    print(f"\n3. Testing bot registration endpoint structure")
    print(f"   Expected: POST {BASE_URL}{API_PREFIX}/bots/register")
    print(f"   Try: curl -X POST {BASE_URL}{API_PREFIX}/bots/register \\")
    print("        -H 'Content-Type: application/json' \\")
    print("        -d '{\"name\":\"test_bot\",\"display_name\":\"Test Bot\",\"description\":\"Test\"}'")
    
    # Test 4: Documentation
    print(f"\n4. Checking API documentation")
    print(f"   📖 OpenAPI docs: {BASE_URL}/docs")
    print(f"   📖 ReDoc: {BASE_URL}/redoc")
    
    print("\n" + "=" * 60)
    print("Production Test Complete")
    print("=" * 60)
    print("\n📋 Next steps:")
    print("1. Deploy to Render using updated render.yaml")
    print("2. Test the actual bot registration endpoint")
    print("3. Update DNS to point api.dynastydroid.com to Render")
    print("4. Update landing page with final production URL")

if __name__ == "__main__":
    test_production_endpoints()
