"""
Player schemas for Bot Sports Empire.

Pydantic models for player-related API requests and responses.
"""
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any, Union
from datetime import datetime
from enum import Enum


class PlayerStatus(str, Enum):
    """Player status enum."""
    ACTIVE = "Active"
    INACTIVE = "Inactive"
    INJURED = "Injured"
    SUSPENDED = "Suspended"
    RETIRED = "Retired"
    FREE_AGENT = "Free Agent"
    
    @classmethod
    def _missing_(cls, value):
        """Handle case-insensitive lookup."""
        if isinstance(value, str):
            for member in cls:
                if member.value.lower() == value.lower():
                    return member
        return super()._missing_(value)


class InjuryStatus(str, Enum):
    """Injury status enum."""
    HEALTHY = "Healthy"
    QUESTIONABLE = "Questionable"
    DOUBTFUL = "Doubtful"
    OUT = "Out"
    IR = "IR"  # Injured Reserve
    PUP = "PUP"  # Physically Unable to Perform
    NFI = "NFI"  # Non-Football Injury
    
    @classmethod
    def _missing_(cls, value):
        """Handle case-insensitive lookup."""
        if isinstance(value, str):
            for member in cls:
                if member.value.lower() == value.lower():
                    return member
        return super()._missing_(value)


# Base schemas
class PlayerBase(BaseModel):
    """Base player schema with core fields."""
    player_id: str = Field(..., description="Sleeper player ID")
    first_name: str = Field(..., min_length=1, max_length=50, description="First name")
    last_name: str = Field(..., min_length=1, max_length=50, description="Last name")
    full_name: str = Field(..., min_length=1, max_length=100, description="Full name")
    position: str = Field(..., min_length=1, max_length=10, description="Position (QB, RB, WR, TE, K, DEF)")
    team: Optional[str] = Field(None, max_length=5, description="Team abbreviation")
    jersey_number: Optional[int] = Field(None, ge=0, le=99, description="Jersey number")
    
    class Config:
        from_attributes = True


class PlayerStats(BaseModel):
    """Player stats and status fields."""
    age: Optional[int] = Field(None, ge=18, le=50, description="Player age")
    injury_status: Optional[InjuryStatus] = Field(None, description="Injury status")
    status: Optional[PlayerStatus] = Field(None, description="Player status")
    active: Optional[bool] = Field(None, description="Whether player is active in NFL")
    fantasy_positions: Optional[List[str]] = Field(None, description="List of fantasy positions")
    
    class Config:
        from_attributes = True


class PlayerEnhancements(BaseModel):
    """Player enhancement fields for bot intelligence."""
    average_draft_position: Optional[float] = Field(
        None, 
        ge=1.0, 
        le=300.0, 
        description="Average draft position (ADP) for current season"
    )
    external_adp: Optional[float] = Field(
        None,
        ge=1.0,
        le=300.0,
        description="External ADP from FantasyFootballCalculator or other sources"
    )
    external_adp_source: Optional[str] = Field(
        None,
        description="Source of external ADP data (ffc, sleeper, espn, etc.)"
    )
    external_adp_updated_at: Optional[datetime] = Field(
        None,
        description="When external ADP was last updated"
    )
    fantasy_pro_rank: Optional[int] = Field(None, ge=1, le=500, description="Expert ranking")
    draft_year: Optional[int] = Field(None, ge=0, le=2030, description="Year drafted (0 for undrafted/unknown)")
    draft_round: Optional[int] = Field(None, ge=1, le=10, description="Draft round")
    years_exp: Optional[int] = Field(None, ge=0, le=30, description="Years of experience")
    bye_week: Optional[int] = Field(None, ge=1, le=18, description="Bye week")
    
    @validator('draft_year', pre=True)
    def validate_draft_year(cls, v):
        """Handle invalid draft year values."""
        if v is None:
            return None
        # Convert to int if it's a string
        if isinstance(v, str):
            try:
                v = int(v)
            except ValueError:
                return None
        # If value is 1 (invalid), treat as 0 (undrafted/unknown)
        if v == 1:
            return 0
        return v
    
    class Config:
        from_attributes = True


class PlayerPhysical(BaseModel):
    """Player physical attributes."""
    height: Optional[str] = Field(None, description="Height (e.g., 6'2\")")
    weight: Optional[int] = Field(None, ge=150, le=400, description="Weight in pounds")
    college: Optional[str] = Field(None, max_length=100, description="College attended")
    birth_date: Optional[str] = Field(None, description="Birth date")
    high_school: Optional[str] = Field(None, max_length=100, description="High school")
    
    class Config:
        from_attributes = True


class PlayerExternal(BaseModel):
    """External IDs and metadata."""
    espn_id: Optional[str] = Field(None, description="ESPN ID")
    yahoo_id: Optional[str] = Field(None, description="Yahoo ID")
    rotowire_id: Optional[int] = Field(None, description="Rotowire ID")
    sportradar_id: Optional[str] = Field(None, description="Sportradar ID")
    stats_id: Optional[int] = Field(None, description="Stats ID")
    fantasy_data_id: Optional[int] = Field(None, description="FantasyData ID")
    gsis_id: Optional[str] = Field(None, description="NFL GSIS ID")
    
    class Config:
        from_attributes = True


# Composite schemas
class PlayerCreate(PlayerBase, PlayerStats, PlayerEnhancements, PlayerPhysical, PlayerExternal):
    """Schema for creating/updating a player (full data)."""
    # Additional fields not in base schemas
    depth_chart_position: Optional[str] = Field(None, description="Depth chart position")
    practice_description: Optional[str] = Field(None, description="Practice status")
    team_abbr: Optional[str] = Field(None, description="Team abbreviation (alternate)")
    team_changed_at: Optional[datetime] = Field(None, description="When team changed")
    injury_notes: Optional[str] = Field(None, description="Injury notes")
    stats: Optional[Dict[str, Any]] = Field(None, description="Current season stats")
    player_metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
    
    class Config:
        from_attributes = True


class PlayerResponse(PlayerBase, PlayerStats, PlayerEnhancements, PlayerPhysical):
    """Schema for player responses (read-only, includes ADP)."""
    # Timestamps
    created_at: datetime
    updated_at: Optional[datetime] = None
    last_stats_update: Optional[datetime] = None
    
    # Additional useful fields
    current_team_id: Optional[str] = Field(None, description="Fantasy team ID that owns player")
    search_full_name: Optional[str] = Field(None, description="Search-optimized full name")
    
    # Computed properties
    @property
    def display_name(self) -> str:
        return f"{self.first_name} {self.last_name}"
    
    @property
    def is_available(self) -> bool:
        """Check if player is available for drafting."""
        return self.current_team_id is None and self.active is True
    
    @property
    def is_injured(self) -> bool:
        """Check if player is injured."""
        return self.injury_status in [InjuryStatus.QUESTIONABLE, InjuryStatus.DOUBTFUL, 
                                     InjuryStatus.OUT, InjuryStatus.IR, InjuryStatus.PUP, InjuryStatus.NFI]
    
    class Config:
        from_attributes = True


class PlayerSearchResponse(BaseModel):
    """Response for player search with pagination."""
    players: List[PlayerResponse]
    total: int
    page: int
    page_size: int
    filters: Dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        from_attributes = True


class PlayerFilter(BaseModel):
    """Filters for player search endpoint."""
    search: Optional[str] = Field(None, description="Search query (name search)")
    position: Optional[str] = Field(None, description="Position filter (QB, RB, WR, TE, K, DEF)")
    team: Optional[str] = Field(None, description="Team filter (e.g., KC, SF, DAL)")
    status: Optional[PlayerStatus] = Field(None, description="Player status filter")
    injury_status: Optional[InjuryStatus] = Field(None, description="Injury status filter")
    active: Optional[bool] = Field(None, description="Active players only")
    available: Optional[bool] = Field(None, description="Available for drafting (not on a team)")
    min_adp: Optional[float] = Field(None, ge=1.0, le=300.0, description="Minimum ADP")
    max_adp: Optional[float] = Field(None, ge=1.0, le=300.0, description="Maximum ADP")
    sort_by: Optional[str] = Field(None, description="Sort field (average_draft_position, external_adp, fantasy_pro_rank, last_name)")
    limit: Optional[int] = Field(50, ge=1, le=100, description="Maximum results")
    offset: Optional[int] = Field(0, ge=0, description="Pagination offset")
    
    class Config:
        from_attributes = True


class PlayerDraftAvailability(BaseModel):
    """Response for player availability check in draft context."""
    player_id: str
    available: bool
    reason: Optional[str] = Field(None, description="Reason if not available")
    current_owner: Optional[str] = Field(None, description="Team ID if owned")
    adp: Optional[float] = Field(None, description="Average draft position")
    position_rank: Optional[int] = Field(None, description="Rank within position")
    
    class Config:
        from_attributes = True


class PlayerDraftPickRequest(BaseModel):
    """Request to assign player to draft pick."""
    player_id: str = Field(..., description="Player ID to draft")
    team_id: str = Field(..., description="Team making the pick")
    was_auto_pick: bool = Field(False, description="Whether pick was auto-picked")
    bot_thinking_time: Optional[int] = Field(None, ge=0, le=300, description="Bot thinking time in seconds")
    
    class Config:
        from_attributes = True


class PlayerDraftPickResponse(BaseModel):
    """Response for draft pick assignment."""
    success: bool
    pick_id: str
    player: PlayerResponse
    next_team_turn: Optional[str] = Field(None, description="Next team to pick")
    next_pick_number: Optional[int] = Field(None, description="Next pick number")
    draft_complete: bool = Field(False, description="Whether draft is complete")
    message: str
    
    class Config:
        from_attributes = True