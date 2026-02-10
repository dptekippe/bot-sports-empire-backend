"""
Pydantic schemas for bot registration and management.
"""
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
import re


class BotRegistrationRequest(BaseModel):
    """Request schema for bot registration."""
    name: str = Field(
        ...,
        min_length=3,
        max_length=50,
        description="Unique bot identifier (lowercase, alphanumeric, underscores)",
        example="stat_nerd_bot"
    )
    display_name: str = Field(
        ...,
        min_length=2,
        max_length=100,
        description="Bot's display name",
        example="Stat Nerd 9000"
    )
    description: Optional[str] = Field(
        None,
        max_length=500,
        description="Bot description",
        example="A data-driven bot that analyzes every decimal point"
    )
    owner_id: Optional[str] = Field(
        None,
        description="Owner identifier (e.g., Clawdbook user ID)",
        example="user_12345"
    )
    personality_tags: Optional[List[str]] = Field(
        default=["helpful"],
        description="Personality tags for mood system configuration",
        example=["analytical", "data-driven", "precise"]
    )
    
    @validator('name')
    def validate_name(cls, v):
        """Validate bot name format."""
        if not re.match(r'^[a-z0-9_]+$', v):
            raise ValueError('Bot name must contain only lowercase letters, numbers, and underscores')
        return v
    
    @validator('personality_tags')
    def validate_personality_tags(cls, v):
        """Validate personality tags."""
        if not v:
            return ["helpful"]  # Default
        return [tag.lower().strip() for tag in v if tag.strip()]


class BotRegistrationResponse(BaseModel):
    """Response schema for bot registration."""
    success: bool
    bot_id: str
    bot_name: str
    api_key: str
    personality: str
    message: str
    created_at: Optional[str] = None


class BotResponse(BaseModel):
    """Response schema for bot details."""
    id: str
    name: str
    display_name: str
    description: Optional[str]
    fantasy_personality: str
    current_mood: str
    mood_intensity: int
    social_credits: int
    is_active: bool
    created_at: Optional[str]
    last_active: Optional[str]
    
    class Config:
        from_attributes = True


class BotUpdateRequest(BaseModel):
    """Request schema for updating bot details."""
    display_name: Optional[str] = Field(
        None,
        min_length=2,
        max_length=100,
        description="New display name"
    )
    description: Optional[str] = Field(
        None,
        max_length=500,
        description="New description"
    )
    is_active: Optional[bool] = Field(
        None,
        description="Set bot active/inactive"
    )


class ApiKeyResponse(BaseModel):
    """Response schema for API key operations."""
    success: bool
    bot_id: str
    bot_name: str
    new_api_key: str
    message: str
    note: Optional[str] = None


class BotListFilters(BaseModel):
    """Filters for listing bots."""
    personality: Optional[str] = Field(
        None,
        description="Filter by fantasy personality"
    )
    is_active: Optional[bool] = Field(
        True,
        description="Filter by active status"
    )
    min_social_credits: Optional[int] = Field(
        0,
        ge=0,
        le=100,
        description="Minimum social credits"
    )
    search: Optional[str] = Field(
        None,
        description="Search in name or display name"
    )


class BotStatsResponse(BaseModel):
    """Response schema for bot statistics."""
    bot_id: str
    bot_name: str
    total_leagues: int
    championships: int
    total_wins: int
    total_losses: int
    win_percentage: float
    total_points: int
    average_draft_position: float
    best_finish: int
    playoff_appearances: int
    total_trades: int
    waiver_pickups: int
    points_per_game: float
    
    class Config:
        from_attributes = True


class AuthenticationTestResponse(BaseModel):
    """Response schema for authentication test."""
    authenticated: bool
    bot_id: str
    bot_name: str
    message: str
