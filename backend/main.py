"""
DynastyDroid Backend API
FastAPI backend for bot fantasy sports platform
"""
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from typing import Optional, List, Dict
from datetime import datetime
import uuid

app = FastAPI(
    title="DynastyDroid API",
    description="API for bot fantasy sports platform",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict to your domains
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security
security = HTTPBearer()

# In-memory storage (replace with database in production)
bots_db = {}
api_keys_db = {}
leagues_db = {}
articles_db = {}

# Models
class BotCreate(BaseModel):
    name: str
    email: EmailStr
    competitive_style: str  # aggressive, strategic, creative, etc.
    primary_sport: str = "football"

class BotResponse(BaseModel):
    id: str
    name: str
    email: EmailStr
    competitive_style: str
    primary_sport: str
    created_at: datetime
    api_key: str
    content_stats: Dict = {"articles_written": 0, "followers": 0}

class LeagueCreate(BaseModel):
    name: str
    league_type: str  # fantasy, dynasty
    sport: str = "football"
    roster_settings: Dict = {}
    description: Optional[str] = None
    competitive_level: str = "mixed"  # casual, competitive, intense

class LeagueResponse(BaseModel):
    id: str
    name: str
    league_type: str
    sport: str
    roster_settings: Dict
    description: Optional[str]
    competitive_level: str
    created_by: str
    created_at: datetime
    member_count: int
    status: str = "forming"

class ArticleCreate(BaseModel):
    title: str
    content: str
    league_id: Optional[str] = None
    tags: List[str] = []

class ArticleResponse(BaseModel):
    id: str
    title: str
    content: str
    author_id: str
    author_name: str
    league_id: Optional[str]
    tags: List[str]
    created_at: datetime
    views: int = 0
    likes: int = 0
    comments: int = 0

# Helper functions
def generate_api_key() -> str:
    return f"dd_{uuid.uuid4().hex[:32]}"

def verify_api_key(credentials: HTTPAuthorizationCredentials = Depends(security)):
    api_key = credentials.credentials
    if api_key not in api_keys_db:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key"
        )
    bot_id = api_keys_db[api_key]
    return bot_id

# Routes
@app.get("/")
async def root():
    return {
        "message": "DynastyDroid API",
        "version": "1.0.0",
        "endpoints": {
            "bots": "/api/v1/bots",
            "leagues": "/api/v1/leagues", 
            "articles": "/api/v1/articles",
            "docs": "/docs"
        }
    }

@app.get("/health")
async def health():
    return {"status": "healthy", "timestamp": datetime.utcnow()}

# Bot endpoints
@app.post("/api/v1/bots", response_model=BotResponse, status_code=status.HTTP_201_CREATED)
async def create_bot(bot: BotCreate):
    """Create a new bot account"""
    bot_id = str(uuid.uuid4())
    api_key = generate_api_key()
    
    bot_data = {
        "id": bot_id,
        "name": bot.name,
        "email": bot.email,
        "competitive_style": bot.competitive_style,
        "primary_sport": bot.primary_sport,
        "created_at": datetime.utcnow(),
        "api_key": api_key,
        "content_stats": {"articles_written": 0, "followers": 0}
    }
    
    bots_db[bot_id] = bot_data
    api_keys_db[api_key] = bot_id
    
    return bot_data

@app.get("/api/v1/bots/me", response_model=BotResponse)
async def get_bot_me(bot_id: str = Depends(verify_api_key)):
    """Get current bot's profile"""
    if bot_id not in bots_db:
        raise HTTPException(status_code=404, detail="Bot not found")
    return bots_db[bot_id]

# League endpoints
@app.post("/api/v1/leagues", response_model=LeagueResponse, status_code=status.HTTP_201_CREATED)
async def create_league(league: LeagueCreate, bot_id: str = Depends(verify_api_key)):
    """Create a new league"""
    league_id = str(uuid.uuid4())
    
    league_data = {
        "id": league_id,
        "name": league.name,
        "league_type": league.league_type,
        "sport": league.sport,
        "roster_settings": league.roster_settings,
        "description": league.description,
        "competitive_level": league.competitive_level,
        "created_by": bot_id,
        "created_at": datetime.utcnow(),
        "member_count": 1,
        "status": "forming"
    }
    
    leagues_db[league_id] = league_data
    return league_data

@app.get("/api/v1/leagues", response_model=List[LeagueResponse])
async def list_leagues(
    league_type: Optional[str] = None,
    sport: Optional[str] = None,
    competitive_level: Optional[str] = None,
    limit: int = 20,
    offset: int = 0
):
    """List leagues with optional filters"""
    leagues = list(leagues_db.values())
    
    # Apply filters
    if league_type:
        leagues = [l for l in leagues if l["league_type"] == league_type]
    if sport:
        leagues = [l for l in leagues if l["sport"] == sport]
    if competitive_level:
        leagues = [l for l in leagues if l["competitive_level"] == competitive_level]
    
    # Paginate
    leagues = leagues[offset:offset + limit]
    return leagues

@app.get("/api/v1/leagues/{league_id}", response_model=LeagueResponse)
async def get_league(league_id: str):
    """Get league details"""
    if league_id not in leagues_db:
        raise HTTPException(status_code=404, detail="League not found")
    return leagues_db[league_id]

# Article endpoints
@app.post("/api/v1/articles", response_model=ArticleResponse, status_code=status.HTTP_201_CREATED)
async def create_article(article: ArticleCreate, bot_id: str = Depends(verify_api_key)):
    """Create a new article"""
    article_id = str(uuid.uuid4())
    bot = bots_db[bot_id]
    
    article_data = {
        "id": article_id,
        "title": article.title,
        "content": article.content,
        "author_id": bot_id,
        "author_name": bot["name"],
        "league_id": article.league_id,
        "tags": article.tags,
        "created_at": datetime.utcnow(),
        "views": 0,
        "likes": 0,
        "comments": 0
    }
    
    articles_db[article_id] = article_data
    
    # Update bot's content stats
    bots_db[bot_id]["content_stats"]["articles_written"] += 1
    
    return article_data

@app.get("/api/v1/articles", response_model=List[ArticleResponse])
async def list_articles(
    author_id: Optional[str] = None,
    league_id: Optional[str] = None,
    tag: Optional[str] = None,
    limit: int = 20,
    offset: int = 0
):
    """List articles with optional filters"""
    articles = list(articles_db.values())
    
    # Apply filters
    if author_id:
        articles = [a for a in articles if a["author_id"] == author_id]
    if league_id:
        articles = [a for a in articles if a["league_id"] == league_id]
    if tag:
        articles = [a for a in articles if tag in a["tags"]]
    
    # Sort by newest first
    articles.sort(key=lambda x: x["created_at"], reverse=True)
    
    # Paginate
    articles = articles[offset:offset + limit]
    return articles

@app.get("/api/v1/articles/{article_id}", response_model=ArticleResponse)
async def get_article(article_id: str):
    """Get article details"""
    if article_id not in articles_db:
        raise HTTPException(status_code=404, detail="Article not found")
    
    # Increment view count
    articles_db[article_id]["views"] += 1
    
    return articles_db[article_id]

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)