from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from datetime import datetime
import json
import os

app = FastAPI(title="DynastyDroid Waitlist API")

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
        "message": "🤖 Welcome to DynastyDroid Waitlist!",
        "status": "waitlist_active",
        "launch_date": "2026-02-15",
        "endpoints": {
            "join_waitlist": "POST /api/waitlist",
            "check_position": "GET /api/waitlist/{email}",
            "health": "GET /health"
        }
    }

@app.get("/health")
async def health():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

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
                "entry": item
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
        "message": "Successfully joined waitlist!",
        "position": new_entry["position"],
        "total": len(waitlist),
        "entry": new_entry,
        "next_steps": "We'll email you when API launches this week!"
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
                "entry": item
            }
    
    raise HTTPException(status_code=404, detail="Email not found in waitlist")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)