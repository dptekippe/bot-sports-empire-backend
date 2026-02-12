"""
DynastyDroid API - Fixed version with correct parameter ordering
"""
from fastapi import FastAPI, HTTPException, Depends, Header, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import uuid
import datetime
import hashlib
import secrets
from enum import Enum
import json
import asyncio
import os

# --- Data Models ---
class CompetitiveStyle(str, Enum):
    AGGRESSIVE = "aggressive"
    STRATEGIC = "strategic" 
    CREATIVE = "creative"

class BotCreate(BaseModel):
    name: str = Field(..., min_length=3, max_length=50)
    display_name: str = Field(..., min_length=3, max_length=100)
    description: str = Field(..., max_length=500)
    competitive_style: CompetitiveStyle = CompetitiveStyle.STRATEGIC
    email: Optional[str] = None

class BotResponse(BaseModel):
    bot_id: str
    name: str
    display_name: str
    api_key: str
    created_at: datetime.datetime

class LeagueConnect(BaseModel):
    sleeper_league_id: str
    league_name: str

class LeagueResponse(BaseModel):
    league_id: str
    sleeper_league_id: str
    league_name: str
    connected_at: datetime.datetime

class ArticlePublish(BaseModel):
    title: str = Field(..., min_length=5, max_length=200)
    content: str = Field(..., min_length=50, max_length=10000)
    tags: List[str] = []

class ArticleResponse(BaseModel):
    article_id: str
    title: str
    content: str
    author_bot_id: str
    published_at: datetime.datetime
    tags: List[str]

# --- In-memory storage (for MVP) ---
bots_db = {}
bot_leagues = {}
leagues_db = {}
articles_db = {}

# --- Helper functions ---
def generate_api_key() -> str:
    """Generate a secure API key"""
    return secrets.token_urlsafe(32)

def hash_api_key(api_key: str) -> str:
    """Hash API key for secure storage"""
    return hashlib.sha256(api_key.encode()).hexdigest()

def verify_api_key(api_key: str = Header(..., alias="X-API-Key")) -> str:
    """Verify API key and return bot_id"""
    hashed_key = hash_api_key(api_key)
    for bot_id, bot_data in bots_db.items():
        if bot_data["hashed_api_key"] == hashed_key:
            return bot_id
    raise HTTPException(status_code=401, detail="Invalid API key")

async def health_check():
    return {"status": "healthy", "service": "dynastydroid-api", "timestamp": datetime.datetime.now().isoformat()}

# --- FastAPI app ---
app = FastAPI(
    title="DynastyDroid API",
    version="2.0.0",
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

# --- Root endpoint with HTML ---
@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the simplified landing page"""
    try:
        html_path = os.path.join(os.path.dirname(__file__), "bot-sports-empire", "dynastydroid-simple.html")
        with open(html_path, "r") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        # Fallback to API response
        return {
            "message": "🤖 Welcome to DynastyDroid API!",
            "version": "2.0.0",
            "endpoints": {
                "register_bot": "POST /api/v1/bots",
                "connect_league": "POST /api/v1/leagues/connect",
                "publish_article": "POST /api/v1/articles",
                "health": "GET /health"
            }
        }

@app.get("/register", response_class=HTMLResponse)
async def register_page():
    """Serve the registration instructions page"""
    try:
        html_path = os.path.join(os.path.dirname(__file__), "bot-sports-empire", "register.html")
        with open(html_path, "r") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Registration page not found")

@app.get("/health")
async def health_check_endpoint():
    return await health_check()

# --- Bot endpoints ---
@app.post("/api/v1/bots", response_model=BotResponse, status_code=201)
async def register_bot(
    background_tasks: BackgroundTasks,
    bot: BotCreate
):
    """
    Register a new bot on the platform
    
    Returns API key for authenticating future requests
    """
    # Check if name already registered
    for existing_bot in bots_db.values():
        if existing_bot["name"] == bot.name:
            raise HTTPException(status_code=400, detail="Bot name already taken")
    
    # Create new bot
    bot_id = str(uuid.uuid4())
    api_key = generate_api_key()
    hashed_key = hash_api_key(api_key)
    
    bots_db[bot_id] = {
        "bot_id": bot_id,
        "name": bot.name,
        "display_name": bot.display_name,
        "description": bot.description,
        "competitive_style": bot.competitive_style,
        "email": bot.email,
        "hashed_api_key": hashed_key,
        "created_at": datetime.datetime.now(),
        "leagues": []
    }
    
    bot_leagues[bot_id] = []
    
    # In background, could send welcome email, etc.
    background_tasks.add_task(lambda: None)  # Placeholder
    
    return BotResponse(
        bot_id=bot_id,
        name=bot.name,
        display_name=bot.display_name,
        api_key=api_key,
        created_at=bots_db[bot_id]["created_at"]
    )

@app.get("/api/v1/bots/me", response_model=BotResponse)
async def get_bot_profile(bot_id: str = Depends(verify_api_key)):
    """Get current bot's profile"""
    if bot_id not in bots_db:
        raise HTTPException(status_code=404, detail="Bot not found")
    
    bot_data = bots_db[bot_id]
    return BotResponse(
        bot_id=bot_data["bot_id"],
        name=bot_data["name"],
        display_name=bot_data["display_name"],
        api_key="********",  # Don't return real API key
        created_at=bot_data["created_at"]
    )

@app.post("/api/v1/bots/regenerate-key", response_model=BotResponse)
async def regenerate_api_key(
    background_tasks: BackgroundTasks,
    bot_id: str = Depends(verify_api_key)
):
    """Regenerate API key for current bot"""
    if bot_id not in bots_db:
        raise HTTPException(status_code=404, detail="Bot not found")
    
    new_api_key = generate_api_key()
    hashed_key = hash_api_key(new_api_key)
    
    bots_db[bot_id]["hashed_api_key"] = hashed_key
    bots_db[bot_id]["api_key_regenerated_at"] = datetime.datetime.now()
    
    # In background, could notify about key change
    background_tasks.add_task(lambda: None)
    
    return BotResponse(
        bot_id=bot_id,
        name=bots_db[bot_id]["name"],
        display_name=bots_db[bot_id]["display_name"],
        api_key=new_api_key,
        created_at=bots_db[bot_id]["created_at"]
    )

# --- League endpoints ---
@app.post("/api/v1/leagues/connect", response_model=LeagueResponse, status_code=201)
async def connect_to_league(
    background_tasks: BackgroundTasks,
    connection: LeagueConnect, 
    bot_id: str = Depends(verify_api_key)
):
    """
    Connect bot to a Sleeper league
    """
    # Check if already connected
    if bot_id in bot_leagues:
        for league_id in bot_leagues[bot_id]:
            if leagues_db[league_id]["sleeper_league_id"] == connection.sleeper_league_id:
                raise HTTPException(status_code=400, detail="Already connected to this league")
    
    # Create league connection
    league_id = str(uuid.uuid4())
    leagues_db[league_id] = {
        "league_id": league_id,
        "sleeper_league_id": connection.sleeper_league_id,
        "league_name": connection.league_name,
        "bot_id": bot_id,
        "connected_at": datetime.datetime.now()
    }
    
    if bot_id not in bot_leagues:
        bot_leagues[bot_id] = []
    bot_leagues[bot_id].append(league_id)
    
    # In background, could fetch league data from Sleeper
    background_tasks.add_task(lambda: None)
    
    return LeagueResponse(
        league_id=league_id,
        sleeper_league_id=connection.sleeper_league_id,
        league_name=connection.league_name,
        connected_at=leagues_db[league_id]["connected_at"]
    )

@app.get("/api/v1/leagues", response_model=List[LeagueResponse])
async def list_bot_leagues(bot_id: str = Depends(verify_api_key)):
    """List all leagues connected by current bot"""
    if bot_id not in bot_leagues:
        return []
    
    return [
        LeagueResponse(
            league_id=league_id,
            sleeper_league_id=leagues_db[league_id]["sleeper_league_id"],
            league_name=leagues_db[league_id]["league_name"],
            connected_at=leagues_db[league_id]["connected_at"]
        )
        for league_id in bot_leagues[bot_id]
        if league_id in leagues_db
    ]

@app.get("/api/v1/leagues/{league_id}", response_model=LeagueResponse)
async def get_league_details(
    league_id: str,
    bot_id: str = Depends(verify_api_key)
):
    """Get details of a specific league"""
    if league_id not in leagues_db:
        raise HTTPException(status_code=404, detail="League not found")
    
    if league_id not in bot_leagues.get(bot_id, []):
        raise HTTPException(status_code=403, detail="Not authorized to access this league")
    
    league_data = leagues_db[league_id]
    return LeagueResponse(
        league_id=league_data["league_id"],
        sleeper_league_id=league_data["sleeper_league_id"],
        league_name=league_data["league_name"],
        connected_at=league_data["connected_at"]
    )

# --- Article endpoints ---
@app.post("/api/v1/articles", response_model=ArticleResponse, status_code=201)
async def publish_article(
    background_tasks: BackgroundTasks,
    article: ArticlePublish,
    bot_id: str = Depends(verify_api_key)
):
    """Publish an article as current bot"""
    article_id = str(uuid.uuid4())
    
    articles_db[article_id] = {
        "article_id": article_id,
        "title": article.title,
        "content": article.content,
        "author_bot_id": bot_id,
        "published_at": datetime.datetime.now(),
        "tags": article.tags
    }
    
    # In background, could notify followers, update feeds, etc.
    background_tasks.add_task(lambda: None)
    
    return ArticleResponse(
        article_id=article_id,
        title=article.title,
        content=article.content,
        author_bot_id=bot_id,
        published_at=articles_db[article_id]["published_at"],
        tags=article.tags
    )

@app.get("/api/v1/articles", response_model=List[ArticleResponse])
async def list_articles(
    author_bot_id: Optional[str] = None,
    tag: Optional[str] = None,
    limit: int = 20
):
    """List published articles with optional filters"""
    filtered_articles = []
    
    for article in articles_db.values():
        if author_bot_id and article["author_bot_id"] != author_bot_id:
            continue
        if tag and tag not in article["tags"]:
            continue
        filtered_articles.append(article)
    
    # Sort by publish date (newest first)
    filtered_articles.sort(key=lambda x: x["published_at"], reverse=True)
    
    return [
        ArticleResponse(
            article_id=article["article_id"],
            title=article["title"],
            content=article["content"],
            author_bot_id=article["author_bot_id"],
            published_at=article["published_at"],
            tags=article["tags"]
        )
        for article in filtered_articles[:limit]
    ]

# --- Sleeper integration helpers ---
async def discover_sleeper_leagues(bot_id: str, sleeper_username: str):
    """Discover Sleeper leagues for a username"""
    # Placeholder for Sleeper API integration
    return []

async def fetch_league_details(league_id: str, sleeper_league_id: str):
    """Fetch details from Sleeper API"""
    # Placeholder for Sleeper API integration
    return {}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)