"""
Trade Evaluation API Endpoints.

POST /api/v1/trade/evaluate - Evaluate a proposed trade
"""
from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from pydantic import BaseModel

from app.services.dynasty_values import DynastyValuesService
from app.services.trade_evaluator import (
    analyze_trade, LeagueConfig, DRAFT_PICK_VALUES
)
from app.integrations.sleeper_client import SleeperClient

router = APIRouter(tags=["trade"])


# Request Models
class TradeEvaluateRequest(BaseModel):
    league_id: str
    user_roster_id: int  # Roster ID of the user proposing
    outgoing_player_ids: List[str]
    incoming_player_ids: List[str]
    format: str = "2qb"  # "1qb" or "2qb"
    num_teams: int = 12
    flex: int = 3
    te_premium: bool = False
    fair_margin: float = 0.15


class TradeEvaluateResponse(BaseModel):
    outgoing: List[dict]
    incoming: List[dict]
    outgoing_value: int
    incoming_value: int
    value_difference: int
    is_fair: bool
    team_classification: str
    strengths: List[str]
    weaknesses: List[str]
    narrative: str


@router.post("/evaluate", response_model=TradeEvaluateResponse)
async def evaluate_trade(request: TradeEvaluateRequest):
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
        
        # Fetch player values
        values_service = DynastyValuesService()
        values = await values_service.fetch_dynasty_process(request.format)
        
        # Fetch all players for details
        all_players = await client.get_all_players()
        
        # Build player lookup (id -> details)
        player_lookup = {}
        for pid, data in all_players.items():
            player_lookup[pid] = data
        
        # Get user roster players
        roster_player_ids = user_roster.get("players", []) or []
        user_roster_players = []
        for pid in roster_player_ids:
            pdata = player_lookup.get(pid, {})
            name = f"{pdata.get('first_name', '')} {pdata.get('last_name', '')}".strip()
            value = values.get(name, 0)
            if value:
                user_roster_players.append({
                    "player_id": pid,
                    "name": name,
                    "position": pdata.get("position", "UNK"),
                    "team": pdata.get("team", "UNK"),
                    "value": value
                })
        
        # Build config
        format_map = {"1qb": "1QB", "2qb": "Superflex"}
        config = LeagueConfig(
            num_teams=request.num_teams,
            format_=format_map.get(request.format, "Superflex"),
            flex=request.flex,
            te_premium=request.te_premium,
            fair_margin=request.fair_margin
        )
        
        # Analyze trade
        result = analyze_trade(
            user_roster=user_roster_players,
            outgoing_player_ids=request.outgoing_player_ids,
            incoming_player_ids=request.incoming_player_ids,
            player_values=values,
            player_details=player_lookup,
            config=config
        )
        
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        
        return result


@router.get("/values")
async def get_player_values(format: str = Query("2qb", pattern="^(1qb|2qb)$")):
    """Get all dynasty player values."""
    values_service = DynastyValuesService()
    values = await values_service.fetch_dynasty_process(format)
    
    # Return as list sorted by value
    player_list = [{"name": name, "value": value} for name, value in values.items()]
    player_list.sort(key=lambda x: x["value"], reverse=True)
    
    return {
        "format": format,
        "count": len(player_list),
        "players": player_list
    }
