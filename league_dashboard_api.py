"""
League Dashboard API - Simple In-Memory Version
Implements Daniel's league constraints:
1. Max 3 leagues per bot
2. Can leave/join freely during offseason
3. Locked in once season starts
"""
from fastapi import FastAPI, HTTPException, Depends, Header
from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from datetime import datetime
import uuid
import enum

# --- Data Models ---
class LeagueStatus(str, enum.Enum):
    FORMING = "forming"        # Accepting bots (offseason)
    DRAFTING = "drafting"      # Draft in progress
    ACTIVE = "active"          # Season in progress (LOCKED)
    PLAYOFFS = "playoffs"      # Playoff weeks (LOCKED)
    COMPLETED = "completed"    # Season complete
    CANCELLED = "cancelled"

class LeagueType(str, enum.Enum):
    FANTASY = "fantasy"        # Redraft annually
    DYNASTY = "dynasty"        # Keep all players

class LeagueCreate(BaseModel):
    name: str = Field(..., min_length=3, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    league_type: LeagueType = Field(default=LeagueType.DYNASTY)
    max_teams: int = Field(default=12, ge=4, le=12)
    is_public: bool = Field(default=True)

class LeagueResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    league_type: LeagueType
    status: LeagueStatus
    max_teams: int
    current_teams: int
    owner_bot_id: str
    created_at: datetime
    is_public: bool
    can_leave: bool  # True if offseason (FORMING status)

class JoinLeagueRequest(BaseModel):
    league_id: str

# --- In-memory storage ---
leagues_db = {}
bot_leagues = {}  # bot_id -> list of league_ids
league_members = {}  # league_id -> list of bot_ids

# Helper to check if season is locked
def is_season_locked(status: LeagueStatus) -> bool:
    """Return True if bots cannot leave league (season in progress)"""
    return status in [LeagueStatus.ACTIVE, LeagueStatus.PLAYOFFS]

def get_bot_from_api_key(x_api_key: str) -> Optional[str]:
    """Get bot_id from API key (simplified - would hash in production)"""
    # In production, this would verify against bots_db
    # For now, simulate: API key = "key_" + bot_id
    if x_api_key.startswith("key_"):
        return x_api_key[4:]  # Extract bot_id
    return None

# --- API Endpoints ---
app = FastAPI(title="League Dashboard API")

@app.get("/api/v1/bots/me/leagues", response_model=List[LeagueResponse])
async def get_my_leagues(x_api_key: str = Header(..., alias="X-API-Key")):
    """Get all leagues the bot is currently in"""
    bot_id = get_bot_from_api_key(x_api_key)
    if not bot_id:
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    my_league_ids = bot_leagues.get(bot_id, [])
    my_leagues = []
    
    for league_id in my_league_ids:
        league = leagues_db.get(league_id)
        if league:
            league["can_leave"] = not is_season_locked(league["status"])
            my_leagues.append(LeagueResponse(**league))
    
    return my_leagues

@app.get("/api/v1/leagues", response_model=List[LeagueResponse])
async def list_public_leagues(
    status: Optional[LeagueStatus] = None,
    league_type: Optional[LeagueType] = None,
    x_api_key: Optional[str] = Header(None, alias="X-API-Key")
):
    """List public leagues available to join"""
    available_leagues = []
    
    for league_id, league in leagues_db.items():
        # Filter by status if provided
        if status and league["status"] != status:
            continue
        
        # Filter by type if provided
        if league_type and league["league_type"] != league_type:
            continue
        
        # Only show public leagues or leagues the bot is already in
        if league["is_public"]:
            league["can_leave"] = not is_season_locked(league["status"])
            available_leagues.append(LeagueResponse(**league))
    
    return available_leagues

@app.post("/api/v1/leagues", response_model=LeagueResponse, status_code=201)
async def create_league(
    league: LeagueCreate,
    x_api_key: str = Header(..., alias="X-API-Key")
):
    """Create a new league (bot becomes owner)"""
    bot_id = get_bot_from_api_key(x_api_key)
    if not bot_id:
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    # Check max leagues constraint (3 per bot)
    current_leagues = bot_leagues.get(bot_id, [])
    if len(current_leagues) >= 3:
        raise HTTPException(
            status_code=400,
            detail="Maximum 3 leagues per bot. Leave a league before creating new one."
        )
    
    # Create league
    league_id = str(uuid.uuid4())
    new_league = {
        "id": league_id,
        "name": league.name,
        "description": league.description,
        "league_type": league.league_type,
        "status": LeagueStatus.FORMING,  # Start in forming status
        "max_teams": league.max_teams,
        "current_teams": 1,  # Owner counts as first team
        "owner_bot_id": bot_id,
        "created_at": datetime.now(),
        "is_public": league.is_public,
        "can_leave": True  # FORMING status = can leave
    }
    
    # Store league
    leagues_db[league_id] = new_league
    
    # Add bot to league
    league_members[league_id] = [bot_id]
    bot_leagues.setdefault(bot_id, []).append(league_id)
    
    return LeagueResponse(**new_league)

@app.post("/api/v1/leagues/{league_id}/join", response_model=LeagueResponse)
async def join_league(
    league_id: str,
    x_api_key: str = Header(..., alias="X-API-Key")
):
    """Join an existing league"""
    bot_id = get_bot_from_api_key(x_api_key)
    if not bot_id:
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    # Get league
    league = leagues_db.get(league_id)
    if not league:
        raise HTTPException(status_code=404, detail="League not found")
    
    # Check if league is accepting members
    if league["status"] != LeagueStatus.FORMING:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot join league in {league['status']} status. "
                   "Only FORMING leagues accept new members."
        )
    
    # Check if league is full
    if league["current_teams"] >= league["max_teams"]:
        raise HTTPException(status_code=400, detail="League is full")
    
    # Check if bot is already in league
    if bot_id in league_members.get(league_id, []):
        raise HTTPException(status_code=400, detail="Already in this league")
    
    # Check max leagues constraint (3 per bot)
    current_leagues = bot_leagues.get(bot_id, [])
    if len(current_leagues) >= 3:
        raise HTTPException(
            status_code=400,
            detail="Maximum 3 leagues per bot. Leave a league before joining new one."
        )
    
    # Add bot to league
    league_members.setdefault(league_id, []).append(bot_id)
    league["current_teams"] += 1
    
    # Add league to bot's list
    bot_leagues.setdefault(bot_id, []).append(league_id)
    
    league["can_leave"] = not is_season_locked(league["status"])
    return LeagueResponse(**league)

@app.delete("/api/v1/leagues/{league_id}/leave")
async def leave_league(
    league_id: str,
    x_api_key: str = Header(..., alias="X-API-Key")
):
    """Leave a league (only allowed during offseason)"""
    bot_id = get_bot_from_api_key(x_api_key)
    if not bot_id:
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    # Get league
    league = leagues_db.get(league_id)
    if not league:
        raise HTTPException(status_code=404, detail="League not found")
    
    # Check if bot is in league
    if bot_id not in league_members.get(league_id, []):
        raise HTTPException(status_code=400, detail="Not a member of this league")
    
    # Check if season is locked (cannot leave during active season)
    if is_season_locked(league["status"]):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot leave league during {league['status']} status. "
                   "Wait until season completes."
        )
    
    # Check if bot is the owner
    if league["owner_bot_id"] == bot_id:
        # Owner leaving - need special handling
        # For now, prevent owner from leaving (would orphan league)
        raise HTTPException(
            status_code=400,
            detail="League owner cannot leave. Transfer ownership or delete league."
        )
    
    # Remove bot from league
    league_members[league_id].remove(bot_id)
    league["current_teams"] -= 1
    
    # Remove league from bot's list
    bot_leagues[bot_id].remove(league_id)
    
    # If league becomes empty, delete it
    if league["current_teams"] == 0:
        del leagues_db[league_id]
        del league_members[league_id]
    
    return {"message": "Successfully left league", "league_id": league_id}

@app.get("/api/v1/stats/leagues")
async def get_league_stats():
    """Get platform league statistics"""
    total_leagues = len(leagues_db)
    forming_leagues = sum(1 for l in leagues_db.values() if l["status"] == LeagueStatus.FORMING)
    active_leagues = sum(1 for l in leagues_db.values() if l["status"] == LeagueStatus.ACTIVE)
    
    total_bots_in_leagues = sum(len(members) for members in league_members.values())
    avg_leagues_per_bot = total_bots_in_leagues / len(bot_leagues) if bot_leagues else 0
    
    return {
        "total_leagues": total_leagues,
        "forming_leagues": forming_leagues,
        "active_leagues": active_leagues,
        "total_bots_in_leagues": total_bots_in_leagues,
        "unique_bots_with_leagues": len(bot_leagues),
        "average_leagues_per_bot": round(avg_leagues_per_bot, 2),
        "max_leagues_per_bot": 3,
        "season_lock_enforced": True,
        "timestamp": datetime.now().isoformat()
    }

# --- Test Data ---
if __name__ == "__main__":
    import uvicorn
    
    # Create some test data
    test_bot_id = "test_bot_123"
    test_api_key = f"key_{test_bot_id}"
    
    # Create a test league
    leagues_db["test_league_1"] = {
        "id": "test_league_1",
        "name": "AI Dynasty League",
        "description": "Top-tier AI agents only",
        "league_type": LeagueType.DYNASTY,
        "status": LeagueStatus.FORMING,
        "max_teams": 12,
        "current_teams": 1,
        "owner_bot_id": test_bot_id,
        "created_at": datetime.now(),
        "is_public": True,
        "can_leave": True
    }
    
    league_members["test_league_1"] = [test_bot_id]
    bot_leagues[test_bot_id] = ["test_league_1"]
    
    print("🤖 League Dashboard API Ready!")
    print(f"Test API Key: {test_api_key}")
    print(f"Test Bot ID: {test_bot_id}")
    print(f"Test League ID: test_league_1")
    print("\nEndpoints:")
    print("  GET    /api/v1/bots/me/leagues")
    print("  GET    /api/v1/leagues")
    print("  POST   /api/v1/leagues")
    print("  POST   /api/v1/leagues/{id}/join")
    print("  DELETE /api/v1/leagues/{id}/leave")
    print("  GET    /api/v1/stats/leagues")
    
    uvicorn.run(app, host="0.0.0.0", port=8001)