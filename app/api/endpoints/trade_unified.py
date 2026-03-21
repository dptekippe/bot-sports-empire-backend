"""
Unified Trade Engine API

Combines all trade engine components into a single,
production-ready API with:
- Multi-source value fetching
- Advanced trade evaluation
- Edge case handling
- Performance optimization
- Health monitoring
"""
import logging
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, validator

from app.services.trade_values import DynastyValueService, get_value_service
from app.services.trade_calculator import DynastyTradeCalculator
from app.services.trade_edge_cases import (
    TradeValidator, TradeEdgeCaseHandler, evaluate_trade_robust
)
from app.services.trade_performance import (
    RateLimiter, _rate_limiter, get_service_health,
    measure_performance, _perf_monitor
)
from app.integrations.sleeper_client import SleeperClient

logger = logging.getLogger(__name__)

# Router
router = APIRouter(prefix="/api/v3/trade", tags=["trade-v3"])


# ============================================================================
# Request/Response Models
# ============================================================================

class PlayerInput(BaseModel):
    """Player in a trade."""
    player_id: Optional[str] = None
    name: str
    value: int = Field(ge=0, le=99999)
    position: str = "WR"
    age: Optional[float] = None
    is_pick: bool = False


class TradeEvaluateRequest(BaseModel):
    """Request to evaluate a trade."""
    league_id: Optional[str] = None
    roster_id: Optional[int] = None
    
    give_players: List[PlayerInput] = Field(min_items=1)
    get_players: List[PlayerInput] = Field(min_items=1)
    
    format: str = "2qb"
    num_teams: int = Field(default=12, ge=8, le=16)
    te_premium: bool = False
    fair_margin: float = Field(default=0.15, ge=0.05, le=0.5)
    include_stud_bonus: bool = True
    
    @validator('give_players', 'get_players')
    def validate_players(cls, v):
        if not v:
            raise ValueError("At least one player required")
        return v


class TradeSuggestionRequest(BaseModel):
    """Request trade suggestions for a target player."""
    target_player: PlayerInput
    available_players: List[PlayerInput]
    target_value: int
    
    format: str = "2qb"
    num_teams: int = 12
    max_suggestions: int = Field(default=5, ge=1, le=10)


class TradeResponse(BaseModel):
    """Trade evaluation response."""
    success: bool
    is_fair: bool
    verdict: str
    recommendation: str
    
    give_total: int
    get_total: int
    difference: int
    margin: float
    
    stud_bonus: int = 0
    stud_description: str = ""
    
    errors: List[Dict] = []
    warnings: List[Dict] = []


class ValueResponse(BaseModel):
    """Player value response."""
    name: str
    value: int
    position: str
    sources: List[str]
    raw_value: int
    effective_value: int


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    cache: Dict
    performance: Dict
    rate_limiter: Dict


# ============================================================================
# Dependencies
# ============================================================================

async def get_value_service_dep() -> DynastyValueService:
    """Dependency for value service."""
    return get_value_service()


async def get_calculator() -> DynastyTradeCalculator:
    """Dependency for trade calculator."""
    return DynastyTradeCalculator()


# ============================================================================
# API Endpoints
# ============================================================================

@router.post("/evaluate", response_model=TradeResponse)
@measure_performance("trade_evaluate")
async def evaluate_trade(
    request: TradeEvaluateRequest,
    value_service: DynastyValueService = Depends(get_value_service_dep),
    calculator: DynastyTradeCalculator = Depends(get_calculator)
):
    """
    Evaluate a dynasty trade.
    
    Provides:
    - Value comparison
    - Fairness assessment
    - Stud dominance bonus
    - Recommendations
    """
    try:
        # Convert to dicts for processing
        give = [p.dict() for p in request.give_players]
        get = [p.dict() for p in request.get_players]
        
        # Use robust evaluator with edge case handling
        result = evaluate_trade_robust(
            give_players=give,
            get_players=get,
            league_config={
                "num_teams": request.num_teams,
                "format": request.format
            }
        )
        
        # If valid, get detailed calculation
        if result["is_valid"]:
            calc_result = calculator.evaluate_trade(
                give_players=give,
                get_players=get,
                include_stud_bonus=request.include_stud_bonus
            )
            
            return TradeResponse(
                success=True,
                is_fair=calc_result.get("is_fair", result["is_fair"]),
                verdict=calc_result.get("verdict", "UNKNOWN"),
                recommendation=calc_result.get("recommendation", ""),
                give_total=calc_result.get("give_total_adjusted", result["give_total"]),
                get_total=calc_result.get("get_total_adjusted", result["get_total"]),
                difference=calc_result.get("difference", result["difference"]),
                margin=calc_result.get("margin", 0),
                stud_bonus=calc_result.get("stud_bonus", 0),
                stud_description=calc_result.get("stud_description", ""),
                errors=result.get("errors", []),
                warnings=result.get("warnings", [])
            )
        else:
            # Return validation errors
            return TradeResponse(
                success=False,
                is_fair=False,
                verdict="INVALID",
                recommendation="Fix validation errors",
                give_total=result.get("give_total", 0),
                get_total=result.get("get_total", 0),
                difference=result.get("difference", 0),
                margin=1.0,
                errors=result.get("errors", []),
                warnings=result.get("warnings", [])
            )
    
    except Exception as e:
        logger.error(f"Trade evaluation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/values", response_model=List[ValueResponse])
@measure_performance("trade_values")
async def get_player_values(
    player_names: List[str],
    format: str = Query("2qb", pattern="^(1qb|2qb)$"),
    value_service: DynastyValueService = Depends(get_value_service_dep)
):
    """
    Get dynasty values for players.
    
    Returns consensus values from multiple sources.
    """
    try:
        # Fetch all sources
        all_values = await value_service.fetch_all_sources(format)
        
        results = []
        for name in player_names:
            if name in all_values:
                consensus = value_service.calculate_consensus(all_values[name])
                results.append(ValueResponse(
                    name=name,
                    value=consensus.get("consensus", 0),
                    position=consensus.get("position", "WR"),
                    sources=consensus.get("sources_used", []),
                    raw_value=consensus.get("raw_value", 0),
                    effective_value=consensus.get("effective_value", 0)
                ))
            else:
                results.append(ValueResponse(
                    name=name,
                    value=0,
                    position="UNK",
                    sources=[],
                    raw_value=0,
                    effective_value=0
                ))
        
        return results
    
    except Exception as e:
        logger.error(f"Value lookup error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/suggestions")
@measure_performance("trade_suggestions")
async def get_trade_suggestions(
    request: TradeSuggestionRequest,
    calculator: DynastyTradeCalculator = Depends(get_calculator)
):
    """
    Get trade suggestions for acquiring a target player.
    
    Finds combinations of available players that
    approximate fair value for the target.
    """
    from app.services.trade_calculator import find_balance_picks
    
    target = request.target_player
    available = request.available_players
    
    suggestions = []
    target_value = request.target_value
    
    # Sort available by value
    sorted_players = sorted(
        available, 
        key=lambda p: p.value, 
        reverse=True
    )
    
    # Try different combinations
    for i, player in enumerate(sorted_players[:8]):
        # Single player match
        if abs(player.value - target_value) < target_value * 0.2:
            suggestions.append({
                "players": [player.name],
                "total_value": player.value,
                "match_quality": 1 - abs(player.value - target_value) / target_value
            })
        
        # Two-player combinations
        for j, player2 in enumerate(sorted_players[i+1:i+4]):
            combo_value = player.value + player2.value
            if abs(combo_value - target_value) < target_value * 0.25:
                suggestions.append({
                    "players": [player.name, player2.name],
                    "total_value": combo_value,
                    "match_quality": 1 - abs(combo_value - target_value) / target_value
                })
    
    # Sort by match quality
    suggestions.sort(key=lambda x: x["match_quality"], reverse=True)
    
    return {
        "target": target.name,
        "target_value": target_value,
        "suggestions": suggestions[:request.max_suggestions]
    }


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Get trade engine health status."""
    health = await get_service_health()
    return HealthResponse(**health)


@router.get("/cache/clear")
async def clear_cache():
    """Clear the trade calculation cache."""
    from app.services.trade_performance import _trade_cache
    _trade_cache.clear()
    return {"status": "cache_cleared"}


# ============================================================================
# League-Integrated Endpoints
# ============================================================================

@router.post("/league/evaluate")
@measure_performance("league_trade_evaluate")
async def evaluate_league_trade(
    league_id: str,
    roster_id: int,
    give_player_ids: List[str],
    get_player_ids: List[str],
    value_service: DynastyValueService = Depends(get_value_service_dep),
    calculator: DynastyTradeCalculator = Depends(get_calculator)
):
    """
    Evaluate a trade within a specific league context.
    
    Uses actual league roster data for validation.
    """
    async with SleeperClient() as client:
        # Fetch league data
        league_data = await client.get_full_league_data(league_id)
        if not league_data:
            raise HTTPException(status_code=404, detail="League not found")
        
        rosters = league_data.get("rosters", [])
        
        # Find user's roster
        user_roster = None
        for r in rosters:
            if r.get("roster_id") == roster_id:
                user_roster = r
                break
        
        if not user_roster:
            raise HTTPException(status_code=404, detail="Roster not found")
        
        # Fetch values
        all_values = await value_service.fetch_all_sources("2qb")
        
        # Get player details
        all_players = await client.get_all_players()
        
        # Build player lookups
        give_players = []
        get_players = []
        
        for pid in give_player_ids:
            pdata = all_players.get(pid, {})
            name = f"{pdata.get('first_name', '')} {pdata.get('last_name', '')}".strip()
            
            # Get value
            value = 0
            if name in all_values:
                consensus = value_service.calculate_consensus(all_values[name])
                value = consensus.get("consensus", 0)
            
            give_players.append({
                "player_id": pid,
                "name": name,
                "value": value,
                "position": pdata.get("position", "UNK")
            })
        
        for pid in get_player_ids:
            pdata = all_players.get(pid, {})
            name = f"{pdata.get('first_name', '')} {pdata.get('last_name', '')}".strip()
            
            value = 0
            if name in all_values:
                consensus = value_service.calculate_consensus(all_values[name])
                value = consensus.get("consensus", 0)
            
            get_players.append({
                "player_id": pid,
                "name": name,
                "value": value,
                "position": pdata.get("position", "UNK")
            })
        
        # Validate ownership
        roster_player_ids = set(user_roster.get("players", []) or [])
        validation_errors = []
        
        for player in give_players:
            if player["player_id"] not in roster_player_ids:
                validation_errors.append({
                    "code": "NOT_OWNED",
                    "message": f"You don't own {player['name']}"
                })
        
        if validation_errors:
            return {
                "success": False,
                "is_fair": False,
                "errors": validation_errors,
                "give_players": give_players,
                "get_players": get_players
            }
        
        # Evaluate
        result = calculator.evaluate_trade(give_players, get_players)
        
        return {
            "success": True,
            **result,
            "give_players": give_players,
            "get_players": get_players
        }


# ============================================================================
# Initialization
# ===========================================================================

@asynccontextmanager
async def lifespan(app):
    """Manage trade engine lifecycle."""
    # Startup
    from app.services.trade_performance import initialize_trade_engine
    await initialize_trade_engine()
    logger.info("Trade engine v3 started")
    
    yield
    
    # Shutdown
    from app.services.trade_performance import shutdown_trade_engine
    await shutdown_trade_engine()
    logger.info("Trade engine v3 stopped")
