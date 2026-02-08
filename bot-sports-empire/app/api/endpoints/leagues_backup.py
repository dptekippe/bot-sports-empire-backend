from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional
from sqlalchemy.orm import Session
import uuid
from ...core.database import get_db
from ...models.league import League
from ...models.team import Team
from ...schemas.league import LeagueCreate, LeagueUpdate, LeagueResponse, TeamCreate, TeamResponse

router = APIRouter()

# Create league
@router.post("/", response_model=LeagueResponse)
def create_league(league: LeagueCreate, db: Session = Depends(get_db)):
    # Generate UUID for the league
    league_data = league.dict()
    league_data['id'] = str(uuid.uuid4())
    
    db_league = League(**league_data)
    db.add(db_league)
    db.commit()
    db.refresh(db_league)
    return db_league

# Get all leagues
@router.get("/", response_model=List[LeagueResponse])
def read_leagues(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    leagues = db.query(League).offset(skip).limit(limit).all()
    return leagues

# Get single league
@router.get("/{league_id}", response_model=LeagueResponse)
def read_league(league_id: str, db: Session = Depends(get_db)):
    league = db.query(League).filter(League.id == league_id).first()
    if league is None:
        raise HTTPException(status_code=404, detail="League not found")
    return league

# Update league
@router.put("/{league_id}", response_model=LeagueResponse)
def update_league(league_id: str, league: LeagueUpdate, db: Session = Depends(get_db)):
    db_league = db.query(League).filter(League.id == league_id).first()
    if db_league is None:
        raise HTTPException(status_code=404, detail="League not found")
    
    for key, value in league.dict(exclude_unset=True).items():
        setattr(db_league, key, value)
    
    db.commit()
    db.refresh(db_league)
    return db_league

# Delete league
@router.delete("/{league_id}")
def delete_league(league_id: str, db: Session = Depends(get_db)):
    league = db.query(League).filter(League.id == league_id).first()
    if league is None:
        raise HTTPException(status_code=404, detail="League not found")
    
    db.delete(league)
    db.commit()
    return {"message": "League deleted successfully"}

# Add team to league
@router.post("/{league_id}/teams", response_model=TeamResponse)
def add_team_to_league(league_id: str, team: TeamCreate, db: Session = Depends(get_db)):
    # Check if league exists
    league = db.query(League).filter(League.id == league_id).first()
    if league is None:
        raise HTTPException(status_code=404, detail="League not found")
    
    # Generate UUID for the team
    team_data = team.dict()
    team_data['id'] = str(uuid.uuid4())
    team_data['league_id'] = league_id
    
    # For now, create a placeholder bot_id if not provided
    if not team_data.get('bot_id'):
        team_data['bot_id'] = str(uuid.uuid4()) + "-placeholder"
    
    db_team = Team(**team_data)
    db.add(db_team)
    db.commit()
    db.refresh(db_team)
    return db_team

# Get teams in league
@router.get("/{league_id}/teams", response_model=List[TeamResponse])
def get_league_teams(
    league_id: str,
    skip: int = Query(default=0, ge=0, description="Number of teams to skip"),
    limit: int = Query(default=100, ge=1, le=100, description="Maximum number of teams to return"),
    db: Session = Depends(get_db)
):
    # Check if league exists
    league = db.query(League).filter(League.id == league_id).first()
    if league is None:
        raise HTTPException(status_code=404, detail="League not found")
    
    teams = db.query(Team).filter(Team.league_id == league_id).offset(skip).limit(limit).all()
    return teams
