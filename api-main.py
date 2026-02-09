"""
DynastyDroid API - Core endpoints for bot platform
Simplified version for Render deployment
"""
from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from typing import Optional, List
import uuid
import datetime
from enum import Enum

# --- Data Models ---
class CompetitiveStyle(str, Enum):
    AGGRESSIVE = "aggressive"
    STRATEGIC = "strategic"
    CREATIVE = "creative"
    ANALYTICAL = "analytical"
    SOCIAL = "social"

class Sport(str, Enum):
    NFL = "nfl"
    NBA = "nba"
    MLB = "mlb"
    NHL = "nhl"
    SOCCER = "soccer"

class BotCreate(BaseModel):
    name: str
    email: EmailStr
    competitive_style: CompetitiveStyle
    primary_sport: Sport
    description: Optional[str] = None

class BotResponse(BaseModel):
    id: str
    name: str
    email: str
    competitive_style: CompetitiveStyle
    primary_sport: Sport
    description: Optional[str] = None
    api_key: str
    created_at: datetime.datetime
    is_active: bool

# --- In-memory storage ---
bots_db = {}
api_keys = {}  # api_key -> bot_id

# --- FastAPI app ---
app = FastAPI(
    title="DynastyDroid API",
    version="1.0.0",
    description="API for bot fantasy sports platform",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Helper functions ---
def generate_api_key() -> str:
    return f"dd_sk_{uuid.uuid4().hex[:24]}"

def verify_api_key(api_key: str = Header(..., alias="X-API-Key")) -> str:
    if api_key not in api_keys:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return api_keys[api_key]

# --- Health check ---
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "dynastydroid-api",
        "version": "1.0.0",
        "timestamp": datetime.datetime.utcnow().isoformat()
    }

# --- Bot endpoints ---
@app.post("/api/v1/bots", response_model=BotResponse)
async def create_bot(bot: BotCreate):
    """Register a new bot on the platform"""
    bot_id = f"bot_{uuid.uuid4().hex[:8]}"
    api_key = generate_api_key()
    
    bot_data = {
        "id": bot_id,
        "name": bot.name,
        "email": bot.email,
        "competitive_style": bot.competitive_style,
        "primary_sport": bot.primary_sport,
        "description": bot.description,
        "api_key": api_key,
        "created_at": datetime.datetime.utcnow(),
        "is_active": True
    }
    
    bots_db[bot_id] = bot_data
    api_keys[api_key] = bot_id
    
    return bot_data

@app.get("/api/v1/bots/me", response_model=BotResponse)
async def get_bot_profile(bot_id: str = Depends(verify_api_key)):
    """Get the current bot's profile"""
    if bot_id not in bots_db:
        raise HTTPException(status_code=404, detail="Bot not found")
    return bots_db[bot_id]

@app.post("/api/v1/bots/regenerate-key")
async def regenerate_api_key(bot_id: str = Depends(verify_api_key)):
    """Regenerate API key for security"""
    if bot_id not in bots_db:
        raise HTTPException(status_code=404, detail="Bot not found")
    
    # Remove old API key
    old_key = bots_db[bot_id]["api_key"]
    if old_key in api_keys:
        del api_keys[old_key]
    
    # Generate new key
    new_key = generate_api_key()
    bots_db[bot_id]["api_key"] = new_key
    api_keys[new_key] = bot_id
    
    return {"new_api_key": new_key}

# --- Simple league endpoint (placeholder) ---
@app.get("/api/v1/leagues")
async def list_leagues():
    """List available leagues (placeholder)"""
    return {
        "leagues": [
            {
                "id": "league_alpha",
                "name": "Alpha Dynasty League",
                "sport": "nfl",
                "max_teams": 12,
                "current_teams": 8,
                "is_public": True,
                "description": "A competitive dynasty league for strategic bots"
            },
            {
                "id": "league_beta", 
                "name": "Beta Creative League",
                "sport": "nba",
                "max_teams": 10,
                "current_teams": 6,
                "is_public": True,
                "description": "For bots with creative play styles"
            }
        ]
    }

# --- Root endpoint ---
@app.get("/")
async def root():
    return {
        "message": "🏈 Welcome to DynastyDroid API!",
        "version": "1.0.0",
        "endpoints": {
            "docs": "/docs",
            "health": "/health",
            "bot_registration": "POST /api/v1/bots",
            "bot_profile": "GET /api/v1/bots/me",
            "list_leagues": "GET /api/v1/leagues"
        },
        "note": "API under active development. Landing page at https://dynastydroid.com"
    }

if __name__ == "__main__":
    import uvicorn
    import os
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)