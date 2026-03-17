"""
Sleeper League API Endpoints.

Endpoints for fetching Sleeper league data for the trade calculator.
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List, Dict, Any
from pydantic import BaseModel

from app.integrations.sleeper_client import SleeperClient
from app.services.dynasty_values import DynastyValuesService

router = APIRouter(tags=["sleeper"])


# Request/Response Models
class LeagueImportRequest(BaseModel):
    league_id: str
    format: str = "2qb"  # 1qb or 2qb (superflex)


class RosterPlayer(BaseModel):
    player_id: str
    name: str
    position: str
    team: Optional[str] = "UNK"
    value: Optional[int] = None


class RosterTeam(BaseModel):
    roster_id: int
    owner_id: str
    owner_name: str
    players: List[RosterPlayer]
    total_value: int


class LeagueImportResponse(BaseModel):
    league_id: str
    league_name: str
    format: str
    teams: List[RosterTeam]
    user_roster: Optional[RosterTeam] = None


@router.get("/league/{league_id}")
async def get_league(league_id: str):
    """Get basic league info."""
    async with SleeperClient() as client:
        league = await client.get_league(league_id)
        if not league:
            raise HTTPException(status_code=404, detail="League not found")
        return league


@router.get("/league/{league_id}/rosters")
async def get_league_rosters(league_id: str, format: str = Query("2qb", pattern="^(1qb|2qb)$")):
    """
    Get all rosters with dynasty values.
    
    - **league_id**: Sleeper league ID
    - **format**: "1qb" or "2qb" (superflex)
    """
    async with SleeperClient() as client:
        # Fetch league data
        league = await client.get_league(league_id)
        if not league:
            raise HTTPException(status_code=404, detail="League not found")
        
        rosters = await client.get_rosters(league_id)
        users = await client.get_league_users(league_id)
        
        if not rosters:
            raise HTTPException(status_code=404, detail="No rosters found")
        
        # Fetch player values
        values_service = DynastyValuesService()
        values = await values_service.fetch_dynasty_process(format)
        
        # Fetch all players for name lookup
        all_players = await client.get_all_players()
        
        # Build user lookup
        user_lookup = {u.get("user_id"): u.get("display_name", "Unknown") for u in users}
        
        # Build teams
        teams = []
        for roster in rosters:
            roster_id = roster.get("roster_id")
            owner_id = roster.get("owner_id")
            player_ids = roster.get("players", []) or []
            
            # Get player details
            roster_players = []
            total_value = 0
            
            for pid in player_ids:
                player_data = all_players.get(pid)
                if not player_data:
                    continue
                
                name = f"{player_data.get('first_name', '')} {player_data.get('last_name', '')}".strip()
                pos = player_data.get("position", "UNK")
                team = player_data.get("team", "UNK")
                
                # Get dynasty value
                value = values_service.get_player_value(name, values)
                if value:
                    total_value += value
                
                roster_players.append(RosterPlayer(
                    player_id=pid,
                    name=name,
                    position=pos,
                    team=team,
                    value=value
                ))
            
            teams.append(RosterTeam(
                roster_id=roster_id,
                owner_id=owner_id,
                owner_name=user_lookup.get(owner_id, "Unknown"),
                players=roster_players,
                total_value=total_value
            ))
        
        return LeagueImportResponse(
            league_id=league_id,
            league_name=league.get("name", "Unknown League"),
            format=format,
            teams=teams
        )


@router.post("/import")
async def import_league(request: LeagueImportRequest):
    """Import league and return full data with values."""
    # Delegate to GET endpoint
    return await get_league_rosters(request.league_id, request.format)
