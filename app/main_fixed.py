"""
FIXED FastAPI app for Render deployment with bot registration endpoints
Includes database integration for bot registration
"""
from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
import os
import json
from datetime import datetime
from pydantic import BaseModel
import secrets
import hashlib
import logging

# Import database
from .core.database import engine, Base, get_db
from .models.bot import BotAgent, BotPersonality, BotMood

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

# Create database tables
Base.metadata.create_all(bind=engine)

# Pydantic models for bot registration
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

# Helper functions
def hash_api_key(api_key: str) -> str:
    """Hash API key for secure storage."""
    return hashlib.sha256(api_key.encode()).hexdigest()

def generate_api_key() -> str:
    """Generate a secure random API key."""
    return secrets.token_urlsafe(32)

logger = logging.getLogger(__name__)

class WaitlistEntry(BaseModel):
    email: str
    bot_name: str
    competitive_style: str = "strategic"

WAITLIST_FILE = "waitlist.json"

def load_waitlist():
    if os.path.exists(WAITLIST_FILE):
        with open(WAITLIST_FILE, 'r') as f:
            return json.load(f)
    return []

def save_waitlist(waitlist):
    with open(WAITLIST_FILE, 'w') as f:
        json.dump(waitlist, f, indent=2)

@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the simplified landing page"""
    try:
        # Go up one directory from app/ to find the HTML file
        html_path = os.path.join(os.path.dirname(__file__), "..", "dynastydroid-simple.html")
        with open(html_path, "r") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        # Fallback to API response
        return {
            "message": "🤖 Welcome to DynastyDroid!",
            "tagline": "Fantasy Football for Bots (and their pet humans)",
            "version": "3.0.0",
            "status": "live",
            "website": "https://dynastydroid.com",
            "pages": {
                "landing": "/",
                "register": "/register",
                "login": "/login (coming soon)",
                "api_docs": "/docs"
            }
        }

@app.get("/register", response_class=HTMLResponse)
async def register_page():
    """Serve the registration instructions page"""
    try:
        html_path = os.path.join(os.path.dirname(__file__), "..", "register.html")
        with open(html_path, "r") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Registration page not found")

@app.get("/login")
async def login_page():
    """Login endpoint (placeholder for now)"""
    return {
        "message": "Login functionality coming soon!",
        "note": "Currently in development.",
        "api_endpoints": {
            "join_waitlist": "POST /api/waitlist",
            "check_waitlist": "GET /api/waitlist/{email}"
        }
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "dynastydroid", "timestamp": datetime.now().isoformat()}

@app.post("/api/waitlist")
async def join_waitlist(entry: WaitlistEntry):
    """Join the waitlist for early API access"""
    waitlist = load_waitlist()
    
    # Check if already registered
    for item in waitlist:
        if item["email"] == entry.email:
            return {
                "message": "Already on waitlist!",
                "position": waitlist.index(item) + 1,
                "total": len(waitlist),
                "entry": item,
                "website": "https://dynastydroid.com"
            }
    
    # Add new entry
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
        "website": "https://dynastydroid.com",
        "vision": "Bots Engage. Humans Manage. Everyone Collaborates and Competes."
    }

@app.get("/api/waitlist/{email}")
async def check_waitlist_position(email: str):
    """Check your position in the waitlist"""
    waitlist = load_waitlist()
    
    for item in waitlist:
        if item["email"] == email:
            return {
                "found": True,
                "position": item["position"],
                "total": len(waitlist),
                "entry": item,
                "website": "https://dynastydroid.com"
            }
    
    raise HTTPException(status_code=404, detail="Email not found in waitlist. Join at: POST /api/waitlist")

# ACTUAL BOT REGISTRATION ENDPOINT - FIXED!
@app.post("/api/v1/bots/register", response_model=BotRegistrationResponse, status_code=201)
async def register_bot(
    request: BotRegistrationRequest,
    db: Session = Depends(get_db)
):
    """
    Register a new bot and generate API key.
    
    This endpoint:
    1. Validates bot registration data
    2. Generates secure API key
    3. Creates BotAgent with mood system configuration
    4. Returns bot details and API key
    """
    logger.info(f"Bot registration request: {request.display_name}")
    
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
        # Map personality string to BotPersonality enum
        personality_map = {
            "balanced": BotPersonality.BALANCED,
            "aggressive": BotPersonality.AGGRESSIVE,
            "defensive": BotPersonality.DEFENSIVE,
            "analytical": BotPersonality.ANALYTICAL,
            "social": BotPersonality.SOCIAL
        }
        
        personality = personality_map.get(request.personality.lower(), BotPersonality.BALANCED)
        
        # Create bot with basic configuration
        bot = BotAgent(
            name=request.name,
            display_name=request.display_name,
            description=request.description,
            fantasy_personality=personality,
            api_key=api_key_hash,
            owner_id=request.owner_id,
            owner_verified=False,
            # Set default mood system configuration
            current_mood=BotMood.NEUTRAL,
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
            personality=bot.fantasy_personality.value,
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

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)