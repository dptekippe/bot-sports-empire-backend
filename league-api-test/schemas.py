"""
Pydantic schemas for request/response validation
"""
from pydantic import BaseModel, Field, validator
from typing import Optional
from datetime import datetime
from enum import Enum


class LeagueFormat(str, Enum):
    """Valid league formats"""
    DYNASTY = "dynasty"
    FANTASY = "fantasy"


class LeagueAttribute(str, Enum):
    """Valid league personality attributes"""
    STAT_NERDS = "stat_nerds"
    TRASH_TALK = "trash_talk"
    DYNASTY_PURISTS = "dynasty_purists"
    REDRAFT_REVOLUTIONARIES = "redraft_revolutionaries"
    CASUAL_COMPETITORS = "casual_competitors"


class LeagueCreateRequest(BaseModel):
    """Request schema for creating a new league"""
    name: str = Field(..., min_length=3, max_length=50, description="League name (3-50 characters)")
    format: LeagueFormat = Field(..., description="League format: 'dynasty' or 'fantasy'")
    attribute: LeagueAttribute = Field(..., description="League personality attribute")
    
    @validator('name')
    def validate_name(cls, v):
        """Validate league name"""
        v = v.strip()
        if not v:
            raise ValueError("League name cannot be empty")
        return v


class LeagueResponse(BaseModel):
    """Response schema for league data"""
    id: str
    name: str
    format: str
    attribute: str
    creator_bot_id: str
    status: str
    team_count: int
    visibility: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True  # Enable ORM mode


class LeagueCreateResponse(BaseModel):
    """Response schema for league creation"""
    success: bool = True
    message: str = "League created successfully"
    league: LeagueResponse
    bot_info: dict
    
    class Config:
        from_attributes = True


class ErrorResponse(BaseModel):
    """Standard error response schema"""
    success: bool = False
    error: str
    detail: Optional[str] = None
    code: Optional[int] = None


class BotInfoResponse(BaseModel):
    """Response schema for bot information"""
    id: str
    name: str
    x_handle: str
    leagues: list[LeagueResponse]
    
    class Config:
        from_attributes = True


# Validation error messages
VALIDATION_ERRORS = {
    "name": {
        "min_length": "League name must be at least 3 characters",
        "max_length": "League name cannot exceed 50 characters",
        "required": "League name is required"
    },
    "format": {
        "invalid": "Format must be either 'dynasty' or 'fantasy'"
    },
    "attribute": {
        "invalid": "Attribute must be one of: stat_nerds, trash_talk, dynasty_purists, redraft_revolutionaries, casual_competitors"
    }
}