#!/usr/bin/env python3
"""
Test Sleeper API integration for Bot Sports Empire.
"""
import asyncio
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.integrations.sleeper_client import SleeperClient
from app.services.sleeper_sync_service import SleeperSyncService
from app.core.database import SessionLocal


async def test_client():
    """Test the Sleeper API client."""
    print("=== Testing Sleeper API Client ===")
    
    async with SleeperClient() as client:
        # Test health check
        healthy = await client.health_check()
        print(f"✅ Sleeper API healthy: {healthy}")
        
        if not healthy:
            print("❌ Sleeper API not accessible. Check internet connection.")
            return False
        
        # Get NFL state
        state = await client.get_nfl_state()
        if state:
            print(f"✅ NFL State: Season {state.get('season')}, Week {state.get('week')}")
        else:
            print("❌ Failed to get NFL state")
            return False
        
        # Get all players (cached)
        players = await client.get_all_players()
        print(f"✅ Total players from Sleeper: {len(players)}")
        
        if players:
            # Show sample players
            print("\n📊 Sample players:")
            sample_ids = list(players.keys())[:5]
            for pid in sample_ids:
                player = players[pid]
                name = f"{player.get('first_name', '')} {player.get('last_name', '')}"
                print(f"  • {name} ({player.get('position')} - {player.get('team')})")
            
            # Test single player lookup
            sample_id = sample_ids[0]
            single_player = await client.get_player(sample_id)
            if single_player:
                print(f"✅ Single player lookup works")
        
        return True


async def test_sync_service():
    """Test the Sleeper sync service."""
    print("\n=== Testing Sleeper Sync Service ===")
    
    db = SessionLocal()
    try:
        service = SleeperSyncService(db)
        
        # Test health check
        health = await service.health_check()
        print(f"✅ Sync service health: {health['status']}")
        print(f"  • API: {health['api_healthy']}")
        print(f"  • DB: {health['db_healthy']}")
        print(f"  • Current player count: {health['player_count']}")
        
        if not health['api_healthy'] or not health['db_healthy']:
            print("❌ Service unhealthy, skipping sync test")
            return False
        
        # Run a quick sync (will use cache)
        print("\n🔄 Running player sync (this may take a moment)...")
        stats = await service.sync_all_players()
        
        print(f"✅ Sync completed:")
        print(f"  • Total players processed: {stats.get('total_players', 0)}")
        print(f"  • New players: {stats.get('new_players', 0)}")
        print(f"  • Updated players: {stats.get('updated_players', 0)}")
        print(f"  • Deactivated players: {stats.get('deactivated_players', 0)}")
        print(f"  • Errors: {stats.get('errors', 0)}")
        
        # Check database
        player_count = db.query(service.db.get_bind().tables['players']).count()
        print(f"📊 Database now has {player_count} players")
        
        # Show some players from our database
        print("\n🏈 Sample players from our database:")
        players = db.query(service.db.get_bind().tables['players']).limit(5).all()
        for player in players:
            print(f"  • {player.full_name} ({player.position} - {player.team}) - Status: {player.status}")
        
        return stats.get('errors', 0) == 0
        
    finally:
        db.close()


async def main():
    """Run all tests."""
    print("🧪 Bot Sports Empire - Sleeper Integration Test")
    print("=" * 50)
    
    # Test client
    client_ok = await test_client()
    if not client_ok:
        print("\n❌ Client test failed. Cannot proceed.")
        return
    
    # Test sync service
    sync_ok = await test_sync_service()
    
    print("\n" + "=" * 50)
    if client_ok and sync_ok:
        print("🎉 ALL TESTS PASSED! Sleeper integration is working.")
        print("\nNext steps:")
        print("1. Run the sync service daily via cron/scheduler")
        print("2. Build player endpoints for draft system")
        print("3. Implement bot draft AI using real player data")
    else:
        print("⚠️  Some tests failed. Check logs above.")
    
    print("\n🚀 Ready to build the draft system with REAL NFL data!")


if __name__ == "__main__":
    asyncio.run(main())