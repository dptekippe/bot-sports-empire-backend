"""
ADP Sync Service for updating external ADP data.

Fetches ADP from FantasyFootballCalculator and updates player records.
Also manages DraftHistory for tracking ADP over time.
"""
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from ..core.database import SessionLocal
from ..models.player import Player
from ..models.draft_history import DraftHistory
from ..integrations.ffc_client import FantasyFootballCalculatorClient

logger = logging.getLogger(__name__)


class ADPSyncService:
    """Service for syncing ADP data from external sources."""
    
    def __init__(self, db: Optional[Session] = None):
        self.db = db or SessionLocal()
        self.ffc_client = None
    
    async def __aenter__(self):
        self.ffc_client = FantasyFootballCalculatorClient()
        await self.ffc_client.__aenter__()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.ffc_client:
            await self.ffc_client.__aexit__(exc_type, exc_val, exc_tb)
        if self.db:
            self.db.close()
    
    async def sync_ffc_adp(
        self,
        year: int = 2025,
        scoring: str = "ppr",
        teams: int = 12,
        update_players: bool = True
    ) -> Dict[str, Any]:
        """
        Sync ADP data from FantasyFootballCalculator.
        
        Args:
            year: Draft year
            scoring: Scoring format
            teams: Number of teams
            update_players: Whether to update Player.external_adp field
            
        Returns:
            Statistics about the sync
        """
        logger.info(f"Starting FFC ADP sync for {year} {scoring} {teams}-team")
        
        stats = {
            "source": "ffc",
            "year": year,
            "scoring": scoring,
            "teams": teams,
            "players_fetched": 0,
            "players_updated": 0,
            "draft_history_created": 0,
            "errors": 0
        }
        
        try:
            # Get ADP data from FFC
            all_players = await self.ffc_client.get_all_positions_adp(year, scoring, teams)
            
            total_players = sum(len(players) for players in all_players.values())
            stats["players_fetched"] = total_players
            
            if total_players == 0:
                logger.warning("No players fetched from FFC API")
                return stats
            
            # Process each position
            for position, players in all_players.items():
                for ffc_player in players:
                    try:
                        normalized = self.ffc_client.normalize_player_data(ffc_player)
                        
                        # Find matching player in our database
                        player = self._find_matching_player(normalized)
                        
                        if player:
                            # Update player's external ADP
                            if update_players:
                                player.external_adp = normalized["adp"]
                                player.external_adp_source = "ffc"
                                player.external_adp_updated_at = datetime.utcnow()
                                stats["players_updated"] += 1
                            
                            # Create draft history record
                            self._create_draft_history_record(
                                player=player,
                                year=year,
                                source="ffc",
                                adp_value=normalized["adp"],
                                scoring_format=scoring,
                                team_count=teams,
                                draft_type="external"
                            )
                            stats["draft_history_created"] += 1
                            
                        else:
                            logger.debug(f"No match found for: {normalized['name']}")
                            
                    except Exception as e:
                        logger.error(f"Error processing player {ffc_player.get('name')}: {e}")
                        stats["errors"] += 1
            
            # Commit changes
            self.db.commit()
            
            logger.info(f"FFC ADP sync complete: {stats}")
            return stats
            
        except Exception as e:
            logger.error(f"Error in FFC ADP sync: {e}")
            self.db.rollback()
            stats["errors"] += 1
            return stats
    
    def _find_matching_player(self, normalized_player: Dict[str, Any]) -> Optional[Player]:
        """Find player in database matching FFC data."""
        # Try to match by name and position
        name = normalized_player["name"]
        position = normalized_player["position"]
        team = normalized_player["team"]
        
        # Try exact name match first
        player = self.db.query(Player).filter(
            Player.full_name == name,
            Player.position == position
        ).first()
        
        if player:
            return player
        
        # Try case-insensitive partial match
        player = self.db.query(Player).filter(
            Player.full_name.ilike(f"%{name}%"),
            Player.position == position
        ).first()
        
        if player:
            return player
        
        # Try matching by first initial and last name (e.g., "C. McCaffrey" -> "Christian McCaffrey")
        if "." in name:
            name_parts = name.split()
            if len(name_parts) >= 2:
                last_name = name_parts[-1]
                player = self.db.query(Player).filter(
                    Player.last_name == last_name,
                    Player.position == position
                ).first()
                
                if player:
                    return player
        
        return None
    
    def _create_draft_history_record(
        self,
        player: Player,
        year: int,
        source: str,
        adp_value: float,
        scoring_format: str,
        team_count: int,
        draft_type: str = "external"
    ) -> DraftHistory:
        """Create a DraftHistory record for ADP data."""
        # Check if record already exists for this year/source
        existing = self.db.query(DraftHistory).filter(
            DraftHistory.player_id == player.player_id,
            DraftHistory.draft_year == year,
            DraftHistory.adp_source == source,
            DraftHistory.scoring_format == scoring_format,
            DraftHistory.team_count == team_count
        ).first()
        
        if existing:
            # Update existing record
            existing.adp_value = adp_value
            return existing
        
        # Create new record
        draft_history = DraftHistory(
            player_id=player.player_id,
            draft_year=year,
            draft_type=draft_type,
            adp_value=adp_value,
            adp_source=source,
            scoring_format=scoring_format,
            team_count=team_count
        )
        
        self.db.add(draft_history)
        return draft_history
    
    def get_player_adp_history(
        self,
        player_id: str,
        source: Optional[str] = None,
        year: Optional[int] = None
    ) -> List[DraftHistory]:
        """Get ADP history for a player."""
        query = self.db.query(DraftHistory).filter(
            DraftHistory.player_id == player_id
        )
        
        if source:
            query = query.filter(DraftHistory.adp_source == source)
        
        if year:
            query = query.filter(DraftHistory.draft_year == year)
        
        return query.order_by(DraftHistory.draft_year.desc()).all()
    
    def get_top_players_by_external_adp(
        self,
        position: Optional[str] = None,
        limit: int = 50,
        source: str = "ffc"
    ) -> List[Player]:
        """Get top players sorted by external ADP."""
        query = self.db.query(Player).filter(
            Player.external_adp.isnot(None),
            Player.external_adp_source == source
        )
        
        if position:
            query = query.filter(Player.position == position)
        
        return query.order_by(Player.external_adp.asc()).limit(limit).all()
    
    async def health_check(self) -> Dict[str, Any]:
        """Check service health."""
        try:
            ffc_healthy = await self.ffc_client.health_check() if self.ffc_client else False
            
            db_healthy = False
            try:
                self.db.execute("SELECT 1")
                db_healthy = True
            except Exception:
                pass
            
            return {
                "ffc_api": ffc_healthy,
                "database": db_healthy,
                "overall": ffc_healthy and db_healthy
            }
            
        except Exception as e:
            logger.error(f"Health check error: {e}")
            return {
                "ffc_api": False,
                "database": False,
                "overall": False
            }


# Quick test function
async def test_ffc_sync():
    """Test FFC ADP sync."""
    async with ADPSyncService() as service:
        # Test health check
        health = await service.health_check()
        print(f"Health check: {health}")
        
        if health["ffc_api"]:
            # Run sync
            stats = await service.sync_ffc_adp(year=2025, scoring="ppr", teams=12)
            print(f"Sync stats: {stats}")
            
            # Test getting top players
            top_qbs = service.get_top_players_by_external_adp(position="QB", limit=5)
            print(f"\nTop 5 QBs by external ADP:")
            for i, qb in enumerate(top_qbs, 1):
                print(f"{i}. {qb.full_name}: {qb.external_adp}")
            
            return stats
        else:
            print("FFC API not accessible")
            return None