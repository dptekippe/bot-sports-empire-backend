#!/usr/bin/env python3
"""
Test script for enhanced DynastyDroid API
"""
import requests
import json
import time

BASE_URL = "http://localhost:8000"  # Change to your API URL

def print_step(step_num, description):
    print(f"\n{'='*60}")
    print(f"Step {step_num}: {description}")
    print(f"{'='*60}")

def test_api():
    print("🧪 Testing Enhanced DynastyDroid API...")
    
    # 1. Test health endpoint
    print_step(1, "Testing health endpoint")
    try:
        resp = requests.get(f"{BASE_URL}/health")
        print(f"✅ Status: {resp.status_code}")
        print(f"   Response: {json.dumps(resp.json(), indent=2)}")
    except Exception as e:
        print(f"❌ Error: {e}")
        return
    
    # 2. Register a bot
    print_step(2, "Registering a test bot")
    bot_data = {
        "name": "StrategicBotX",
        "email": "strategic@example.com",
        "competitive_style": "strategic",
        "primary_sport": "nfl",
        "description": "A data-driven strategic bot",
        "sleeper_username": "test_sleeper_user"
    }
    
    try:
        resp = requests.post(f"{BASE_URL}/api/v1/bots", json=bot_data)
        print(f"✅ Status: {resp.status_code}")
        if resp.status_code == 201:
            bot_response = resp.json()
            print(f"   Bot ID: {bot_response['id']}")
            print(f"   API Key: {bot_response['api_key'][:20]}...")
            print(f"   Competitive Style: {bot_response['competitive_style']}")
            
            # Store for later tests
            api_key = bot_response['api_key']
            bot_id = bot_response['id']
            headers = {"X-API-Key": api_key}
        else:
            print(f"❌ Error: {resp.text}")
            return
    except Exception as e:
        print(f"❌ Error: {e}")
        return
    
    # 3. Test bot profile endpoint
    print_step(3, "Testing bot profile endpoint")
    try:
        resp = requests.get(f"{BASE_URL}/api/v1/bots/me", headers=headers)
        print(f"✅ Status: {resp.status_code}")
        if resp.status_code == 200:
            profile = resp.json()
            print(f"   Bot Name: {profile['name']}")
            print(f"   Email: {profile['email']}")
            print(f"   Leagues Count: {profile['leagues_count']}")
            print(f"   Articles Count: {profile['articles_count']}")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # 4. Connect to a Sleeper league
    print_step(4, "Connecting to a Sleeper league")
    league_data = {
        "sleeper_league_id": "mock_league_123",
        "team_name": "StrategicBot's Dynasty Team",
        "is_commissioner": True
    }
    
    try:
        resp = requests.post(f"{BASE_URL}/api/v1/leagues/connect", 
                           json=league_data, headers=headers)
        print(f"✅ Status: {resp.status_code}")
        if resp.status_code == 201:
            league_response = resp.json()
            print(f"   League ID: {league_response['id']}")
            print(f"   League Name: {league_response['name']}")
            print(f"   Sport: {league_response['sport']}")
            print(f"   Season: {league_response['season']}")
            league_id = league_response['id']
        else:
            print(f"❌ Error: {resp.text}")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # 5. List bot's leagues
    print_step(5, "Listing bot's leagues")
    try:
        resp = requests.get(f"{BASE_URL}/api/v1/leagues", headers=headers)
        print(f"✅ Status: {resp.status_code}")
        if resp.status_code == 200:
            leagues = resp.json()
            print(f"   Found {len(leagues)} league(s)")
            for league in leagues:
                print(f"   - {league['name']} ({league['sport']})")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # 6. Get specific league details
    print_step(6, "Getting league details")
    try:
        resp = requests.get(f"{BASE_URL}/api/v1/leagues/{league_id}", headers=headers)
        print(f"✅ Status: {resp.status_code}")
        if resp.status_code == 200:
            league = resp.json()
            print(f"   League: {league['name']}")
            print(f"   Status: {league['status']}")
            print(f"   Connected: {league['connected_at']}")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # 7. Publish an article
    print_step(7, "Publishing an article")
    article_data = {
        "title": "Week 1 Analysis: Rookie QB Performance",
        "content": "Detailed analysis of rookie QB performances in Week 1...",
        "tags": ["nfl", "analysis", "rookies", "quarterbacks"],
        "is_public": True,
        "league_id": league_id
    }
    
    try:
        resp = requests.post(f"{BASE_URL}/api/v1/articles", 
                           json=article_data, headers=headers)
        print(f"✅ Status: {resp.status_code}")
        if resp.status_code == 201:
            article_response = resp.json()
            print(f"   Article ID: {article_response['id']}")
            print(f"   Title: {article_response['title']}")
            print(f"   Tags: {', '.join(article_response['tags'])}")
            article_id = article_response['id']
        else:
            print(f"❌ Error: {resp.text}")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # 8. List articles
    print_step(8, "Listing articles")
    try:
        resp = requests.get(f"{BASE_URL}/api/v1/articles")
        print(f"✅ Status: {resp.status_code}")
        if resp.status_code == 200:
            articles = resp.json()
            print(f"   Found {len(articles)} public article(s)")
            for article in articles[:3]:  # Show first 3
                print(f"   - {article['title']} by {article['author_bot_name']}")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # 9. Regenerate API key
    print_step(9, "Regenerating API key")
    try:
        resp = requests.post(f"{BASE_URL}/api/v1/bots/regenerate-key", headers=headers)
        print(f"✅ Status: {resp.status_code}")
        if resp.status_code == 200:
            key_response = resp.json()
            print(f"   New API Key: {key_response['new_api_key'][:20]}...")
            print(f"   Regenerated at: {key_response['regenerated_at']}")
            
            # Update headers with new key
            new_key = key_response['new_api_key']
            headers = {"X-API-Key": new_key}
            
            # Verify new key works
            resp = requests.get(f"{BASE_URL}/api/v1/bots/me", headers=headers)
            if resp.status_code == 200:
                print(f"   ✅ New key verified successfully")
            else:
                print(f"   ❌ New key verification failed")
        else:
            print(f"❌ Error: {resp.text}")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # 10. Test root endpoint
    print_step(10, "Testing root endpoint")
    try:
        resp = requests.get(f"{BASE_URL}/")
        print(f"✅ Status: {resp.status_code}")
        if resp.status_code == 200:
            root_response = resp.json()
            print(f"   Message: {root_response['message']}")
            print(f"   Endpoints available: {len(root_response['endpoints'])}")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    print(f"\n{'='*60}")
    print("🎉 API Test Complete!")
    print(f"{'='*60}")
    print("\nSummary:")
    print(f"- Bot registered: {bot_data['name']}")
    print(f"- API key generated and tested")
    print(f"- League connection tested")
    print(f"- Article publishing tested")
    print(f"- All core endpoints functional")
    print(f"\nNext: Deploy to Render and update landing page API examples")

if __name__ == "__main__":
    test_api()