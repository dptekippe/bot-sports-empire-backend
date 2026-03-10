#!/usr/bin/env python3
"""
Full Sleeper integration test for Bot Sports Empire.
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.integrations.sleeper_client import SleeperClient
from app.services.sleeper_sync_service import SleeperSyncService
from app.core.database import SessionLocal
from app.models.player import Player


async def full_sleeper_test():
    """Run full Sleeper integration test."""
    print("🏈 Bot Sports Empire - Sleeper Integration Test")
    print("=" * 60)
    
    # Test 1: Sleeper API Client
    print("\n1. Testing Sleeper API Client...")
    async with SleeperClient() as client:
        # Health check
        healthy = await client.health_check()
        if not healthy:
            print("❌ Sleeper API not accessible")
            return False
        print("✅ Sleeper API is healthy")
        
        # Get NFL state
        state = await client.get_nfl_state()
        if state:
            print(f"✅ NFL Season: {state.get('season')}, Week: {state.get('week')}")
        
        # Get players
        players = await client.get_all_players()
        print(f"✅ Retrieved {len(players):,} players from Sleeper")
        
        # Show sample
        sample_id = list(players.keys())[0]
        sample_player = players[sample_id]
        print(f"✅ Sample player: {sample_player.get('first_name')} {sample_player.get('last_name')}")
    
    # Test 2: Database connection
    print("\n2. Testing database connection...")
    db = SessionLocal()
    try:
        # Count current players
        current_count = db.query(Player).count()
        print(f"✅ Database connected, currently has {current_count} players")
        
        # Test 3: Sync service
        print("\n3. Testing Sleeper Sync Service...")
        service = SleeperSyncService(db)
        
        # Health check
        health = await service.health_check()
        print(f"✅ Sync service health: {health['status']}")
        
        if health['api_healthy'] and health['db_healthy']:
            # Run sync
            print("\n4. Running player sync (this may take a moment)...")
            stats = await service.sync_all_players()
            
            print(f"✅ Sync completed:")
            print(f"   • Total processed: {stats.get('total_players', 0):,}")
            print(f"   • New players: {stats.get('new_players', 0)}")
            print(f"   • Updated players: {stats.get('updated_players', 0)}")
            print(f"   • Errors: {stats.get('errors', 0)}")
            
            # Check results
            new_count = db.query(Player).count()
            print(f"✅ Database now has {new_count:,} players")
            
            # Show some players
            print("\n5. Sample players in database:")
            sample_players = db.query(Player).order_by(Player.full_name).limit(5).all()
            for player in sample_players:
                status = "🏈" if player.active else "⏸️"
                print(f"   {status} {player.full_name} ({player.position} - {player.team})")
            
            if stats.get('errors', 0) == 0:
                print("\n" + "=" * 60)
                print("🎉 ALL TESTS PASSED!")
                print("=" * 60)
                print("\n🚀 Sleeper integration is WORKING!")
                print(f"📊 Database now has {new_count:,} REAL NFL players")
                print("💡 Ready for draft system development!")
                return True
            else:
                print(f"\n⚠️  Sync had {stats.get('errors', 0)} errors")
                return False
        else:
            print(f"❌ Service unhealthy: {health}")
            return False
            
    finally:
        db.close()


async def quick_sync():
    """Quick sync for testing."""
    print("🔄 Running quick sync test...")
    db = SessionLocal()
    try:
        service = SleeperSyncService(db)
        stats = await service.sync_all_players()
        print(f"✅ Quick sync: {stats.get('new_players', 0)} new, {stats.get('updated_players', 0)} updated")
        return stats
    finally:
        db.close()


if __name__ == "__main__":
    print("Starting Sleeper integration test...")
    
    # Run full test
    success = asyncio.run(full_sleeper_test())
    
    if success:
        print("\n" + "=" * 60)
        print("NEXT STEPS:")
        print("=" * 60)
        print("1. ✅ Sleeper API client: COMPLETE")
        print("2. ✅ Sync service: COMPLETE")  
        print("3. ✅ Database schema: COMPLETE")
        print("4. 🚀 Ready for: Player endpoints & draft system!")
        print("\nRun daily sync via:")
        print("  python3 -m app.services.sleeper_sync_service")
        sys.exit(0)
    else:
        print("\n❌ Tests failed")
        sys.exit(1)