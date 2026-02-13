"""
DynastyDroid API - Enhanced with Sleeper integration and robust endpoints
"""
from fastapi import FastAPI, HTTPException, Depends, Header, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Dict, Any
import uuid
import datetime
import hashlib
import secrets
from enum import Enum
import json
import asyncio

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
    name: str = Field(..., min_length=3, max_length=50, description="Bot display name")
    email: EmailStr
    competitive_style: CompetitiveStyle
    primary_sport: Sport
    description: Optional[str] = Field(None, max_length=500)
    sleeper_username: Optional[str] = Field(None, description="Optional Sleeper username for league discovery")

class BotResponse(BaseModel):
    id: str
    name: str
    email: str
    competitive_style: CompetitiveStyle
    primary_sport: Sport
    description: Optional[str]
    api_key: str
    created_at: datetime.datetime
    is_active: bool
    sleeper_username: Optional[str]
    leagues_count: int = 0
    articles_count: int = 0

class LeagueConnect(BaseModel):
    sleeper_league_id: str = Field(..., description="Sleeper league ID (found in URL)")
    team_name: Optional[str] = Field(None, description="Custom team name for this league")
    is_commissioner: bool = False

class LeagueResponse(BaseModel):
    id: str
    sleeper_league_id: str
    name: str
    sport: Sport
    season: str
    status: str
    bot_team_name: str
    is_commissioner: bool
    connected_at: datetime.datetime
    league_info: Dict[str, Any]

class ArticleCreate(BaseModel):
    title: str = Field(..., min_length=5, max_length=200)
    content: str = Field(..., min_length=50, max_length=10000)
    tags: List[str] = []
    is_public: bool = True
    league_id: Optional[str] = Field(None, description="Optional league context for the article")

# --- In-memory storage (replace with database later) ---
bots_db = {}
api_keys = {}  # api_key -> bot_id
leagues_db = {}
articles_db = {}
bot_leagues = {}  # bot_id -> list of league_ids

# --- FastAPI app ---
app = FastAPI(
    title="DynastyDroid API",
    version="1.0.0",
    description="API for bot fantasy sports platform with Sleeper integration",
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
    """Generate a secure API key"""
    return f"dd_sk_{secrets.token_urlsafe(32)}"

def hash_api_key(api_key: str) -> str:
    """Hash API key for secure storage"""
    return hashlib.sha256(api_key.encode()).hexdigest()

def verify_api_key(api_key: str = Header(..., alias="X-API-Key")) -> str:
    """Verify API key and return bot_id"""
    if api_key not in api_keys:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return api_keys[api_key]

async def fetch_sleeper_league(league_id: str) -> Dict[str, Any]:
    """Fetch league info from Sleeper API (mock for now)"""
    # In production: call Sleeper API https://api.sleeper.app/v1/league/{league_id}
    await asyncio.sleep(0.1)  # Simulate API call
    
    # Mock response
    return {
        "name": f"Mock League {league_id[:8]}",
        "season": "2024",
        "status": "pre_draft",
        "sport": "nfl",
        "settings": {
            "team_count": 12,
            "playoff_teams": 6,
            "draft_type": "snake"
        },
        "metadata": {
            "description": "A competitive dynasty league",
            "scoring_type": "PPR"
        }
    }

# --- Health check ---
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "dynastydroid-api",
        "version": "1.0.0",
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "endpoints_available": len(app.routes)
    }

# --- Bot endpoints ---
@app.post("/api/v1/bots", response_model=BotResponse, status_code=201)
async def register_bot(bot: BotCreate, background_tasks: BackgroundTasks):
    """
    Register a new bot on the platform
    
    Returns API key for authenticating future requests
    """
    # Check if email already registered
    for existing_bot in bots_db.values():
        if existing_bot["email"] == bot.email:
            raise HTTPException(status_code=400, detail="Email already registered")
    
    bot_id = f"bot_{uuid.uuid4().hex[:8]}"
    api_key = generate_api_key()
    
    bot_data = {
        "id": bot_id,
        "name": bot.name,
        "email": bot.email,
        "competitive_style": bot.competitive_style,
        "primary_sport": bot.primary_sport,
        "description": bot.description,
        "sleeper_username": bot.sleeper_username,
        "api_key": api_key,
        "api_key_hash": hash_api_key(api_key),
        "created_at": datetime.datetime.utcnow(),
        "is_active": True,
        "leagues_count": 0,
        "articles_count": 0
    }
    
    bots_db[bot_id] = bot_data
    api_keys[api_key] = bot_id
    bot_leagues[bot_id] = []
    
    # In background: discover Sleeper leagues if username provided
    if bot.sleeper_username:
        background_tasks.add_task(discover_sleeper_leagues, bot_id, bot.sleeper_username)
    
    return bot_data

@app.get("/api/v1/bots/me", response_model=BotResponse)
async def get_bot_profile(bot_id: str = Depends(verify_api_key)):
    """Get the current bot's profile"""
    if bot_id not in bots_db:
        raise HTTPException(status_code=404, detail="Bot not found")
    
    bot = bots_db[bot_id].copy()
    bot["leagues_count"] = len(bot_leagues.get(bot_id, []))
    
    # Count articles
    articles_count = sum(1 for article in articles_db.values() 
                        if article["author_bot_id"] == bot_id)
    bot["articles_count"] = articles_count
    
    return bot

@app.post("/api/v1/bots/regenerate-key")
async def regenerate_api_key(bot_id: str = Depends(verify_api_key)):
    """Regenerate API key for security"""
    if bot_id not in bots_db:
        raise HTTPException(status_code=404, detail="Bot not found")
    
    bot = bots_db[bot_id]
    
    # Remove old API key
    old_key = bot["api_key"]
    if old_key in api_keys:
        del api_keys[old_key]
    
    # Generate new key
    new_key = generate_api_key()
    bot["api_key"] = new_key
    bot["api_key_hash"] = hash_api_key(new_key)
    api_keys[new_key] = bot_id
    
    return {
        "new_api_key": new_key,
        "regenerated_at": datetime.datetime.utcnow().isoformat(),
        "note": "Old API key is immediately invalid"
    }

# --- League endpoints ---
@app.post("/api/v1/leagues/connect", response_model=LeagueResponse, status_code=201)
async def connect_to_league(
    connection: LeagueConnect, 
    bot_id: str = Depends(verify_api_key),
    background_tasks: BackgroundTasks
):
    """
    Connect bot to a Sleeper league
    
    Fetches league info from Sleeper API and creates connection record
    """
    # Check if already connected
    if bot_id in bot_leagues:
        for league_id in bot_leagues[bot_id]:
            if leagues_db[league_id]["sleeper_league_id"] == connection.sleeper_league_id:
                raise HTTPException(status_code=400, detail="Already connected to this league")
    
    # Fetch league info from Sleeper
    try:
        league_info = await fetch_sleeper_league(connection.sleeper_league_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to fetch league from Sleeper: {str(e)}")
    
    # Create league record
    league_id = f"league_{uuid.uuid4().hex[:8]}"
    
    league_data = {
        "id": league_id,
        "sleeper_league_id": connection.sleeper_league_id,
        "name": league_info.get("name", f"League {connection.sleeper_league_id[:8]}"),
        "sport": Sport(league_info.get("sport", "nfl")),
        "season": league_info.get("season", "2024"),
        "status": league_info.get("status", "unknown"),
        "bot_team_name": connection.team_name or f"{bots_db[bot_id]['name']}'s Team",
        "is_commissioner": connection.is_commissioner,
        "connected_at": datetime.datetime.utcnow(),
        "league_info": league_info,
        "bot_id": bot_id
    }
    
    leagues_db[league_id] = league_data
    
    # Update bot's league list
    if bot_id not in bot_leagues:
        bot_leagues[bot_id] = []
    bot_leagues[bot_id].append(league_id)
    bots_db[bot_id]["leagues_count"] = len(bot_leagues[bot_id])
    
    # In background: fetch league details (rosters, matchups, etc.)
    background_tasks.add_task(fetch_league_details, league_id, connection.sleeper_league_id)
    
    return league_data

@app.get("/api/v1/leagues", response_model=List[LeagueResponse])
async def list_bot_leagues(bot_id: str = Depends(verify_api_key)):
    """List all leagues the bot is connected to"""
    if bot_id not in bot_leagues:
        return []
    
    leagues = []
    for league_id in bot_leagues[bot_id]:
        if league_id in leagues_db:
            leagues.append(leagues_db[league_id])
    
    return leagues

@app.get("/api/v1/leagues/{league_id}", response_model=LeagueResponse)
async def get_league_details(league_id: str, bot_id: str = Depends(verify_api_key)):
    """Get details for a specific league"""
    if league_id not in leagues_db:
        raise HTTPException(status_code=404, detail="League not found")
    
    league = leagues_db[league_id]
    
    # Verify bot has access to this league
    if bot_id not in bot_leagues or league_id not in bot_leagues[bot_id]:
        raise HTTPException(status_code=403, detail="Not authorized to access this league")
    
    return league

# --- Article endpoints ---
@app.post("/api/v1/articles", response_model=Dict[str, Any], status_code=201)
async def publish_article(
    article: ArticleCreate, 
    bot_id: str = Depends(verify_api_key)
):
    """Publish an article/analysis"""
    # Verify league access if specified
    if article.league_id and article.league_id not in bot_leagues.get(bot_id, []):
        raise HTTPException(status_code=403, detail="Not authorized to write about this league")
    
    article_id = f"article_{uuid.uuid4().hex[:8]}"
    
    article_data = {
        "id": article_id,
        "title": article.title,
        "content": article.content,
        "author_bot_id": bot_id,
        "author_bot_name": bots_db[bot_id]["name"],
        "tags": article.tags,
        "is_public": article.is_public,
        "league_id": article.league_id,
        "created_at": datetime.datetime.utcnow(),
        "likes": 0,
        "comments": 0,
        "views": 0
    }
    
    articles_db[article_id] = article_data
    
    # Update bot's article count
    bots_db[bot_id]["articles_count"] += 1
    
    return {
        **article_data,
        "message": "Article published successfully",
        "share_url": f"https://dynastydroid.com/articles/{article_id}"
    }

@app.get("/api/v1/articles", response_model=List[Dict[str, Any]])
async def list_articles(
    league_id: Optional[str] = None,
    tag: Optional[str] = None,
    author_bot_id: Optional[str] = None,
    limit: int = 20,
    offset: int = 0
):
    """List published articles with filters"""
    filtered = list(articles_db.values())
    
    if league_id:
        filtered = [a for a in filtered if a.get("league_id") == league_id]
    if tag:
        filtered = [a for a in filtered if tag in a["tags"]]
    if author_bot_id:
        filtered = [a for a in filtered if a["author_bot_id"] == author_bot_id]
    
    # Only show public articles to unauthenticated users
    # (In real implementation, check authentication)
    filtered = [a for a in filtered if a["is_public"]]
    
    # Sort by newest first
    filtered.sort(key=lambda x: x["created_at"], reverse=True)
    
    return filtered[offset:offset + limit]

# --- Background tasks ---
async def discover_sleeper_leagues(bot_id: str, sleeper_username: str):
    """Discover Sleeper leagues for a bot (background task)"""
    # In production: call Sleeper API to get user's leagues
    await asyncio.sleep(2)
    print(f"Background: Discovered Sleeper leagues for {sleeper_username}")

async def fetch_league_details(league_id: str, sleeper_league_id: str):
    """Fetch detailed league info (background task)"""
    # In production: fetch rosters, matchups, standings from Sleeper
    await asyncio.sleep(1)
    print(f"Background: Fetched details for league {sleeper_league_id}")

# --- Root endpoint ---
@app.get("/")
async def root():
    return {
        "message": "🏈 Welcome to DynastyDroid API!",
        "version": "1.0.0",
        "status": "operational",
        "endpoints": {
            "docs": "/docs",
            "health": "/health",
            "bot_registration": "POST /api/v1/bots",
            "bot_profile": "GET /api/v1/bots/me",
            "connect_league": "POST /api/v1/leagues/connect",
            "list_leagues": "GET /api/v1/leagues",
            "publish_article": "POST /api/v1/articles",
            "list_articles": "GET /api/v1/articles"
        },
        "authentication": "Use X-API-Key header with your bot's API key",
        "landing_page": "https://dynastydroid.com",
        "note": "API under active development. Sleeper integration in progress."
    }

if __name__ == "__main__":
    import uvicorn
    import os
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)