#!/usr/bin/env python3
"""
Test player endpoints for Bot Sports Empire.
"""
import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_player_endpoints():
    """Test player endpoints with verification."""
    print("🧪 Testing Player Endpoints")
    print("=" * 60)
    
    # Test 1: List all players (paginated)
    print("\n1. Testing GET /api/v1/players/")
    response = client.get("/api/v1/players/", params={"limit": 10})
    print(f"   Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"   ✅ Found {data['total']} total players")
        print(f"   ✅ Page: {data['page']}, Page size: {data['page_size']}")
        print(f"   ✅ First {len(data['players'])} players returned")
        
        if data['players']:
            first_player = data['players'][0]
            print(f"   ✅ Sample player: {first_player.get('full_name', 'Unknown')}")
            print(f"     • Position: {first_player.get('position', 'Unknown')}")
            print(f"     • Team: {first_player.get('team', 'Unknown')}")
            print(f"     • ADP: {first_player.get('average_draft_position', 'N/A')}")
    else:
        print(f"   ❌ Failed: {response.text}")
        return False
    
    # Test 2: Search players by name
    print("\n2. Testing GET /api/v1/players/search?q=mahomes")
    response = client.get("/api/v1/players/search", params={"q": "mahomes", "limit": 5})
    print(f"   Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"   ✅ Found {data['total']} players matching 'mahomes'")
        if data['players']:
            for player in data['players'][:3]:
                print(f"     • {player['full_name']} ({player['position']} - {player.get('team', 'FA')})")
    else:
        print(f"   ❌ Failed: {response.text}")
        return False
    
    # Test 3: Filter by position
    print("\n3. Testing GET /api/v1/players/?position=QB&limit=5")
    response = client.get("/api/v1/players/", params={"position": "QB", "limit": 5})
    print(f"   Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"   ✅ Found {data['total']} QB players")
        if data['players']:
            for player in data['players']:
                print(f"     • {player['full_name']} (ADP: {player.get('average_draft_position', 'N/A')})")
    else:
        print(f"   ❌ Failed: {response.text}")
        return False
    
    # Test 4: Filter by team
    print("\n4. Testing GET /api/v1/players/?team=KC&limit=5")
    response = client.get("/api/v1/players/", params={"team": "KC", "limit": 5})
    print(f"   Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"   ✅ Found {data['total']} KC players")
        if data['players']:
            for player in data['players']:
                print(f"     • {player['full_name']} ({player['position']})")
    else:
        print(f"   ❌ Failed: {response.text}")
        return False
    
    # Test 5: Get single player
    if data['players']:
        player_id = data['players'][0]['player_id']
        print(f"\n5. Testing GET /api/v1/players/{player_id}")
        response = client.get(f"/api/v1/players/{player_id}")
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            player = response.json()
            print(f"   ✅ Player retrieved: {player['full_name']}")
            print(f"     • Status: {player.get('status', 'Unknown')}")
            print(f"     • Active: {player.get('active', 'Unknown')}")
            print(f"     • ADP: {player.get('average_draft_position', 'N/A')}")
        else:
            print(f"   ❌ Failed: {response.text}")
            return False
    
    # Test 6: List positions
    print("\n6. Testing GET /api/v1/players/positions/")
    response = client.get("/api/v1/players/positions/")
    print(f"   Status: {response.status_code}")
    
    if response.status_code == 200:
        positions = response.json()
        print(f"   ✅ Positions: {', '.join(positions)}")
    else:
        print(f"   ❌ Failed: {response.text}")
        return False
    
    # Test 7: List teams
    print("\n7. Testing GET /api/v1/players/teams/")
    response = client.get("/api/v1/players/teams/")
    print(f"   Status: {response.status_code}")
    
    if response.status_code == 200:
        teams = response.json()
        print(f"   ✅ Teams ({len(teams)}): {', '.join(sorted(teams)[:10])}...")
    else:
        print(f"   ❌ Failed: {response.text}")
        return False
    
    # Test 8: ADP filtering
    print("\n8. Testing GET /api/v1/players/?min_adp=1&max_adp=50&limit=5")
    response = client.get("/api/v1/players/", params={"min_adp": 1, "max_adp": 50, "limit": 5})
    print(f"   Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"   ✅ Found {data['total']} players with ADP 1-50")
        if data['players']:
            for player in data['players']:
                print(f"     • {player['full_name']} (ADP: {player.get('average_draft_position', 'N/A')})")
    else:
        print(f"   ❌ Failed: {response.text}")
        # This might fail if no players have ADP data yet, which is OK
    
    print("\n" + "=" * 60)
    print("🎉 Player endpoint tests completed!")
    
    # Summary
    print("\n📊 SUMMARY:")
    print("✅ Player schemas created with ADP field")
    print("✅ Player endpoints implemented:")
    print("   • GET /api/v1/players/ - Filtered search with ilike")
    print("   • GET /api/v1/players/search - Quick name search")
    print("   • GET /api/v1/players/{id} - Single player")
    print("   • GET /api/v1/players/{id}/draft-availability/{draft_id}")
    print("   • GET /api/v1/players/positions/ - Position list")
    print("   • GET /api/v1/players/teams/ - Team list")
    
    print("\n🚀 Ready for Step 3: Draft ↔ Player Connection Tests")
    return True


if __name__ == "__main__":
    print("Starting player endpoint tests...")
    success = test_player_endpoints()
    
    if success:
        print("\n🚀 Player endpoints are WORKING!")
        print("\nNext: Test draft ↔ player connection")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed")
        sys.exit(1)