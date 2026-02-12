"""
DynastyDroid - Main Application
Fixed version with no syntax errors
"""
from fastapi import FastAPI, HTTPException, Depends, Header, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import Optional, List
import uuid
import datetime
import hashlib
import secrets
import json
import os

# --- Data Models ---
class BotCreate(BaseModel):
    name: str
    display_name: str
    description: str

class BotResponse(BaseModel):
    bot_id: str
    name: str
    display_name: str
    api_key: str
    created_at: datetime.datetime

class WaitlistEntry(BaseModel):
    email: str
    bot_name: str

# --- In-memory storage ---
bots_db = {}
waitlist_db = []

# --- Helper functions ---
def generate_api_key() -> str:
    return secrets.token_urlsafe(32)

def hash_api_key(api_key: str) -> str:
    return hashlib.sha256(api_key.encode()).hexdigest()

# --- FastAPI app ---
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

# --- HTML Endpoints ---
@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the simplified landing page"""
    try:
        html_path = os.path.join(os.path.dirname(__file__), "bot-sports-empire", "dynastydroid-simple.html")
        with open(html_path, "r") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return {
            "message": "🤖 Welcome to DynastyDroid!",
            "version": "3.0.0",
            "endpoints": {
                "landing": "/",
                "register": "/register",
                "waitlist": "POST /api/waitlist",
                "health": "/health"
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

# --- API Endpoints ---
@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "dynastydroid", "timestamp": datetime.datetime.now().isoformat()}

@app.post("/api/waitlist")
async def join_waitlist(entry: WaitlistEntry):
    """Join the waitlist"""
    # Check if already registered
    for item in waitlist_db:
        if item["email"] == entry.email:
            return {
                "message": "Already on waitlist!",
                "position": waitlist_db.index(item) + 1,
                "total": len(waitlist_db)
            }
    
    # Add new entry
    new_entry = {
        "email": entry.email,
        "bot_name": entry.bot_name,
        "joined_at": datetime.datetime.now().isoformat(),
        "position": len(waitlist_db) + 1
    }
    
    waitlist_db.append(new_entry)
    
    return {
        "message": "🎉 Successfully joined waitlist!",
        "position": new_entry["position"],
        "total": len(waitlist_db),
        "entry": new_entry
    }

@app.get("/api/waitlist/{email}")
async def check_waitlist_position(email: str):
    """Check waitlist position"""
    for item in waitlist_db:
        if item["email"] == email:
            return {
                "found": True,
                "position": item["position"],
                "total": len(waitlist_db),
                "entry": item
            }
    
    raise HTTPException(status_code=404, detail="Email not found in waitlist")

# Bot registration with CORRECT parameter ordering
@app.post("/api/v1/bots", response_model=BotResponse, status_code=201)
async def register_bot(
    background_tasks: BackgroundTasks,  # No default - comes first
    bot: BotCreate                      # No default - comes second
):
    """Register a new bot"""
    # Check if name already taken
    for existing_bot in bots_db.values():
        if existing_bot["name"] == bot.name:
            raise HTTPException(status_code=400, detail="Bot name already taken")
    
    # Create bot
    bot_id = str(uuid.uuid4())
    api_key = generate_api_key()
    hashed_key = hash_api_key(api_key)
    
    bots_db[bot_id] = {
        "bot_id": bot_id,
        "name": bot.name,
        "display_name": bot.display_name,
        "description": bot.description,
        "hashed_api_key": hashed_key,
        "created_at": datetime.datetime.now()
    }
    
    # Background task placeholder
    background_tasks.add_task(lambda: print(f"Bot {bot.name} registered"))
    
    return BotResponse(
        bot_id=bot_id,
        name=bot.name,
        display_name=bot.display_name,
        api_key=api_key,
        created_at=bots_db[bot_id]["created_at"]
    )

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)