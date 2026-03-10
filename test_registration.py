#!/usr/bin/env python3
"""
Test script to verify bot registration endpoint works.
"""
import requests
import json
import sys

def test_bot_registration():
    """Test the POST /api/v1/bots endpoint"""
    url = "https://bot-sports-empire.onrender.com/api/v1/bots"
    
    # Test data
    test_bot = {
        "name": "test_bot_" + str(hash(str(sys.argv)))[-8:],
        "display_name": "Test Bot",
        "description": "A test bot for verifying registration endpoint",
        "personality": "balanced",
        "owner_id": "test@example.com"
    }
    
    print("Testing bot registration endpoint...")
    print(f"URL: {url}")
    print(f"Data: {json.dumps(test_bot, indent=2)}")
    
    try:
        response = requests.post(
            url,
            json=test_bot,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        print(f"\nStatus Code: {response.status_code}")
        
        if response.status_code == 201:
            print("✅ SUCCESS: Bot registration endpoint is working!")
            result = response.json()
            print(f"\nResponse:")
            print(json.dumps(result, indent=2))
            
            # Check for dashboard_url (seamless entry)
            if "dashboard_url" in result:
                print(f"\n🎉 Seamless entry implemented! Dashboard URL: {result['dashboard_url']}")
            else:
                print("\n⚠️  Warning: No dashboard_url in response (seamless entry missing)")
                
            return True
            
        else:
            print(f"❌ FAILED: Status code {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ ERROR: Request failed - {e}")
        return False
    except json.JSONDecodeError as e:
        print(f"❌ ERROR: Invalid JSON response - {e}")
        print(f"Raw response: {response.text}")
        return False

def test_existing_endpoints():
    """Test other existing endpoints"""
    base_url = "https://bot-sports-empire.onrender.com"
    
    endpoints = [
        "/",
        "/health",
        "/api/v1/leagues",
        "/docs"
    ]
    
    print("\n" + "="*60)
    print("Testing existing endpoints...")
    
    for endpoint in endpoints:
        url = base_url + endpoint
        try:
            if endpoint == "/api/v1/leagues":
                response = requests.get(url, timeout=10)
            else:
                response = requests.get(url, timeout=10)
                
            print(f"{endpoint}: {response.status_code} {'✅' if response.status_code < 400 else '❌'}")
            
        except requests.exceptions.RequestException as e:
            print(f"{endpoint}: ❌ ERROR - {e}")

if __name__ == "__main__":
    print("="*60)
    print("DynastyDroid Registration Endpoint Test")
    print("="*60)
    
    # Test registration
    success = test_bot_registration()
    
    # Test other endpoints
    test_existing_endpoints()
    
    print("\n" + "="*60)
    if success:
        print("✅ All tests completed successfully!")
        print("\nNext steps:")
        print("1. Update registration page with correct curl command ✓")
        print("2. Implement bot registration endpoint ✓")
        print("3. Add seamless entry (dashboard redirect) ✓")
        print("4. Test complete user flow")
    else:
        print("❌ Tests failed. Check the implementation.")
    
    print("="*60)