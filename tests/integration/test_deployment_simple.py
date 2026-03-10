#!/usr/bin/env python3
"""
Test script to verify the simplified landing page deployment
"""
import requests
import time

BASE_URL = "https://bot-sports-empire.onrender.com"

def test_endpoint(endpoint, expected_status=200, is_html=False):
    """Test a specific endpoint"""
    url = f"{BASE_URL}{endpoint}"
    print(f"\nTesting: {url}")
    
    try:
        response = requests.get(url, timeout=10)
        print(f"  Status: {response.status_code}")
        print(f"  Content-Type: {response.headers.get('content-type', 'unknown')}")
        
        if response.status_code == expected_status:
            if is_html:
                # Check if it's HTML
                content_type = response.headers.get('content-type', '').lower()
                if 'html' in content_type:
                    print("  ✓ HTML content detected")
                    # Check for key elements
                    content = response.text.lower()
                    if endpoint == "/":
                        if "dynastydroid" in content and "login" in content and "register" in content:
                            print("  ✓ Landing page contains key elements")
                        else:
                            print("  ✗ Missing key elements in landing page")
                    elif endpoint == "/register":
                        if "register your bot" in content and "step" in content:
                            print("  ✓ Registration page contains key elements")
                        else:
                            print("  ✗ Missing key elements in registration page")
                else:
                    print("  ✗ Not HTML content")
            else:
                print("  ✓ API endpoint working")
            return True
        else:
            print(f"  ✗ Expected {expected_status}, got {response.status_code}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"  ✗ Request failed: {e}")
        return False
    except Exception as e:
        print(f"  ✗ Unexpected error: {e}")
        return False

def main():
    print("Testing DynastyDroid Simplified Deployment")
    print("=" * 50)
    
    # Give Render time to deploy
    print("Waiting 30 seconds for deployment to update...")
    time.sleep(30)
    
    tests = [
        ("/", 200, True),  # Landing page (HTML)
        ("/register", 200, True),  # Registration page (HTML)
        ("/login", 200, False),  # Login endpoint (API)
        ("/health", 200, False),  # Health check
        ("/docs", 200, False),  # API documentation
    ]
    
    passed = 0
    total = len(tests)
    
    for endpoint, expected_status, is_html in tests:
        if test_endpoint(endpoint, expected_status, is_html):
            passed += 1
    
    print(f"\n{'=' * 50}")
    print(f"Test Results: {passed}/{total} passed")
    
    if passed == total:
        print("✅ All tests passed! Deployment successful.")
        print(f"\nVisit the live site:")
        print(f"  Landing page: {BASE_URL}/")
        print(f"  Registration: {BASE_URL}/register")
    else:
        print("❌ Some tests failed. Check deployment logs.")
        
    return passed == total

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)