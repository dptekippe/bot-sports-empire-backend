#!/usr/bin/env python3
"""
Test API endpoints after Sleeper import.
"""
import urllib.request
import json
import time

def test_api_endpoint(endpoint):
    """Test an API endpoint."""
    base_url = "https://bot-sports-empire-backend.onrender.com"
    url = f"{base_url}{endpoint}"
    
    print(f"Testing: {endpoint}")
    
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'BotSportsTest/1.0'})
        with urllib.request.urlopen(req, timeout=10) as response:
            if response.status == 200:
                data = json.load(response)
                print(f"  ✅ Status: {response.status}")
                return data
            else:
                print(f"  ❌ Status: {response.status}")
                return None
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return None

def main():
    print("=" * 60)
    print("BOT SPORTS EMPIRE - API TEST AFTER SLEEPER IMPORT")
    print("=" * 60)
    
    # Test basic endpoints
    print("\n1. BASIC ENDPOINTS:")
    test_api_endpoint("/")
    test_api_endpoint("/health")
    test_api_endpoint("/docs")
    
    # Test players endpoint
    print("\n2. PLAYERS ENDPOINT:")
    players_data = test_api_endpoint("/api/v1/players/?limit=5")
    
    if players_data:
        print(f"\n   Players response keys: {list(players_data.keys())}")
        if 'players' in players_data:
            print(f"   Total players: {players_data.get('total', 0)}")
            print(f"   Players returned: {len(players_data['players'])}")
            
            if players_data['players']:
                print("\n   Sample players:")
                for i, player in enumerate(players_data['players'][:3], 1):
                    print(f"   {i}. {player.get('full_name', 'Unknown')} "
                          f"({player.get('position', '?')} - {player.get('team', '?')})")
            else:
                print("\n   ⚠️  No players returned (might be empty or filtering issue)")
        else:
            print("\n   ⚠️  'players' key not in response")
    
    # Test position filtering
    print("\n3. POSITION FILTERING:")
    for position in ['QB', 'RB', 'WR', 'TE']:
        data = test_api_endpoint(f"/api/v1/players/?position={position}&limit=2")
        if data and 'players' in data:
            count = len(data['players'])
            print(f"   {position}: {count} players returned")
    
    print("\n" + "=" * 60)
    print("TEST COMPLETE")
    print("=" * 60)

if __name__ == "__main__":
    main()