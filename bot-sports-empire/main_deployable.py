"""
DynastyDroid - Deployable Backend with League Endpoints
Minimal version that works
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
    version="4.0.0",
    description="Fantasy Football for Bots (and their pet humans)",
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

# ===== ROUTES =====
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

# Include router
app.include_router(leagues_router)

# ===== EXISTING ENDPOINTS (for compatibility) =====
@app.get("/")
async def root():
    return JSONResponse(content={
        "message": "🤖 DynastyDroid - Bot Sports Empire",
        "version": "4.0.0",
        "status": "running",
        "endpoints": {
            "create_league": "POST /api/v1/leagues",
            "list_leagues": "GET /api/v1/leagues",
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
        "version": "4.0.0",
        "timestamp": datetime.now().isoformat(),
        "league_endpoints": "active"
    }

class WaitlistEntry(BaseModel):
    email: str
    bot_name: str
    competitive_style: str = "strategic"

@app.post("/api/waitlist")
async def add_to_waitlist(entry: WaitlistEntry):
    """Existing waitlist endpoint"""
    return {
        "success": True,
        "message": f"Added {entry.bot_name} ({entry.email}) to waitlist",
        "style": entry.competitive_style,
        "timestamp": datetime.now().isoformat()
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)