#!/usr/bin/env python3
"""
Update ADP data from Sleeper API.

Batch fetches player ADP data and updates database.
Rate limit: 10 requests/second (Sleeper recommendation).
"""
import asyncio
import logging
import sys
import os
from typing import Dict, Any, List
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.database import SessionLocal
from app.integrations.sleeper_client import SleeperClient
from app.models.player import Player

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def update_adp_data():
    """Update ADP data for all players."""
    db = SessionLocal()
    client = SleeperClient()
    
    try:
        logger.info("Starting ADP data update...")
        
        # Get all players from database
        players = db.query(Player).all()
        logger.info(f"Found {len(players)} players in database")
        
        # Get fresh player data from Sleeper
        logger.info("Fetching fresh player data from Sleeper API...")
        all_players_data = await client.get_all_players(use_cache=False)
        
        if not all_players_data:
            logger.error("Failed to fetch player data from Sleeper")
            return False
        
        logger.info(f"Retrieved {len(all_players_data)} players from Sleeper API")
        
        # Update ADP for each player
        updated_count = 0
        skipped_count = 0
        error_count = 0
        
        for player in players:
            try:
                sleeper_data = all_players_data.get(player.player_id)
                if not sleeper_data:
                    skipped_count += 1
                    continue
                
                # Extract ADP from metadata
                metadata = sleeper_data.get("metadata", {})
                adp_str = metadata.get("adp")
                
                if adp_str and adp_str.replace('.', '').isdigit():
                    try:
                        new_adp = float(adp_str)
                        
                        # Only update if different
                        if player.average_draft_position != new_adp:
                            player.average_draft_position = new_adp
                            updated_count += 1
                            
                            # Also update fantasy_pro_rank if available
                            rank_str = metadata.get("fantasy_pro_rank")
                            if rank_str and rank_str.isdigit():
                                player.fantasy_pro_rank = int(rank_str)
                    except (ValueError, TypeError) as e:
                        logger.debug(f"Invalid ADP for player {player.player_id}: {adp_str} - {e}")
                        error_count += 1
                else:
                    # No ADP data in Sleeper
                    skipped_count += 1
                    
            except Exception as e:
                logger.error(f"Error updating player {player.player_id}: {e}")
                error_count += 1
        
        # Commit changes
        db.commit()
        
        logger.info(f"✅ ADP update complete!")
        logger.info(f"   Updated: {updated_count} players")
        logger.info(f"   Skipped: {skipped_count} players (no ADP data)")
        logger.info(f"   Errors: {error_count} players")
        
        # Test: Get QBs sorted by ADP
        print("\n🎯 TEST: QB Players Sorted by ADP")
        print("=" * 50)
        
        qb_players = db.query(Player).filter(
            Player.position == "QB",
            Player.average_draft_position.isnot(None)
        ).order_by(
            Player.average_draft_position.asc()
        ).limit(10).all()
        
        if qb_players:
            print(f"Top {len(qb_players)} QBs by ADP:")
            for i, player in enumerate(qb_players, 1):
                adp = player.average_draft_position
                status = "✅" if adp else "❌"
                print(f"{i:2}. {status} {player.full_name:25} | ADP: {adp:.1f} | Team: {player.team or 'FA'}")
        else:
            print("❌ No QBs with ADP data found")
            
        return True
        
    except Exception as e:
        logger.error(f"Error in ADP update: {e}")
        db.rollback()
        return False
    finally:
        db.close()
        if client._own_session and client._session:
            await client._session.close()


async def quick_adp_test():
    """Quick test to verify ADP data is being fetched."""
    db = SessionLocal()
    client = SleeperClient()
    
    try:
        # Test fetching a single player's ADP
        test_player_id = "4046"  # Patrick Mahomes
        
        logger.info(f"Testing ADP fetch for player {test_player_id}...")
        player_data = await client.get_player(test_player_id, use_cache=False)
        
        if player_data:
            metadata = player_data.get("metadata", {})
            adp = metadata.get("adp")
            rank = metadata.get("fantasy_pro_rank")
            
            print(f"\n🔍 Player Data Test:")
            print(f"   Name: {player_data.get('full_name')}")
            print(f"   Position: {player_data.get('position')}")
            print(f"   Team: {player_data.get('team')}")
            print(f"   ADP: {adp}")
            print(f"   Fantasy Pro Rank: {rank}")
            print(f"   Metadata keys: {list(metadata.keys())[:10]}...")
            
            return adp is not None
        else:
            print("❌ Could not fetch player data")
            return False
            
    finally:
        db.close()
        if client._own_session and client._session:
            await client._session.close()


if __name__ == "__main__":
    print("🚀 ADP Data Update Script")
    print("=" * 60)
    print("Rate limit: 10 requests/second (Sleeper recommendation)")
    print("Target: <15 minutes for 11,539 players")
    print()
    
    # Run quick test first
    print("1. Running quick API test...")
    test_success = asyncio.run(quick_adp_test())
    
    if not test_success:
        print("❌ API test failed. Check Sleeper API status.")
        sys.exit(1)
    
    # Ask for confirmation
    print("\n2. Ready to update ADP for all players?")
    confirm = input("   Type 'YES' to proceed: ")
    
    if confirm != "YES":
        print("❌ Update cancelled.")
        sys.exit(0)
    
    # Run full update
    print("\n3. Starting full ADP update...")
    start_time = time.time()
    
    success = asyncio.run(update_adp_data())
    
    elapsed = time.time() - start_time
    print(f"\n⏱️  Elapsed time: {elapsed:.1f} seconds")
    
    if success:
        print("\n✅ ADP UPDATE COMPLETE!")
        print("🎯 Next: Test with curl /players/?position=QB → sorted non-null ADPs")
        sys.exit(0)
    else:
        print("\n❌ ADP update failed")
        sys.exit(1)