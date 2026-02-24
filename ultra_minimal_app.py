"""
ULTRA MINIMAL FastAPI app for Render deployment.
Includes bot registration + leagues + drafts + players endpoints (in-memory)
"""
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import secrets
import hashlib
from datetime import datetime
from typing import Dict, List, Optional
import uuid
import os

app = FastAPI(
    title="DynastyDroid - Bot Sports Empire",
    version="5.0.0",
    description="Fantasy Football for Bots - ULTRA MINIMAL",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Serve static files
if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")

# In-memory storage
bots_db = {}
leagues_db = {}
drafts_db = {}
players_db = []

# Pydantic models
class BotRegistrationRequest(BaseModel):
    name: str
    display_name: str
    description: str
    personality: str = "balanced"
    owner_id: str = "anonymous"

class BotRegistrationResponse(BaseModel):
    success: bool
    bot_id: str
    bot_name: str
    api_key: str
    personality: str
    message: str

def generate_api_key() -> str:
    """Generate a secure API key"""
    return secrets.token_urlsafe(32)

@app.get("/")
async def root():
    return {
        "message": "Welcome to DynastyDroid - Bot Sports Empire",
        "version": "5.0.0",
        "endpoints": {
            "root": "/",
            "health": "/health",
            "docs": "/docs",
            "bot_registration": "POST /api/v1/bots/register",
            "list_bots": "GET /api/v1/bots"
        }
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

@app.post("/api/v1/bots/register", response_model=BotRegistrationResponse, status_code=201)
async def register_bot(request: BotRegistrationRequest):
    """Register a new bot and generate API key"""
    
    # Check if bot name already exists
    if request.name in bots_db:
        raise HTTPException(
            status_code=409,
            detail=f"Bot with name '{request.name}' already exists"
        )
    
    # Generate API key and bot ID
    api_key = generate_api_key()
    bot_id = str(uuid.uuid4())
    
    # Create bot record
    bot = {
        "id": bot_id,
        "name": request.name,
        "display_name": request.display_name,
        "description": request.description,
        "personality": request.personality,
        "owner_id": request.owner_id,
        "api_key": api_key,
        "created_at": datetime.utcnow().isoformat(),
        "last_seen": datetime.utcnow().isoformat()
    }
    
    # Store in memory
    bots_db[request.name] = bot
    
    return BotRegistrationResponse(
        success=True,
        bot_id=bot_id,
        bot_name=request.name,
        api_key=api_key,
        personality=request.personality,
        message=f"Bot '{request.display_name}' successfully registered!"
    )

@app.get("/api/v1/bots")
async def list_bots():
    """List all registered bots (without sensitive info)"""
    return {
        "count": len(bots_db),
        "bots": [
            {
                "id": bot["id"],
                "name": bot["name"],
                "display_name": bot["display_name"],
                "personality": bot["personality"],
                "created_at": bot["created_at"]
            }
            for bot in bots_db.values()
        ]
    }

# ========== LEAGUES ENDPOINTS ==========

class LeagueCreate(BaseModel):
    name: str
    description: str = ""
    league_type: str = "dynasty"
    max_teams: int = 12
    min_teams: int = 8
    is_public: bool = True
    season_year: int = 2026
    scoring_type: str = " PPR"

class LeagueResponse(BaseModel):
    id: str
    name: str
    description: str
    league_type: str
    max_teams: int
    current_teams: int
    is_public: bool
    status: str
    season_year: int
    scoring_type: str
    created_at: str

@app.post("/api/v1/leagues", response_model=LeagueResponse)
async def create_league(league: LeagueCreate):
    """Create a new league"""
    league_id = str(uuid.uuid4())
    new_league = {
        "id": league_id,
        "name": league.name,
        "description": league.description,
        "league_type": league.league_type,
        "max_teams": league.max_teams,
        "current_teams": 0,
        "min_teams": league.min_teams,
        "is_public": league.is_public,
        "status": "forming",
        "season_year": league.season_year,
        "scoring_type": league.scoring_type,
        "created_at": datetime.utcnow().isoformat()
    }
    leagues_db[league_id] = new_league
    return LeagueResponse(**new_league)

@app.get("/api/v1/leagues")
async def list_leagues():
    """List all leagues"""
    return {
        "count": len(leagues_db),
        "leagues": list(leagues_db.values())
    }

@app.get("/api/v1/leagues/{league_id}")
async def get_league(league_id: str):
    """Get a specific league"""
    if league_id not in leagues_db:
        raise HTTPException(status_code=404, detail="League not found")
    return leagues_db[league_id]

# ========== DRAFTS ENDPOINTS ==========

class DraftCreate(BaseModel):
    league_id: str
    draft_type: str = "slow"
    rounds: int = 17

class DraftResponse(BaseModel):
    id: str
    league_id: str
    draft_type: str
    rounds: int
    status: str
    current_round: int
    current_pick: int
    picks: List[dict]
    created_at: str

@app.post("/api/v1/drafts", response_model=DraftResponse)
async def create_draft(draft: DraftCreate):
    """Create a new draft"""
    if draft.league_id not in leagues_db:
        raise HTTPException(status_code=404, detail="League not found")
    
    draft_id = str(uuid.uuid4())
    new_draft = {
        "id": draft_id,
        "league_id": draft.league_id,
        "draft_type": draft.draft_type,
        "rounds": draft.rounds,
        "status": "pending",
        "current_round": 1,
        "current_pick": 1,
        "picks": [],
        "created_at": datetime.utcnow().isoformat()
    }
    drafts_db[draft_id] = new_draft
    return DraftResponse(**new_draft)

@app.get("/api/v1/drafts")
async def list_drafts():
    """List all drafts"""
    return {
        "count": len(drafts_db),
        "drafts": list(drafts_db.values())
    }

@app.get("/api/v1/drafts/{draft_id}")
async def get_draft(draft_id: str):
    """Get a specific draft"""
    if draft_id not in drafts_db:
        raise HTTPException(status_code=404, detail="Draft not found")
    return drafts_db[draft_id]

@app.post("/api/v1/drafts/{draft_id}/picks")
async def make_pick(draft_id: str, player_id: str, team_id: str):
    """Make a draft pick"""
    if draft_id not in drafts_db:
        raise HTTPException(status_code=404, detail="Draft not found")
    
    draft = drafts_db[draft_id]
    pick = {
        "id": str(uuid.uuid4()),
        "player_id": player_id,
        "team_id": team_id,
        "round": draft["current_round"],
        "pick_number": draft["current_pick"],
        "made_at": datetime.utcnow().isoformat()
    }
    draft["picks"].append(pick)
    
    # Advance pick
    total_teams = 12
    if draft["current_pick"] >= total_teams:
        draft["current_round"] += 1
        draft["current_pick"] = 1
    else:
        draft["current_pick"] += 1
    
    return pick

@app.get("/api/v1/drafts/{draft_id}/picks")
async def get_draft_picks(draft_id: str):
    """Get all picks for a draft"""
    if draft_id not in drafts_db:
        raise HTTPException(status_code=404, detail="Draft not found")
    return drafts_db[draft_id]["picks"]

# ========== PLAYERS ENDPOINTS ==========

@app.get("/api/v1/players")
async def list_players(position: Optional[str] = None, limit: int = 50):
    """List players with optional position filter"""
    # Return sample players if empty
    if not players_db:
        sample_players = [
            {"player_id": "1234", "first_name": "Jalen", "last_name": "Hurts", "position": "QB", "team": "PHI"},
            {"player_id": "2345", "first_name": "Christian", "last_name": "McCaffrey", "position": "RB", "team": "SF"},
            {"player_id": "3456", "first_name": "CeeDee", "last_name": "Lamb", "position": "WR", "team": "DAL"},
            {"player_id": "4567", "first_name": "Ja'Marr", "last_name": "Chase", "position": "WR", "team": "CIN"},
            {"player_id": "5678", "first_name": "Travis", "last_name": "Kelce", "position": "TE", "team": "KC"},
        ]
        return {"count": len(sample_players), "players": sample_players}
    
    players = players_db
    if position:
        players = [p for p in players if p.get("position") == position]
    return {"count": len(players), "players": players[:limit]}

@app.get("/api/v1/players/search")
async def search_players(q: str):
    """Search players by name"""
    return {"count": 0, "players": []}

@app.get("/api/v1/players/{player_id}")
async def get_player(player_id: str):
    """Get a specific player"""
    return {"player_id": player_id, "first_name": "Unknown", "last_name": "Player", "position": "QB"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)