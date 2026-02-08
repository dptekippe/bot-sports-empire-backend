"""
Draft Analytics endpoints for Bot Sports Empire.

Provides insights into our community's draft behavior and internal ADP evolution.
These endpoints enable the vision of community-driven ADP development.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any

from ...core.database import get_db
from ...services.draft_analytics import DraftAnalyticsService
from ...schemas.draft_analytics import (
    DraftTrendsResponse,
    PlayerADPComparisonResponse,
    CommunityInsightsResponse,
    PlayerADPResponse,
    ADPEvolutionStatsResponse
)

router = APIRouter()


@router.get("/trends", response_model=List[DraftTrendsResponse])
def get_draft_trends(
    year: Optional[int] = Query(None, description="Filter by draft year"),
    league_type: Optional[str] = Query(None, description="Filter by league type (fantasy/dynasty)"),
    position: Optional[str] = Query(None, description="Filter by player position"),
    limit: int = Query(50, description="Maximum number of trends to return"),
    db: Session = Depends(get_db)
):
    """
    Get draft trends from our community's drafts.
    
    Shows which players are most frequently drafted and their ADP ranges.
    This data forms the foundation of our internal ADP evolution.
    """
    try:
        analytics_service = DraftAnalyticsService(db)
        trends = analytics_service.get_draft_trends(
            year=year,
            league_type=league_type,
            position=position,
            limit=limit
        )
        
        # Convert to response format
        response = []
        for trend in trends:
            response.append(DraftTrendsResponse(**trend))
        
        return response
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting draft trends: {str(e)}"
        )


@router.get("/players/{player_id}/adp", response_model=PlayerADPResponse)
def get_player_adp(
    player_id: str,
    year: Optional[int] = Query(None, description="Filter by draft year"),
    league_type: Optional[str] = Query(None, description="Filter by league type (fantasy/dynasty)"),
    db: Session = Depends(get_db)
):
    """
    Get ADP data for a specific player.
    
    Returns both internal ADP (from our community) and external ADP
    (from sources like FFC, Sleeper, etc.).
    """
    try:
        analytics_service = DraftAnalyticsService(db)
        
        # Calculate internal ADP
        internal_adp = analytics_service.calculate_player_internal_adp(
            player_id=player_id,
            year=year,
            league_type=league_type
        )
        
        # Get comparison data
        comparison = analytics_service.compare_internal_vs_external_adp(
            player_id=player_id,
            year=year
        )
        
        return PlayerADPResponse(
            player_id=player_id,
            year=year,
            internal_adp=internal_adp,
            external_adp=comparison.get('external_adp'),
            external_source=comparison.get('external_source'),
            adp_difference=comparison.get('adp_difference'),
            internal_pick_count=comparison.get('internal_pick_count', 0),
            external_source_count=comparison.get('external_source_count', 0),
            community_valuation=comparison.get('community_valuation')
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting player ADP: {str(e)}"
        )


@router.get("/players/{player_id}/adp/comparison", response_model=PlayerADPComparisonResponse)
def compare_player_adp(
    player_id: str,
    year: Optional[int] = Query(None, description="Filter by draft year"),
    db: Session = Depends(get_db)
):
    """
    Compare internal vs external ADP for a player.
    
    Shows how our community values a player compared to external sources.
    """
    try:
        analytics_service = DraftAnalyticsService(db)
        comparison = analytics_service.compare_internal_vs_external_adp(
            player_id=player_id,
            year=year
        )
        
        return PlayerADPComparisonResponse(**comparison)
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error comparing ADP: {str(e)}"
        )


@router.get("/community/insights", response_model=CommunityInsightsResponse)
def get_community_insights(
    year: Optional[int] = Query(None, description="Filter by draft year"),
    db: Session = Depends(get_db)
):
    """
    Get high-level insights about our community's draft behavior.
    
    Provides metrics on total picks, unique players, position distribution,
    and other insights about how our bot community drafts.
    """
    try:
        analytics_service = DraftAnalyticsService(db)
        insights = analytics_service.get_community_draft_insights(year=year)
        
        return CommunityInsightsResponse(**insights)
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting community insights: {str(e)}"
        )


@router.post("/players/{player_id}/update-adp")
def update_player_adp(
    player_id: str,
    year: Optional[int] = Query(None, description="Filter by draft year"),
    db: Session = Depends(get_db)
):
    """
    Manually trigger update of a player's internal ADP field.
    
    Normally this happens automatically when picks are made, but this
    endpoint allows manual updates if needed.
    """
    try:
        analytics_service = DraftAnalyticsService(db)
        success = analytics_service.update_player_internal_adp_field(
            player_id=player_id,
            year=year
        )
        
        if success:
            return {"status": "success", "message": f"Updated internal ADP for player {player_id}"}
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Player {player_id} not found or insufficient data"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating player ADP: {str(e)}"
        )


@router.get("/evolution/stats")
def get_adp_evolution_stats(
    year: Optional[int] = Query(None, description="Filter by draft year"),
    min_picks: int = Query(5, description="Minimum picks to consider reliable ADP"),
    db: Session = Depends(get_db)
):
    """
    Get statistics about our internal ADP evolution.
    
    Shows how many players have reliable internal ADP data and how our
    community's valuations compare to external sources.
    """
    try:
        analytics_service = DraftAnalyticsService(db)
        
        # Get all players with internal ADP
        query = db.query(DraftHistory.player_id).filter(
            DraftHistory.draft_type == 'internal',
            DraftHistory.pick_number.isnot(None)
        )
        
        if year:
            query = query.filter(DraftHistory.draft_year == year)
        
        query = query.group_by(DraftHistory.player_id)
        query = query.having(func.count(DraftHistory.id) >= min_picks)
        
        players_with_adp = query.count()
        
        # Get players with both internal and external ADP
        players_with_both = 0
        significant_differences = 0
        
        # This would be more efficient with a proper query, but for now
        # we'll return basic stats
        stats = {
            "year": year or "all",
            "players_with_internal_adp": players_with_adp,
            "min_picks_required": min_picks,
            "note": "Detailed comparison stats would require more complex queries"
        }
        
        return stats
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting ADP evolution stats: {str(e)}"
        )