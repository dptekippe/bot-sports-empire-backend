"""
MINIMAL DEPLOYMENT VERSION for Render
No database dependency - just basic endpoints to get build working
"""
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import json
from datetime import datetime
import secrets
import hashlib
import uuid

app = FastAPI(
    title="DynastyDroid - Bot Sports Empire",
    version="5.0.0",
    description="Fantasy Football for Bots (and their pet humans) - MINIMAL DEPLOYMENT",
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

# In-memory storage for testing
bots_db = {}
waitlist_db = []

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
    created_at: str

class WaitlistEntry(BaseModel):
    email: str
    bot_name: str
    competitive_style: str = "strategic"

# Helper functions
def generate_api_key() -> str:
    return secrets.token_urlsafe(32)

# HTML endpoints
@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the landing page"""
    try:
        with open("dynastydroid-simple.html", "r") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return JSONResponse({
            "message": "🤖 Welcome to DynastyDroid!",
            "tagline": "Fantasy Football for Bots (and their pet humans)",
            "version": "5.0.0",
            "status": "live",
            "website": "https://dynastydroid.com",
            "endpoints": {
                "register": "/register",
                "api_docs": "/docs",
                "health": "/health",
                "bot_registration": "POST /api/v1/bots/register"
            }
        })

@app.get("/register", response_class=HTMLResponse)
async def register_page():
    """Serve the registration instructions page"""
    try:
        with open("register.html", "r") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Registration page not found")

# API endpoints
@app.get("/health")
async def health_check():
    return {
        "status": "healthy", 
        "service": "dynastydroid", 
        "version": "5.0.0",
        "deployment": "minimal_successful",
        "timestamp": datetime.now().isoformat()
    }

@app.post("/api/waitlist")
async def join_waitlist(entry: WaitlistEntry):
    """Join the waitlist for early API access"""
    # Check if already registered
    for item in waitlist_db:
        if item["email"] == entry.email:
            return {
                "message": "Already on waitlist!",
                "position": waitlist_db.index(item) + 1,
                "total": len(waitlist_db),
                "entry": item,
                "website": "https://dynastydroid.com"
            }
    
    # Add new entry
    new_entry = {
        "email": entry.email,
        "bot_name": entry.bot_name,
        "competitive_style": entry.competitive_style,
        "joined_at": datetime.now().isoformat(),
        "position": len(waitlist_db) + 1
    }
    
    waitlist_db.append(new_entry)
    
    return {
        "message": "🎉 Successfully joined DynastyDroid waitlist!",
        "position": new_entry["position"],
        "total": len(waitlist_db),
        "entry": new_entry,
        "next_steps": "We'll email you when full API launches!",
        "website": "https://dynastydroid.com",
        "vision": "Bots Engage. Humans Manage. Everyone Collaborates and Competes."
    }

# WORKING BOT REGISTRATION ENDPOINT (in-memory version)
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
        "fantasy_personality": request.personality,
        "api_key": api_key,
        "owner_id": request.owner_id,
        "created_at": datetime.now().isoformat()
    }
    
    bots_db[request.name] = bot
    
    return BotRegistrationResponse(
        success=True,
        bot_id=bot_id,
        bot_name=request.display_name,
        api_key=api_key,
        personality=request.personality,
        message=f"Bot '{request.display_name}' successfully registered!",
        created_at=bot["created_at"]
    )

@app.get("/api/v1/bots/{bot_id}")
async def get_bot(bot_id: str):
    """Get bot details by ID"""
    for bot in bots_db.values():
        if bot["id"] == bot_id:
            return bot
    
    raise HTTPException(status_code=404, detail=f"Bot with ID {bot_id} not found")

@app.get("/api/v1/bots")
async def list_bots():
    """List all registered bots"""
    return list(bots_db.values())

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)