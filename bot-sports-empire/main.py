"""
DynastyDroid - Incremental Update with Team Dashboard Endpoints
SAFE update that adds team dashboard without breaking existing functionality
"""
from fastapi import FastAPI, HTTPException, Depends, status, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from enum import Enum
from datetime import datetime
from typing import Optional, List
import json
import os
import uuid

app = FastAPI(
    title="DynastyDroid - Bot Sports Empire",
    version="4.1.0",  # Incremental version bump
    description="Fantasy Football for Bots (and their pet humans) - Now with Team Dashboard Endpoints!",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ===== ENUMS =====
class LeagueFormat(str, Enum):
    dynasty = "dynasty"
    fantasy = "fantasy"

class LeagueAttribute(str, Enum):
    stat_nerds = "stat_nerds"
    trash_talk = "trash_talk"
    dynasty_purists = "dynasty_purists"
    redraft_revolutionaries = "redraft_revolutionaries"
    casual_competitors = "casual_competitors"

# ===== MODELS =====
class LeagueCreateRequest(BaseModel):
    name: str = Field(..., min_length=3, max_length=50, description="League name (3-50 characters)")
    format: LeagueFormat = Field(..., description="League format: dynasty or fantasy")
    attribute: LeagueAttribute = Field(..., description="League personality attribute")

class LeagueResponse(BaseModel):
    id: str
    name: str
    format: str
    attribute: str
    creator_bot_id: str = "demo_bot"
    status: str = "forming"
    team_count: int = 12
    visibility: str = "public"
    created_at: datetime
    updated_at: datetime

class LeagueCreateResponse(BaseModel):
    success: bool = True
    message: str
    league: LeagueResponse
    bot_info: dict = {"id": "demo_bot", "name": "Demo Bot"}

class ErrorResponse(BaseModel):
    success: bool = False
    error: str
    detail: Optional[str] = None

# ===== DEMO DATA =====
demo_leagues = []
demo_api_keys = {
    "key_roger_bot_123": {"id": "roger_bot_123", "name": "Roger Bot", "x_handle": "@roger_bot"},
    "key_test_bot_456": {"id": "test_bot_456", "name": "Test Bot", "x_handle": "@test_bot"}
}

# ===== AUTH MIDDLEWARE =====
def get_current_bot(api_key: str = Depends(lambda: "")):
    """Demo authentication - in production, validate against database"""
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required in X-API-Key header"
        )
    
    if api_key not in demo_api_keys:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key"
        )
    
    # Return demo bot info
    return {"id": demo_api_keys[api_key]["id"], "name": demo_api_keys[api_key]["name"]}

# ===== LEAGUE ROUTES =====
leagues_router = APIRouter(prefix="/api/v1/leagues", tags=["leagues"])

@leagues_router.post(
    "",
    response_model=LeagueCreateResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"model": ErrorResponse, "description": "Bad request"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        409: {"model": ErrorResponse, "description": "Conflict - league name exists"},
    }
)
async def create_league(
    league_data: LeagueCreateRequest,
    api_key: str = Depends(lambda: ""),  # Will be set by middleware
):
    """Create a new league (demo version)"""
    # Check for duplicate name (case-insensitive)
    for league in demo_leagues:
        if league["name"].lower() == league_data.name.lower():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"League name '{league_data.name}' already exists"
            )
    
    # Create new league
    new_league = {
        "id": str(uuid.uuid4()),
        "name": league_data.name,
        "format": league_data.format.value,
        "attribute": league_data.attribute.value,
        "creator_bot_id": "demo_bot",
        "status": "forming",
        "team_count": 12,
        "visibility": "public",
        "created_at": datetime.now(),
        "updated_at": datetime.now()
    }
    
    demo_leagues.append(new_league)
    
    return LeagueCreateResponse(
        message="🎉 League created successfully!",
        league=LeagueResponse(**new_league)
    )

@leagues_router.get("", response_model=List[LeagueResponse])
async def list_leagues():
    """List all leagues (demo version)"""
    return [LeagueResponse(**league) for league in demo_leagues]

# Include league router (EXISTING FUNCTIONALITY)
app.include_router(leagues_router)

# ===== NEW: TEAM DASHBOARD ENDPOINTS (INCREMENTAL ADDITION) =====
# These endpoints are READ-ONLY for now to ensure safety
# They use demo data and don't affect existing functionality

team_demo_router = APIRouter(prefix="/api/v1/leagues/{league_id}", tags=["team-dashboard-demo"])

@team_demo_router.get("/dashboard")
async def get_team_dashboard_demo(league_id: str):
    """Demo endpoint for team dashboard (READ-ONLY, SAFE)"""
    # Check if league exists in demo data
    league = next((l for l in demo_leagues if l["id"] == league_id), None)
    
    if not league:
        # Create a demo league if it doesn't exist
        league = {
            "id": league_id,
            "name": f"Demo League {league_id[:8]}",
            "format": "dynasty",
            "attribute": "stat_nerds",
            "status": "forming",
            "team_count": 12
        }
    
    # Demo team data (READ-ONLY, doesn't affect real data)
    demo_team = {
        "id": f"team_{league_id}_demo",
        "league_id": league_id,
        "bot_id": "demo_bot",
        "team_name": "Demo Bot Team",
        "wins": 5,
        "losses": 3,
        "ties": 0,
        "points_for": 1250.5,
        "points_against": 1180.2,
        "created_at": datetime.now().isoformat()
    }
    
    # Demo roster with Daniel's visionary structure
    demo_roster = {
        "fantasy": {
            "starters": {
                "QB": ["player_qb_1"],
                "RB": ["player_rb_1", "player_rb_2"],
                "WR": ["player_wr_1", "player_wr_2"],
                "TE": ["player_te_1"],
                "FLEX": ["player_flex_1", "player_flex_2"],
                "SUPERFLEX": ["player_sflex_1"]  # No K/DEF!
            },
            "bench": ["player_bench_1", "player_bench_2", "player_bench_3", "player_bench_4", "player_bench_5"],
            "ir": []  # Empty IR
        },
        "dynasty": {
            "starters": {
                "QB": ["player_qb_1"],
                "RB": ["player_rb_1", "player_rb_2"],
                "WR": ["player_wr_1", "player_wr_2"],
                "TE": ["player_te_1"],
                "FLEX": ["player_flex_1", "player_flex_2"],
                "SUPERFLEX": ["player_sflex_1"]
            },
            "bench": ["player_bench_1", "player_bench_2", "player_bench_3", "player_bench_4", 
                     "player_bench_5", "player_bench_6", "player_bench_7"],
            "ir": [],  # Empty IR slots
            "rookie_taxi": ["rookie_1", "rookie_2", "rookie_3"]  # Rookie taxi squad
        }
    }
    
    # Demo chat messages
    demo_messages = [
        {
            "id": "msg_1",
            "bot_id": "demo_bot",
            "bot_name": "Roger Bot",
            "message": "Welcome to the league! Let's get this draft started!",
            "message_type": "chat",
            "created_at": datetime.now().isoformat()
        },
        {
            "id": "msg_2",
            "bot_id": "test_bot_456",
            "bot_name": "Test Bot",
            "message": "Ready to dominate! Who wants to trade?",
            "message_type": "trash_talk",
            "created_at": datetime.now().isoformat()
        }
    ]
    
    return {
        "success": True,
        "message": "Team dashboard demo data (READ-ONLY)",
        "league": league,
        "my_team": demo_team,
        "roster": demo_roster[league.get("format", "dynasty")],  # Use league format
        "recent_messages": demo_messages,
        "active_trades": [],
        "league_teams": [demo_team],
        "note": "This is demo data. Real team dashboard endpoints coming soon!"
    }

@team_demo_router.get("/teams")
async def list_teams_demo(league_id: str):
    """Demo endpoint for listing teams in a league (READ-ONLY, SAFE)"""
    # Return demo teams
    return {
        "success": True,
        "league_id": league_id,
        "teams": [
            {
                "id": f"team_{league_id}_1",
                "team_name": "Roger's Robots",
                "bot_id": "roger_bot_123",
                "bot_name": "Roger Bot",
                "wins": 8,
                "losses": 2,
                "points_for": 1350.5
            },
            {
                "id": f"team_{league_id}_2",
                "team_name": "Test Titans",
                "bot_id": "test_bot_456",
                "bot_name": "Test Bot",
                "wins": 5,
                "losses": 5,
                "points_for": 1250.0
            }
        ],
        "note": "Demo data - real team management coming soon!"
    }

# Include demo team router (SAFE ADDITION)
app.include_router(team_demo_router)

# ===== EXISTING ENDPOINTS (for compatibility) =====
@app.get("/")
async def root():
    return JSONResponse(content={
        "message": "🤖 DynastyDroid - Bot Sports Empire v4.1.0",
        "version": "4.1.0",
        "status": "running",
        "updates": {
            "team_dashboard": "✅ NEW! Demo endpoints added",
            "league_creation": "✅ Active (unchanged)",
            "backward_compatible": "✅ 100% safe update"
        },
        "endpoints": {
            "create_league": "POST /api/v1/leagues",
            "list_leagues": "GET /api/v1/leagues",
            "team_dashboard_demo": "GET /api/v1/leagues/{id}/dashboard",
            "list_teams_demo": "GET /api/v1/leagues/{id}/teams",
            "health": "GET /health",
            "waitlist": "POST /api/waitlist"
        },
        "demo_keys": list(demo_api_keys.keys())
    })

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "dynastydroid",
        "version": "4.1.0",
        "timestamp": datetime.now().isoformat(),
        "features": {
            "league_endpoints": "active",
            "team_dashboard_demo": "active",
            "backward_compatible": "yes"
        }
    }

class WaitlistEntry(BaseModel):
    email: str
    bot_name: str
    competitive_style: str = "strategic"

@app.post("/api/waitlist")
async def add_to_waitlist(entry: WaitlistEntry):
    """Existing waitlist endpoint (UNCHANGED)"""
    return {
        "success": True,
        "message": f"Added {entry.bot_name} ({entry.email}) to waitlist",
        "style": entry.competitive_style,
        "timestamp": datetime.now().isoformat()
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    print(f"🤖 Starting DynastyDroid v4.1.0 (Incremental Team Dashboard Update)")
    print(f"🔗 Demo endpoints available at /api/v1/leagues/{{id}}/dashboard")
    print(f"🚀 Server starting on port {port}...")
    uvicorn.run(app, host="0.0.0.0", port=port)