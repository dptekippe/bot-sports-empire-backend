"""
Cron job for ADP data updates.

Scheduled to run daily during fantasy football season to keep ADP data fresh.
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any

from ..services.adp_sync_service import ADPSyncService
from ..models.player import Player

logger = logging.getLogger(__name__)


async def update_adp_data():
    """
    Update ADP data from external sources.
    
    This function is designed to be called by a cron scheduler.
    It updates ADP data for multiple scoring formats and team sizes.
    """
    logger.info("Starting scheduled ADP data update")
    
    start_time = datetime.utcnow()
    all_stats = []
    
    try:
        async with ADPSyncService() as service:
            # Check service health
            health = await service.health_check()
            if not health["overall"]:
                logger.error(f"Service unhealthy: {health}")
                return {"success": False, "error": "Service unhealthy", "health": health}
            
            # Update ADP for different scoring formats (PPR is most common)
            scoring_formats = ["ppr", "half", "standard"]
            team_sizes = [12, 10, 14]  # 12-team is standard
            
            for scoring in scoring_formats:
                for teams in team_sizes:
                    logger.info(f"Updating ADP for {scoring} {teams}-team")
                    
                    stats = await service.sync_ffc_adp(
                        year=2025,  # Current season
                        scoring=scoring,
                        teams=teams,
                        update_players=True
                    )
                    
                    all_stats.append(stats)
                    
                    # Small delay between requests
                    await asyncio.sleep(1)
            
            # Log summary
            total_updated = sum(s.get("players_updated", 0) for s in all_stats)
            total_history = sum(s.get("draft_history_created", 0) for s in all_stats)
            
            elapsed = (datetime.utcnow() - start_time).total_seconds()
            
            summary = {
                "success": True,
                "elapsed_seconds": elapsed,
                "total_players_updated": total_updated,
                "total_history_records": total_history,
                "scenarios_run": len(all_stats),
                "stats_by_scenario": all_stats,
                "timestamp": start_time.isoformat()
            }
            
            logger.info(f"ADP update complete: {summary}")
            return summary
            
    except Exception as e:
        logger.error(f"Error in ADP cron job: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "timestamp": start_time.isoformat()
        }


async def quick_adp_test():
    """Quick test function for development."""
    print("🚀 Quick ADP Test")
    print("=" * 60)
    
    async with ADPSyncService() as service:
        # Test health
        health = await service.health_check()
        print(f"Health: {health}")
        
        if not health["ffc_api"]:
            print("⚠️  FFC API not accessible - using mock data")
            # Create some mock external ADP data for testing
            db = service.db
            players = db.query(Player).limit(20).all()
            
            for i, player in enumerate(players):
                if player.position in ["QB", "RB", "WR", "TE"]:
                    player.external_adp = 50.0 + i  # Mock ADP values
                    player.external_adp_source = "mock"
                    player.external_adp_updated_at = datetime.utcnow()
            
            db.commit()
            print("✅ Created mock external ADP data")
        
        else:
            # Run actual sync
            print("Running FFC ADP sync...")
            stats = await service.sync_ffc_adp(
                year=2025,
                scoring="ppr",
                teams=12,
                update_players=True
            )
            print(f"Sync stats: {stats}")
        
        # Test sorting by external ADP
        print("\n🎯 Testing external ADP sorting:")
        top_players = service.get_top_players_by_external_adp(limit=10)
        
        if top_players:
            print("Top 10 players by external ADP:")
            for i, player in enumerate(top_players, 1):
                adp = player.external_adp
                source = player.external_adp_source or "N/A"
                print(f"{i:2}. {player.full_name:25} | ADP: {adp:6.1f} | Source: {source:10}")
        else:
            print("❌ No players with external ADP found")
        
        return True


if __name__ == "__main__":
    # For testing
    import sys
    logging.basicConfig(level=logging.INFO)
    
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        asyncio.run(quick_adp_test())
    else:
        # Run full update
        result = asyncio.run(update_adp_data())
        print(f"Result: {result}")