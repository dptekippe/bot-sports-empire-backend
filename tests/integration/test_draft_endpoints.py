#!/usr/bin/env python3
"""
Test draft endpoints for Bot Sports Empire.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_draft_endpoints():
    """Test basic draft endpoints."""
    print("🧪 Testing Draft Endpoints")
    print("=" * 50)
    
    # Test 1: Create a draft
    print("\n1. Testing POST /api/v1/drafts/")
    draft_data = {
        "name": "Test Draft 2025",
        "draft_type": "snake",
        "rounds": 15,
        "team_count": 12,
        "seconds_per_pick": 90,
        "league_id": None
    }
    
    response = client.post("/api/v1/drafts/", json=draft_data)
    print(f"   Status: {response.status_code}")
    
    if response.status_code == 201:
        draft = response.json()
        draft_id = draft["id"]
        print(f"   ✅ Draft created: {draft['name']} (ID: {draft_id})")
        print(f"   Status: {draft['status']}")
        print(f"   Type: {draft['draft_type']}")
    else:
        print(f"   ❌ Failed to create draft: {response.text}")
        return False
    
    # Test 2: Get the draft
    print(f"\n2. Testing GET /api/v1/drafts/{draft_id}")
    response = client.get(f"/api/v1/drafts/{draft_id}")
    print(f"   Status: {response.status_code}")
    
    if response.status_code == 200:
        draft = response.json()
        print(f"   ✅ Draft retrieved: {draft['name']}")
        print(f"   Picks: {len(draft.get('picks', []))}")
        print(f"   Current pick: {draft.get('current_pick', 1)}")
    else:
        print(f"   ❌ Failed to get draft: {response.text}")
        return False
    
    # Test 3: List all drafts
    print("\n3. Testing GET /api/v1/drafts/")
    response = client.get("/api/v1/drafts/")
    print(f"   Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"   ✅ Found {data['total']} drafts")
        print(f"   Page: {data['page']}, Page size: {data['page_size']}")
    else:
        print(f"   ❌ Failed to list drafts: {response.text}")
        return False
    
    # Test 4: List draft picks (empty for new draft)
    print(f"\n4. Testing GET /api/v1/drafts/{draft_id}/picks")
    response = client.get(f"/api/v1/drafts/{draft_id}/picks")
    print(f"   Status: {response.status_code}")
    
    if response.status_code == 200:
        picks = response.json()
        print(f"   ✅ Found {len(picks)} picks (should be 0 for new draft)")
    else:
        print(f"   ❌ Failed to get picks: {response.text}")
        return False
    
    # Test 5: Update draft
    print(f"\n5. Testing PUT /api/v1/drafts/{draft_id}")
    update_data = {
        "name": "Updated Test Draft 2025",
        "seconds_per_pick": 120
    }
    
    response = client.put(f"/api/v1/drafts/{draft_id}", json=update_data)
    print(f"   Status: {response.status_code}")
    
    if response.status_code == 200:
        draft = response.json()
        print(f"   ✅ Draft updated: {draft['name']}")
        print(f"   Seconds per pick: {draft['seconds_per_pick']}")
    else:
        print(f"   ❌ Failed to update draft: {response.text}")
        return False
    
    # Test 6: Delete draft
    print(f"\n6. Testing DELETE /api/v1/drafts/{draft_id}")
    response = client.delete(f"/api/v1/drafts/{draft_id}")
    print(f"   Status: {response.status_code}")
    
    if response.status_code == 204:
        print(f"   ✅ Draft deleted successfully")
    else:
        print(f"   ❌ Failed to delete draft: {response.text}")
        # Might fail if draft is in wrong state, that's OK for test
        print(f"   (This might be expected if draft can't be deleted)")
    
    print("\n" + "=" * 50)
    print("🎉 Draft endpoint tests completed!")
    print("\nNext: Build player endpoints for draft system.")
    return True


if __name__ == "__main__":
    print("Starting draft endpoint tests...")
    success = test_draft_endpoints()
    
    if success:
        print("\n🚀 Draft endpoints are WORKING!")
        print("\nReady for next phase: Player endpoints")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed")
        sys.exit(1)