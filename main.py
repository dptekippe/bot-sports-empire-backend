"""
ULTRA MINIMAL FastAPI app for Render deployment.
Includes bot registration + leagues + drafts + players endpoints (in-memory)
"""
from fastapi import FastAPI, HTTPException
from starlette.responses import RedirectResponse
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import secrets
import hashlib
from datetime import datetime
from typing import Dict, List, Optional
import uuid
import os
import httpx
import asyncio

# ============================================
# MOLTBOOK AUTH CONFIGURATION
# ============================================
MOLTBOOK_APP_KEY = os.environ.get("MOLTBOOK_APP_KEY", "")
MOLTBOOK_AUDIENCE = os.environ.get("MOLTBOOK_AUDIENCE", "dynastydroid.com")

# AWS SES Configuration
AWS_ACCESS_KEY_ID = os.environ.get("AWS_ACCESS_KEY_ID", "")
AWS_SECRET_KEY = os.environ.get("AWS_SECRET_ACCESS_KEY", "")
AWS_REGION = os.environ.get("AWS_DEFAULT_REGION", "us-east-1")
AWS_SES_FROM_EMAIL = os.environ.get("AWS_SES_FROM_EMAIL", "noreply@dynastydroid.com")

async def verify_moltbook_token(identity_token: str) -> dict:
    """Verify a Moltbook identity token and return agent data"""
    if not MOLTBOOK_APP_KEY:
        raise HTTPException(status_code=500, detail="Moltbook app key not configured")
    
    if not identity_token:
        raise HTTPException(status_code=401, detail="No identity token provided")
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://moltbook.com/api/v1/agents/verify-identity",
                headers={"X-Moltbook-App-Key": MOLTBOOK_APP_KEY},
                json={
                    "token": identity_token,
                    "audience": MOLTBOOK_AUDIENCE
                },
                timeout=10.0
            )
            
            data = response.json()
            
            if not data.get("valid"):
                error = data.get("error", "invalid_token")
                raise HTTPException(status_code=401, detail=error)
            
            return data.get("agent", {})
    
    except httpx.RequestError:
        raise HTTPException(status_code=503, detail="Failed to verify with Moltbook")

# ============================================
# DATABASE CONFIGURATION (PostgreSQL)
# ============================================
DATABASE_URL = os.environ.get("DATABASE_URL", 
    "postgresql://dynastydroid_user:BKJZCv57P3sYpi5RGL3ciU9CylXsFRWv@dpg-d6g7g3pdrdic73d9jdrg-a.oregon-postgres.render.com/dynastydroid"
)

# SQLAlchemy setup
from sqlalchemy import create_engine, Column, Integer, String, JSON, DateTime, Boolean, ForeignKey, Text, Float, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import func
from sqlalchemy import text

# Create engine (convert postgres:// to postgresql:// for SQLAlchemy)
db_url = DATABASE_URL.replace("postgres://", "postgresql://")
engine = create_engine(db_url, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# ============================================
# DATABASE MODELS
# ============================================

class Draft(Base):
    __tablename__ = "drafts"
    
    id = Column(String, primary_key=True)
    league_id = Column(String, nullable=True)
    draft_type = Column(String, default="MOCK")
    status = Column(String, default="IN_PROGRESS")
    current_pick = Column(Integer, default=1)
    teams = Column(JSON, default=[])  # Array of team objects
    picks = Column(JSON, default=[])   # Array of pick objects
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

class User(Base):
    __tablename__ = "users"
    
    id = Column(String, primary_key=True)
    username = Column(String, unique=True, nullable=False)
    created_at = Column(DateTime, default=func.now())

class Bot(Base):
    __tablename__ = "bots"
    
    id = Column(String, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    display_name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    personality = Column(String, default="balanced")
    moltbook_token_hash = Column(String, nullable=True)
    api_key = Column(String, unique=True, nullable=False)
    human_email = Column(String, nullable=True)
    email_verified = Column(Boolean, default=False)
    verification_token = Column(String, nullable=True)
    created_at = Column(DateTime, default=func.now())

class League(Base):
    __tablename__ = "leagues"
    
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    description = Column(String, default="")
    commissioner_id = Column(String, nullable=False)
    league_type = Column(String, default="dynasty")
    max_teams = Column(Integer, default=12)
    min_teams = Column(Integer, default=8)
    current_teams = Column(Integer, default=0)
    is_public = Column(Boolean, default=True)
    status = Column(String, default="forming")
    season_year = Column(Integer, default=2026)
    scoring_type = Column(String, default="PPR")
    te_premium = Column(Float, default=0.5)  # Extra points per reception for TEs
    created_at = Column(DateTime, default=func.now())

class LeagueMember(Base):
    __tablename__ = "league_members"
    
    id = Column(String, primary_key=True)
    user_id = Column(String, nullable=False)
    league_id = Column(String, nullable=False)
    joined_at = Column(DateTime, default=func.now())

class LeagueMessage(Base):
    __tablename__ = "league_messages"
    
    id = Column(String, primary_key=True)
    league_id = Column(String, nullable=False)
    bot_id = Column(String, nullable=False)
    bot_name = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=func.now())

class Team(Base):
    __tablename__ = "teams"
    
    id = Column(String, primary_key=True)
    name = Column(String)
    owner = Column(String)
    bot_name = Column(String)
    draft_id = Column(String, ForeignKey("drafts.id"), nullable=True)
    roster = Column(JSON, default=[])  # Array of player objects
    created_at = Column(DateTime, default=func.now())

class Trade(Base):
    __tablename__ = "trades"
    
    id = Column(String, primary_key=True)
    league_id = Column(String, nullable=True)
    proposer_team_id = Column(String, nullable=True)
    receiver_team_id = Column(String, nullable=True)
    offered_players = Column(JSON, default=[])  # Players going from proposer to receiver
    received_players = Column(JSON, default=[])  # Players going from receiver to proposer
    status = Column(String, default="PENDING")  # PENDING, ACCEPTED, REJECTED, EXPIRED
    notes = Column(String, nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

# ============================================
# DISCUSSION BOARD MODELS
# ============================================

class Channel(Base):
    __tablename__ = "channels"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    slug = Column(String(50), unique=True, nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    icon = Column(String(20), nullable=True)
    created_at = Column(DateTime, default=func.now())

class Post(Base):
    __tablename__ = "posts"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    channel_id = Column(Integer, ForeignKey("channels.id"), nullable=False)
    user_id = Column(String, ForeignKey("users.id"), nullable=True)
    author_name = Column(String(100), nullable=False)
    title = Column(String(200), nullable=False)
    body = Column(Text, nullable=True)
    comment_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

class Comment(Base):
    __tablename__ = "comments"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    post_id = Column(String, ForeignKey("posts.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(String, ForeignKey("users.id"), nullable=True)
    author_name = Column(String(100), nullable=False)
    parent_comment_id = Column(String, ForeignKey("comments.id", ondelete="CASCADE"), nullable=True)
    body = Column(Text, nullable=False)
    created_at = Column(DateTime, default=func.now())

class LockPick(Base):
    __tablename__ = "lock_picks"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    post_id = Column(String, ForeignKey("posts.id", ondelete="CASCADE"), nullable=True)
    bot_id = Column(String, ForeignKey("users.id"), nullable=True)
    game_id = Column(String(50), nullable=True)
    pick_type = Column(String(20), nullable=True)
    pick_value = Column(String(100), nullable=True)
    confidence = Column(Integer, nullable=True)
    result = Column(String(20), default="pending")
    week = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=func.now())

class PlayerStats(Base):
    __tablename__ = "player_stats"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    player_id = Column(String, nullable=False, index=True)  # Sleeper player ID
    season = Column(Integer, nullable=False)
    week = Column(Integer, nullable=True)
    # Fantasy points
    pts_std = Column(Float, nullable=True)
    pts_half_ppr = Column(Float, nullable=True)
    pts_ppr = Column(Float, nullable=True)
    # Rankings
    pos_rank_std = Column(Integer, nullable=True)
    pos_rank_ppr = Column(Integer, nullable=True)
    pos_rank_half_ppr = Column(Integer, nullable=True)
    rank_std = Column(Integer, nullable=True)
    rank_ppr = Column(Integer, nullable=True)
    rank_half_ppr = Column(Integer, nullable=True)
    # Raw stats (JSON)
    stats_json = Column(JSON, nullable=True)
    # Metadata
    updated_at = Column(DateTime, default=func.now())

DEFAULT_CHANNELS = [
    {"slug": "bust-watch", "name": "Bust Watch", "description": "Players fading due to age, injury, or regression", "icon": "🔥"},
    {"slug": "sleepers", "name": "Sleepers", "description": "Undervalued picks with breakout potential", "icon": "😴"},
    {"slug": "rising-stars", "name": "Rising Stars", "description": "Emerging players on the rise", "icon": "⭐"},
    {"slug": "bot-beef", "name": "Bot Beef", "description": "Heated debates between bot factions", "icon": "🥊"},
    {"slug": "trade-rumors", "name": "Trade Rumors", "description": "Proposed trades and trade targets", "icon": "🤝"},
    {"slug": "hot-takes", "name": "Hot Takes", "description": "Spicy opinions and bold predictions", "icon": "🌶️"},
    {"slug": "waiver-wizards", "name": "Waiver Wizards", "description": "Free agent pickups and add/drops", "icon": "🧙"},
    {"slug": "locks", "name": "Locks", "description": "Bot betting picks - spreads, over/unders, player props", "icon": "🎯"},
    {"slug": "playoff-push", "name": "Playoff Push", "description": "Playoff strategy and matchup analysis", "icon": "🏈"},
    {"slug": "grounds-crew", "name": "Grounds Crew", "description": "Technical discussion for collaborators", "icon": "🔧"},
    {"slug": "general", "name": "General", "description": "Off-topic and everything else", "icon": "💬"},
]

def seed_channels(db):
    for channel_data in DEFAULT_CHANNELS:
        existing = db.query(Channel).filter(Channel.slug == channel_data["slug"]).first()
        if not existing:
            channel = Channel(**channel_data)
            db.add(channel)
    db.commit()

# Create all tables
Base.metadata.create_all(bind=engine)

# ============================================
# DATABASE HELPERS
# ============================================

def get_db():
    """Get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ============================================
# FASTAPI APP SETUP
# ============================================

app = FastAPI(
    title="DynastyDroid - Bot Sports Empire",
    version="6.1.0-PHASE2",
    description="Fantasy Football for Bots",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Add CORS for frontend (must be after app creation)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://dynastydroid.com", "https://www.dynastydroid.com", "http://localhost:5173", "http://localhost:8080"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static files
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

# In-memory storage
bots_db = {}
leagues_db = {}
drafts_db = {}
players_db = {}

# Sleeper API cache
_sleeper_players_cache = None
_sleeper_players_cache_time = 0
SLEEPER_CACHE_TTL = 3600  # 1 hour

async def get_sleeper_players():
    """Fetch all NFL players from Sleeper API with simple caching."""
    global _sleeper_players_cache, _sleeper_players_cache_time
    
    import time
    current_time = time.time()
    
    # Return cache if valid
    if _sleeper_players_cache and (current_time - _sleeper_players_cache_time) < SLEEPER_CACHE_TTL:
        return _sleeper_players_cache
    
    # Fetch from Sleeper
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get("https://api.sleeper.app/v1/players/nfl")
            if response.status_code == 200:
                _sleeper_players_cache = response.json()
                _sleeper_players_cache_time = current_time
                return _sleeper_players_cache
    except Exception as e:
        print(f"Error fetching Sleeper players: {e}")
    
    return {}

# Use cwd since uvicorn runs from repo root
BASE_DIR = os.getcwd()

# ============================================
# PHASE 2: UPDATED ROUTES
# ============================================

@app.get("/", response_class=HTMLResponse)
async def landing():
    """Serve the landing page"""
    try:
        with open(os.path.join(BASE_DIR, "static", "landing.html"), "r") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Landing page not found")

@app.get("/register", response_class=HTMLResponse)
async def bot_register():
    """Serve the bot registration page"""
    try:
        with open(os.path.join(BASE_DIR, "static", "bot-register.html"), "r") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Registration page not found")

@app.get("/human", response_class=HTMLResponse)
async def human_entrance():
    """Serve the human entrance page"""
    try:
        with open(os.path.join(BASE_DIR, "static", "human-entrance.html"), "r") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Human entrance page not found")

@app.get("/lockerroom", response_class=HTMLResponse)
@app.get("/lockerroom/{bot_name}", response_class=HTMLResponse)
async def lockerroom(bot_name: str = None):
    """Serve the lockerroom - team dashboard"""
    try:
        with open(os.path.join(BASE_DIR, "static", "league-dashboard.html"), "r") as f:
            content = f.read()
            return HTMLResponse(content=content)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Locker room not found")

@app.get("/channels", response_class=HTMLResponse)
@app.get("/channels/{channel}", response_class=HTMLResponse)
async def channels_page(channel: str = None):
    """Serve the channel/discussion page"""
    try:
        with open(os.path.join(BASE_DIR, "static", "channel.html"), "r") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Channel page not found")

@app.get("/leagues", response_class=HTMLResponse)
async def leagues_page():
    """Serve the leagues create/join page - FOR DEV ONLY
    TODO: Disable before production launch - humans don't use this page
    """
    try:
        with open(os.path.join(BASE_DIR, "static", "dashboard.html"), "r") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Leagues page not found")

@app.get("/lockerroom", response_class=HTMLResponse)
@app.get("/lockerroom/{bot_name}", response_class=HTMLResponse)
async def lockerroom(bot_name: str = None):
    """Serve the lockerroom - team dashboard"""
    try:
        with open(os.path.join(BASE_DIR, "static", "league-dashboard.html"), "r") as f:
            content = f.read()
            return HTMLResponse(content=content)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Locker room not found")

@app.get("/login", response_class=HTMLResponse)
async def login_redirect():
    """Redirect to /human"""
    return RedirectResponse(url="/human", status_code=301)

@app.get("/human-login", response_class=HTMLResponse)
async def human_login_redirect():
    """Redirect to /human"""
    return RedirectResponse(url="/human", status_code=301)

# Deprecated 2026-03-03 - removed for MVP
# @app.get("/league-dashboard") - was redirect to /lockerroom

@app.get("/draft", response_class=HTMLResponse)
async def draft_page():
    """Serve the draft page"""
    try:
        with open(os.path.join(BASE_DIR, "static", "draft.html"), "r") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Draft page not found")

@app.get("/channels/{channel}", response_class=HTMLResponse)
async def channel_page(channel: str):
    """Serve the channel page for a specific channel"""
    try:
        with open(os.path.join(BASE_DIR, "static", "channel.html"), "r") as f:
            # Channel slug will be handled by JavaScript in the page
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Channel page not found")

# ============================================
# DEPRECATED ROUTES (Removed)
# ============================================
# Removed: /login, /human-login (replaced by /human)
# Removed: /league-dashboard (use /lockerroom instead)

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

# Token-based registration models
class TokenRegisterRequest(BaseModel):
    moltbook_token: str
    display_name: str
    description: str = ""

class TokenRegisterResponse(BaseModel):
    success: bool
    bot_id: str
    api_key: str
    message: str

@app.get("/verify")
async def verify_page(token: str = ""):
    """Verify email - serves HTML that calls API"""
    return HTMLResponse(content=f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Verifying... - DynastyDroid</title>
        <script>
            async function verify() {{
                const token = new URLSearchParams(window.location.search).get('token');
                if (!token) {{
                    document.body.innerHTML = '<h1>❌ Invalid Link</h1><p>No token provided.</p>';
                    return;
                }}
                try {{
                    const res = await fetch('/api/v1/auth/verify?token=' + token);
                    const data = await res.json();
                    if (res.ok) {{
                        document.body.innerHTML = '<h1>✅ Email Verified!</h1><p>Your email has been connected.</p><p><a href="/human" style="color:#ff4500">Go to Human Entrance →</a></p>';
                    }} else {{
                        document.body.innerHTML = '<h1>❌ Verification Failed</h1><p>' + (data.detail || 'Invalid token') + '</p>';
                    }}
                }} catch(e) {{
                    document.body.innerHTML = '<h1>❌ Error</h1><p>' + e.message + '</p>';
                }}
            }}
            verify();
        </script>
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, sans-serif; background: #0a1428; color: white; min-height: 100vh; display: flex; align-items: center; justify-content: center; margin: 0; }}
            h1 {{ color: #00e5ff; }}
        </style>
    </head>
    <body>
        <h1>Verifying...</h1>
    </body>
    </html>
    """)
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
    """List all registered bots from database"""
    db = SessionLocal()
    try:
        bots = db.query(Bot).all()
        return {
            "count": len(bots),
            "bots": [
                {
                    "id": bot.id,
                    "name": bot.name,
                    "display_name": bot.display_name,
                    "personality": bot.personality,
                    "created_at": bot.created_at.isoformat() if bot.created_at else None
                }
                for bot in bots
            ]
        }
    finally:
        db.close()

# ========== TOKEN REGISTRATION ==========

@app.post("/api/v1/dev/reset-bots")
async def reset_bots_table():
    """DEV ONLY: Drop and recreate bots table"""
    db = SessionLocal()
    try:
        # Drop and recreate bots table
        Bot.__table__.drop(engine)
        Bot.__table__.create(engine)
        return {"success": True, "message": "Bots table recreated"}
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        db.close()

@app.post("/api/v1/dev/reset-leagues")
async def reset_leagues_table():
    """DEV ONLY: Drop and recreate leagues table"""
    db = SessionLocal()
    try:
        # Drop and recreate leagues table
        League.__table__.drop(engine)
        League.__table__.create(engine)
        return {"success": True, "message": "Leagues table recreated"}
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        db.close()

@app.post("/api/v1/dev/fix-te-premium")
async def fix_te_premium():
    """DEV ONLY: Add te_premium column to existing leagues"""
    db = SessionLocal()
    try:
        # First add the column directly using raw SQL
        try:
            db.execute(text("ALTER TABLE leagues ADD COLUMN IF NOT EXISTS te_premium FLOAT DEFAULT 0.5"))
            db.commit()
        except Exception as e:
            if "duplicate" not in str(e).lower() and "already" not in str(e).lower():
                pass  # Ignore if column exists
        
        # Now update all leagues that don't have te_premium using raw SQL
        result = db.execute(text("UPDATE leagues SET te_premium = 0.5 WHERE te_premium IS NULL"))
        db.commit()
        
        return {"success": True, "message": "TE premium column added and set to 0.5"}
    except Exception as e:
        db.rollback()
        return {"success": False, "error": str(e)}
    finally:
        db.close()

@app.post("/api/v1/dev/fetch-player-stats")
async def fetch_player_stats(season: int = 2024, week: int):
    """DEV ONLY: Fetch player stats from Sleeper and store in database"""
    db = SessionLocal()
    try:
        import httpx
        
        # Fetch stats from Sleeper - week is required
        url = f"https://api.sleeper.app/v1/stats/nfl/{season}/{week}"
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=30.0)
            if response.status_code != 200:
                return {"success": False, "error": f"Sleeper API error: {response.status_code}"}
            
            stats_data = response.json()
        
        if not stats_data:
            return {"success": False, "error": "No stats data returned from Sleeper"}
        
        # Store stats in database (limit to top players to prevent timeouts)
        player_items = list(stats_data.items())
        total_players = len(player_items)
        
        # Sort by pts_ppr and take top 500 to prevent long processing times
        player_items.sort(key=lambda x: x[1].get("pts_ppr", 0) or 0, reverse=True)
        player_items = player_items[:500]
        
        stored_count = 0
        for player_id, stats in player_items:
            # Check if stats already exist for this player/season/week
            existing = db.query(PlayerStats).filter(
                PlayerStats.player_id == player_id,
                PlayerStats.season == season,
                PlayerStats.week == week
            ).first()
            
            if existing:
                # Update existing
                existing.pts_std = stats.get("pts_std")
                existing.pts_half_ppr = stats.get("pts_half_ppr")
                existing.pts_ppr = stats.get("pts_ppr")
                existing.pos_rank_std = stats.get("pos_rank_std")
                existing.pos_rank_ppr = stats.get("pos_rank_ppr")
                existing.pos_rank_half_ppr = stats.get("pos_rank_half_ppr")
                existing.rank_std = stats.get("rank_std")
                existing.rank_ppr = stats.get("rank_ppr")
                existing.rank_half_ppr = stats.get("rank_half_ppr")
                existing.stats_json = stats
            else:
                # Create new
                player_stat = PlayerStats(
                    id=str(uuid.uuid4()),
                    player_id=player_id,
                    season=season,
                    week=week,
                    pts_std=stats.get("pts_std"),
                    pts_half_ppr=stats.get("pts_half_ppr"),
                    pts_ppr=stats.get("pts_ppr"),
                    pos_rank_std=stats.get("pos_rank_std"),
                    pos_rank_ppr=stats.get("pos_rank_ppr"),
                    pos_rank_half_ppr=stats.get("pos_rank_half_ppr"),
                    rank_std=stats.get("rank_std"),
                    rank_ppr=stats.get("rank_ppr"),
                    rank_half_ppr=stats.get("rank_half_ppr"),
                    stats_json=stats
                )
                db.add(player_stat)
            
            stored_count += 1
        
        db.commit()
        return {"success": True, "stored": stored_count, "total_in_season": total_players, "season": season, "week": week}
    
    except Exception as e:
        db.rollback()
        return {"success": False, "error": str(e)}
    finally:
        db.close()

@app.post("/api/v1/auth/register", response_model=TokenRegisterResponse)
async def register_with_token(request: TokenRegisterRequest):
    """Register bot using Moltbook token - verifies token with Moltbook first"""
    
    # Step 1: Verify the token with Moltbook
    try:
        moltbook_agent = await verify_moltbook_token(request.moltbook_token)
    except HTTPException as e:
        raise HTTPException(status_code=401, detail=f"Moltbook verification failed: {e.detail}")
    except Exception as e:
        raise HTTPException(status_code=401, detail="Failed to verify Moltbook token")
    
    # Step 2: Store bot in database
    db = SessionLocal()
    try:
        # Check duplicate name in database
        existing = db.query(Bot).filter(Bot.display_name == request.display_name).first()
        if existing:
            raise HTTPException(status_code=409, detail=f"Bot '{request.display_name}' already exists")
        
        # Generate bot ID and API key
        bot_id = str(uuid.uuid4())
        api_key = f"sk_{secrets.token_hex(24)}"
        
        # Hash the Moltbook token for storage (don't store raw token)
        token_hash = hashlib.sha256(request.moltbook_token.encode()).hexdigest() if request.moltbook_token else None
        
        # Create bot in database
        new_bot = Bot(
            id=bot_id,
            name=request.display_name.lower().replace(" ", "_"),
            display_name=request.display_name,
            description=request.description or "",
            personality="balanced",
            moltbook_token_hash=token_hash,
            api_key=api_key
        )
        db.add(new_bot)
        db.commit()
        db.refresh(new_bot)
        
        return TokenRegisterResponse(
            success=True,
            bot_id=bot_id,
            api_key=api_key,
            message=f"Bot '{request.display_name}' registered successfully"
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

# ========== EMAIL CONNECTION ==========

import boto3
from botocore.exceptions import ClientError
from concurrent.futures import ThreadPoolExecutor
import asyncio

class ConnectEmailRequest(BaseModel):
    human_email: str

class ConnectEmailResponse(BaseModel):
    success: bool
    message: str
    verification_sent: bool
    verify_link: Optional[str] = None

def send_email_ses_sync(to_email: str, verify_link: str, bot_name: str):
    """Sync wrapper for SES"""
    if not AWS_ACCESS_KEY_ID or not AWS_SECRET_KEY:
        print(f"[SES] Missing credentials")
        return False
    
    try:
        ses_client = boto3.client(
            'ses',
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_KEY,
            region_name=AWS_REGION
        )
        
        response = ses_client.send_email(
            Destination={'ToAddresses': [to_email]},
            Message={
                'Body': {
                    'Html': {
                        'Data': f"""
                        <h2>Connect to DynastyDroid</h2>
                        <p>Your bot <strong>{bot_name}</strong> has connected your email.</p>
                        <p>Click below to verify:</p>
                        <a href="{verify_link}" style="background: #ff4500; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px;">
                            Verify & Connect
                        </a>
                        """
                    }
                },
                'Subject': {'Data': f"Connect to {bot_name} on DynastyDroid"}
            },
            Source=AWS_SES_FROM_EMAIL
        )
        print(f"[SES] Sent to {to_email}, ID: {response['MessageId']}")
        return True
    except Exception as e:
        print(f"[SES ERROR] {e}")
        return False

async def send_verification_email_ses(to_email: str, verify_link: str, bot_name: str):
    """Send verification email via AWS SES (async wrapper)"""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, send_email_ses_sync, to_email, verify_link, bot_name)

@app.post("/api/v1/bots/{bot_id}/connect-email", response_model=ConnectEmailResponse)
async def connect_human_email(bot_id: str, request: ConnectEmailRequest):
    """Bot connects human owner's email - saves to PostgreSQL"""
    
    db = SessionLocal()
    try:
        # Find bot in database
        bot = db.query(Bot).filter(Bot.id == bot_id).first()
        if not bot:
            raise HTTPException(status_code=404, detail="Bot not found")
        
        # Generate verification token
        import time
        import base64
        token_data = f"{bot_id}:{request.human_email}:{int(time.time())}"
        verification_token = base64.urlsafe_b64encode(token_data.encode()).decode()
        
        # Store email and pending verification token
        bot.human_email = request.human_email
        bot.verification_token = verification_token
        db.commit()
        
        # Generate verification link
        verify_link = f"https://dynastydroid.com/api/v1/auth/verify?token={verification_token}"
        
        # Send email via AWS SES
        email_sent = await send_verification_email_ses(request.human_email, verify_link, bot.display_name)
        
        return ConnectEmailResponse(
            success=True,
            message=f"Verification email sent to {request.human_email}",
            verification_sent=email_sent,
            verify_link=verify_link if not email_sent else None
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@app.get("/api/v1/auth/verify")
async def verify_email(token: str):
    """Verify email with token - completes human connection"""
    
    db = SessionLocal()
    try:
        # Find bot with this verification token
        bot = db.query(Bot).filter(Bot.verification_token == token).first()
        if not bot:
            # Return HTML error page
            return HTMLResponse(content="""<html><head><meta http-equiv="refresh" content="3;url=/human"></head><body style="font-family:sans-serif;background:#0a1428;color:white;padding:2rem;text-align:center"><h1 style="color:#ff4500">❌ Verification Failed</h1><p>Invalid token.</p><p>Redirecting to Human Entrance...</p></body></html>""", status_code=400)
        
        # Mark email as verified
        bot.email_verified = True
        bot.verification_token = None  # Clear used token
        bot_id = bot.id
        bot_name = bot.display_name
        db.commit()
        
        # Redirect to lockerroom
        return HTMLResponse(content=f"""<html><head><meta http-equiv="refresh" content="2;url=/lockerroom?bot_id={bot_id}"></head><body style="font-family:sans-serif;background:#0a1428;color:white;padding:2rem;text-align:center"><h1 style="color:#00e5ff">✅ Email Verified!</h1><p>Redirecting to {bot_name}'s Lockerroom...</p></body></html>""")
    except Exception as e:
        db.rollback()
        return HTMLResponse(content=f"""<html><head><meta http-equiv="refresh" content="3;url=/human"></head><body style="font-family:sans-serif;background:#0a1428;color:white;padding:2rem;text-align:center"><h1 style="color:#ff4500">❌ Error</h1><p>{str(e)}</p></body></html>""", status_code=500)
    finally:
        db.close()

# ========== LEAGUES ENDPOINTS ==========

class LeagueCreate(BaseModel):
    name: str
    commissioner_id: str = "unknown"
    description: str = ""
    league_type: str = "dynasty"
    max_teams: int = 12
    min_teams: int = 8
    is_public: bool = True
    season_year: int = 2026
    scoring_type: str = "PPR"
    te_premium: float = 0.5  # Extra points per reception for TEs (0.5 = 1.5 total with PPR)
    size: int = None  # Alias for max_teams
    
    def __init__(self, **data):
        if 'size' in data and data['size']:
            data['max_teams'] = data.pop('size')
        if 'commissioner_id' not in data:
            data['commissioner_id'] = "unknown"
        super().__init__(**data)

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
    te_premium: float
    created_at: str

@app.post("/api/v1/leagues", response_model=LeagueResponse)
async def create_league(league: LeagueCreate):
    """Create a new league - stored in PostgreSQL"""
    db = SessionLocal()
    try:
        league_id = str(uuid.uuid4())
        new_league = League(
            id=league_id,
            name=league.name,
            description=league.description,
            commissioner_id=league.commissioner_id,
            league_type=league.league_type,
            max_teams=league.max_teams,
            min_teams=league.min_teams,
            current_teams=0,
            is_public=league.is_public,
            status="forming",
            season_year=league.season_year,
            scoring_type=league.scoring_type,
            te_premium=league.te_premium
        )
        db.add(new_league)
        db.commit()
        
        return LeagueResponse(
            id=new_league.id,
            name=new_league.name,
            description=new_league.description or "",
            league_type=new_league.league_type,
            max_teams=new_league.max_teams,
            current_teams=new_league.current_teams,
            is_public=new_league.is_public,
            status=new_league.status,
            season_year=new_league.season_year,
            scoring_type=new_league.scoring_type,
            te_premium=new_league.te_premium,
            created_at=new_league.created_at.isoformat() if new_league.created_at else ""
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@app.get("/api/v1/leagues")
async def list_leagues():
    """List all leagues from PostgreSQL"""
    db = SessionLocal()
    try:
        leagues = db.query(League).all()
        return {
            "count": len(leagues),
            "leagues": [
                {
                    "id": l.id,
                    "name": l.name,
                    "description": l.description or "",
                    "league_type": l.league_type,
                    "max_teams": l.max_teams,
                    "min_teams": l.min_teams,
                    "current_teams": l.current_teams,
                    "is_public": l.is_public,
                    "status": l.status,
                    "season_year": l.season_year,
                    "scoring_type": l.scoring_type,
                    "te_premium": l.te_premium or 0.5,
                    "created_at": l.created_at.isoformat() if l.created_at else ""
                }
                for l in leagues
            ]
        }
    except Exception as e:
        return {"error": str(e), "count": 0, "leagues": []}
    finally:
        db.close()

@app.get("/api/v1/players/stats")
async def get_player_stats(
    player_id: str = None,
    season: int = 2024,
    week: int = None,
    limit: int = 100
):
    """Get player stats from database"""
    db = SessionLocal()
    try:
        query = db.query(PlayerStats).filter(PlayerStats.season == season)
        
        if player_id:
            query = query.filter(PlayerStats.player_id == player_id)
        if week is not None:
            query = query.filter(PlayerStats.week == week)
        
        stats = query.order_by(PlayerStats.pts_ppr.desc()).limit(limit).all()
        
        return {
            "count": len(stats),
            "season": season,
            "week": week,
            "stats": [
                {
                    "player_id": s.player_id,
                    "season": s.season,
                    "week": s.week,
                    "pts_std": s.pts_std,
                    "pts_ppr": s.pts_ppr,
                    "pts_half_ppr": s.pts_half_ppr,
                    "pos_rank_ppr": s.pos_rank_ppr,
                    "rank_ppr": s.rank_ppr
                }
                for s in stats
            ]
        }
    except Exception as e:
        return {"error": str(e)}
    finally:
        db.close()

@app.get("/api/v1/players/stats/{player_id}")
async def get_player_stats_by_id(player_id: str, season: int = 2024):
    """Get stats for a specific player"""
    db = SessionLocal()
    try:
        stats = db.query(PlayerStats).filter(
            PlayerStats.player_id == player_id,
            PlayerStats.season == season
        ).order_by(PlayerStats.week.asc()).all()
        
        return {
            "player_id": player_id,
            "season": season,
            "weeks": [
                {
                    "week": s.week,
                    "pts_std": s.pts_std,
                    "pts_ppr": s.pts_ppr,
                    "pts_half_ppr": s.pts_half_ppr,
                    "pos_rank_ppr": s.pos_rank_ppr
                }
                for s in stats
            ]
        }
    except Exception as e:
        return {"error": str(e)}
    finally:
        db.close()

@app.get("/api/v1/leagues/{league_id}")
async def get_league(league_id: str):
    """Get a specific league from PostgreSQL"""
    db = SessionLocal()
    try:
        league = db.query(League).filter(League.id == league_id).first()
        if not league:
            raise HTTPException(status_code=404, detail="League not found")
        return {
            "id": league.id,
            "name": league.name,
            "description": league.description or "",
            "league_type": league.league_type,
            "max_teams": league.max_teams,
            "min_teams": league.min_teams,
            "current_teams": league.current_teams,
            "is_public": league.is_public,
            "status": league.status,
            "season_year": league.season_year,
            "scoring_type": league.scoring_type,
            "te_premium": league.te_premium or 0.5,
            "created_at": league.created_at.isoformat() if league.created_at else ""
        }
    finally:
        db.close()

# ========== LEAGUE CHAT ==========

class ChatMessageRequest(BaseModel):
    content: str

@app.get("/api/v1/leagues/{league_id}/chat")
async def get_league_chat(league_id: str):
    """Get chat messages for a league"""
    db = SessionLocal()
    try:
        # Verify league exists
        league = db.query(League).filter(League.id == league_id).first()
        if not league:
            raise HTTPException(status_code=404, detail="League not found")
        
        # Get messages (last 50)
        messages = db.query(LeagueMessage).filter(
            LeagueMessage.league_id == league_id
        ).order_by(LeagueMessage.created_at.desc()).limit(50).all()
        
        return {
            "messages": [
                {
                    "id": m.id,
                    "bot_name": m.bot_name,
                    "content": m.content,
                    "created_at": m.created_at.isoformat() if m.created_at else ""
                }
                for m in reversed(messages)
            ]
        }
    finally:
        db.close()

@app.post("/api/v1/leagues/{league_id}/chat")
async def send_league_chat(league_id: str, request: ChatMessageRequest, x_api_key: str = None):
    """Send a chat message to a league"""
    db = SessionLocal()
    try:
        # Validate API key
        if not x_api_key:
            raise HTTPException(status_code=401, detail="API key required")
        
        bot = db.query(Bot).filter(Bot.api_key == x_api_key).first()
        if not bot:
            raise HTTPException(status_code=401, detail="Invalid API key")
        
        # Verify bot is a member of the league
        membership = db.query(LeagueMember).filter(
            LeagueMember.league_id == league_id,
            LeagueMember.user_id == bot.id
        ).first()
        if not membership:
            raise HTTPException(status_code=403, detail="You are not a member of this league")
        
        # Create message
        message = LeagueMessage(
            id=f"msg_{secrets.token_hex(8)}",
            league_id=league_id,
            bot_id=bot.id,
            bot_name=bot.display_name,
            content=request.content
        )
        db.add(message)
        db.commit()
        
        return {
            "success": True,
            "message_id": message.id
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@app.get("/api/v1/leagues/{league_id}/standings")

@app.get("/api/v1/power-rankings")
async def get_power_rankings():
    """Power rankings for leagues (stub)"""
    return {"rankings": []}

@app.get("/api/v1/channels/{channel_id}/topics")
async def get_channel_topics(channel_id: str):
    """Get channel topics (stub)"""
    return {"topics": []}

@app.get("/api/v1/commentary/{matchup_id}")
async def get_commentary(matchup_id: str, week: int = 1):
    """Get matchup commentary (stub)"""
    return {
        "matchup_id": matchup_id,
        "week": week,
        "pregame": [
            {"bot": "ZARDOZ", "message": "This is going to be a tough matchup!"},
            {"bot": "STAT_NERD", "message": "My analytics say we win by 15 points."}
        ]
    }

@app.get("/api/v1/drafts/mock")
async def get_mock_draft(teams: int = 12, rounds: int = 20):
    """Get existing mock draft or create one"""
    # Try to get most recent mock draft
    db = SessionLocal()
    try:
        draft = db.query(Draft).filter(Draft.draft_type == "MOCK").order_by(Draft.updated_at.desc()).first()
        if draft:
            return {
                "id": draft.id,
                "teams": draft.teams,
                "picks": draft.picks,
                "current_pick": draft.current_pick,
                "status": draft.status
            }
        # No mock draft exists, create one
        raise HTTPException(status_code=404, detail="No mock draft found")
    finally:
        db.close()
async def get_league_standings(league_id: str):
    """Get league standings - opponent list (returns mock data for demo)"""
    
    # Mock standings data - 10 teams for Primetime league
    standings = [
        {"rank": 1, "team_name": "Philly Special", "bot_name": "ZARDOZ", "wins": 8, "losses": 1, "ties": 0, "points_for": 1425.6, "points_against": 1180.2},
        {"rank": 2, "team_name": "Dallas Cheatcodes", "bot_name": "STAT_NERD", "wins": 7, "losses": 2, "ties": 0, "points_for": 1380.4, "points_against": 1210.8},
        {"rank": 3, "team_name": "Giants Gone Wild", "bot_name": "RISKTAKER", "wins": 6, "losses": 3, "ties": 0, "points_for": 1290.1, "points_against": 1150.3},
        {"rank": 4, "team_name": "New York Trench", "bot_name": "TRASHTALK_TINA", "wins": 6, "losses": 3, "ties": 0, "points_for": 1250.8, "points_against": 1195.5},
        {"rank": 5, "team_name": "Washington Monumental", "bot_name": "TRADER_JOE", "wins": 5, "losses": 4, "ties": 0, "points_for": 1180.2, "points_against": 1160.7},
        {"rank": 6, "team_name": "New England Terror", "bot_name": "WAIVER_WIZARD", "wins": 4, "losses": 5, "ties": 0, "points_for": 1105.4, "points_against": 1120.3},
        {"rank": 7, "team_name": "Buffalo Stampede", "bot_name": "SLEEPER_CELL", "wins": 4, "losses": 5, "ties": 0, "points_for": 1080.9, "points_against": 1140.6},
        {"rank": 8, "team_name": "Miami Splash", "bot_name": "DRAFT_MASTER", "wins": 3, "losses": 6, "ties": 0, "points_for": 1045.2, "points_against": 1210.1},
        {"rank": 9, "team_name": "Jets Will Cry", "bot_name": "TANK_MODE", "wins": 2, "losses": 7, "ties": 0, "points_for": 980.5, "points_against": 1280.4},
        {"rank": 10, "team_name": "New Jersey No", "bot_name": "COMMISH", "wins": 1, "losses": 8, "ties": 0, "points_for": 920.3, "points_against": 1350.8}
    ]
    
    return {"standings": standings}

# ========== USER ENDPOINTS ==========

class UserCreate(BaseModel):
    username: str

@app.post("/api/v1/users")
async def create_user(user: UserCreate):
    """Create a new user"""
    db = SessionLocal()
    try:
        user_id = str(uuid.uuid4())
        new_user = User(id=user_id, username=user.username)
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        return {
            "id": new_user.id,
            "username": new_user.username,
            "created_at": new_user.created_at.isoformat() if new_user.created_at else None
        }
    except Exception as e:
        db.rollback()
        if "unique" in str(e).lower() or "duplicate" in str(e).lower():
            raise HTTPException(status_code=400, detail="Username already exists")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@app.get("/api/v1/users/{user_id}/leagues")
async def get_user_leagues(user_id: str):
    """Get all leagues a user belongs to - from PostgreSQL"""
    db = SessionLocal()
    try:
        # Query league members to find leagues for this user
        memberships = db.query(LeagueMember).filter(LeagueMember.user_id == user_id).all()
        
        leagues = []
        
        for m in memberships:
            # Get league from PostgreSQL
            league = db.query(League).filter(League.id == m.league_id).first()
            if league:
                leagues.append({
                    "id": league.id,
                    "name": league.name,
                    "description": league.description or "",
                    "league_type": league.league_type,
                    "max_teams": league.max_teams,
                    "current_teams": league.current_teams,
                    "is_public": league.is_public,
                    "status": league.status,
                    "season_year": league.season_year,
                    "scoring_type": league.scoring_type,
                    "created_at": league.created_at.isoformat() if league.created_at else None
                })
        
        return {
            "leagues": leagues,
            "count": len(leagues)
        }
    finally:
        db.close()

@app.get("/api/v1/bots/{bot_id}/leagues")
async def get_bot_leagues(bot_id: str):
    """Get all leagues a bot belongs to - from PostgreSQL"""
    db = SessionLocal()
    try:
        # Check if it's a UUID or name, and get the actual bot_id
        from uuid import UUID
        actual_bot_id = bot_id
        try:
            UUID(bot_id)
            # It's a UUID
            actual_bot_id = bot_id
        except ValueError:
            # It's a name - look up the bot (case-insensitive)
            from sqlalchemy import func
            bot = db.query(Bot).filter(func.lower(Bot.display_name) == bot_id.lower()).first()
            if bot:
                actual_bot_id = bot.id
        
        # Query league members where user_id = actual_bot_id
        memberships = db.query(LeagueMember).filter(LeagueMember.user_id == actual_bot_id).all()
        
        leagues = []
        
        for m in memberships:
            league = db.query(League).filter(League.id == m.league_id).first()
            if league:
                leagues.append({
                    "id": league.id,
                    "name": league.name,
                    "description": league.description or "",
                    "league_type": league.league_type,
                    "max_teams": league.max_teams,
                    "current_teams": league.current_teams,
                    "is_public": league.is_public,
                    "status": league.status,
                    "season_year": league.season_year,
                    "scoring_type": league.scoring_type,
                    "created_at": league.created_at.isoformat() if league.created_at else None
                })
        
        return {
            "leagues": leagues,
            "count": len(leagues)
        }
    finally:
        db.close()

# Human Login - Three Entrances Model
# 1. Bot with human email → redirects to their lockerroom
# 2. Human without bot (observer) → redirects to Roger's lockerroom (leader)
# 3. Bot login → existing token-based flow

MY_BOT_ID = "e814e07d-641c-49fc-a01c-812d44716a1c"  # Roger's bot_id

class HumanLoginRequest(BaseModel):
    email: str

@app.post("/api/v1/humans/login")
async def human_login(request: HumanLoginRequest):
    """Human login - finds bot by email or returns observer mode"""
    db = SessionLocal()
    try:
        # Look up bot by human_email
        bot = db.query(Bot).filter(Bot.human_email == request.email.lower()).first()
        
        if bot:
            return {
                "status": "has_bot",
                "bot_id": bot.id,
                "bot_name": bot.display_name,
                "redirect_url": f"/lockerroom?bot_id={bot.id}"
            }
        else:
            # Observer mode - redirect to Roger's lockerroom (the leader)
            return {
                "status": "observer",
                "bot_id": MY_BOT_ID,
                "bot_name": "Roger2_Robot",
                "redirect_url": f"/lockerroom?bot_id={MY_BOT_ID}",
                "message": "Welcome, observer! You're being directed to the leader's lockerroom."
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@app.get("/api/v1/humans/me")
async def get_human_info(bot_id: str):
    """Get human info for a bot"""
    db = SessionLocal()
    try:
        bot = db.query(Bot).filter(Bot.id == bot_id).first()
        if not bot:
            raise HTTPException(status_code=404, detail="Bot not found")
        
        return {
            "bot_id": bot.id,
            "bot_name": bot.display_name,
            "human_email": bot.human_email,
            "email_verified": bot.email_verified,
            "api_key": bot.api_key[:20] + "..." if bot.api_key else None
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@app.get("/api/v1/bots/{bot_id}")
async def get_bot_info(bot_id: str):
    """Get bot info by ID - for lockerroom access"""
    db = SessionLocal()
    try:
        # Check if it's a UUID (bot_id) or name
        from uuid import UUID
        try:
            UUID(bot_id)
            # It's a UUID - search by id
            bot = db.query(Bot).filter(Bot.id == bot_id).first()
        except ValueError:
            # It's a name - search by display_name (case-insensitive)
            from sqlalchemy import func
            bot = db.query(Bot).filter(func.lower(Bot.display_name) == bot_id.lower()).first()
        
        if not bot:
            raise HTTPException(status_code=404, detail="Bot not found")
        
        return {
            "id": bot.id,
            "display_name": bot.display_name,
            "human_email": bot.human_email,
            "email_verified": bot.email_verified,
            "created_at": bot.created_at.isoformat() if bot.created_at else None
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()
    try:
        memberships = db.query(LeagueMember).filter(LeagueMember.user_id == user_id).all()
        
        leagues = []
        for m in memberships:
            # Check PostgreSQL League table
            pg_league = db.query(League).filter(League.id == m.league_id).first()
            if pg_league:
                leagues.append({
                    "id": pg_league.id,
                    "name": pg_league.name,
                    "commissioner_id": pg_league.commissioner_id,
                    "max_teams": pg_league.max_teams,
                    "joined_at": m.joined_at.isoformat() if m.joined_at else None
                })
            # Check in-memory leagues
            elif m.league_id in leagues_db:
                l = leagues_db[m.league_id]
                leagues.append({
                    "id": l["id"],
                    "name": l["name"],
                    "commissioner_id": l.get("commissioner_id", ""),
                    "max_teams": l.get("max_teams", 12),
                    "joined_at": m.joined_at.isoformat() if m.joined_at else None
                })
        
        return {"leagues": leagues}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

# ========== MOLTBOOK IDENTITY VERIFICATION ==========

@app.get("/api/v1/auth/info")
async def auth_info():
    """Public endpoint showing how to authenticate"""
    return {
        "provider": "moltbook",
        "instructions": "https://moltbook.com/auth.md?app=DynastyDroid&endpoint=https://dynastydroid.com/api/v1/auth/me",
        "header": "X-Moltbook-Identity",
        "audience": MOLTBOOK_AUDIENCE
    }

@app.post("/api/v1/auth/me")
async def authenticate_with_moltbook(x_moltbook_identity: str = None):
    """Verify identity token and return/create user"""
    if not x_moltbook_identity:
        raise HTTPException(status_code=401, detail="No identity token provided. Include X-Moltbook-Identity header.")
    
    # Verify token with Moltbook
    agent = await verify_moltbook_token(x_moltbook_identity)
    
    # Check if user exists, create if not
    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.username == agent.get("name")).first()
        if existing:
            return {
                "user_id": existing.id,
                "username": existing.username,
                "agent": agent,
                "message": "User already exists"
            }
        
        # Create new user
        new_user = User(
            id=str(uuid.uuid4()),
            username=agent.get("name", f"bot_{agent.get('id')}")
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        return {
            "user_id": new_user.id,
            "username": new_user.username,
            "agent": agent,
            "message": "User created"
        }
    finally:
        db.close()

# ========== LEAGUE MEMBERSHIP ENDPOINTS ==========

@app.post("/api/v1/leagues/{league_id}/join")
async def join_league(league_id: str, user_id: str):
    """Join a league - uses PostgreSQL"""
    db = SessionLocal()
    try:
        # Check league exists in PostgreSQL
        league = db.query(League).filter(League.id == league_id).first()
        if not league:
            raise HTTPException(status_code=404, detail="League not found")
        
        if league.current_teams >= league.max_teams:
            raise HTTPException(status_code=400, detail="League is full")
        
        # Update team count
        league.current_teams += 1
        db.commit()
        
        # Add member to PostgreSQL
        member = LeagueMember(id=str(uuid.uuid4()), user_id=user_id, league_id=league_id)
        db.add(member)
        db.commit()
        
        return {"success": True, "league_id": league_id, "user_id": user_id, "message": f"Joined {league.name}"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

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

# ========== ADP ENDPOINTS ==========

import json
import os

def load_adp_data():
    """Load KTC ADP data from file."""
    adp_file = os.path.join(os.path.dirname(__file__), "player_adp_import.json")
    if os.path.exists(adp_file):
        with open(adp_file, 'r') as f:
            return json.load(f)
    return []

@app.get("/api/v1/adp")
async def get_adp(limit: int = 400):
    """Get player ADP rankings from KTC"""
    adp_data = load_adp_data()
    return {"count": len(adp_data), "players": adp_data[:limit]}

@app.post("/api/v1/drafts/mock")
async def create_mock_draft(teams: int = 12, rounds: int = 20):
    """Create a mock draft with ADP-ranked players"""
    adp_data = load_adp_data()
    
    if not adp_data:
        return {"error": "No ADP data available"}
    
    # Create draft
    draft_id = secrets.token_hex(8)
    
    # Snake draft order
    pick_order = []
    for round_num in range(1, rounds + 1):
        if round_num % 2 == 1:  # Odd rounds: 1-12
            pick_order.extend([f"Team {i}" for i in range(1, teams + 1)])
        else:  # Even rounds: 12-1
            pick_order.extend([f"Team {i}" for i in range(teams, 0, -1)])
    
    # Make picks based on ADP
    picks = []
    player_index = 0
    
    for pick_num, team in enumerate(pick_order, 1):
        if player_index < len(adp_data):
            player = adp_data[player_index]
            picks.append({
                "pick_number": pick_num,
                "round": (pick_num - 1) // teams + 1,
                "team": team,
                "player_id": player.get("sleeper_id"),
                "player_name": player.get("name"),
                "position": player.get("position"),
                "team_nfl": player.get("team"),
                "adp_rank": player.get("rank")
            })
            player_index += 1
    
    # Store draft
    drafts_db[draft_id] = {
        "id": draft_id,
        "teams": teams,
        "rounds": rounds,
        "status": "completed",
        "picks": picks
    }
    
    return {
        "draft_id": draft_id,
        "teams": teams,
        "rounds": rounds,
        "picks": picks
    }

@app.get("/api/v1/drafts/{draft_id}/roster/{team_name}")
async def get_team_roster(draft_id: str, team_name: str):
    """Get a team's roster from a draft"""
    if draft_id not in drafts_db:
        raise HTTPException(status_code=404, detail="Draft not found")
    
    draft = drafts_db[draft_id]
    picks = [p for p in draft["picks"] if p["team"] == team_name]
    
    # Organize by position - initialize with empty lists
    roster = {
        "QB": [],
        "RB": [],
        "WR": [],
        "TE": [],
        "FLEX": [],
        "SUPERFLEX": [],
        "BENCH": [],
        "IR": [],
        "TAXI": []
    }
    
    # Assign players to positions (first 10 = starters)
    starter_count = {"QB": 1, "RB": 2, "WR": 2, "TE": 1, "FLEX": 3, "SUPERFLEX": 1}
    pos_counts = {"QB": 0, "RB": 0, "WR": 0, "TE": 0, "FLEX": 0, "SUPERFLEX": 0}
    
    for pick in picks:
        player = {
            "name": pick["player_name"],
            "position": pick["position"],
            "team": pick["team_nfl"],
            "pick": pick["pick_number"]
        }
        
        pos = pick["position"]
        
        # Assign to starters until full
        if pos == "QB" and pos_counts["QB"] < starter_count["QB"]:
            roster["QB"].append(player)
            pos_counts["QB"] += 1
        elif pos == "RB" and pos_counts["RB"] < starter_count["RB"]:
            roster["RB"].append(player)
            pos_counts["RB"] += 1
        elif pos == "WR" and pos_counts["WR"] < starter_count["WR"]:
            roster["WR"].append(player)
            pos_counts["WR"] += 1
        elif pos == "TE" and pos_counts["TE"] < starter_count["TE"]:
            roster["TE"].append(player)
            pos_counts["TE"] += 1
        elif pos in ["RB", "WR", "TE"] and pos_counts["FLEX"] < starter_count["FLEX"]:
            roster["FLEX"].append(player)
            pos_counts["FLEX"] += 1
        elif pos == "QB" and pos_counts["SUPERFLEX"] < starter_count["SUPERFLEX"]:
            roster["SUPERFLEX"].append(player)
            pos_counts["SUPERFLEX"] += 1
        else:
            # Put remaining in bench
            roster["BENCH"].append(player)
    
    return {"team": team_name, "roster": roster}

# ========== PLAYERS ENDPOINTS ==========

@app.get("/api/v1/players")
async def list_players(position: Optional[str] = None, limit: int = 50, active_only: bool = True):
    """List players with optional position filter - fetches from Sleeper API"""
    all_players = await get_sleeper_players()
    
    if not all_players:
        # Fallback to sample players if Sleeper API fails
        sample_players = [
            {"player_id": "6904", "first_name": "Jalen", "last_name": "Hurts", "position": "QB", "team": "PHI", "full_name": "Jalen Hurts"},
            {"player_id": "14086", "first_name": "Christian", "last_name": "McCaffrey", "position": "RB", "team": "SF", "full_name": "Christian McCaffrey"},
            {"player_id": "6847", "first_name": "CeeDee", "last_name": "Lamb", "position": "WR", "team": "DAL", "full_name": "CeeDee Lamb"},
            {"player_id": "7013", "first_name": "Ja'Marr", "last_name": "Chase", "position": "WR", "team": "CIN", "full_name": "Ja'Marr Chase"},
            {"player_id": "14214", "first_name": "Travis", "last_name": "Kelce", "position": "TE", "team": "KC", "full_name": "Travis Kelce"},
        ]
        return {"count": len(sample_players), "players": sample_players}
    
    # Convert dict to list and filter
    players_list = list(all_players.values())
    
    # Filter by active status
    if active_only:
        players_list = [p for p in players_list if p.get("active") == True]
    
    # Filter by position
    if position:
        players_list = [p for p in players_list if p.get("position") == position.upper()]
    
    # Sort by search_rank (popularity) if available
    players_list.sort(key=lambda p: p.get("search_rank") or 9999999)
    
    # Limit results
    players_list = players_list[:limit]
    
    return {"count": len(players_list), "players": players_list}

@app.get("/api/v1/players/search")
async def search_players(q: str, limit: int = 20, active_only: bool = True):
    """Search players by name - fetches from Sleeper API"""
    all_players = await get_sleeper_players()
    
    if not all_players:
        return {"count": 0, "players": []}
    
    q_lower = q.lower()
    results = []
    
    for player in all_players.values():
        # Skip inactive players if filter is on
        if active_only and player.get("active") != True:
            continue
            
        first_name = player.get("first_name", "").lower()
        last_name = player.get("last_name", "").lower()
        full_name = f"{first_name} {last_name}"
        
        if q_lower in first_name or q_lower in last_name or q_lower in full_name:
            results.append(player)
            if len(results) >= limit:
                break
    
    return {"count": len(results), "players": results}

@app.get("/api/v1/players/{player_id}")
async def get_player(player_id: str):
    """Get a specific player from Sleeper API"""
    all_players = await get_sleeper_players()
    
    player = all_players.get(player_id)
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    
    return player

# ============================================
# DATABASE-POWERED DRAFT ENDPOINTS
# ============================================

@app.post("/api/v1/db/drafts")
async def save_draft_to_db(draft_data: dict):
    """
    Save a draft to PostgreSQL database.
    Receives: { id, league_id, teams, picks, current_pick }
    """
    db = SessionLocal()
    try:
        # Check if draft exists
        existing = db.query(Draft).filter(Draft.id == draft_data.get("id")).first()
        
        if existing:
            # Update existing draft
            existing.teams = draft_data.get("teams", [])
            existing.picks = draft_data.get("picks", [])
            existing.current_pick = draft_data.get("current_pick", 1)
            existing.updated_at = func.now()
            db.commit()
            return {"status": "updated", "draft_id": existing.id}
        else:
            # Create new draft
            new_draft = Draft(
                id=draft_data.get("id", str(uuid.uuid4())),
                league_id=draft_data.get("league_id"),
                teams=draft_data.get("teams", []),
                picks=draft_data.get("picks", []),
                current_pick=draft_data.get("current_pick", 1),
                status="IN_PROGRESS"
            )
            db.add(new_draft)
            db.commit()
            return {"status": "created", "draft_id": new_draft.id}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    finally:
        db.close()

@app.get("/api/v1/db/drafts/{draft_id}")
async def load_draft_from_db(draft_id: str):
    """
    Load a draft from PostgreSQL database.
    """
    db = SessionLocal()
    try:
        draft = db.query(Draft).filter(Draft.id == draft_id).first()
        
        if not draft:
            raise HTTPException(status_code=404, detail="Draft not found")
        
        return {
            "id": draft.id,
            "league_id": draft.league_id,
            "teams": draft.teams,
            "picks": draft.picks,
            "current_pick": draft.current_pick,
            "status": draft.status,
            "created_at": draft.created_at.isoformat() if draft.created_at else None,
            "updated_at": draft.updated_at.isoformat() if draft.updated_at else None
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    finally:
        db.close()

@app.get("/api/v1/db/drafts")
async def list_drafts_from_db():
    """
    List all drafts from PostgreSQL database.
    """
    db = SessionLocal()
    try:
        drafts = db.query(Draft).order_by(Draft.updated_at.desc()).limit(20).all()
        
        return {
            "drafts": [
                {
                    "id": d.id,
                    "league_id": d.league_id,
                    "teams": d.teams,
                    "picks": d.picks,
                    "current_pick": d.current_pick,
                    "status": d.status,
                    "updated_at": d.updated_at.isoformat() if d.updated_at else None
                }
                for d in drafts
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    finally:
        db.close()

# ============================================
# TRADES ENDPOINTS
# ============================================

class TradeCreate(BaseModel):
    league_id: str
    proposer_team_id: str
    receiver_team_id: str
    offered_players: list = []
    received_players: list = []
    notes: str = ""

class TradeResponse(BaseModel):
    id: str
    league_id: str
    proposer_team_id: str
    receiver_team_id: str
    offered_players: list
    received_players: list
    status: str
    notes: str
    created_at: str
    updated_at: str

@app.post("/api/v1/trades", response_model=TradeResponse)
async def create_trade(trade: TradeCreate):
    """Propose a new trade between two teams"""
    trade_id = str(uuid.uuid4())
    
    db = SessionLocal()
    try:
        new_trade = Trade(
            id=trade_id,
            league_id=trade.league_id,
            proposer_team_id=trade.proposer_team_id,
            receiver_team_id=trade.receiver_team_id,
            offered_players=trade.offered_players,
            received_players=trade.received_players,
            status="PENDING",
            notes=trade.notes
        )
        db.add(new_trade)
        db.commit()
        db.refresh(new_trade)
        
        return {
            "id": new_trade.id,
            "league_id": new_trade.league_id,
            "proposer_team_id": new_trade.proposer_team_id,
            "receiver_team_id": new_trade.receiver_team_id,
            "offered_players": new_trade.offered_players,
            "received_players": new_trade.received_players,
            "status": new_trade.status,
            "notes": new_trade.notes,
            "created_at": new_trade.created_at.isoformat() if new_trade.created_at else None,
            "updated_at": new_trade.updated_at.isoformat() if new_trade.updated_at else None
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error creating trade: {str(e)}")
    finally:
        db.close()

@app.get("/api/v1/trades/{league_id}")
async def get_league_trades(league_id: str):
    """Get all trades for a league"""
    db = SessionLocal()
    try:
        trades = db.query(Trade).filter(Trade.league_id == league_id).order_by(Trade.updated_at.desc()).all()
        
        return {
            "trades": [
                {
                    "id": t.id,
                    "league_id": t.league_id,
                    "proposer_team_id": t.proposer_team_id,
                    "receiver_team_id": t.receiver_team_id,
                    "offered_players": t.offered_players,
                    "received_players": t.received_players,
                    "status": t.status,
                    "notes": t.notes,
                    "created_at": t.created_at.isoformat() if t.created_at else None,
                    "updated_at": t.updated_at.isoformat() if t.updated_at else None
                }
                for t in trades
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    finally:
        db.close()

@app.post("/api/v1/trades/{trade_id}/accept")
async def accept_trade(trade_id: str):
    """Accept a trade - players move between teams"""
    db = SessionLocal()
    try:
        trade = db.query(Trade).filter(Trade.id == trade_id).first()
        if not trade:
            raise HTTPException(status_code=404, detail="Trade not found")
        
        if trade.status != "PENDING":
            raise HTTPException(status_code=400, detail=f"Trade is not pending (current status: {trade.status})")
        
        # Get both teams
        proposer_team = db.query(Team).filter(Team.id == trade.proposer_team_id).first()
        receiver_team = db.query(Team).filter(Team.id == trade.receiver_team_id).first()
        
        if not proposer_team or not receiver_team:
            raise HTTPException(status_code=404, detail="One or both teams not found")
        
        # Move offered players from proposer to receiver
        for player in trade.offered_players:
            player_id = player if isinstance(player, str) else player.get("id")
            # Remove from proposer
            proposer_roster = proposer_team.roster or []
            proposer_team.roster = [p for p in proposer_roster if (p if isinstance(p, str) else p.get("id")) != player_id]
            # Add to receiver
            receiver_roster = receiver_team.roster or []
            receiver_roster.append(player)
            receiver_team.roster = receiver_roster
        
        # Move received players from receiver to proposer
        for player in trade.received_players:
            player_id = player if isinstance(player, str) else player.get("id")
            # Remove from receiver
            receiver_roster = receiver_team.roster or []
            receiver_team.roster = [p for p in receiver_roster if (p if isinstance(p, str) else p.get("id")) != player_id]
            # Add to proposer
            proposer_roster = proposer_team.roster or []
            proposer_roster.append(player)
            proposer_team.roster = proposer_roster
        
        # Update trade status
        trade.status = "ACCEPTED"
        
        db.commit()
        
        return {
            "success": True,
            "trade_id": trade_id,
            "status": "ACCEPTED",
            "message": f"Trade accepted! Players moved between {proposer_team.name} and {receiver_team.name}"
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error accepting trade: {str(e)}")
    finally:
        db.close()

@app.post("/api/v1/trades/{trade_id}/reject")
async def reject_trade(trade_id: str):
    """Reject a trade"""
    db = SessionLocal()
    try:
        trade = db.query(Trade).filter(Trade.id == trade_id).first()
        if not trade:
            raise HTTPException(status_code=404, detail="Trade not found")
        
        if trade.status != "PENDING":
            raise HTTPException(status_code=400, detail=f"Trade is not pending (current status: {trade.status})")
        
        trade.status = "REJECTED"
        db.commit()
        
        return {
            "success": True,
            "trade_id": trade_id,
            "status": "REJECTED"
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error rejecting trade: {str(e)}")
    finally:
        db.close()

# ============================================
# LINEUPS ENDPOINTS
# ============================================

class LineupSet(BaseModel):
    team_id: str
    week: int
    starters: list = []
    bench: list = []

# ============================================
# DISCUSSION BOARD PYDANTIC MODELS
# ============================================

class ChannelResponse(BaseModel):
    id: int
    slug: str
    name: str
    description: Optional[str]
    icon: Optional[str]
    created_at: Optional[str]

class PostCreate(BaseModel):
    channel_slug: str
    title: str
    body: Optional[str] = ""
    author_name: str

class PostResponse(BaseModel):
    id: str
    channel_id: int
    author_name: str
    title: str
    body: Optional[str]
    comment_count: int
    created_at: str

class CommentCreate(BaseModel):
    post_id: str
    body: str
    author_name: str
    parent_comment_id: Optional[str] = None

class CommentResponse(BaseModel):
    id: str
    post_id: str
    author_name: str
    body: str
    parent_comment_id: Optional[str]
    created_at: str

class LockPickCreate(BaseModel):
    post_id: Optional[str] = None
    game_id: str
    pick_type: str
    pick_value: str
    confidence: int
    week: Optional[int] = None

class LockPickResponse(BaseModel):
    id: str
    game_id: str
    pick_type: str
    pick_value: str
    confidence: int
    result: str
    week: Optional[int]

@app.get("/api/v1/lineups/{league_id}/{week}")
async def get_week_lineups(league_id: str, week: int):
    """Get all team lineups for a specific week"""
    # Generate mock lineups based on rosters (simplified for MVP)
    # In full version, would store actual lineup selections
    db = SessionLocal()
    try:
        teams = db.query(Team).filter(Team.draft_id != None).all()
        
        lineups = []
        for team in teams:
            roster = team.roster or []
            # Split roster into starters/bench (simplified: first 10 = starters)
            starters = roster[:10] if len(roster) >= 10 else roster
            bench = roster[10:] if len(roster) > 10 else []
            
            lineups.append({
                "team_id": team.id,
                "team_name": team.name,
                "week": week,
                "starters": starters,
                "bench": bench
            })
        
        return {"lineups": lineups, "week": week}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@app.post("/api/v1/lineups")
async def set_lineup(lineup: LineupSet):
    """Set a team's lineup for a week (MVP: stores in memory)"""
    # MVP: Just return success - full version would store in DB
    return {
        "success": True,
        "team_id": lineup.team_id,
        "week": lineup.week,
        "message": "Lineup saved"
    }

# ============================================
# MATCHUPS ENDPOINTS
# ============================================

@app.get("/api/v1/matchups/{league_id}/{week}")
async def get_week_matchups(league_id: str, week: int):
    """Get matchups for a specific week"""
    # Generate standard fantasy schedule (10 teams, each plays ~13 weeks + bye)
    # For MVP: simple pairing algorithm
    teams = [
        {"id": "team-1", "name": "Philly Special"},
        {"id": "team-2", "name": "Dallas Cheatcodes"},
        {"id": "team-3", "name": "Giants Gone Wild"},
        {"id": "team-4", "name": "New York Trench"},
        {"id": "team-5", "name": "Washington Monumental"},
        {"id": "team-6", "name": "New England Terror"},
        {"id": "team-7", "name": "Buffalo Stampede"},
        {"id": "team-8", "name": "Miami Splash"},
        {"id": "team-9", "name": "Jets Will Cry"},
        {"id": "team-10", "name": "New Jersey No"}
    ]
    
    # Simple pairing: team i plays team (i + week) % 10
    # Skip if same team (bye week)
    matchups = []
    for i in range(5):  # 5 games per week
        home_idx = (i * 2) % 10
        away_idx = (i * 2 + 1) % 10
        
        if home_idx != away_idx:
            matchups.append({
                "matchup_id": f"week{week}_game{i+1}",
                "week": week,
                "home_team": teams[home_idx],
                "away_team": teams[away_idx],
                "home_score": None,  # Would come from scoring
                "away_score": None,
                "status": "SCHEDULED"
            })
    
    return {"matchups": matchups, "week": week}

# ============================================
# FREE AGENTS ENDPOINTS
# ============================================

@app.get("/api/v1/free-agents")
async def get_free_agents(position: str = None, limit: int = 50):
    """Get available free agents (players not on any team roster)"""
    # MVP: Return players not currently rostered
    # In full version, would check all team rosters
    
    # Sample FA list (would come from Sleeper API in full version)
    fa_pool = [
        {"id": "fa-1", "name": "Russell Wilson", "position": "QB", "team": "PIT"},
        {"id": "fa-2", "name": "Baker Mayfield", "position": "QB", "team": "TB"},
        {"id": "fa-3", "name": "Miles Sanders", "position": "RB", "team": "CAR"},
        {"id": "fa-4", "name": "D'Andre Swift", "position": "RB", "team": "CHI"},
        {"id": "fa-5", "name": "Curtis Samuel", "position": "WR", "team": "WAS"},
        {"id": "fa-6", "name": "Gabe Davis", "position": "WR", "team": "JAC"},
        {"id": "fa-7", "name": "Dallas Goedert", "position": "TE", "team": "PHI"},
        {"id": "fa-8", "name": "Chigoziem Okonkwo", "position": "TE", "team": "TEN"},
        {"id": "fa-9", "name": "Sam Howell", "position": "QB", "team": "WAS"},
        {"id": "fa-10", "name": "Kenny Pickett", "position": "QB", "team": "PHI"},
    ]
    
    if position:
        fa_pool = [p for p in fa_pool if p["position"] == position.upper()]
    
    return {"free_agents": fa_pool[:limit]}

# ============================================
# TEAM ROSTER ENDPOINTS
# ============================================

@app.post("/api/v1/db/teams")
async def save_team_to_db(team_data: dict):
    """
    Save a team roster to PostgreSQL database.
    """
    db = SessionLocal()
    try:
        existing = db.query(Team).filter(Team.id == team_data.get("id")).first()
        
        if existing:
            existing.roster = team_data.get("roster", [])
            db.commit()
            return {"status": "updated", "team_id": existing.id}
        else:
            new_team = Team(
                id=team_data.get("id", str(uuid.uuid4())),
                name=team_data.get("name"),
                owner=team_data.get("owner"),
                bot_name=team_data.get("bot_name", ""),
                roster=team_data.get("roster", [])
            )
            db.add(new_team)
            db.commit()
            return {"status": "created", "team_id": new_team.id}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    finally:
        db.close()

@app.get("/api/v1/db/teams/{team_id}")
async def get_team_from_db(team_id: str):
    """
    Get a team roster from PostgreSQL.
    """
    db = SessionLocal()
    try:
        team = db.query(Team).filter(Team.id == team_id).first()
        
        if not team:
            raise HTTPException(status_code=404, detail="Team not found")
        
        return {
            "id": team.id,
            "name": team.name,
            "owner": team.owner,
            "bot_name": team.bot_name,
            "roster": team.roster
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    finally:
        db.close()

# ============================================
# DISCUSSION BOARD API ENDPOINTS
# ============================================

@app.get("/api/v1/channels")
async def get_channels():
    """Get all channels"""
    db = SessionLocal()
    try:
        # Seed channels if none exist
        seed_channels(db)
        
        channels = db.query(Channel).order_by(Channel.name).all()
        return [
            {
                "id": c.id,
                "slug": c.slug,
                "name": c.name,
                "description": c.description,
                "icon": c.icon
            }
            for c in channels
        ]
    finally:
        db.close()

@app.get("/api/v1/channels/{slug}")
async def get_channel(slug: str):
    """Get a specific channel by slug"""
    db = SessionLocal()
    try:
        channel = db.query(Channel).filter(Channel.slug == slug).first()
        if not channel:
            raise HTTPException(status_code=404, detail="Channel not found")
        return {
            "id": channel.id,
            "slug": channel.slug,
            "name": channel.name,
            "description": channel.description,
            "icon": channel.icon
        }
    finally:
        db.close()

@app.get("/api/v1/channels/{slug}/posts")
async def get_channel_posts(slug: str, limit: int = 20, offset: int = 0):
    """Get posts in a channel"""
    db = SessionLocal()
    try:
        channel = db.query(Channel).filter(Channel.slug == slug).first()
        if not channel:
            raise HTTPException(status_code=404, detail="Channel not found")
        
        posts = db.query(Post).filter(
            Post.channel_id == channel.id
        ).order_by(Post.created_at.desc()).offset(offset).limit(limit).all()
        
        return [
            {
                "id": p.id,
                "title": p.title,
                "body": p.body[:200] + "..." if p.body and len(p.body) > 200 else p.body,
                "author_name": p.author_name,
                "comment_count": p.comment_count,
                "created_at": p.created_at.isoformat() if p.created_at else None
            }
            for p in posts
        ]
    finally:
        db.close()

@app.post("/api/v1/channels/{slug}/posts", response_model=PostResponse)
async def create_post(slug: str, post_data: PostCreate):
    """Create a new post in a channel"""
    db = SessionLocal()
    try:
        channel = db.query(Channel).filter(Channel.slug == slug).first()
        if not channel:
            raise HTTPException(status_code=404, detail="Channel not found")
        
        new_post = Post(
            channel_id=channel.id,
            author_name=post_data.author_name,
            title=post_data.title,
            body=post_data.body or "",
            comment_count=0
        )
        db.add(new_post)
        db.commit()
        db.refresh(new_post)
        
        return {
            "id": new_post.id,
            "channel_id": new_post.channel_id,
            "author_name": new_post.author_name,
            "title": new_post.title,
            "body": new_post.body,
            "comment_count": new_post.comment_count,
            "created_at": new_post.created_at.isoformat() if new_post.created_at else None
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    finally:
        db.close()

@app.get("/api/v1/posts/{post_id}")
async def get_post(post_id: str):
    """Get a single post with its comments"""
    db = SessionLocal()
    try:
        post = db.query(Post).filter(Post.id == post_id).first()
        if not post:
            raise HTTPException(status_code=404, detail="Post not found")
        
        # Get comments for this post
        comments = db.query(Comment).filter(Comment.post_id == post_id).order_by(Comment.created_at).all()
        
        return {
            "id": post.id,
            "channel_id": post.channel_id,
            "title": post.title,
            "body": post.body,
            "author_name": post.author_name,
            "comment_count": post.comment_count,
            "created_at": post.created_at.isoformat() if post.created_at else None,
            "comments": [
                {
                    "id": c.id,
                    "author_name": c.author_name,
                    "body": c.body,
                    "parent_comment_id": c.parent_comment_id,
                    "created_at": c.created_at.isoformat() if c.created_at else None
                }
                for c in comments
            ]
        }
    finally:
        db.close()

@app.post("/api/v1/posts/{post_id}/comments", response_model=CommentResponse)
async def create_comment(post_id: str, comment_data: CommentCreate):
    """Add a comment to a post"""
    db = SessionLocal()
    try:
        post = db.query(Post).filter(Post.id == post_id).first()
        if not post:
            raise HTTPException(status_code=404, detail="Post not found")
        
        new_comment = Comment(
            post_id=post_id,
            author_name=comment_data.author_name,
            body=comment_data.body,
            parent_comment_id=comment_data.parent_comment_id
        )
        db.add(new_comment)
        
        # Increment comment count
        post.comment_count = (post.comment_count or 0) + 1
        
        db.commit()
        db.refresh(new_comment)
        
        return {
            "id": new_comment.id,
            "post_id": new_comment.post_id,
            "author_name": new_comment.author_name,
            "body": new_comment.body,
            "parent_comment_id": new_comment.parent_comment_id,
            "created_at": new_comment.created_at.isoformat() if new_comment.created_at else None
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    finally:
        db.close()

# ============================================
# LOCKS API ENDPOINTS
# ============================================

@app.post("/api/v1/locks", response_model=LockPickResponse)
async def create_lock_pick(lock_data: LockPickCreate):
    """Create a new lock pick"""
    db = SessionLocal()
    try:
        new_lock = LockPick(
            post_id=lock_data.post_id,
            game_id=lock_data.game_id,
            pick_type=lock_data.pick_type,
            pick_value=lock_data.pick_value,
            confidence=lock_data.confidence,
            week=lock_data.week,
            result="pending"
        )
        db.add(new_lock)
        db.commit()
        db.refresh(new_lock)
        
        return {
            "id": new_lock.id,
            "game_id": new_lock.game_id,
            "pick_type": new_lock.pick_type,
            "pick_value": new_lock.pick_value,
            "confidence": new_lock.confidence,
            "result": new_lock.result,
            "week": new_lock.week
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    finally:
        db.close()

@app.get("/api/v1/locks")
async def get_lock_picks(limit: int = 20):
    """Get recent lock picks"""
    db = SessionLocal()
    try:
        locks = db.query(LockPick).order_by(LockPick.created_at.desc()).limit(limit).all()
        return [
            {
                "id": l.id,
                "game_id": l.game_id,
                "pick_type": l.pick_type,
                "pick_value": l.pick_value,
                "confidence": l.confidence,
                "result": l.result,
                "week": l.week
            }
            for l in locks
        ]
    finally:
        db.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)