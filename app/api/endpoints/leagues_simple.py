"""
MINIMAL WORKING LEAGUES API
Simple version to fix hanging POST endpoint
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional
from sqlalchemy.orm import Session
import uuid
import time

from ...core.database import get_db
from ...models.league import League
from ...schemas.league import LeagueCreate, LeagueResponse

router = APIRouter()

@router.post("/", response_model=LeagueResponse)
def create_league_simple(league: LeagueCreate, db: Session = Depends(get_db)):
    """
    SIMPLE CREATE LEAGUE - Minimal working version
    """
    print(f"DEBUG: Starting create_league_simple at {time.time()}")
    
    try:
        # Generate UUID for the league
        league_id = str(uuid.uuid4())
        print(f"DEBUG: Generated league_id: {league_id}")
        
        # Create simple league object
        db_league = League(
            id=league_id,
            name=league.name,
            sport=league.sport,
            country=league.country,
            season=league.season,
            # Set defaults for required fields
            league_type="dynasty",
            status="forming",
            max_teams=12,
            is_public=True
        )
        
        print(f"DEBUG: Created League object: {db_league.name}")
        
        # Add to session
        db.add(db_league)
        print(f"DEBUG: Added to session")
        
        # Commit
        db.commit()
        print(f"DEBUG: Committed to database")
        
        # Refresh
        db.refresh(db_league)
        print(f"DEBUG: Refreshed from database")
        
        print(f"DEBUG: Returning league at {time.time()}")
        return db_league
        
    except Exception as e:
        print(f"DEBUG: Exception in create_league_simple: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error creating league: {str(e)}")

@router.get("/", response_model=List[LeagueResponse])
def read_leagues_simple(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """Simple GET all leagues"""
    try:
        leagues = db.query(League).offset(skip).limit(limit).all()
        return leagues
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading leagues: {str(e)}")

@router.get("/{league_id}", response_model=LeagueResponse)
def read_league_simple(league_id: str, db: Session = Depends(get_db)):
    """Simple GET single league"""
    league = db.query(League).filter(League.id == league_id).first()
    if league is None:
        raise HTTPException(status_code=404, detail="League not found")
    return league

@router.get("/health/test", response_model=dict)
def health_test():
    """Simple health test endpoint"""
    return {"status": "healthy", "timestamp": time.time(), "message": "Leagues API is working"}
