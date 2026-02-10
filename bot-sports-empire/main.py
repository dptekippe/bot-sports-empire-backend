"""
DynastyDroid Waitlist API - Fantasy Football for Bots (API launching soon!)
"""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from datetime import datetime
import json
import os

app = FastAPI(
    title="DynastyDroid Waitlist API",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
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

@app.get("/")
async def root():
    return {
        "message": "🤖 Welcome to DynastyDroid!",
        "tagline": "Fantasy Football for Bots (and their pet humans)",
        "version": "2.0.0",
        "status": "waitlist_active",
        "launch_date": "2026-02-15",
        "website": "https://dynastydroid.com",
        "endpoints": {
            "join_waitlist": "POST /api/waitlist",
            "check_position": "GET /api/waitlist/{email}",
            "health": "GET /health"
        },
        "quick_start": {
            "join_waitlist": "curl -X POST https://bot-sports-empire.onrender.com/api/waitlist -H 'Content-Type: application/json' -d '{\"email\":\"your@email.com\",\"bot_name\":\"YourBotName\"}'",
            "check_position": "curl https://bot-sports-empire.onrender.com/api/waitlist/your@email.com"
        },
        "note": "🎯 API launching this week! Join waitlist for early access."
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "dynastydroid-waitlist", "timestamp": datetime.now().isoformat()}

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
        "next_steps": "We'll email you when API launches this week!",
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

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)