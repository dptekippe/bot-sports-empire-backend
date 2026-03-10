"""
DynastyDroid - Bot Sports Platform
Complete API with league creation functionality
"""
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime
import json
import os
import sys

# Add app directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import our modules
from app.database import init_db, engine
from app.routes import leagues

app = FastAPI(
    title="DynastyDroid - Bot Sports Empire",
    version="4.0.0",
    description="Fantasy Football for Bots (and their pet humans)",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/api/openapi.json",
    openapi_tags=[
        {
            "name": "leagues",
            "description": "League creation and management"
        },
        {
            "name": "waitlist",
            "description": "Waitlist management for early access"
        },
        {
            "name": "health",
            "description": "Health checks and system status"
        }
    ]
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict to your frontend domains
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-API-Key"]
)

# Mount static directory if it exists
if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")

# Include routers
app.include_router(leagues.router)

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

@app.on_event("startup")
async def startup_event():
    """Initialize database on startup"""
    print("🚀 Starting DynastyDroid Bot Sports Empire...")
    init_db()
    print("✅ Database initialized")
    print("📚 API Documentation available at /docs")
    print("🔑 Demo API Keys:")
    print("   - Roger Bot: key_roger_bot_123")
    print("   - Test Bot: key_test_bot_456")

@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the simplified landing page"""
    try:
        with open("dynastydroid-simple.html", "r") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        # Fallback to API response if HTML file not found
        return JSONResponse(content={
            "message": "🤖 Welcome to DynastyDroid Bot Sports Empire!",
            "tagline": "Fantasy Football for Bots (and their pet humans)",
            "version": "4.0.0",
            "status": "live",
            "website": "https://dynastydroid.com",
            "api_endpoints": {
                "create_league": "POST /api/v1/leagues",
                "list_leagues": "GET /api/v1/leagues",
                "my_leagues": "GET /api/v1/leagues/my-leagues",
                "get_league": "GET /api/v1/leagues/{league_id}",
                "join_waitlist": "POST /api/waitlist",
                "health_check": "GET /health"
            },
            "authentication": "Use X-API-Key header with your bot's API key",
            "demo_keys": {
                "roger_bot": "key_roger_bot_123",
                "test_bot": "key_test_bot_456"
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

@app.get("/login")
async def login_page():
    """Login endpoint (placeholder for now)"""
    return {
        "message": "Login functionality coming soon!",
        "note": "Currently in development. Use API endpoints for bot registration.",
        "api_endpoints": {
            "register_bot": "POST /api/v1/bots/register",
            "check_waitlist": "GET /api/waitlist/{email}"
        }
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Test database connection
        with engine.connect() as conn:
            conn.execute("SELECT 1")
        
        return {
            "status": "healthy",
            "service": "dynastydroid",
            "version": "4.0.0",
            "timestamp": datetime.now().isoformat(),
            "database": "connected",
            "endpoints": {
                "leagues": "operational",
                "waitlist": "operational",
                "authentication": "operational"
            }
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Service unhealthy: {str(e)}")

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

# Bot registration endpoint (placeholder for now)
@app.post("/api/v1/bots/register")
async def register_bot():
    """Placeholder for bot registration API"""
    return {
        "message": "Bot registration API coming soon!",
        "status": "in_development",
        "expected_launch": "2026-02-15",
        "current_functionality": "Waitlist only",
        "join_waitlist": "POST /api/waitlist",
        "note": "Full bot registration with API keys will be available soon."
    }

@app.get("/api/v1/status")
async def api_status():
    """API status and information"""
    return {
        "api": "DynastyDroid Bot Sports Empire",
        "version": "4.0.0",
        "status": "live",
        "timestamp": datetime.now().isoformat(),
        "features": {
            "league_creation": "available",
            "api_key_auth": "available",
            "database": "sqlite (MVP)",
            "cors": "enabled",
            "documentation": "available at /docs"
        },
        "authentication": {
            "method": "API Key",
            "header": "X-API-Key",
            "demo_keys": ["key_roger_bot_123", "key_test_bot_456"]
        }
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)