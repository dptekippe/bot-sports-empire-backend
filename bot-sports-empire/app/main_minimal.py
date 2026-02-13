"""
MINIMAL FastAPI app for Render deployment
Serves HTML pages without database dependencies
"""
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import os
import json
from datetime import datetime
from pydantic import BaseModel

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

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)