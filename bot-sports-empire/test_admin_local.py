#!/usr/bin/env python3
"""
Quick local test for Admin Endpoints
Run this to verify endpoints work before deployment
"""

import sys
import os

# Add the app directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health_endpoint():
    """Test admin health endpoint"""
    print("🔍 Testing /admin/health endpoint...")
    try:
        response = client.get("/api/v1/admin/health")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Health check PASSED")
            print(f"   Status: {data.get('status')}")
            print(f"   Players in DB: {data.get('database', {}).get('players', 0)}")
            print(f"   Drafts in DB: {data.get('database', {}).get('drafts', 0)}")
            return True
        else:
            print(f"❌ Health check FAILED: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Health check ERROR: {e}")
        return False

def test_import_players_endpoint():
    """Test player import endpoint (will start background task)"""
    print("\n🚀 Testing /admin/import-players endpoint...")
    try:
        response = client.post("/api/v1/admin/import-players")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Player import STARTED")
            print(f"   Job ID: {data.get('job_id')}")
            print(f"   Status: {data.get('status')}")
            print(f"   Message: {data.get('message')}")
            return True
        else:
            print(f"❌ Player import FAILED: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Player import ERROR: {e}")
        return False

def test_sync_sleeper_endpoint():
    """Test Sleeper sync endpoint"""
    print("\n📡 Testing /admin/sync-sleeper endpoint...")
    try:
        response = client.post("/api/v1/admin/sync-sleeper", json={"data_types": ["players"]})
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Sleeper sync STARTED")
            print(f"   Job ID: {data.get('job_id')}")
            print(f"   Data types: {', '.join(data.get('data_types', []))}")
            return True
        else:
            print(f"❌ Sleeper sync FAILED: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Sleeper sync ERROR: {e}")
        return False

def test_players_endpoint():
    """Test if players endpoint returns data"""
    print("\n👥 Testing /api/v1/players endpoint...")
    try:
        response = client.get("/api/v1/players/?limit=5")
        if response.status_code == 200:
            data = response.json()
            player_count = data.get('total', 0)
            players = data.get('players', [])
            
            if player_count > 0:
                print(f"✅ Players endpoint PASSED")
                print(f"   Total players: {player_count}")
                print(f"   Sample players:")
                for i, player in enumerate(players[:3], 1):
                    name = player.get('full_name', player.get('name', 'Unknown'))
                    position = player.get('position', 'Unknown')
                    print(f"     {i}. {name} ({position})")
                return True
            else:
                print(f"⚠️ Players endpoint returned empty (need to run import first)")
                return False
        else:
            print(f"❌ Players endpoint FAILED: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Players endpoint ERROR: {e}")
        return False

def main():
    """Run all tests"""
    print("=" * 60)
    print("BOT SPORTS EMPIRE - LOCAL ADMIN ENDPOINTS TEST")
    print("=" * 60)
    
    # Test 1: Health endpoint
    health_ok = test_health_endpoint()
    
    if not health_ok:
        print("\n❌ Health check failed. Cannot proceed.")
        return
    
    # Test 2: Check current player count
    has_players = test_players_endpoint()
    
    # Test 3: Import players if needed
    if not has_players:
        print("\n📥 No players found. Testing import endpoint...")
        test_import_players_endpoint()
    
    # Test 4: Sync Sleeper data
    print("\n" + "=" * 40)
    print("TESTING SLEEPER SYNC ENDPOINT")
    print("=" * 40)
    test_sync_sleeper_endpoint()
    
    print("\n" + "=" * 60)
    print("LOCAL TEST COMPLETE!")
    print("=" * 60)
    print("\nNext steps:")
    print("1. Commit and push changes to GitHub")
    print("2. Render will auto-deploy (2-3 minutes)")
    print("3. Run production tests with:")
    print("   curl https://bot-sports-empire-backend.onrender.com/admin/health")
    print("4. Import players with:")
    print("   curl -X POST https://bot-sports-empire-backend.onrender.com/admin/import-players")

if __name__ == "__main__":
    main()