"""
Player endpoints for Bot Sports Empire.

FastAPI endpoints for player search, filtering, and draft availability.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi import status
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from typing import List, Optional
import logging

from ...core.database import get_db
from ...models.player import Player
from ...schemas.player import (
    PlayerResponse, PlayerSearchResponse, PlayerFilter,
    PlayerDraftAvailability, PlayerStatus, InjuryStatus
)

router = APIRouter()
logger = logging.getLogger(__name__)


def build_player_query(db: Session, filters: PlayerFilter):
    """
    Build SQLAlchemy query based on player filters.
    
    Uses ilike for case-insensitive search on name fields.
    """
    query = db.query(Player)
    
    # Search query (name search with ilike)
    if filters.search:
        search_term = f"%{filters.search}%"
        query = query.filter(
            or_(
                Player.search_full_name.ilike(search_term),
                Player.search_first_name.ilike(search_term),
                Player.search_last_name.ilike(search_term),
                Player.full_name.ilike(search_term)
            )
        )
    
    # Position filter
    if filters.position:
        query = query.filter(Player.position == filters.position.upper())
    
    # Team filter
    if filters.team:
        # Try both team fields
        query = query.filter(
            or_(
                Player.team == filters.team.upper(),
                Player.team_abbr == filters.team.upper()
            )
        )
    
    # Status filter
    if filters.status:
        query = query.filter(Player.status == filters.status.value)
    
    # Injury status filter
    if filters.injury_status:
        query = query.filter(Player.injury_status == filters.injury_status.value)
    
    # Active filter
    if filters.active is not None:
        query = query.filter(Player.active == filters.active)
    
    # Available filter (not on a fantasy team)
    if filters.available is not None:
        if filters.available:
            query = query.filter(Player.current_team_id.is_(None))
        else:
            query = query.filter(Player.current_team_id.isnot(None))
    
    # ADP range filter
    if filters.min_adp is not None:
        query = query.filter(Player.average_draft_position >= filters.min_adp)
    
    if filters.max_adp is not None:
        query = query.filter(Player.average_draft_position <= filters.max_adp)
    
    # Apply sorting
    if filters.sort_by:
        if filters.sort_by == "average_draft_position":
            query = query.order_by(
                Player.average_draft_position.asc().nulls_last(),
                Player.last_name.asc(),
                Player.first_name.asc()
            )
        elif filters.sort_by == "external_adp":
            query = query.order_by(
                Player.external_adp.asc().nulls_last(),
                Player.last_name.asc(),
                Player.first_name.asc()
            )
        elif filters.sort_by == "fantasy_pro_rank":
            query = query.order_by(
                Player.fantasy_pro_rank.asc().nulls_last(),
                Player.last_name.asc(),
                Player.first_name.asc()
            )
        elif filters.sort_by == "last_name":
            query = query.order_by(
                Player.last_name.asc(),
                Player.first_name.asc(),
                Player.average_draft_position.asc().nulls_last()
            )
        else:
            # Invalid sort field, use default
            query = query.order_by(
                Player.average_draft_position.asc().nulls_last(),
                Player.last_name.asc(),
                Player.first_name.asc()
            )
    else:
        # Default ordering: by ADP (lower is better), then by name
        query = query.order_by(
            Player.average_draft_position.asc().nulls_last(),
            Player.last_name.asc(),
            Player.first_name.asc()
        )
    
    return query


@router.get("/", response_model=PlayerSearchResponse)
def list_players(
    search: Optional[str] = Query(None, description="Search query (name search)"),
    position: Optional[str] = Query(None, description="Position filter (QB, RB, WR, TE, K, DEF)"),
    team: Optional[str] = Query(None, description="Team filter (e.g., KC, SF, DAL)"),
    status: Optional[str] = Query(None, description="Player status filter"),
    injury_status: Optional[str] = Query(None, description="Injury status filter"),
    active: Optional[bool] = Query(None, description="Active players only"),
    available: Optional[bool] = Query(None, description="Available for drafting (not on a team)"),
    min_adp: Optional[float] = Query(None, ge=1.0, le=300.0, description="Minimum ADP"),
    max_adp: Optional[float] = Query(None, ge=1.0, le=300.0, description="Maximum ADP"),
    sort_by: Optional[str] = Query(None, description="Sort field (average_draft_position, external_adp, fantasy_pro_rank, last_name)"),
    limit: int = Query(50, ge=1, le=100, description="Maximum results"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    db: Session = Depends(get_db)
):
    """
    List players with filtering and search.
    
    Supports:
    - Name search (case-insensitive, ilike)
    - Position filter
    - Team filter  
    - Status filters (active, injured, etc.)
    - ADP range filtering
    - Availability filter (not on a fantasy team)
    
    Results ordered by ADP (best available first).
    """
    try:
        # Convert string enums to enum types if provided
        status_enum = None
        if status:
            try:
                status_enum = PlayerStatus(status)
            except ValueError:
                # Try case-insensitive lookup
                for member in PlayerStatus:
                    if member.value.lower() == status.lower():
                        status_enum = member
                        break
                if not status_enum:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Invalid status value: {status}. Valid values: {[e.value for e in PlayerStatus]}"
                    )
        
        injury_enum = None
        if injury_status:
            try:
                injury_enum = InjuryStatus(injury_status)
            except ValueError:
                # Try case-insensitive lookup
                for member in InjuryStatus:
                    if member.value.lower() == injury_status.lower():
                        injury_enum = member
                        break
                if not injury_enum:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Invalid injury_status value: {injury_status}. Valid values: {[e.value for e in InjuryStatus]}"
                    )
        
        # Build filters object
        filters = PlayerFilter(
            search=search,
            position=position,
            team=team,
            status=status_enum,
            injury_status=injury_enum,
            active=active,
            available=available,
            min_adp=min_adp,
            max_adp=max_adp,
            sort_by=sort_by,
            limit=limit,
            offset=offset
        )
        
        # Build query
        query = build_player_query(db, filters)
        
        # Get total count
        total = query.count()
        
        # Apply pagination
        players = query.offset(offset).limit(limit).all()
        
        # Convert to response models
        player_responses = [PlayerResponse.from_orm(player) for player in players]
        
        # Build response
        return PlayerSearchResponse(
            players=player_responses,
            total=total,
            page=(offset // limit) + 1 if limit > 0 else 1,
            page_size=limit,
            filters=filters.dict(exclude_none=True)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing players: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error listing players: {str(e)}"
        )


@router.get("/search", response_model=PlayerSearchResponse)
def search_players(
    q: str = Query(..., min_length=2, max_length=50, description="Search query"),
    limit: int = Query(20, ge=1, le=50, description="Maximum results"),
    db: Session = Depends(get_db)
):
    """
    Quick search endpoint for player names.
    
    Optimized for draft room autocomplete/search.
    Returns top matches ordered by relevance.
    """
    try:
        search_term = f"%{q}%"
        
        # Search across name fields
        query = db.query(Player).filter(
            or_(
                Player.search_full_name.ilike(search_term),
                Player.search_first_name.ilike(search_term),
                Player.search_last_name.ilike(search_term),
                Player.full_name.ilike(search_term)
            )
        )
        
        # Order by: exact match first, then ADP
        # For simple implementation, order by ADP (better players first)
        query = query.order_by(
            Player.average_draft_position.asc().nulls_last(),
            Player.last_name.asc(),
            Player.first_name.asc()
        )
        
        total = query.count()
        players = query.limit(limit).all()
        
        player_responses = [PlayerResponse.from_orm(player) for player in players]
        
        return PlayerSearchResponse(
            players=player_responses,
            total=total,
            page=1,
            page_size=limit,
            filters={"search": q, "limit": limit}
        )
        
    except Exception as e:
        logger.error(f"Error searching players: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error searching players: {str(e)}"
        )


@router.get("/{player_id}", response_model=PlayerResponse)
def get_player(player_id: str, db: Session = Depends(get_db)):
    """
    Get a single player by ID.
    
    Returns full player details including ADP and status.
    """
    try:
        player = db.query(Player).filter(Player.player_id == player_id).first()
        if not player:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Player {player_id} not found"
            )
        
        return PlayerResponse.from_orm(player)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting player {player_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting player: {str(e)}"
        )


@router.get("/{player_id}/draft-availability/{draft_id}", response_model=PlayerDraftAvailability)
def check_draft_availability(
    player_id: str,
    draft_id: str,
    db: Session = Depends(get_db)
):
    """
    Check if a player is available for drafting in a specific draft.
    
    Validates:
    1. Player exists and is active
    2. Player is not already on a fantasy team
    3. Player is not already drafted in this draft
    """
    try:
        # Get player
        player = db.query(Player).filter(Player.player_id == player_id).first()
        if not player:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Player {player_id} not found"
            )
        
        # Check if player is active
        if not player.active:
            return PlayerDraftAvailability(
                player_id=player_id,
                available=False,
                reason="Player is not active",
                adp=player.average_draft_position
            )
        
        # Check if player is already on a fantasy team
        if player.current_team_id:
            return PlayerDraftAvailability(
                player_id=player_id,
                available=False,
                reason=f"Player already owned by team {player.current_team_id}",
                current_owner=player.current_team_id,
                adp=player.average_draft_position
            )
        
        # TODO: Check if player already drafted in this draft
        # Need to query draft_picks table
        # For now, assume available if not on a team
        
        # Calculate position rank (simplified - would need more logic)
        position_rank = None
        if player.average_draft_position:
            # Simple rank: ADP rounded to nearest integer
            position_rank = int(round(player.average_draft_position))
        
        return PlayerDraftAvailability(
            player_id=player_id,
            available=True,
            reason="Player is available for drafting",
            adp=player.average_draft_position,
            position_rank=position_rank
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error checking draft availability: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error checking draft availability: {str(e)}"
        )


@router.get("/positions/", response_model=List[str])
def list_positions(db: Session = Depends(get_db)):
    """
    Get list of unique player positions in database.
    
    Useful for dropdowns in UI.
    """
    try:
        positions = db.query(Player.position).distinct().all()
        # Extract position strings from result tuples
        position_list = [pos[0] for pos in positions if pos[0]]
        return sorted(position_list)
        
    except Exception as e:
        logger.error(f"Error listing positions: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error listing positions: {str(e)}"
        )


@router.get("/teams/", response_model=List[str])
def list_teams(db: Session = Depends(get_db)):
    """
    Get list of unique NFL teams in database.
    
    Useful for dropdowns in UI.
    """
    try:
        teams = db.query(Player.team).distinct().all()
        # Extract team strings from result tuples
        team_list = [team[0] for team in teams if team[0]]
        return sorted(team_list)
        
    except Exception as e:
        logger.error(f"Error listing teams: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error listing teams: {str(e)}"
        )


# Helper endpoint for testing
@router.get("/test/adp-top/{position}", response_model=List[PlayerResponse])
def test_adp_top(
    position: str,
    limit: int = Query(10, ge=1, le=20),
    db: Session = Depends(get_db)
):
    """
    TEST ENDPOINT: Get top players by ADP for a position.
    
    Only for development/testing draft logic.
    """
    try:
        players = db.query(Player).filter(
            Player.position == position.upper(),
            Player.active == True,
            Player.average_draft_position.isnot(None)
        ).order_by(
            Player.average_draft_position.asc()
        ).limit(limit).all()
        
        return [PlayerResponse.from_orm(player) for player in players]
        
    except Exception as e:
        logger.error(f"Error in test endpoint: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error in test endpoint: {str(e)}"
        )