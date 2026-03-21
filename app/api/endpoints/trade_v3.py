"""
Trade Evaluation API Endpoints v2.

Enhanced endpoints with:
- Proper validation
- Multi-source value integration
- Draft pick valuation
- Trade suggestions
"""
from fastapi import APIRouter, HTTPException, Query, Depends
from typing import List, Optional
from pydantic import BaseModel, validator

from app.services.trade_values import DynastyValueService, get_value_service
from app.services.trade_evaluator_v2 import (
    analyze_trade, LeagueConfig, RosterAnalyzer, TradeEvaluator
)
from app.integrations.sleeper_client import SleeperClient

router = APIRouter(tags=["trade"])


# Request Models
class TradeEvaluateRequest(BaseModel):
    league_id: str
    user_roster_id: int
    outgoing_player_ids: List[str]
    incoming_player_ids: List[str]
    format: str = "2qb"
    num_teams: int = 12
    flex: int = 3
    te_premium: bool = False
    fair_margin: float = 0.15
    
    @validator('outgoing_player_ids', 'incoming_player_ids')
    def validate_player_ids(cls, v):
        if not v:
            raise ValueError("Player IDs list cannot be empty")
        return v


class ConsensusValueRequest(BaseModel):
    player_names: List[str]
    format: str = "2qb"
    force_refresh: bool = False


class FairTradeRequest(BaseModel):
    league_id: str
    roster_id: int
    target_player_id: Optional[str] = None
    target_player_value: Optional[int] = None


class TradeEvaluateResponse(BaseModel):
    outgoing: List[dict]
    incoming: List[dict]
    outgoing_value: int
    incoming_value: int
    value_difference: int
    is_fair: bool
    fairness_details: dict
    team_classification: str
    strengths: List[str]
    weaknesses: List[str]
    narrative: str
    suggestions: List[str]


# Dependencies
async def get_value_service_dep() -> DynastyValueService:
    """Dependency for value service."""
    return get_value_service()


# API Endpoints
@router.post("/evaluate", response_model=TradeEvaluateResponse)
async def evaluate_trade(
    request: TradeEvaluateRequest,
    value_service: DynastyValueService = Depends(get_value_service_dep)
):
    """
    Evaluate a dynasty trade proposal.
    
    Analyzes:
    - Trade value equity
    - Positional needs
    - Win-now vs rebuild fit
    - Roger-style narrative
    """
    async with SleeperClient() as client:
        # Fetch league data
        league_data = await client.get_full_league_data(request.league_id)
        if not league_data:
            raise HTTPException(status_code=404, detail="League not found")
        
        rosters = league_data.get("rosters", [])
        
        # Find user's roster
        user_roster = None
        for r in rosters:
            if r.get("roster_id") == request.user_roster_id:
                user_roster = r
                break
        
        if not user_roster:
            raise HTTPException(status_code=404, detail="Roster not found")
        
        # Fetch player values from multiple sources
        all_values = await value_service.fetch_all_sources(request.format)
        
        # Build consensus values dict
        player_values = {}
        for name, sources in all_values.items():
            consensus = value_service.calculate_consensus(sources)
            if consensus and "consensus" in consensus:
                player_values[name] = consensus["consensus"]
        
        # Fetch all players for details
        all_players = await client.get_all_players()
        
        # Build player lookup
        player_lookup = {}
        for pid, data in all_players.items():
            player_lookup[pid] = data
        
        # Get user roster players
        roster_player_ids = user_roster.get("players", []) or []
        user_roster_players = []
        for pid in roster_player_ids:
            pdata = player_lookup.get(pid, {})
            name = f"{pdata.get('first_name', '')} {pdata.get('last_name', '')}".strip()
            value = player_values.get(name, 0)
            if value:
                user_roster_players.append({
                    "player_id": pid,
                    "name": name,
                    "position": pdata.get("position", "UNK"),
                    "team": pdata.get("team", "UNK"),
                    "value": value
                })
        
        # Build config
        format_map = {"1qb": "1qb", "2qb": "2qb"}
        config = LeagueConfig(
            num_teams=request.num_teams,
            format=format_map.get(request.format, "2qb"),
            flex=request.flex,
            te_premium=request.te_premium,
            fair_margin=request.fair_margin
        )
        
        # Analyze trade
        result = analyze_trade(
            user_roster=user_roster_players,
            outgoing_player_ids=request.outgoing_player_ids,
            incoming_player_ids=request.incoming_player_ids,
            player_values=player_values,
            player_details=player_lookup,
            config=config
        )
        
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        
        return result


@router.post("/consensus-values")
async def get_consensus_values(
    request: ConsensusValueRequest,
    value_service: DynastyValueService = Depends(get_value_service_dep)
):
    """
    Get consensus dynasty values for players.
    
    Blends multiple sources:
    - KTC (30%)
    - DynastyProcess (25%)
    - DLF (15%)
    - FantasyPros (15%)
    - DraftSharks (15%)
    """
    # Fetch all sources
    all_values = await value_service.fetch_all_sources(
        request.format, 
        request.force_refresh
    )
    
    results = []
    for player_name in request.player_names:
        if player_name in all_values:
            consensus = value_service.calculate_consensus(all_values[player_name])
            results.append({
                "name": player_name,
                **consensus
            })
        else:
            results.append({
                "name": player_name,
                "error": "Player not found",
                "consensus": 0
            })
    
    return {
        "format": request.format,
        "count": len(results),
        "players": results
    }


@router.get("/values")
async def get_player_values(
    format: str = Query("2qb", pattern="^(1qb|2qb)$"),
    value_service: DynastyValueService = Depends(get_value_service_dep)
):
    """Get all dynasty player values."""
    all_values = await value_service.fetch_all_sources(format)
    
    # Build consensus for each player
    player_list = []
    for name, sources in all_values.items():
        consensus = value_service.calculate_consensus(sources)
        if consensus and consensus.get("consensus", 0) > 0:
            player_list.append({
                "name": name,
                "value": consensus["consensus"],
                "position": consensus.get("position", "WR"),
                "sources": consensus.get("sources_used", [])
            })
    
    # Sort by value descending
    player_list.sort(key=lambda x: x["value"], reverse=True)
    
    return {
        "format": format,
        "count": len(player_list),
        "players": player_list[:500]  # Limit to top 500
    }


@router.get("/pick-values")
async def get_draft_pick_values(
    num_teams: int = Query(12, ge=8, le=16),
    value_service: DynastyValueService = Depends(get_value_service_dep)
):
    """Get calculated draft pick values."""
    pick_values = await value_service.get_draft_pick_values(num_teams)
    
    return {
        "num_teams": num_teams,
        "picks": pick_values
    }


@router.post("/find-fair-trades")
async def find_fair_trades(
    request: FairTradeRequest,
    value_service: DynastyValueService = Depends(get_value_service_dep)
):
    """
    Find fair trade packages for a target player.
    
    Given a target player you want to acquire, find
    what packages would make a fair trade.
    """
    # Would integrate with league roster data
    # For now, return mock suggestions
    
    return {
        "target": request.target_player_id,
        "suggestions": [],
        "note": "Full implementation requires league roster access"
    }


@router.get("/health")
async def health_check():
    """Health check for trade service."""
    service = get_value_service()
    staleness = service.cache.get_staleness("ktc")
    
    return {
        "status": "healthy",
        "cache_staleness": str(staleness) if staleness else "no cache"
    }
