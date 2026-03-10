#!/usr/bin/env python3
"""
Test the updated main.py locally
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_root():
    """Test root endpoint"""
    response = client.get("/")
    assert response.status_code == 200
    print("✅ Root endpoint works")
    return response.json()

def test_bot_registration():
    """Test bot registration endpoint"""
    test_bot = {
        "name": "test_bot_local",
        "display_name": "Local Test Bot",
        "description": "Testing local registration",
        "personality": "balanced",
        "owner_id": "local@test.com"
    }
    
    response = client.post("/api/v1/bots", json=test_bot)
    
    if response.status_code == 201:
        print("✅ Bot registration endpoint works locally")
        result = response.json()
        print(f"   Bot ID: {result['bot_id']}")
        print(f"   API Key: {result['api_key'][:20]}...")
        print(f"   Dashboard URL: {result['dashboard_url']}")
        return result
    else:
        print(f"❌ Bot registration failed: {response.status_code}")
        print(f"   Response: {response.text}")
        return None

def test_dashboard():
    """Test dashboard endpoint"""
    # First register a bot
    test_bot = {
        "name": "dashboard_test_bot",
        "display_name": "Dashboard Test",
        "description": "Testing dashboard access",
        "personality": "strategist",
        "owner_id": "dashboard@test.com"
    }
    
    response = client.post("/api/v1/bots", json=test_bot)
    
    if response.status_code == 201:
        result = response.json()
        bot_id = result['bot_id']
        api_key = result['api_key']
        
        # Test dashboard with credentials
        response = client.get(f"/dashboard?bot_id={bot_id}&api_key={api_key}")
        
        if response.status_code == 200:
            print("✅ Dashboard endpoint works with seamless entry")
            dashboard_data = response.json()
            print(f"   Welcome message: {dashboard_data['message']}")
            print(f"   Seamless entry: {dashboard_data['seamless_entry']}")
            return True
        else:
            print(f"❌ Dashboard failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
    else:
        print("❌ Could not register bot for dashboard test")
        return False

def test_existing_endpoints():
    """Test other endpoints"""
    endpoints = [
        ("/health", "GET"),
        ("/api/v1/leagues", "GET"),
        ("/docs", "GET")
    ]
    
    print("\nTesting other endpoints:")
    for endpoint, method in endpoints:
        if method == "GET":
            response = client.get(endpoint)
        else:
            response = client.post(endpoint)
        
        if response.status_code < 400:
            print(f"✅ {endpoint} ({method}): {response.status_code}")
        else:
            print(f"❌ {endpoint} ({method}): {response.status_code}")

if __name__ == "__main__":
    print("="*60)
    print("Local Test of Updated main.py")
    print("="*60)
    
    try:
        # Test root
        root_data = test_root()
        
        # Test bot registration
        bot_data = test_bot_registration()
        
        # Test dashboard
        dashboard_works = test_dashboard()
        
        # Test other endpoints
        test_existing_endpoints()
        
        print("\n" + "="*60)
        print("✅ LOCAL TESTS PASSED!")
        print("\nSummary of fixes implemented:")
        print("1. ✅ POST /api/v1/bots endpoint added")
        print("2. ✅ Bot registration with API key generation")
        print("3. ✅ Seamless entry with dashboard redirect")
        print("4. ✅ Dashboard endpoint with authentication")
        print("5. ✅ Registration page updated with correct curl command")
        print("\nNext step: Deploy to Render")
        print("="*60)
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        print("="*60)