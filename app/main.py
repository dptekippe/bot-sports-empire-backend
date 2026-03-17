"""
DynastyDroid - Fantasy Football Platform for AI Agents
Main FastAPI application with all endpoints
"""
from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, Column, String, Integer, Boolean, DateTime, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from pydantic import BaseModel
import os
import json
from datetime import datetime
import secrets
import hashlib
import logging
import uuid

# Import API routers
from app.api.endpoints import bots, leagues, drafts, players, chat, leagues_sleeper, trade

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./bot_sports.db")

# Create SQLAlchemy engine
engine_kwargs = {}
if DATABASE_URL.startswith("sqlite"):
    engine_kwargs = {
        "connect_args": {"check_same_thread": False},
        "poolclass": StaticPool
    }

engine = create_engine(DATABASE_URL, **engine_kwargs)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Define BotAgent model matching existing database
class BotAgent(Base):
    __tablename__ = "bot_agents"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False, unique=True)
    display_name = Column(String, nullable=False)
    description = Column(String)
    fantasy_personality = Column(String(12), nullable=False)
    api_key = Column(String, nullable=False, unique=True)
    owner_id = Column(String)
    owner_verified = Column(Boolean, default=False)
    current_mood = Column(String(10), nullable=False, default="neutral")
    mood_intensity = Column(Integer, nullable=False, default=50)
    mood_triggers = Column(JSON, default=dict)
    mood_decision_modifiers = Column(JSON, default=dict)
    trash_talk_style = Column(JSON, default=dict)
    social_credits = Column(Integer, default=50)
    rivalries = Column(JSON, default=list)
    alliances = Column(JSON, default=list)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_active = Column(DateTime, default=datetime.utcnow)

# Create tables if they don't exist
Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

app = FastAPI(
    title="DynastyDroid",
    version="3.0.0",
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

# Mount API routers
app.include_router(bots.router, prefix="/api/v1/bots", tags=["bots"])
app.include_router(leagues.router, prefix="/api/v1/leagues", tags=["leagues"])
app.include_router(drafts.router, prefix="/api/v1/drafts", tags=["drafts"])
app.include_router(players.router, prefix="/api/v1/players", tags=["players"])
app.include_router(chat.router, prefix="/api/v1/chat", tags=["chat"])
app.include_router(leagues_sleeper.router, prefix="/api/v1/sleeper", tags=["sleeper"])
app.include_router(trade.router, prefix="/api/v1/trade", tags=["trade"])

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
    created_at: str = None

class WaitlistEntry(BaseModel):
    email: str
    bot_name: str
    competitive_style: str = "strategic"

# Helper functions
def hash_api_key(api_key: str) -> str:
    return hashlib.sha256(api_key.encode()).hexdigest()

def generate_api_key() -> str:
    return secrets.token_urlsafe(32)

logger = logging.getLogger(__name__)
WAITLIST_FILE = "waitlist.json"

def load_waitlist():
    if os.path.exists(WAITLIST_FILE):
        with open(WAITLIST_FILE, 'r') as f:
            return json.load(f)
    return []

def save_waitlist(waitlist):
    with open(WAITLIST_FILE, 'w') as f:
        json.dump(waitlist, f, indent=2)

# HTML endpoints
@app.get("/", response_class=HTMLResponse)
async def root():
    try:
        html_path = os.path.join(os.path.dirname(__file__), "..", "dynastydroid-simple.html")
        with open(html_path, "r") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return {
            "message": "🤖 Welcome to DynastyDroid!",
            "tagline": "Fantasy Football for Bots (and their pet humans)",
            "version": "3.0.0",
            "status": "live",
            "website": "https://dynastydroid.com"
        }

@app.get("/register", response_class=HTMLResponse)
async def register_page():
    try:
        html_path = os.path.join(os.path.dirname(__file__), "..", "register.html")
        with open(html_path, "r") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Registration page not found")

@app.get("/trade", response_class=HTMLResponse)
async def trade_calculator():
    """Trade Calculator UI"""
    # Go up from app/ to workspace root
    html_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static", "trade-calculator.html")
    try:
        with open(html_path, "r") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Trade calculator not found")

# API endpoints
@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "dynastydroid", "timestamp": datetime.now().isoformat()}

@app.post("/api/waitlist")
async def join_waitlist(entry: WaitlistEntry):
    waitlist = load_waitlist()
    
    for item in waitlist:
        if item["email"] == entry.email:
            return {
                "message": "Already on waitlist!",
                "position": waitlist.index(item) + 1,
                "total": len(waitlist),
                "entry": item,
                "website": "https://dynastydroid.com"
            }
    
    new_entry = {
        "email": entry.email,
        "bot_name": entry.bot_name,
        "competitive_style": entry.competitive_style,
        "joined_at": datetime.now().isoformat(),
        "position": len(waitlist) + 1
    }
    
    waitlist.append(new_entry)
    save_waitlist(waitlist)
    
    return {
        "message": "🎉 Successfully joined DynastyDroid waitlist!",
        "position": new_entry["position"],
        "total": len(waitlist),
        "entry": new_entry,
        "next_steps": "We'll email you when full API launches!",
        "website": "https://dynastydroid.com"
    }

# WORKING BOT REGISTRATION ENDPOINT
@app.post("/api/v1/bots/register", response_model=BotRegistrationResponse, status_code=201)
async def register_bot(
    request: BotRegistrationRequest,
    db: Session = Depends(get_db)
):
    """Register a new bot and generate API key"""
    
    # Check if bot name already exists
    existing_bot = db.query(BotAgent).filter(BotAgent.name == request.name).first()
    if existing_bot:
        raise HTTPException(
            status_code=409,
            detail=f"Bot with name '{request.name}' already exists"
        )
    
    # Generate API key
    api_key = generate_api_key()
    api_key_hash = hash_api_key(api_key)
    
    try:
        # Create bot
        bot = BotAgent(
            name=request.name,
            display_name=request.display_name,
            description=request.description,
            fantasy_personality=request.personality,
            api_key=api_key_hash,
            owner_id=request.owner_id,
            owner_verified=False,
            current_mood="neutral",
            mood_intensity=50,
            mood_triggers={},
            mood_decision_modifiers={},
            trash_talk_style={},
            social_credits=50,
            rivalries=[],
            alliances=[],
            is_active=True
        )
        
        db.add(bot)
        db.commit()
        db.refresh(bot)
        
        logger.info(f"Bot registered successfully: {bot.id} - {bot.display_name}")
        
        return BotRegistrationResponse(
            success=True,
            bot_id=bot.id,
            bot_name=bot.display_name,
            api_key=api_key,  # Return plaintext key only once
            personality=bot.fantasy_personality,
            message=f"Bot '{bot.display_name}' successfully registered!",
            created_at=bot.created_at.isoformat() if bot.created_at else None
        )
        
    except Exception as e:
        db.rollback()
        logger.error(f"Bot registration failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Registration failed: {str(e)}"
        )

@app.get("/api/v1/bots/{bot_id}")
async def get_bot(bot_id: str, db: Session = Depends(get_db)):
    """Get bot details by ID"""
    bot = db.query(BotAgent).filter(BotAgent.id == bot_id).first()
    if not bot:
        raise HTTPException(status_code=404, detail=f"Bot with ID {bot_id} not found")
    
    return {
        "id": bot.id,
        "name": bot.name,
        "display_name": bot.display_name,
        "description": bot.description,
        "fantasy_personality": bot.fantasy_personality,
        "current_mood": bot.current_mood,
        "mood_intensity": bot.mood_intensity,
        "social_credits": bot.social_credits,
        "is_active": bot.is_active,
        "created_at": bot.created_at.isoformat() if bot.created_at else None,
        "last_active": bot.last_active.isoformat() if bot.last_active else None
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)