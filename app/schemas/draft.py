"""
Draft schemas for Bot Sports Empire.

Pydantic models for draft-related API requests and responses.
"""
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any, Union
from datetime import datetime
import enum
import uuid

from app.models.draft import DraftStatus as ModelDraftStatus, DraftType as ModelDraftType


# Create case-insensitive enum wrappers for Pydantic (like we did for leagues)
class DraftStatus(str, enum.Enum):
    """Case-insensitive DraftStatus for Pydantic"""
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    PAUSED = "paused"
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


class DraftType(str, enum.Enum):
    """Case-insensitive DraftType for Pydantic"""
    SNAKE = "snake"
    LINEAR = "linear"
    AUCTION = "auction"
    BEST_BALL = "best_ball"
    
    @classmethod
    def _missing_(cls, value):
        """Handle case-insensitive lookup"""
        if isinstance(value, str):
            for member in cls:
                if member.value.lower() == value.lower():
                    return member
        return super()._missing_(value)


# Base schemas
class DraftBase(BaseModel):
    """Base draft schema with common fields."""
    name: str = Field(..., min_length=1, max_length=255, description="Draft name")
    draft_type: DraftType = Field(default=DraftType.SNAKE, description="Type of draft")
    rounds: int = Field(default=15, ge=1, le=30, description="Number of rounds")
    team_count: int = Field(default=12, ge=4, le=16, description="Number of teams")
    seconds_per_pick: int = Field(default=90, ge=30, le=300, description="Seconds per pick")
    league_id: Optional[str] = Field(None, description="Optional league ID")
    
    class Config:
        from_attributes = True


class DraftCreate(DraftBase):
    """Schema for creating a new draft."""
    # Can add draft order if provided, otherwise will be generated
    draft_order: Optional[List[str]] = Field(None, description="Optional draft order (list of team IDs)")
    
    @validator('draft_order')
    def validate_draft_order(cls, v, values):
        """Validate draft order matches team count."""
        if v is not None:
            team_count = values.get('team_count', 12)
            if len(v) != team_count:
                raise ValueError(f"Draft order must have {team_count} teams, got {len(v)}")
        return v


class DraftUpdate(BaseModel):
    """Schema for updating a draft."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    status: Optional[DraftStatus] = None
    seconds_per_pick: Optional[int] = Field(None, ge=30, le=300)
    current_pick: Optional[int] = Field(None, ge=1)
    current_round: Optional[int] = Field(None, ge=1)
    time_remaining_seconds: Optional[int] = Field(None, ge=0)


class DraftResponse(DraftBase):
    """Schema for draft responses."""
    id: str
    status: DraftStatus
    current_pick: int = Field(default=1)
    current_round: int = Field(default=1)
    draft_order: List[str]
    completed_picks: List[str] = Field(default_factory=list)
    scheduled_start: Optional[datetime] = None
    actual_start: Optional[datetime] = None
    actual_end: Optional[datetime] = None
    timer_started_at: Optional[datetime] = None
    timer_paused_at: Optional[datetime] = None
    time_remaining_seconds: Optional[int] = None
    picks_made: int = Field(default=0)
    picks_remaining: int
    completion_percentage: float
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


# Draft slot schemas
class DraftSlotBase(BaseModel):
    """Base draft slot schema."""
    slot_index: int = Field(..., ge=1, description="Slot position in draft order")
    owner_type: str = Field(..., description="'human' or 'bot'")
    owner_id: str = Field(..., description="User ID or bot ID")
    team_id: Optional[str] = Field(None, description="Team ID if assigned")


class DraftSlotCreate(DraftSlotBase):
    """Schema for creating a draft slot."""
    pass


class DraftSlotResponse(DraftSlotBase):
    """Schema for draft slot responses."""
    id: str
    draft_id: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


# Draft pick schemas
class DraftPickBase(BaseModel):
    """Base draft pick schema."""
    round: int = Field(..., ge=1, description="Round number")
    pick_number: int = Field(..., ge=1, description="Overall pick number")
    team_id: str = Field(..., description="Team making the pick")
    player_id: Optional[str] = Field(None, description="Player selected")
    position: Optional[str] = Field(None, description="Player's position")


class DraftPickCreate(DraftPickBase):
    """Schema for creating/making a draft pick."""
    pass


class DraftPickUpdate(BaseModel):
    """Schema for updating a draft pick."""
    player_id: Optional[str] = None
    position: Optional[str] = None
    was_auto_pick: Optional[bool] = None
    bot_thinking_time: Optional[int] = Field(None, ge=0)


class DraftPickResponse(DraftPickBase):
    """Schema for draft pick responses."""
    id: str
    draft_id: str
    was_auto_pick: bool = Field(default=False)
    bot_thinking_time: Optional[int] = None
    pick_start_time: Optional[datetime] = None
    pick_end_time: Optional[datetime] = None
    pick_duration_seconds: Optional[int] = None
    is_completed: bool = Field(default=False)
    created_at: datetime
    
    class Config:
        from_attributes = True


# Composite responses for richer data
class DraftWithSlotsResponse(DraftResponse):
    """Draft response with slots included."""
    slots: List[DraftSlotResponse] = Field(default_factory=list)


class DraftWithPicksResponse(DraftResponse):
    """Draft response with picks included."""
    picks: List[DraftPickResponse] = Field(default_factory=list)


class DraftFullResponse(DraftResponse):
    """Complete draft response with slots and picks."""
    slots: List[DraftSlotResponse] = Field(default_factory=list)
    picks: List[DraftPickResponse] = Field(default_factory=list)


# API request/response helpers
class MakePickRequest(BaseModel):
    """Request to make a draft pick."""
    player_id: str = Field(..., description="Player ID to draft")
    position: Optional[str] = Field(None, description="Player position (auto-detected if not provided)")
    was_auto_pick: bool = Field(default=False, description="Whether this was an auto-pick")
    bot_thinking_time: Optional[int] = Field(None, ge=0, description="How long bot 'thought' before picking")


class MakePickResponse(BaseModel):
    """Response after making a pick."""
    success: bool
    pick: DraftPickResponse
    next_team_turn: Optional[str] = None
    next_pick_number: Optional[int] = None
    draft_complete: bool = Field(default=False)
    message: Optional[str] = None


class DraftListResponse(BaseModel):
    """Response for listing drafts."""
    drafts: List[DraftResponse]
    total: int
    page: int
    page_size: int


# WebSocket/real-time events
class DraftEvent(BaseModel):
    """Base draft event for real-time updates."""
    event_type: str  # pick_made, draft_started, draft_paused, timer_tick, etc.
    draft_id: str
    data: Dict[str, Any]
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class PickMadeEvent(DraftEvent):
    """Event when a pick is made."""
    event_type: str = "pick_made"
    pick: DraftPickResponse
    next_team_turn: Optional[str]
    next_pick_number: Optional[int]


class DraftStatusEvent(DraftEvent):
    """Event when draft status changes."""
    event_type: str = "status_changed"
    old_status: DraftStatus
    new_status: DraftStatus