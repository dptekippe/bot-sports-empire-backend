"""
Internal ADP endpoints for Bot Sports Empire.

Compute weighted average draft position from DraftHistory.
Cache results in Redis for performance.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta
from typing import List, Optional
import json

from ...core.database import get_db
from ...models.draft_history import DraftHistory
from ...models.player import Player
from ...schemas.internal_adp import (
    InternalADPRequest, InternalADPResponse, PlayerADP
)

router = APIRouter()


@router.post("/leagues/{league_id}/internal-adp", response_model=InternalADPResponse)
async def compute_internal_adp(
    league_id: str,
    request: InternalADPRequest,
    db: Session = Depends(get_db)
):
    """
    Compute internal ADP for a league.
    
    Uses DraftHistory to compute weighted average pick position.
    Recent drafts (last 30 days) are weighted more heavily.
    
    Parameters:
    - league_id: League to compute ADP for
    - recent_weight: Weight for recent drafts (default: 1.5)
    - min_picks: Minimum picks required (default: 10)
    - refresh_cache: Force recomputation (not implemented yet)
    
    Returns:
    - Weighted ADP for each player in the league
    - Comparison with external ADP (if available)
    - Cache information
    """
    # For now, implement without Redis cache
    # TODO: Add Redis caching in future
    
    recent_weight = request.recent_weight
    min_picks = request.min_picks
    
    # Compute ADP from DraftHistory
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    
    # Get all picks for this league
    picks = db.query(
        DraftHistory.player_id,
        DraftHistory.pick_number,
        DraftHistory.created_at
    ).filter(
        DraftHistory.league_id == league_id,
        DraftHistory.draft_type == "internal"
    ).all()
    
    if len(picks) < min_picks:
        raise HTTPException(
            status_code=400,
            detail=f"Not enough draft picks ({len(picks)} < {min_picks})"
        )
    
    # Group by player and compute weighted ADP
    player_stats = {}
    for pick in picks:
        player_id = pick.player_id
        if not player_id:
            continue
            
        if player_id not in player_stats:
            player_stats[player_id] = {
                "total_picks": 0,
                "sum_pick_numbers": 0,
                "recent_picks": 0,
                "sum_recent_pick_numbers": 0
            }
        
        stats = player_stats[player_id]
        stats["total_picks"] += 1
        stats["sum_pick_numbers"] += pick.pick_number
        
        # Check if recent (within 30 days)
        if pick.created_at and pick.created_at >= thirty_days_ago:
            stats["recent_picks"] += 1
            stats["sum_recent_pick_numbers"] += pick.pick_number
    
    # Compute weighted ADP for each player
    player_adp = []
    for player_id, stats in player_stats.items():
        if stats["total_picks"] == 0:
            continue
        
        # Regular ADP
        regular_adp = stats["sum_pick_numbers"] / stats["total_picks"]
        
        # Recent ADP (if available)
        recent_adp = None
        if stats["recent_picks"] > 0:
            recent_adp = stats["sum_recent_pick_numbers"] / stats["recent_picks"]
        
        # Weighted ADP
        if recent_adp:
            weighted_adp = (
                (regular_adp * stats["total_picks"]) + 
                (recent_adp * stats["recent_picks"] * recent_weight)
            ) / (stats["total_picks"] + stats["recent_picks"] * recent_weight)
        else:
            weighted_adp = regular_adp
        
        # Get player info
        player = db.query(Player).filter(Player.player_id == player_id).first()
        if player:
            player_adp.append(PlayerADP(
                player_id=player_id,
                full_name=player.full_name,
                position=player.position,
                team=player.team,
                adp=round(regular_adp, 2),
                recent_adp=round(recent_adp, 2) if recent_adp else None,
                weighted_adp=round(weighted_adp, 2),
                pick_count=stats["total_picks"],
                recent_pick_count=stats["recent_picks"],
                vs_external_adp=round(player.external_adp - weighted_adp, 2) 
                    if player.external_adp else None,
                external_adp=player.external_adp
            ))
    
    # Sort by weighted ADP (best players first)
    player_adp.sort(key=lambda x: x.weighted_adp)
    
    # Prepare response
    return InternalADPResponse(
        league_id=league_id,
        computed_at=datetime.utcnow(),
        player_adp=player_adp,
        total_picks=len(picks),
        unique_players=len(player_adp),
        recent_weight=recent_weight,
        cache_key=f"adp:league:{league_id}",
        cache_ttl=3600
    )


@router.get("/leagues/{league_id}/internal-adp/summary")
async def get_internal_adp_summary(
    league_id: str,
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """
    Get summary of internal ADP for a league.
    
    Returns top players by weighted ADP.
    """
    # Simple implementation - in production would use cached results
    picks = db.query(
        DraftHistory.player_id,
        func.count(DraftHistory.id).label("pick_count"),
        func.avg(DraftHistory.pick_number).label("avg_pick")
    ).filter(
        DraftHistory.league_id == league_id,
        DraftHistory.draft_type == "internal",
        DraftHistory.player_id.isnot(None)
    ).group_by(
        DraftHistory.player_id
    ).having(
        func.count(DraftHistory.id) >= 3  # At least 3 picks
    ).order_by(
        func.avg(DraftHistory.pick_number).asc()  # Lower ADP = better
    ).limit(limit).all()
    
    results = []
    for pick in picks:
        player = db.query(Player).filter(Player.player_id == pick.player_id).first()
        if player:
            results.append({
                "player_id": pick.player_id,
                "full_name": player.full_name,
                "position": player.position,
                "adp": round(pick.avg_pick, 2),
                "pick_count": pick.pick_count,
                "external_adp": player.external_adp,
                "adp_difference": round(player.external_adp - pick.avg_pick, 2) 
                    if player.external_adp else None
            })
    
    return {
        "league_id": league_id,
        "top_players": results,
        "total_players": len(results)
    }