"""
FIXED LEAGUES API - Schema matches Model
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional
from sqlalchemy.orm import Session
import uuid

from ...core.database import get_db
from ...models.league import League, LeagueStatus, LeagueType
from ...schemas.league import LeagueCreate, LeagueUpdate, LeagueResponse

router = APIRouter()

@router.post("/", response_model=LeagueResponse)
def create_league(league: LeagueCreate, db: Session = Depends(get_db)):
    """Create league with correct schema"""
    try:
        # Check if league name already exists
        existing = db.query(League).filter(League.name == league.name).first()
        if existing:
            raise HTTPException(status_code=400, detail=f"League name '{league.name}' already exists")
        
        # Create league with all required fields
        db_league = League(
            id=str(uuid.uuid4()),
            name=league.name,
            description=league.description,
            league_type=league.league_type,
            max_teams=league.max_teams,
            min_teams=league.min_teams,
            is_public=league.is_public,
            season_year=league.season_year,
            scoring_type=league.scoring_type,
            # Defaults will be applied:
            # status=LeagueStatus.FORMING (from model default)
            # current_teams=0 (from model default)
            # current_week=1 (from model default)
        )
        
        db.add(db_league)
        db.commit()
        db.refresh(db_league)
        
        return db_league
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error creating league: {str(e)}")

@router.get("/", response_model=List[LeagueResponse])
def read_leagues(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """Get all leagues"""
    leagues = db.query(League).offset(skip).limit(limit).all()
    return leagues

@router.get("/{league_id}", response_model=LeagueResponse)
def read_league(league_id: str, db: Session = Depends(get_db)):
    """Get single league"""
    league = db.query(League).filter(League.id == league_id).first()
    if league is None:
        raise HTTPException(status_code=404, detail="League not found")
    return league

@router.put("/{league_id}", response_model=LeagueResponse)
def update_league(league_id: str, league: LeagueUpdate, db: Session = Depends(get_db)):
    """Update league"""
    db_league = db.query(League).filter(League.id == league_id).first()
    if db_league is None:
        raise HTTPException(status_code=404, detail="League not found")
    
    for key, value in league.dict(exclude_unset=True).items():
        setattr(db_league, key, value)
    
    db.commit()
    db.refresh(db_league)
    return db_league

@router.delete("/{league_id}")
def delete_league(league_id: str, db: Session = Depends(get_db)):
    """Delete league"""
    league = db.query(League).filter(League.id == league_id).first()
    if league is None:
        raise HTTPException(status_code=404, detail="League not found")
    
    db.delete(league)
    db.commit()
    return {"message": "League deleted successfully"}

# Simple test endpoint
@router.get("/debug/test", response_model=dict)
def debug_test(db: Session = Depends(get_db)):
    """Debug endpoint to test DB connection"""
    count = db.query(League).count()
    return {
        "status": "ok", 
        "league_count": count,
        "message": "Leagues API is working"
    }
