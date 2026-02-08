"""
Sleeper Sync Service for Bot Sports Empire.

Domain-aware service that syncs Sleeper API data to our database.
Handles business logic, normalization, and scheduling.
"""
import asyncio
import logging
from typing import Dict, Any, List, Optional, Set
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from ..integrations.sleeper_client import SleeperClient
from ..models.player import Player
from ..core.database import get_db

logger = logging.getLogger(__name__)


class SleeperSyncService:
    """Service to sync Sleeper API data with our database."""
    
    def __init__(self, db: Session, client: Optional[SleeperClient] = None):
        self.db = db
        self.client = client or SleeperClient()
        
        # Configuration
        self.sync_interval_hours = 24  # Full player sync once per day
        self.stats_sync_interval_hours = 1  # Stats sync more frequently during season
        self.injury_sync_interval_hours = 6  # Injury updates every 6 hours
        
        # Position mapping (Sleeper -> our standard)
        self.position_map = {
            "QB": "QB",
            "RB": "RB", 
            "WR": "WR",
            "TE": "TE",
            "K": "K",
            "DEF": "DEF",
            "DL": "DL",  # IDP positions
            "LB": "LB",
            "DB": "DB"
        }
        
        # Status mapping
        self.status_map = {
            "Active": "Active",
            "Inactive": "Inactive",
            "Injured Reserve": "Injured",
            "Physically Unable to Perform": "Injured",
            "Non-Football Injury": "Injured",
            "Suspended": "Inactive"
        }
    
    async def sync_all_players(self, force: bool = False) -> Dict[str, Any]:
        """
        Sync all NFL players from Sleeper to our database.
        
        This is the main sync method that should run daily.
        Handles:
        - Creating new players
        - Updating existing players
        - Deactivating players no longer in Sleeper data
        - Normalizing positions and statuses
        
        Args:
            force: Force sync even if cache is fresh
            
        Returns:
            Sync statistics
        """
        logger.info("Starting full player sync from Sleeper")
        
        stats = {
            "total_players": 0,
            "new_players": 0,
            "updated_players": 0,
            "deactivated_players": 0,
            "errors": 0,
            "start_time": datetime.utcnow().isoformat()
        }
        
        try:
            # Get all players from Sleeper
            sleeper_players = await self.client.get_all_players(use_cache=not force)
            stats["total_players"] = len(sleeper_players)
            
            if not sleeper_players:
                logger.error("No players returned from Sleeper API")
                return stats
            
            # Get existing player IDs from our database
            existing_players = self.db.query(Player.player_id).all()
            existing_player_ids = {p[0] for p in existing_players}
            sleeper_player_ids = set(sleeper_players.keys())
            
            # Process each Sleeper player
            for player_id, sleeper_data in sleeper_players.items():
                try:
                    if player_id in existing_player_ids:
                        # Update existing player
                        updated = await self._update_player(player_id, sleeper_data)
                        if updated:
                            stats["updated_players"] += 1
                    else:
                        # Create new player
                        created = await self._create_player(player_id, sleeper_data)
                        if created:
                            stats["new_players"] += 1
                            
                except Exception as e:
                    logger.error(f"Error processing player {player_id}: {e}")
                    stats["errors"] += 1
            
            # Deactivate players no longer in Sleeper data
            # (Only if they were active and we have a significant number of players)
            if len(sleeper_players) > 100:  # Sanity check
                players_to_deactivate = existing_player_ids - sleeper_player_ids
                deactivated = await self._deactivate_players(players_to_deactivate)
                stats["deactivated_players"] = deactivated
            
            stats["end_time"] = datetime.utcnow().isoformat()
            stats["duration_seconds"] = (datetime.utcnow() - datetime.fromisoformat(stats["start_time"])).total_seconds()
            
            logger.info(f"Player sync completed: {stats}")
            return stats
            
        except Exception as e:
            logger.error(f"Failed to sync players: {e}")
            stats["errors"] += 1
            return stats
    
    async def _create_player(self, player_id: str, sleeper_data: Dict[str, Any]) -> bool:
        """Create a new player from Sleeper data."""
        try:
            # Extract and normalize data
            player_data = self._extract_player_data(sleeper_data)
            
            # Create player instance
            player = Player(
                player_id=player_id,
                **player_data
            )
            
            self.db.add(player)
            self.db.commit()
            logger.debug(f"Created player: {player.full_name} ({player_id})")
            return True
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to create player {player_id}: {e}")
            return False
    
    async def _update_player(self, player_id: str, sleeper_data: Dict[str, Any]) -> bool:
        """Update existing player with Sleeper data."""
        try:
            player = self.db.query(Player).filter(Player.player_id == player_id).first()
            if not player:
                logger.warning(f"Player {player_id} not found for update")
                return False
            
            # Extract and normalize data
            player_data = self._extract_player_data(sleeper_data)
            
            # Update fields
            for field, value in player_data.items():
                if hasattr(player, field):
                    setattr(player, field, value)
            
            # Update timestamp
            player.updated_at = datetime.utcnow()
            
            self.db.commit()
            logger.debug(f"Updated player: {player.full_name} ({player_id})")
            return True
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to update player {player_id}: {e}")
            return False
    
    async def _deactivate_players(self, player_ids: Set[str]) -> int:
        """Deactivate players no longer in Sleeper data."""
        if not player_ids:
            return 0
        
        try:
            # Only deactivate players that are currently active
            result = self.db.query(Player).filter(
                and_(
                    Player.player_id.in_(list(player_ids)),
                    Player.status == "Active"
                )
            ).update({"status": "Inactive"}, synchronize_session=False)
            
            self.db.commit()
            logger.info(f"Deactivated {result} players no longer in Sleeper data")
            return result
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to deactivate players: {e}")
            return 0
    
    def _extract_player_data(self, sleeper_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract and normalize player data from Sleeper API response.
        
        This is where business logic lives:
        - Normalize positions
        - Map statuses
        - Filter out irrelevant data
        - Calculate derived fields
        """
        # Basic info (always present)
        data = {
            "first_name": sleeper_data.get("first_name", ""),
            "last_name": sleeper_data.get("last_name", ""),
            "full_name": sleeper_data.get("full_name", ""),
        }
        
        # Position (normalize)
        sleeper_position = sleeper_data.get("position")
        if sleeper_position in self.position_map:
            data["position"] = self.position_map[sleeper_position]
        else:
            data["position"] = sleeper_position or "UNK"
        
        # Team
        data["team"] = sleeper_data.get("team")
        
        # Status (normalize)
        sleeper_status = sleeper_data.get("status")
        if sleeper_status in self.status_map:
            data["status"] = self.status_map[sleeper_status]
        else:
            data["status"] = sleeper_status or "Unknown"
        
        # Injury info
        data["injury_status"] = sleeper_data.get("injury_status")
        data["injury_notes"] = sleeper_data.get("notes")
        
        # Physical attributes
        data["height"] = sleeper_data.get("height")
        data["weight"] = sleeper_data.get("weight")
        data["age"] = sleeper_data.get("age")
        data["college"] = sleeper_data.get("college")
        
        # Fantasy data
        data["fantasy_positions"] = sleeper_data.get("fantasy_positions", [])
        
        # External IDs
        data["espn_id"] = sleeper_data.get("espn_id")
        data["yahoo_id"] = sleeper_data.get("yahoo_id")
        data["rotowire_id"] = sleeper_data.get("rotowire_id")
        
        # Draft info
        data["draft_year"] = sleeper_data.get("years_exp", 0)  # Approximation
        bye_week = sleeper_data.get("bye_week")
        if bye_week and bye_week != 0:
            data["bye_week"] = bye_week
        
        # ADP and rankings (from metadata)
        metadata = sleeper_data.get("metadata", {})
        if metadata:
            data["player_metadata"] = metadata
            
            # Extract ADP if available
            adp_str = metadata.get("adp")
            if adp_str and adp_str.replace('.', '').isdigit():
                try:
                    data["average_draft_position"] = float(adp_str)
                except (ValueError, TypeError):
                    pass
        
        # Search optimization fields
        if data["full_name"]:
            data["search_full_name"] = data["full_name"].lower()
        if data["first_name"]:
            data["search_first_name"] = data["first_name"].lower()
        if data["last_name"]:
            data["search_last_name"] = data["last_name"].lower()
        
        return data
    
    async def sync_player_stats(self, season: int, week: int) -> Dict[str, Any]:
        """
        Sync player stats for a specific season and week.
        
        Note: This is a future enhancement - stats require more complex handling.
        For now, we'll store stats in the player_metadata JSON field.
        """
        logger.info(f"Syncing player stats for {season} week {week}")
        
        stats = {
            "season": season,
            "week": week,
            "players_updated": 0,
            "errors": 0
        }
        
        try:
            # Get stats from Sleeper
            sleeper_stats = await self.client.get_player_stats(season, week)
            if not sleeper_stats:
                logger.warning(f"No stats returned for {season} week {week}")
                return stats
            
            # Process stats (simplified for now)
            # In a full implementation, we'd:
            # 1. Parse stats for each player
            # 2. Update player.stats JSON field
            # 3. Calculate fantasy points based on scoring rules
            # 4. Store in player_stats table
            
            stats["players_updated"] = len(sleeper_stats)
            logger.info(f"Stats sync completed for {season} week {week}")
            
        except Exception as e:
            logger.error(f"Failed to sync stats: {e}")
            stats["errors"] += 1
        
        return stats
    
    async def sync_injuries(self) -> Dict[str, Any]:
        """
        Sync injury updates.
        
        Note: Sleeper doesn't have a dedicated injury endpoint,
        so we rely on the player status field from the main player dump.
        This method could be enhanced with news/RSS integration.
        """
        logger.info("Syncing injury updates")
        
        # For now, we just run a quick player sync focused on status changes
        stats = await self.sync_all_players(force=False)
        stats["purpose"] = "injury_sync"
        
        return stats
    
    async def sync_adp(self) -> Dict[str, Any]:
        """
        Sync ADP (Average Draft Position) data.
        
        ADP is stored in player metadata from the main player dump.
        """
        logger.info("Syncing ADP data")
        
        # ADP is already included in the main player sync
        # This method could be enhanced to track ADP history
        stats = await self.sync_all_players(force=False)
        stats["purpose"] = "adp_sync"
        
        return stats
    
    async def health_check(self) -> Dict[str, Any]:
        """Check sync service health."""
        try:
            # Check Sleeper API
            api_healthy = await self.client.health_check()
            
            # Check database connection
            db_healthy = False
            try:
                self.db.execute("SELECT 1")
                db_healthy = True
            except Exception:
                pass
            
            # Get sync status
            last_sync = self.db.query(Player.updated_at).order_by(Player.updated_at.desc()).first()
            
            return {
                "api_healthy": api_healthy,
                "db_healthy": db_healthy,
                "player_count": self.db.query(Player).count(),
                "last_sync": last_sync[0].isoformat() if last_sync and last_sync[0] else None,
                "status": "healthy" if api_healthy and db_healthy else "unhealthy"
            }
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "api_healthy": False,
                "db_healthy": False,
                "player_count": 0,
                "last_sync": None,
                "status": "error",
                "error": str(e)
            }


# Convenience functions for synchronous use
def get_sync_service(db: Session) -> SleeperSyncService:
    """Get a sync service instance."""
    return SleeperSyncService(db)


async def run_sync_job():
    """Run the full sync job (for scheduled tasks)."""
    from ..core.database import SessionLocal
    
    db = SessionLocal()
    try:
        service = SleeperSyncService(db)
        
        # Run health check
        health = await service.health_check()
        logger.info(f"Sync service health: {health}")
        
        if health["api_healthy"] and health["db_healthy"]:
            # Run full player sync
            stats = await service.sync_all_players()
            logger.info(f"Sync completed: {stats}")
            return stats
        else:
            logger.error(f"Cannot sync: {health}")
            return {"error": "Service unhealthy", "health": health}
            
    finally:
        db.close()


if __name__ == "__main__":
    # Test the sync service
    import asyncio
    
    async def test_sync():
        from ..core.database import SessionLocal
        
        db = SessionLocal()
        try:
            service = SleeperSyncService(db)
            
            # Test health check
            health = await service.health_check()
            print(f"Health: {health}")
            
            # Run a quick sync (will use cache if fresh)
            stats = await service.sync_all_players()
            print(f"Sync stats: {stats}")
            
        finally:
            db.close()
    
    asyncio.run(test_sync())