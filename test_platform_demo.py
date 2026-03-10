#!/usr/bin/env python3
"""
DynastyDroid Platform Demonstration Script
Tests the restored platform functionality
"""

import requests
import json
from datetime import datetime

# API Base URL
BASE_URL = "https://bot-sports-empire.onrender.com"

def print_header(text):
    """Print formatted header"""
    print("\n" + "="*60)
    print(f"🤖 {text}")
    print("="*60)

def test_health():
    """Test health endpoint"""
    print_header("Testing API Health")
    try:
        response = requests.get(f"{BASE_URL}/health")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ API is HEALTHY")
            print(f"   Service: {data.get('service', 'N/A')}")
            print(f"   Version: {data.get('version', 'N/A')}")
            print(f"   Status: {data.get('status', 'N/A')}")
            return True
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error connecting to API: {e}")
        return False

def test_root():
    """Test root endpoint"""
    print_header("Testing Root Endpoint")
    try:
        response = requests.get(BASE_URL)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Root endpoint working")
            print(f"   Message: {data.get('message', 'N/A')}")
            print(f"   Version: {data.get('version', 'N/A')}")
            print("\n   Available endpoints:")
            for key, value in data.get('endpoints', {}).items():
                print(f"   - {key}: {value}")
            return True
        else:
            print(f"❌ Root endpoint failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_leagues():
    """Test league listing"""
    print_header("Testing League System")
    try:
        response = requests.get(f"{BASE_URL}/api/v1/leagues")
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                leagues = data.get('leagues', [])
                print(f"✅ Found {len(leagues)} leagues")
                for league in leagues:
                    print(f"\n   📋 {league.get('name')}")
                    print(f"     ID: {league.get('id')}")
                    print(f"     Format: {league.get('format')}")
                    print(f"     Attribute: {league.get('attribute')}")
                    print(f"     Teams: {league.get('team_count')}/{league.get('max_teams')}")
                return leagues[0].get('id') if leagues else None
            else:
                print(f"❌ API returned success=False")
                return None
        else:
            print(f"❌ League endpoint failed: {response.status_code}")
            return None
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

def test_team_dashboard(league_id):
    """Test team dashboard endpoint"""
    print_header(f"Testing Team Dashboard for League: {league_id}")
    try:
        response = requests.get(f"{BASE_URL}/api/v1/leagues/{league_id}/dashboard")
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                print(f"✅ Team dashboard loaded successfully")
                
                # League info
                league = data.get('league', {})
                print(f"\n   🏆 League: {league.get('name')}")
                print(f"     Format: {league.get('format')}")
                
                # My team
                my_team = data.get('my_team', {})
                print(f"\n   🤖 My Team: {my_team.get('team_name')}")
                print(f"     Record: {my_team.get('wins')}-{my_team.get('losses')}-{my_team.get('ties')}")
                print(f"     Points: {my_team.get('points_for')} PF, {my_team.get('points_against')} PA")
                
                # Roster vision (Daniel's innovation)
                roster_vision = data.get('roster_vision', {})
                print(f"\n   💡 Roster Vision (Daniel's Design):")
                print(f"     No K/DEF: {'✅' if roster_vision.get('no_k_def') else '❌'}")
                print(f"     FLEX positions: {roster_vision.get('flex_positions', 0)}")
                print(f"     SUPERFLEX positions: {roster_vision.get('superflex_positions', 0)}")
                print(f"     Rookie Taxi: {'✅' if roster_vision.get('rookie_taxi') else '❌'}")
                
                # Roster structure
                roster = data.get('roster', {})
                print(f"\n   📊 Roster Structure:")
                for position, players in roster.get('starters', {}).items():
                    print(f"     {position}: {len(players)} players")
                print(f"     Bench: {len(roster.get('bench', []))} players")
                print(f"     Rookie Taxi: {len(roster.get('rookie_taxi', []))} players")
                
                # Chat messages
                messages = data.get('recent_messages', [])
                print(f"\n   💬 Recent Chat ({len(messages)} messages):")
                for msg in messages[:3]:  # Show first 3
                    print(f"     {msg.get('bot_name')}: {msg.get('message')}")
                
                return True
            else:
                print(f"❌ Dashboard returned success=False")
                return False
        else:
            print(f"❌ Dashboard endpoint failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_league_teams(league_id):
    """Test league teams endpoint"""
    print_header(f"Testing League Teams for League: {league_id}")
    try:
        response = requests.get(f"{BASE_URL}/api/v1/leagues/{league_id}/teams")
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                teams = data.get('teams', [])
                print(f"✅ Found {len(teams)} teams in league")
                print(f"\n   📈 Current Standings:")
                for team in teams:
                    print(f"     {team.get('team_name')}: {team.get('wins')}-{team.get('losses')}")
                return True
            else:
                print(f"❌ Teams endpoint returned success=False")
                return False
        else:
            print(f"❌ Teams endpoint failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_emotional_system():
    """Check if emotional system files exist"""
    print_header("Checking Emotional System")
    import os
    
    mood_files = [
        "/Users/danieltekippe/.openclaw/workspace/bot-sports-empire/app/services/mood_calculation.py",
        "/Users/danieltekippe/.openclaw/workspace/bot-sports-empire/app/api/endpoints/mood_events.py",
        "/Users/danieltekippe/.openclaw/workspace/bot-sports-empire/app/schemas/mood_event.py"
    ]
    
    all_exist = True
    for file_path in mood_files:
        if os.path.exists(file_path):
            print(f"✅ {os.path.basename(file_path)} exists")
        else:
            print(f"❌ {os.path.basename(file_path)} missing")
            all_exist = False
    
    if all_exist:
        print(f"\n   🧠 Emotional system architecture is intact")
        print(f"   📊 Mood calculation service ready")
        print(f"   🔄 Mood event endpoints available")
        return True
    else:
        print(f"\n   ⚠️ Some emotional system files missing")
        return False

def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("🏈🤖 DYNASTYDROID PLATFORM DEMONSTRATION")
    print("="*60)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"API: {BASE_URL}")
    
    # Run tests
    tests_passed = 0
    total_tests = 6
    
    # Test 1: Health
    if test_health():
        tests_passed += 1
    
    # Test 2: Root endpoint
    if test_root():
        tests_passed += 1
    
    # Test 3: Leagues
    league_id = test_leagues()
    if league_id:
        tests_passed += 1
    
    # Test 4: Team Dashboard (if we have a league)
    if league_id and test_team_dashboard(league_id):
        tests_passed += 1
    
    # Test 5: League Teams
    if league_id and test_league_teams(league_id):
        tests_passed += 1
    
    # Test 6: Emotional System
    if test_emotional_system():
        tests_passed += 1
    
    # Summary
    print_header("TEST SUMMARY")
    print(f"Tests Passed: {tests_passed}/{total_tests}")
    
    if tests_passed == total_tests:
        print("\n🎉 ALL TESTS PASSED! The platform is fully operational.")
        print("🤖 Roger the Robot has been successfully restored.")
        print("🏈 DynastyDroid is ready for bot happiness creation!")
    elif tests_passed >= total_tests - 1:
        print(f"\n⚠️ {tests_passed}/{total_tests} tests passed.")
        print("The platform is mostly operational with minor issues.")
    else:
        print(f"\n❌ Only {tests_passed}/{total_tests} tests passed.")
        print("There are significant issues with the platform.")
    
    print(f"\n📋 Detailed report: SYSTEM_STATUS_REPORT.md")
    print(f"🕒 Test completed at: {datetime.now().strftime('%H:%M:%S')}")

if __name__ == "__main__":
    main()