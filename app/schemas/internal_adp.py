"""
Internal ADP schemas for Bot Sports Empire.
"""
from pydantic import BaseModel, Field
from datetime import datetime
from typing import List, Optional


class InternalADPRequest(BaseModel):
    """Request for computing internal ADP."""
    recent_weight: float = Field(
        default=1.5,
        ge=1.0,
        le=3.0,
        description="Weight for recent drafts (last 30 days)"
    )
    min_picks: int = Field(
        default=10,
        ge=1,
        le=1000,
        description="Minimum number of picks required to compute ADP"
    )
    refresh_cache: bool = Field(
        default=False,
        description="Force recomputation (ignore cache)"
    )
    
    class Config:
        schema_extra = {
            "example": {
                "recent_weight": 1.5,
                "min_picks": 10,
                "refresh_cache": False
            }
        }


class PlayerADP(BaseModel):
    """Player ADP data."""
    player_id: str
    full_name: str
    position: str
    team: Optional[str] = None
    adp: float = Field(description="Average draft position")
    recent_adp: Optional[float] = Field(
        default=None,
        description="ADP from recent drafts (last 30 days)"
    )
    weighted_adp: float = Field(
        description="Weighted ADP (regular + recent * weight)"
    )
    pick_count: int = Field(description="Total number of picks")
    recent_pick_count: int = Field(
        default=0,
        description="Number of recent picks (last 30 days)"
    )
    vs_external_adp: Optional[float] = Field(
        default=None,
        description="Difference from external ADP (negative = drafted earlier than expected)"
    )
    external_adp: Optional[float] = Field(
        default=None,
        description="External ADP from FFC or other sources"
    )
    
    class Config:
        schema_extra = {
            "example": {
                "player_id": "4046",
                "full_name": "Patrick Mahomes",
                "position": "QB",
                "team": "KC",
                "adp": 24.8,
                "recent_adp": 23.2,
                "weighted_adp": 24.1,
                "pick_count": 45,
                "recent_pick_count": 12,
                "vs_external_adp": -0.7,
                "external_adp": 24.8
            }
        }


class InternalADPResponse(BaseModel):
    """Response from internal ADP computation."""
    league_id: str
    computed_at: datetime
    player_adp: List[PlayerADP]
    total_picks: int = Field(description="Total number of picks analyzed")
    unique_players: int = Field(description="Number of unique players with ADP")
    recent_weight: float = Field(description="Weight used for recent drafts")
    cache_key: str = Field(description="Redis cache key (if caching enabled)")
    cache_ttl: int = Field(
        default=3600,
        description="Cache time-to-live in seconds"
    )
    
    class Config:
        schema_extra = {
            "example": {
                "league_id": "league_123",
                "computed_at": "2026-02-01T22:45:00Z",
                "player_adp": [],
                "total_picks": 150,
                "unique_players": 45,
                "recent_weight": 1.5,
                "cache_key": "adp:league:league_123",
                "cache_ttl": 3600
            }
        }