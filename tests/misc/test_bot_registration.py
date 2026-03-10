#!/usr/bin/env python3
"""
Test script for bot registration API endpoints.
"""
import requests
import json
import sys

# Configuration
BASE_URL = "http://localhost:8000"  # Update to bot-sports-empire.onrender.com for production
API_PREFIX = "/api/v1"

def test_bot_registration():
    """Test POST /api/bots/register endpoint."""
    url = f"{BASE_URL}{API_PREFIX}/bots/register"
    
    # Test data
    payload = {
        "name": "test_bot_001",
        "display_name": "Test Bot 001",
        "description": "A test bot for API validation",
        "owner_id": "test_user_123",
        "personality_tags": ["analytical", "data-driven"]
    }
    
    print(f"Testing bot registration: POST {url}")
    print(f"Payload: {json.dumps(payload, indent=2)}")
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 201:
            data = response.json()
            print(f"✅ Success! Bot registered:")
            print(f"   Bot ID: {data.get('bot_id')}")
            print(f"   Bot Name: {data.get('bot_name')}")
            print(f"   API Key: {data.get('api_key')[:20]}...")  # Show first 20 chars
            print(f"   Personality: {data.get('personality')}")
            print(f"   Message: {data.get('message')}")
            return data
        else:
            print(f"❌ Failed: {response.text}")
            return None
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")
        return None

def test_get_bot_details(bot_id, api_key):
    """Test GET /api/bots/{bot_id} endpoint with authentication."""
    url = f"{BASE_URL}{API_PREFIX}/bots/{bot_id}"
    headers = {"Authorization": f"Bearer {api_key}"}
    
    print(f"\nTesting bot details retrieval: GET {url}")
    print(f"Headers: Authorization: Bearer {api_key[:20]}...")
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Success! Bot details retrieved:")
            print(f"   Bot ID: {data.get('id')}")
            print(f"   Name: {data.get('name')}")
            print(f"   Display Name: {data.get('display_name')}")
            print(f"   Personality: {data.get('fantasy_personality')}")
            print(f"   Mood: {data.get('current_mood')}")
            print(f"   Social Credits: {data.get('social_credits')}")
            return data
        else:
            print(f"❌ Failed: {response.text}")
            return None
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")
        return None

def test_list_bots():
    """Test GET /api/bots/ endpoint (public)."""
    url = f"{BASE_URL}{API_PREFIX}/bots/"
    
    print(f"\nTesting bot listing: GET {url}")
    
    try:
        response = requests.get(url, timeout=10)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Success! Found {len(data)} bots")
            for i, bot in enumerate(data[:3]):  # Show first 3
                print(f"   {i+1}. {bot.get('display_name')} ({bot.get('name')})")
            return data
        else:
            print(f"❌ Failed: {response.text}")
            return None
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")
        return None

def test_api_key_rotation(bot_id, api_key):
    """Test POST /api/bots/{bot_id}/rotate-key endpoint."""
    url = f"{BASE_URL}{API_PREFIX}/bots/{bot_id}/rotate-key"
    headers = {"Authorization": f"Bearer {api_key}"}
    
    print(f"\nTesting API key rotation: POST {url}")
    print(f"Headers: Authorization: Bearer {api_key[:20]}...")
    
    try:
        response = requests.post(url, headers=headers, timeout=10)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Success! API key rotated:")
            print(f"   New API Key: {data.get('new_api_key')[:20]}...")
            print(f"   Message: {data.get('message')}")
            return data.get('new_api_key')
        else:
            print(f"❌ Failed: {response.text}")
            return None
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")
        return None

def main():
    """Run all tests."""
    print("=" * 60)
    print("Bot Registration API Tests")
    print("=" * 60)
    
    # Test 1: Register a bot
    registration_result = test_bot_registration()
    if not registration_result:
        print("\n❌ Bot registration test failed. Exiting.")
        sys.exit(1)
    
    bot_id = registration_result.get('bot_id')
    api_key = registration_result.get('api_key')
    
    # Test 2: Get bot details (with authentication)
    test_get_bot_details(bot_id, api_key)
    
    # Test 3: List bots (public endpoint)
    test_list_bots()
    
    # Test 4: Rotate API key
    new_api_key = test_api_key_rotation(bot_id, api_key)
    
    if new_api_key:
        # Test 5: Verify old key no longer works
        print(f"\nTesting old API key (should fail):")
        test_get_bot_details(bot_id, api_key)
        
        # Test 6: Verify new key works
        print(f"\nTesting new API key (should succeed):")
        test_get_bot_details(bot_id, new_api_key)
    
    print("\n" + "=" * 60)
    print("Tests completed!")
    print("=" * 60)

if __name__ == "__main__":
    main()
