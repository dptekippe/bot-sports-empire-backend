"""
Bot AI endpoints for draft recommendations.

Simple AI that recommends picks based on ADP, team needs, and player status.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, not_
from typing import List, Optional, Dict, Any
import logging

from ...core.database import get_db
from ...models.draft import Draft, DraftPick
from ...models.player import Player
from ...models.team import Team
from ...schemas.player import PlayerResponse, PlayerFilter
from ...schemas.draft import DraftPickResponse

router = APIRouter()
logger = logging.getLogger(__name__)


def calculate_team_needs(team_id: str, db: Session, draft_id: str) -> Dict[str, int]:
    """
    Calculate position needs for a team based on current roster.
    
    Returns dict of position -> count needed (higher = more urgent).
    """
    # Get current roster from draft picks
    current_picks = db.query(DraftPick).filter(
        DraftPick.draft_id == draft_id,
        DraftPick.team_id == team_id,
        DraftPick.player_id.isnot(None)
    ).all()
    
    # Count players by position
    position_counts = {}
    for pick in current_picks:
        if pick.position:
            position_counts[pick.position] = position_counts.get(pick.position, 0) + 1
    
    # Standard fantasy roster composition
    target_roster = {
        "QB": 2,   # Start 1, bench 1
        "RB": 4,   # Start 2, bench 2  
        "WR": 4,   # Start 2, bench 2
        "TE": 2,   # Start 1, bench 1
        "K": 1,    # Start 1
        "DEF": 1,  # Start 1
    }
    
    # Calculate needs (target - current)
    needs = {}
    for position, target in target_roster.items():
        current = position_counts.get(position, 0)
        if current < target:
            needs[position] = target - current
    
    return needs


@router.get("/drafts/{draft_id}/ai-pick")
def get_ai_pick_recommendation(
    draft_id: str,
    team_id: Optional[str] = Query(None, description="Team to get recommendation for"),
    position: Optional[str] = Query(None, description="Filter by specific position"),
    limit: int = Query(5, ge=1, le=20, description="Number of recommendations"),
    db: Session = Depends(get_db)
):
    """
    Get AI pick recommendations for a draft.
    
    Algorithm:
    1. If team_id provided, calculate position needs
    2. Filter available players by position needs
    3. Sort by ADP (best available)
    4. Filter out injured/inactive players
    5. Return top recommendations
    
    Example: GET /api/v1/drafts/{id}/ai-pick?team_needs=QB,WR
    """
    try:
        # Validate draft exists and is in progress
        draft = db.query(Draft).filter(Draft.id == draft_id).first()
        if not draft:
            raise HTTPException(status_code=404, detail=f"Draft {draft_id} not found")
        
        if draft.status != "in_progress":
            raise HTTPException(
                status_code=422, 
                detail=f"Cannot get AI picks for draft in {draft.status} status"
            )
        
        # Get team needs if team_id provided
        position_priority = []
        if team_id:
            needs = calculate_team_needs(team_id, db, draft_id)
            # Sort needs by urgency (positions with biggest deficit first)
            position_priority = [pos for pos, _ in sorted(needs.items(), key=lambda x: x[1], reverse=True)]
        
        # If specific position requested, prioritize it
        if position:
            position_priority = [position.upper()] + [p for p in position_priority if p != position.upper()]
        
        # Get all players already drafted in this draft
        drafted_player_ids = db.query(DraftPick.player_id).filter(
            DraftPick.draft_id == draft_id,
            DraftPick.player_id.isnot(None)
        ).all()
        drafted_player_ids = [pid[0] for pid in drafted_player_ids]
        
        # Build query for available players
        query = db.query(Player).filter(
            Player.active == True,  # Only active players
            Player.player_id.notin_(drafted_player_ids) if drafted_player_ids else True,
            Player.current_team_id.is_(None)  # Not already on a fantasy team
        )
        
        # Filter by position if specified
        if position_priority:
            # Try positions in priority order
            for pos in position_priority:
                pos_players = query.filter(Player.position == pos).all()
                if pos_players:
                    # Found players in this position
                    players = pos_players
                    recommended_position = pos
                    break
            else:
                # No players in priority positions, get any available
                players = query.all()
                recommended_position = "BPA"  # Best Player Available
        else:
            # No position priority, get best available
            players = query.all()
            recommended_position = "BPA"
        
        # Sort by ADP (best first)
        players_with_adp = [p for p in players if p.average_draft_position]
        players_without_adp = [p for p in players if not p.average_draft_position]
        
        # Sort players with ADP
        players_with_adp.sort(key=lambda x: x.average_draft_position)
        
        # Combine lists (players with ADP first)
        sorted_players = players_with_adp + players_without_adp
        
        # Take top recommendations
        top_players = sorted_players[:limit]
        
        # Convert to response
        player_responses = [PlayerResponse.from_orm(player) for player in top_players]
        
        # Calculate recommendation confidence
        confidence = "high"
        if not players_with_adp:
            confidence = "low"
        elif len(players_with_adp) < 3:
            confidence = "medium"
        
        return {
            "draft_id": draft_id,
            "team_id": team_id,
            "recommended_position": recommended_position,
            "confidence": confidence,
            "total_available": len(sorted_players),
            "recommendations": player_responses,
            "logic": {
                "position_priority": position_priority,
                "filter_active": True,
                "filter_drafted": True,
                "sort_by": "ADP",
                "team_needs_calculated": team_id is not None
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting AI pick: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error getting AI pick: {str(e)}")


@router.get("/drafts/{draft_id}/ai-pick/simple")
def get_simple_ai_pick(
    draft_id: str,
    team_id: str = Query(..., description="Team to get recommendation for"),
    db: Session = Depends(get_db)
):
    """
    Simple AI pick - returns single best recommendation.
    
    Used by bots for auto-picking.
    """
    try:
        # Get full recommendations
        result = get_ai_pick_recommendation(draft_id, team_id, limit=1, db=db)
        
        if not result["recommendations"]:
            return {
                "success": False,
                "message": "No available players found",
                "recommendation": None
            }
        
        top_player = result["recommendations"][0]
        
        return {
            "success": True,
            "message": f"Recommended: {top_player.full_name} ({top_player.position})",
            "recommendation": top_player,
            "confidence": result["confidence"],
            "position_needed": result["recommended_position"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in simple AI pick: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error in simple AI pick: {str(e)}")


@router.get("/drafts/{draft_id}/team-needs")
def get_team_needs(
    draft_id: str,
    team_id: str = Query(..., description="Team to analyze"),
    db: Session = Depends(get_db)
):
    """
    Get detailed team needs analysis.
    
    Returns position needs and suggested draft strategy.
    """
    try:
        needs = calculate_team_needs(team_id, db, draft_id)
        
        # Get current picks for this team
        current_picks = db.query(DraftPick).filter(
            DraftPick.draft_id == draft_id,
            DraftPick.team_id == team_id,
            DraftPick.player_id.isnot(None)
        ).all()
        
        current_roster = [
            {
                "player_id": pick.player_id,
                "position": pick.position,
                "pick_number": pick.pick_number,
                "round": pick.round
            }
            for pick in current_picks
        ]
        
        # Generate draft strategy advice
        strategy = []
        if needs.get("QB", 0) >= 2:
            strategy.append("Prioritize QB early - need starter and backup")
        if needs.get("RB", 0) >= 3:
            strategy.append("Load up on RBs - high injury risk position")
        if not needs:  # All positions filled
            strategy.append("Best Player Available (BPA) - roster complete")
        
        return {
            "team_id": team_id,
            "draft_id": draft_id,
            "current_roster_size": len(current_roster),
            "current_roster": current_roster,
            "position_needs": needs,
            "draft_strategy": strategy,
            "recommended_next_pick": max(needs.keys(), key=lambda k: needs[k]) if needs else "BPA"
        }
        
    except Exception as e:
        logger.error(f"Error analyzing team needs: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error analyzing team needs: {str(e)}")


# Test endpoint for AI logic
@router.get("/test/ai-logic")
def test_ai_logic(
    position: str = Query("QB", description="Position to test"),
    limit: int = Query(5, ge=1, le=10),
    db: Session = Depends(get_db)
):
    """
    Test AI logic with sample data.
    
    Returns top players by position for debugging.
    """
    players = db.query(Player).filter(
        Player.position == position.upper(),
        Player.active == True,
        Player.average_draft_position.isnot(None)
    ).order_by(
        Player.average_draft_position.asc()
    ).limit(limit).all()
    
    return {
        "position": position,
        "players": [
            {
                "name": p.full_name,
                "adp": p.average_draft_position,
                "team": p.team,
                "status": p.status,
                "active": p.active
            }
            for p in players
        ],
        "ai_note": "AI would recommend these players in order (best ADP first)"
    }