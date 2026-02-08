import requests
import json
import time

BASE_URL = "http://localhost:8001"

print("Testing API endpoints...")

# Test 1: Health endpoint
print("\n1. Testing health endpoint...")
try:
    response = requests.get(f"{BASE_URL}/health", timeout=5)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
except Exception as e:
    print(f"Error: {e}")

# Test 2: Create league with timeout
print("\n2. Creating test league...")
league_data = {
    "name": "Test League",
    "sport": "football", 
    "country": "USA",
    "season": "2024"
}
try:
    start_time = time.time()
    response = requests.post(
        f"{BASE_URL}/api/v1/leagues/",
        json=league_data,
        timeout=10  # 10 second timeout
    )
    elapsed = time.time() - start_time
    print(f"Request took {elapsed:.2f} seconds")
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        print(f"Response: {response.json()}")
    else:
        print(f"Error: {response.text}")
except requests.exceptions.Timeout:
    print("ERROR: Request timed out after 10 seconds")
except Exception as e:
    print(f"Error: {e}")

print("\nTest complete.")
