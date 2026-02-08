#!/usr/bin/env python3
"""
Test script to debug hanging POST endpoint
"""
import sys
sys.path.append('.')

from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
import uvicorn
import uuid
import time

from app.core.database import get_db, engine, Base, SessionLocal
from app.models.league import League

# Create minimal app
app = FastAPI()

@app.get("/test")
async def test():
    return {"status": "ok", "time": time.time()}

@app.post("/test-post")
async def test_post(data: dict):
    return {"status": "ok", "received": data, "time": time.time()}

@app.post("/test-db-post")
async def test_db_post(data: dict, db: Session = Depends(get_db)):
    """Test database write"""
    start = time.time()
    print(f"DEBUG [{start}]: Starting test_db_post")
    
    try:
        # Test simple query first
        count = db.query(League).count()
        print(f"DEBUG: League count: {count}")
        
        # Create simple league
        league_id = str(uuid.uuid4())
        league = League(
            id=league_id,
            name=f"Test League {int(time.time())}",
            sport="football",
            league_type="dynasty",
            status="forming",
            max_teams=12,
            is_public=True
        )
        
        print(f"DEBUG: Created league object")
        db.add(league)
        print(f"DEBUG: Added to session")
        db.commit()
        print(f"DEBUG: Committed")
        
        elapsed = time.time() - start
        return {
            "status": "success", 
            "league_id": league_id,
            "elapsed": elapsed,
            "league_count": count + 1
        }
        
    except Exception as e:
        print(f"DEBUG: Exception: {e}")
        db.rollback()
        return {"status": "error", "error": str(e)}

if __name__ == "__main__":
    print("Starting test server on http://0.0.0.0:8003")
    uvicorn.run(app, host="0.0.0.0", port=8003, log_level="info")
