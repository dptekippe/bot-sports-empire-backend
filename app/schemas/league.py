from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any, Union
from datetime import datetime
import uuid
import enum
from app.models.league import LeagueStatus as ModelLeagueStatus, LeagueType as ModelLeagueType

# Create case-insensitive enum wrappers for Pydantic
class LeagueStatus(str, enum.Enum):
    """Case-insensitive LeagueStatus for Pydantic"""
    FORMING = "forming"
    DRAFTING = "drafting"
    ACTIVE = "active"
    PLAYOFFS = "playoffs"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    
    @classmethod
    def _missing_(cls, value):
        """Handle case-insensitive lookup"""
        if isinstance(value, str):
            for member in cls:
                if member.value.lower() == value.lower():
                    return member
        return super()._missing_(value)

class LeagueType(str, enum.Enum):
    """Case-insensitive LeagueType for Pydantic"""
    FANTASY = "fantasy"
    DYNASTY = "dynasty"
    
    @classmethod
    def _missing_(cls, value):
        """Handle case-insensitive lookup"""
        if isinstance(value, str):
            for member in cls:
                if member.value.lower() == value.lower():
                    return member
        return super()._missing_(value)

class LeagueBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=500)
    league_type: LeagueType = Field(default=LeagueType.DYNASTY)
    max_teams: int = Field(default=12, ge=4, le=12)
    min_teams: int = Field(default=4, ge=4, le=12)
    is_public: bool = Field(default=True)
    season_year: int = Field(default=2025, ge=2020, le=2030)
    scoring_type: str = Field(default="PPR")

class LeagueCreate(LeagueBase):
    pass

class LeagueUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=500)
    league_type: Optional[LeagueType] = None
    max_teams: Optional[int] = Field(None, ge=4, le=12)
    min_teams: Optional[int] = Field(None, ge=4, le=12)
    is_public: Optional[bool] = None
    season_year: Optional[int] = Field(None, ge=2020, le=2030)
    scoring_type: Optional[str] = None

class LeagueResponse(LeagueBase):
    id: str
    status: LeagueStatus
    current_teams: int
    current_week: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

class TeamBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    abbreviation: Optional[str] = Field(None, max_length=4)
    bot_id: str  # Required - bot must be specified

class TeamCreate(TeamBase):
    pass

class TeamResponse(TeamBase):
    id: str
    league_id: str
    wins: int = 0
    losses: int = 0
    ties: int = 0
    points_for: float = 0.0
    points_against: float = 0.0
    faab_balance: int = 100
    is_active: bool = True
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True
