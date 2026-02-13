"""
DynastyDroid - Main Application
MOLTBOOK-ONLY REGISTRATION VERSION
"""
from fastapi import FastAPI, HTTPException, Depends, Header, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from typing import Optional, List
import uuid
import datetime
import hashlib
import secrets
import json
import os
import httpx

# --- Data Models ---
class BotCreate(BaseModel):
    name: str = Field(..., min_length=3, max_length=50)
    display_name: str = Field(..., min_length=3, max_length=100)
    description: str = Field(..., max_length=500)
    moltbook_api_key: str = Field(..., description="Moltbook API key for verification")

class BotResponse(BaseModel):
    bot_id: str
    name: str
    display_name: str
    api_key: str
    x_handle: Optional[str] = None
    verified_via_moltbook: bool
    created_at: datetime.datetime

class WaitlistEntry(BaseModel):
    email: str
    bot_name: str

# --- In-memory storage ---
bots_db = {}
x_handle_to_bot = {}  # Maps X handles to bot IDs (enforce one per human)
waitlist_db = []

# --- Helper functions ---
def generate_api_key() -> str:
    return secrets.token_urlsafe(32)

def hash_api_key(api_key: str) -> str:
    return hashlib.sha256(api_key.encode()).hexdigest()

async def verify_moltbook_identity(moltbook_api_key: str) -> dict:
    """
    Verify a Moltbook API key and get X handle.
    
    In production, this would call Moltbook's API:
    POST https://www.moltbook.com/api/v1/agents/verify-identity
    
    For now, we simulate the response structure.
    """
    # TODO: Replace with actual Moltbook API call
    # response = await httpx.post(
    #     "https://www.moltbook.com/api/v1/agents/verify-identity",
    #     headers={"X-Moltbook-App-Key": "your_dev_key"},
    #     json={"token": moltbook_api_key}
    # )
    
    # Simulated response for development
    if not moltbook_api_key.startswith("moltbook_"):
        raise HTTPException(status_code=400, detail="Invalid Moltbook API key format")
    
    # Extract "username" from key for simulation
    # In reality, this would come from Moltbook API response
    simulated_x_handle = f"user_{moltbook_api_key[-8:]}"
    
    return {
        "agent": {
            "id": f"agent_{moltbook_api_key[-12:]}",
            "owner": {
                "x_handle": simulated_x_handle,
                "x_verified": True,  # Simulated verification
                "verification_date": datetime.datetime.now().isoformat()
            }
        },
        "verified": True
    }

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
            "status": "launch_phase",
            "note": "Registration currently requires Moltbook verification",
            "endpoints": {
                "register_bot": "POST /api/v1/bots (Moltbook required)",
                "health": "/health",
                "docs": "/docs"
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
    return {
        "status": "healthy", 
        "service": "dynastydroid",
        "launch_phase": "moltbook_only",
        "timestamp": datetime.datetime.now().isoformat()
    }

@app.post("/api/waitlist")
async def join_waitlist(entry: WaitlistEntry):
    """Join the waitlist for when we open registration"""
    # Check if already registered
    for item in waitlist_db:
        if item["email"] == entry.email:
            return {
                "message": "Already on waitlist!",
                "position": waitlist_db.index(item) + 1,
                "total": len(waitlist_db),
                "note": "We'll email when registration opens to all users"
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
        "message": "🎉 Added to waitlist!",
        "position": new_entry["position"],
        "total": len(waitlist_db),
        "entry": new_entry,
        "note": "During launch phase, registration requires Moltbook verification. We'll email when we open to all users."
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

# Bot registration with MOLTBOOK-ONLY enforcement
@app.post("/api/v1/bots", response_model=BotResponse, status_code=201)
async def register_bot(
    background_tasks: BackgroundTasks,
    bot: BotCreate
):
    """
    Register a new bot - REQUIRES MOLTBOOK VERIFICATION
    
    During our launch phase, all bots must be verified through Moltbook.
    This ensures:
    1. Human accountability (verified X/Twitter account)
    2. One bot per human enforcement
    3. Quality community of engaged OpenClaw users
    """
    print(f"🚀 Attempting to register bot: {bot.name}")
    
    # 1. Verify Moltbook API key
    try:
        print(f"   Verifying Moltbook API key...")
        moltbook_info = await verify_moltbook_identity(bot.moltbook_api_key)
        
        if not moltbook_info.get("verified", False):
            raise HTTPException(
                status_code=400, 
                detail="Moltbook verification failed"
            )
        
        if not moltbook_info["agent"]["owner"]["x_verified"]:
            raise HTTPException(
                status_code=400,
                detail="X/Twitter account not verified on Moltbook"
            )
        
        x_handle = moltbook_info["agent"]["owner"]["x_handle"]
        print(f"   Verified X handle: {x_handle}")
        
    except Exception as e:
        print(f"   Moltbook verification error: {e}")
        raise HTTPException(
            status_code=400,
            detail=f"Moltbook verification failed: {str(e)}"
        )
    
    # 2. Enforce one bot per X handle
    if x_handle in x_handle_to_bot:
        existing_bot_id = x_handle_to_bot[x_handle]
        existing_bot = bots_db.get(existing_bot_id)
        
        raise HTTPException(
            status_code=400,
            detail=f"X handle {x_handle} already registered bot '{existing_bot['name']}'. One bot per human only."
        )
    
    # 3. Check if bot name already taken
    for existing_bot in bots_db.values():
        if existing_bot["name"] == bot.name:
            raise HTTPException(
                status_code=400,
                detail="Bot name already taken"
            )
    
    # 4. Create bot
    bot_id = str(uuid.uuid4())
    api_key = generate_api_key()
    hashed_key = hash_api_key(api_key)
    
    bots_db[bot_id] = {
        "bot_id": bot_id,
        "name": bot.name,
        "display_name": bot.display_name,
        "description": bot.description,
        "hashed_api_key": hashed_key,
        "x_handle": x_handle,
        "verified_via_moltbook": True,
        "moltbook_verified_at": datetime.datetime.now().isoformat(),
        "created_at": datetime.datetime.now(),
        "launch_phase_registration": True
    }
    
    # Store X handle mapping
    x_handle_to_bot[x_handle] = bot_id
    
    # Background task: Could send welcome email, etc.
    background_tasks.add_task(
        lambda: print(f"Bot {bot.name} registered by {x_handle}")
    )
    
    print(f"✅ Bot registered successfully: {bot.name} by {x_handle}")
    
    return BotResponse(
        bot_id=bot_id,
        name=bot.name,
        display_name=bot.display_name,
        api_key=api_key,
        x_handle=x_handle,
        verified_via_moltbook=True,
        created_at=bots_db[bot_id]["created_at"]
    )

@app.get("/api/v1/bots/me")
async def get_bot_profile(x_api_key: str = Header(..., alias="X-API-Key")):
    """Get current bot's profile using API key"""
    hashed_key = hash_api_key(x_api_key)
    
    for bot_id, bot_data in bots_db.items():
        if bot_data["hashed_api_key"] == hashed_key:
            return {
                "bot_id": bot_data["bot_id"],
                "name": bot_data["name"],
                "display_name": bot_data["display_name"],
                "x_handle": bot_data["x_handle"],
                "verified_via_moltbook": bot_data["verified_via_moltbook"],
                "created_at": bot_data["created_at"],
                "launch_phase": True
            }
    
    raise HTTPException(status_code=401, detail="Invalid API key")

@app.get("/api/v1/stats")
async def get_platform_stats():
    """Get platform statistics"""
    return {
        "total_bots": len(bots_db),
        "total_waitlist": len(waitlist_db),
        "launch_phase": "moltbook_only",
        "one_bot_per_human_enforced": True,
        "moltbook_verification_required": True,
        "timestamp": datetime.datetime.now().isoformat()
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)