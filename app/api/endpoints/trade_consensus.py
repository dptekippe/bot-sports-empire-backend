# app/api/endpoints/trade_consensus.py
"""
DynastyDroid Trade Consensus API - Phase 2
Uses ValueBlenderService (v2) for multi-source dynasty value blending

Endpoints:
- POST /api/v2/consensus-values - Get blended consensus values for players
- POST /api/v2/evaluate-trade - Evaluate a trade between two sides
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Optional
import asyncio

router = APIRouter(prefix="/api/v2", tags=["v2-consensus"])

# Import value blender v2
from app.services.value_blender_v2 import ValueBlenderService, BlendResult

# Global service instance (initialized on first request)
_service: Optional[ValueBlenderService] = None
_service_lock = asyncio.Lock()


async def get_service() -> ValueBlenderService:
    """Get or initialize the ValueBlenderService singleton"""
    global _service
    if _service is None:
        async with _service_lock:
            if _service is None:
                _service = ValueBlenderService()
                await _service.initialize()
    return _service


# === PYDANTIC MODELS ===

class ConsensusRequest(BaseModel):
    players: List[str]
    te_premium: bool = False


class BlendResultResponse(BaseModel):
    name: str
    position: str
    consensus: float
    sources_used: int
    breakdown: Dict[str, float]
    weights_applied: Dict[str, float]
    stud_bonus_applied: bool = False
    te_premium_applied: bool = False


class ConsensusResponse(BaseModel):
    results: List[BlendResultResponse]
    summary: Dict


class EvaluateTradeRequest(BaseModel):
    give: List[str]
    get: List[str]
    te_premium: bool = False


class TradeEvaluationResponse(BaseModel):
    give_total: float
    get_total: float
    net: float
    winner: str
    verdict: str
    give_players: List[BlendResultResponse]
    get_players: List[BlendResultResponse]


# === ENDPOINTS ===

@router.post("/consensus-values", response_model=ConsensusResponse)
async def get_consensus_values(request: ConsensusRequest):
    """
    Get blended consensus dynasty values for a list of players.
    
    Request body:
        players: List of player names (e.g., ["Bijan Robinson", "Josh Allen"])
        te_premium: Whether to apply 1.65x premium to TE values
    
    Response:
        results: List of BlendResult for each player
        summary: Service configuration summary
    """
    service = await get_service()
    
    # Update TE premium setting
    service.te_premium = request.te_premium
    
    results = []
    for player_name in request.players:
        result = await service.blend_player(player_name)
        # Normalize consensus to 0-999 scale for frontend compatibility
        normalized_consensus = min(result.consensus / 10, 999) if result.consensus > 0 else 0
        results.append(BlendResultResponse(
            name=result.name,
            position=result.position,
            consensus=round(normalized_consensus, 1),
            sources_used=result.sources_used,
            breakdown=result.breakdown,
            weights_applied=result.weights_applied,
            stud_bonus_applied=result.stud_bonus_applied,
            te_premium_applied=result.te_premium_applied
        ))
    
    return ConsensusResponse(
        results=results,
        summary=service.get_blend_summary()
    )


@router.post("/evaluate-trade", response_model=TradeEvaluationResponse)
async def evaluate_trade(request: EvaluateTradeRequest):
    """
    Evaluate a trade by blending values for both sides.
    
    Request body:
        give: List of players/picks being given away
        get: List of players/picks being received
        te_premium: Whether to apply 1.65x premium to TE values
    
    Response:
        give_total: Total blended value of players given
        get_total: Total blended value of players received
        net: Difference (get - give)
        winner: "give", "get", or "even"
        verdict: Human-readable verdict
        give_players: Breakdown of give side
        get_players: Breakdown of get side
    """
    service = await get_service()
    
    # Update TE premium setting
    service.te_premium = request.te_premium
    
    # Evaluate the trade
    evaluation = await service.blend_trade(request.give, request.get)
    
    # Convert to response format
    give_players = [
        BlendResultResponse(
            name=r.name,
            position=r.position,
            consensus=r.consensus,
            sources_used=r.sources_used,
            breakdown=r.breakdown,
            weights_applied=r.weights_applied,
            stud_bonus_applied=r.stud_bonus_applied,
            te_premium_applied=r.te_premium_applied
        )
        for r in evaluation["give"]["players"]
    ]
    
    get_players = [
        BlendResultResponse(
            name=r.name,
            position=r.position,
            consensus=r.consensus,
            sources_used=r.sources_used,
            breakdown=r.breakdown,
            weights_applied=r.weights_applied,
            stud_bonus_applied=r.stud_bonus_applied,
            te_premium_applied=r.te_premium_applied
        )
        for r in evaluation["get"]["players"]
    ]
    
    return TradeEvaluationResponse(
        give_total=evaluation["give"]["total"],
        get_total=evaluation["get"]["total"],
        net=evaluation["net"],
        winner=evaluation["winner"],
        verdict=evaluation["verdict"],
        give_players=give_players,
        get_players=get_players
    )
