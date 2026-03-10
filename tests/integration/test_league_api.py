#!/usr/bin/env python3
"""
Test script for League Creation API
"""
import requests
import json
import sys

BASE_URL = "http://localhost:8000"
API_KEY_ROGER = "key_roger_bot_123"
API_KEY_TEST = "key_test_bot_456"

def print_response(response, label="Response"):
    """Pretty print response"""
    print(f"\n{'='*60}")
    print(f"{label}:")
    print(f"{'='*60}")
    print(f"Status: {response.status_code}")
    try:
        print(json.dumps(response.json(), indent=2))
    except:
        print(f"Text: {response.text}")
    print(f"{'='*60}")

def test_health():
    """Test health endpoint"""
    print("\n🔍 Testing Health Endpoint...")
    response = requests.get(f"{BASE_URL}/health")
    print_response(response, "Health Check")
    return response.status_code == 200

def test_api_status():
    """Test API status endpoint"""
    print("\n📊 Testing API Status...")
    response = requests.get(f"{BASE_URL}/api/v1/status")
    print_response(response, "API Status")
    return response.status_code == 200

def test_create_league(api_key, league_data, test_name):
    """Test league creation"""
    print(f"\n🚀 {test_name}...")
    headers = {
        "Content-Type": "application/json",
        "X-API-Key": api_key
    }
    response = requests.post(
        f"{BASE_URL}/api/v1/leagues",
        headers=headers,
        json=league_data
    )
    print_response(response, f"Create League - {test_name}")
    return response

def test_list_leagues(api_key):
    """Test listing leagues"""
    print("\n📋 Testing List Leagues...")
    headers = {"X-API-Key": api_key}
    response = requests.get(f"{BASE_URL}/api/v1/leagues", headers=headers)
    print_response(response, "List Leagues")
    return response

def test_my_leagues(api_key):
    """Test getting my leagues"""
    print("\n🤖 Testing My Leagues...")
    headers = {"X-API-Key": api_key}
    response = requests.get(f"{BASE_URL}/api/v1/leagues/my-leagues", headers=headers)
    print_response(response, "My Leagues")
    return response

def test_invalid_api_key():
    """Test with invalid API key"""
    print("\n❌ Testing Invalid API Key...")
    headers = {
        "Content-Type": "application/json",
        "X-API-Key": "invalid_key_123"
    }
    response = requests.post(
        f"{BASE_URL}/api/v1/leagues",
        headers=headers,
        json={"name": "Test", "format": "dynasty", "attribute": "stat_nerds"}
    )
    print_response(response, "Invalid API Key Test")
    return response.status_code == 401

def test_validation_errors():
    """Test validation errors"""
    print("\n⚠️ Testing Validation Errors...")
    
    # Test 1: Name too short
    print("\nTest 1: Name too short")
    headers = {"Content-Type": "application/json", "X-API-Key": API_KEY_ROGER}
    response = requests.post(
        f"{BASE_URL}/api/v1/leagues",
        headers=headers,
        json={"name": "AB", "format": "dynasty", "attribute": "stat_nerds"}
    )
    print_response(response, "Validation - Name too short")
    
    # Test 2: Invalid format
    print("\nTest 2: Invalid format")
    response = requests.post(
        f"{BASE_URL}/api/v1/leagues",
        headers=headers,
        json={"name": "Test League", "format": "invalid", "attribute": "stat_nerds"}
    )
    print_response(response, "Validation - Invalid format")
    
    # Test 3: Invalid attribute
    print("\nTest 3: Invalid attribute")
    response = requests.post(
        f"{BASE_URL}/api/v1/leagues",
        headers=headers,
        json={"name": "Test League", "format": "dynasty", "attribute": "invalid"}
    )
    print_response(response, "Validation - Invalid attribute")
    
    return True

def main():
    """Run all tests"""
    print("🤖 Bot Sports Empire - API Test Suite")
    print("="*60)
    
    # Check if server is running
    try:
        requests.get(f"{BASE_URL}/health", timeout=2)
    except requests.exceptions.ConnectionError:
        print(f"❌ Server not running at {BASE_URL}")
        print("Start the server first: python main.py")
        sys.exit(1)
    
    # Run tests
    tests_passed = 0
    total_tests = 0
    
    # Test 1: Health check
    total_tests += 1
    if test_health():
        tests_passed += 1
    
    # Test 2: API status
    total_tests += 1
    if test_api_status():
        tests_passed += 1
    
    # Test 3: Create league with Roger Bot
    total_tests += 1
    response = test_create_league(
        API_KEY_ROGER,
        {
            "name": "Roger's Dynasty League",
            "format": "dynasty",
            "attribute": "trash_talk"
        },
        "Create League with Roger Bot"
    )
    if response.status_code == 201:
        tests_passed += 1
        roger_league_id = response.json().get("league", {}).get("id")
    
    # Test 4: Create league with Test Bot
    total_tests += 1
    response = test_create_league(
        API_KEY_TEST,
        {
            "name": "Test Bot Fantasy League",
            "format": "fantasy",
            "attribute": "stat_nerds"
        },
        "Create League with Test Bot"
    )
    if response.status_code == 201:
        tests_passed += 1
        test_league_id = response.json().get("league", {}).get("id")
    
    # Test 5: List all leagues
    total_tests += 1
    response = test_list_leagues(API_KEY_ROGER)
    if response.status_code == 200:
        tests_passed += 1
    
    # Test 6: Get my leagues (Roger Bot)
    total_tests += 1
    response = test_my_leagues(API_KEY_ROGER)
    if response.status_code == 200:
        tests_passed += 1
    
    # Test 7: Get my leagues (Test Bot)
    total_tests += 1
    response = test_my_leagues(API_KEY_TEST)
    if response.status_code == 200:
        tests_passed += 1
    
    # Test 8: Invalid API key
    total_tests += 1
    if test_invalid_api_key():
        tests_passed += 1
    
    # Test 9: Validation errors
    total_tests += 1
    if test_validation_errors():
        tests_passed += 1
    
    # Test 10: Duplicate league name
    total_tests += 1
    print("\n🚫 Testing Duplicate League Name...")
    headers = {"Content-Type": "application/json", "X-API-Key": API_KEY_ROGER}
    response = requests.post(
        f"{BASE_URL}/api/v1/leagues",
        headers=headers,
        json={"name": "Roger's Dynasty League", "format": "dynasty", "attribute": "stat_nerds"}
    )
    print_response(response, "Duplicate League Name")
    if response.status_code == 409:
        tests_passed += 1
    
    # Summary
    print("\n" + "="*60)
    print("📊 TEST SUMMARY")
    print("="*60)
    print(f"Tests Passed: {tests_passed}/{total_tests}")
    print(f"Success Rate: {(tests_passed/total_tests)*100:.1f}%")
    
    if tests_passed == total_tests:
        print("✅ All tests passed!")
    else:
        print(f"⚠️ {total_tests - tests_passed} tests failed")
    
    print("\n🎯 Next Steps:")
    print("1. Check API documentation at http://localhost:8000/docs")
    print("2. Test frontend integration with frontend_integration.js")
    print("3. Deploy to production with proper security settings")

if __name__ == "__main__":
    main()