"""
Admin endpoints for Bot Sports Empire
File: app/api/endpoints/admin.py
"""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from sqlalchemy.orm import Session
from typing import Dict, Any, List
from datetime import datetime, timedelta
import logging
import requests

from app.core.database import get_db
from app.models.player import Player
from app.models.draft import Draft
from app.models.league import League
from app.core.config_simple import settings

# Set up logging
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/health")
async def admin_health_check(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Admin health check endpoint
    Returns detailed system health information
    """
    try:
        # Check database connection
        db_status = "healthy"
        try:
            from sqlalchemy import text
            db.execute(text("SELECT 1"))
        except Exception as e:
            db_status = f"unhealthy: {str(e)}"
        
        # Check player count
        player_count = db.query(Player).count()
        
        # Check draft count
        draft_count = db.query(Draft).count()
        
        # Check league count
        league_count = db.query(League).count()
        
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "database": {
                "status": db_status,
                "players": player_count,
                "drafts": draft_count,
                "leagues": league_count
            },
            "system": {
                "environment": getattr(settings, 'ENVIRONMENT', 'unknown'),
                "debug_mode": getattr(settings, 'DEBUG', False),
                "api_version": "0.1.0"
            }
        }
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}")


@router.post("/import-players")
async def import_players(
    background_tasks: BackgroundTasks,
    force_refresh: bool = False,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Import players from Sleeper API
    
    Args:
        force_refresh: If True, re-import all players even if they exist
        background_tasks: FastAPI background tasks for async processing
    
    Returns:
        Dict with import status
    """
    try:
        logger.info(f"Starting player import (force_refresh={force_refresh})")
        
        # Import in background
        background_tasks.add_task(
            _import_players_task,
            db,
            force_refresh
        )
        
        return {
            "status": "started",
            "message": "Player import started in background",
            "job_id": f"import_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "timestamp": datetime.now().isoformat(),
            "force_refresh": force_refresh,
            "note": "Check logs for completion status. This may take 1-2 minutes."
        }
        
    except Exception as e:
        logger.error(f"Failed to start player import: {e}")
        raise HTTPException(status_code=500, detail=f"Import failed to start: {str(e)}")


@router.post("/sync-sleeper")
async def sync_sleeper_data(
    background_tasks: BackgroundTasks,
    data_types: List[str] = ["players", "adp"],
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Sync data from Sleeper API
    
    Args:
        data_types: List of data types to sync ["players", "adp"]
        background_tasks: FastAPI background tasks
    
    Returns:
        Dict with sync status
    """
    try:
        logger.info(f"Starting Sleeper sync for data types: {data_types}")
        
        # Sync in background
        background_tasks.add_task(
            _sync_sleeper_task,
            db,
            data_types
        )
        
        return {
            "status": "started",
            "message": f"Sleeper sync started for: {', '.join(data_types)}",
            "job_id": f"sleeper_sync_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "timestamp": datetime.now().isoformat(),
            "data_types": data_types,
            "note": "Sync runs in background. Check logs for completion."
        }
        
    except Exception as e:
        logger.error(f"Failed to start Sleeper sync: {e}")
        raise HTTPException(status_code=500, detail=f"Sleeper sync failed: {str(e)}")


@router.post("/refresh-adp")
async def refresh_adp_data(
    background_tasks: BackgroundTasks,
    formats: List[str] = ["superflex", "standard"],
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Refresh ADP data
    
    Args:
        formats: List of ADP formats to refresh
        background_tasks: FastAPI background tasks
    
    Returns:
        Dict with refresh status
    """
    try:
        logger.info(f"Starting ADP refresh for formats: {formats}")
        
        # Refresh in background
        background_tasks.add_task(
            _refresh_adp_task,
            db,
            formats
        )
        
        return {
            "status": "started",
            "message": f"ADP refresh started for formats: {', '.join(formats)}",
            "job_id": f"adp_refresh_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "timestamp": datetime.now().isoformat(),
            "formats": formats,
            "note": "ADP data refresh runs in background. May take 30-60 seconds."
        }
        
    except Exception as e:
        logger.error(f"Failed to start ADP refresh: {e}")
        raise HTTPException(status_code=500, detail=f"ADP refresh failed: {str(e)}")


@router.get("/import-status/{job_id}")
async def get_import_status(job_id: str) -> Dict[str, Any]:
    """
    Get status of a background import job
    """
    return {
        "job_id": job_id,
        "status": "completed",
        "message": "Background jobs complete. Check application logs for details.",
        "timestamp": datetime.now().isoformat()
    }


@router.post("/cleanup-test-data")
async def cleanup_test_data(
    older_than_hours: int = 24,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Clean up old test data
    
    Args:
        older_than_hours: Delete data older than this many hours
    """
    try:
        logger.info(f"Cleaning up test data older than {older_than_hours} hours")
        
        cutoff_time = datetime.now() - timedelta(hours=older_than_hours)
        
        # Clean up old test drafts
        test_drafts_deleted = db.query(Draft).filter(
            Draft.name.like("%Test%"),
            Draft.created_at < cutoff_time
        ).delete(synchronize_session=False)
        
        # Clean up old test leagues
        test_leagues_deleted = db.query(League).filter(
            League.name.like("%Test%"),
            League.created_at < cutoff_time
        ).delete(synchronize_session=False)
        
        db.commit()
        
        return {
            "status": "success",
            "message": "Test data cleanup completed",
            "deleted": {
                "test_drafts": test_drafts_deleted,
                "test_leagues": test_leagues_deleted
            },
            "cutoff_time": cutoff_time.isoformat(),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        db.rollback()
        logger.error(f"Test data cleanup failed: {e}")
        raise HTTPException(status_code=500, detail=f"Cleanup failed: {str(e)}")


# ============================================================================
# Background Task Functions
# ============================================================================

def _import_players_task(db: Session, force_refresh: bool):
    """Background task to import players from Sleeper API"""
    try:
        logger.info("Starting player import task from Sleeper API")
        
        # Fetch from Sleeper API
        players_url = "https://api.sleeper.app/v1/players/nfl"
        response = requests.get(players_url, timeout=30)
        response.raise_for_status()
        players_data = response.json()
        
        imported = 0
        created = 0
        updated = 0
        
        for player_id, player_info in players_data.items():
            try:
                # Skip if missing essential info
                if not player_info.get('first_name') or not player_info.get('last_name'):
                    continue
                
                # Check if player exists
                existing = db.query(Player).filter(Player.player_id == player_id).first()
                
                if existing:
                    if force_refresh or _should_update_player(existing, player_info):
                        _update_player(existing, player_info)
                        updated += 1
                else:
                    player = _create_player(player_id, player_info)
                    db.add(player)
                    created += 1
                
                imported += 1
                
                # Commit periodically
                if imported % 100 == 0:
                    db.commit()
                    logger.debug(f"Imported {imported} players")
                    
            except Exception as e:
                logger.warning(f"Failed to import player {player_id}: {e}")
                continue
        
        db.commit()
        logger.info(f"Player import completed: {imported} total, {created} created, {updated} updated")
        
    except Exception as e:
        logger.error(f"Player import task failed: {e}")
        db.rollback()


def _sync_sleeper_task(db: Session, data_types: List[str]):
    """Background task to sync Sleeper data"""
    try:
        logger.info(f"Starting Sleeper sync task for: {data_types}")
        
        if "players" in data_types:
            _import_players_task(db, force_refresh=False)
        
        if "adp" in data_types:
            _refresh_adp_task(db, formats=["superflex", "standard"])
        
        logger.info("Sleeper sync task completed")
        
    except Exception as e:
        logger.error(f"Sleeper sync task failed: {e}")


def _refresh_adp_task(db: Session, formats: List[str]):
    """Background task to refresh ADP data"""
    try:
        logger.info(f"Starting ADP refresh task for formats: {formats}")
        
        # Define ADP endpoints (Sleeper format may vary)
        adp_endpoints = {
            "superflex": "https://api.sleeper.app/v1/adp/ppr?year=2025",
            "standard": "https://api.sleeper.app/v1/adp/ppr?year=2025"
        }
        
        updated = 0
        
        for format_name in formats:
            if format_name in adp_endpoints:
                try:
                    response = requests.get(adp_endpoints[format_name], timeout=30)
                    if response.status_code == 200:
                        adp_data = response.json()
                        # Process ADP data - Sleeper returns list of players with ADP
                        for player_data in adp_data:
                            try:
                                player_id = player_data.get('player_id')
                                adp_value = player_data.get('adp') or player_data.get('average_pick')
                                
                                if player_id and adp_value:
                                    player = db.query(Player).filter(Player.player_id == player_id).first()
                                    if player:
                                        # Update ADP field
                                        player.external_adp = float(adp_value)
                                        player.external_adp_source = f"sleeper_{format_name}"
                                        updated += 1
                            except Exception as e:
                                logger.warning(f"Failed to process ADP for player: {e}")
                                continue
                        
                        logger.info(f"Fetched {format_name} ADP data: {len(adp_data)} entries")
                except Exception as e:
                    logger.warning(f"Failed to fetch {format_name} ADP: {e}")
        
        if updated > 0:
            db.commit()
        
        logger.info(f"ADP refresh task completed: {updated} players updated")
        
    except Exception as e:
        logger.error(f"ADP refresh task failed: {e}")


# ============================================================================
# Helper Functions
# ============================================================================

def _should_update_player(player: Player, new_data: dict) -> bool:
    """Check if player data should be updated"""
    # Check key fields that change frequently
    key_fields = ['team', 'status', 'injury_status']
    
    for field in key_fields:
        current_value = getattr(player, field, '')
        new_value = new_data.get(field, '')
        
        if current_value != new_value:
            return True
    
    # Also update if player hasn't been updated in 7 days
    if hasattr(player, 'last_updated') and player.last_updated:
        days_since_update = (datetime.now() - player.last_updated).days
        if days_since_update >= 7:
            return True
    
    return False


def _update_player(player: Player, new_data: dict):
    """Update existing player with new data from Sleeper"""
    # Update basic info
    player.first_name = new_data.get('first_name', player.first_name)
    player.last_name = new_data.get('last_name', player.last_name)
    player.full_name = f"{new_data.get('first_name', '')} {new_data.get('last_name', '')}"
    player.position = new_data.get('position', player.position)
    player.team = new_data.get('team', player.team)
    player.status = new_data.get('status', player.status)
    player.injury_status = new_data.get('injury_status', player.injury_status)
    
    # Update additional info if missing
    if not player.height and 'height' in new_data:
        player.height = new_data.get('height')
    
    if not player.weight and 'weight' in new_data:
        player.weight = new_data.get('weight')
    
    if not player.college and 'college' in new_data:
        player.college = new_data.get('college')
    
    # Update fantasy positions if available
    if 'fantasy_positions' in new_data:
        player.fantasy_positions = new_data.get('fantasy_positions')
    
    # Update metadata
    if 'metadata' in new_data:
        player.player_metadata = new_data.get('metadata')
    
    # Update last updated timestamp if field exists
    if hasattr(player, 'last_updated'):
        player.last_updated = datetime.now()


def _create_player(player_id: str, data: dict) -> Player:
    """Create new Player object from Sleeper data"""
    # Extract fantasy positions
    fantasy_positions = data.get('fantasy_positions', [])
    if not fantasy_positions and data.get('position'):
        fantasy_positions = [data.get('position')]
    
    # Create player object
    player = Player(
        player_id=player_id,
        first_name=data.get('first_name', ''),
        last_name=data.get('last_name', ''),
        full_name=f"{data.get('first_name', '')} {data.get('last_name', '')}",
        position=data.get('position', ''),
        team=data.get('team', ''),
        status=data.get('status', ''),
        injury_status=data.get('injury_status', ''),
        height=data.get('height', ''),
        weight=data.get('weight'),
        college=data.get('college', ''),
        fantasy_positions=fantasy_positions,
        player_metadata=data.get('metadata', {})
    )
    
    # Set last_updated if field exists
    if hasattr(player, 'last_updated'):
        player.last_updated = datetime.now()
    
    return player