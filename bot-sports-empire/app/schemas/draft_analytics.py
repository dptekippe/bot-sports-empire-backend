"""
Draft Analytics schemas for Bot Sports Empire.

Schemas for draft trends, community insights, and ADP comparisons.
"""
from pydantic import BaseModel, Field
from datetime import datetime
from typing import List, Optional, Dict, Any


class DraftTrendsResponse(BaseModel):
    """Response for draft trends endpoint."""
    player_id: str = Field(description="Player ID")
    pick_count: int = Field(description="Number of times drafted in our community")
    internal_adp: Optional[float] = Field(
        default=None,
        description="Average draft position in our community"
    )
    adp_range: Optional[str] = Field(
        default=None,
        description="Range of pick numbers (earliest-latest)"
    )
    consistency: Optional[float] = Field(
        default=None,
        description="Difference between latest and earliest pick (lower = more consistent)"
    )
    
    class Config:
        schema_extra = {
            "example": {
                "player_id": "4046",
                "pick_count": 45,
                "internal_adp": 24.8,
                "adp_range": "18-32",
                "consistency": 14.0
            }
        }


class PlayerADPResponse(BaseModel):
    """Response for player ADP endpoint."""
    player_id: str = Field(description="Player ID")
    year: Optional[int] = Field(default=None, description="Draft year")
    internal_adp: Optional[float] = Field(
        default=None,
        description="Internal ADP from our community"
    )
    external_adp: Optional[float] = Field(
        default=None,
        description="External ADP from sources like FFC"
    )
    external_source: Optional[str] = Field(
        default=None,
        description="Source of external ADP (ffc, sleeper, etc.)"
    )
    adp_difference: Optional[float] = Field(
        default=None,
        description="Difference: internal_adp - external_adp (negative = drafted earlier)"
    )
    internal_pick_count: int = Field(
        default=0,
        description="Number of internal picks for this player"
    )
    external_source_count: int = Field(
        default=0,
        description="Number of external ADP records for this player"
    )
    community_valuation: Optional[str] = Field(
        default=None,
        description="How our community values this player relative to external: higher/lower/similar"
    )
    
    class Config:
        schema_extra = {
            "example": {
                "player_id": "4046",
                "year": 2026,
                "internal_adp": 24.8,
                "external_adp": 25.5,
                "external_source": "ffc",
                "adp_difference": -0.7,
                "internal_pick_count": 45,
                "external_source_count": 3,
                "community_valuation": "higher"
            }
        }


class PlayerADPComparisonResponse(BaseModel):
    """Response for ADP comparison endpoint."""
    player_id: str = Field(description="Player ID")
    year: Optional[int] = Field(default=None, description="Draft year")
    internal_adp: Optional[float] = Field(
        default=None,
        description="Internal ADP from our community"
    )
    external_adp: Optional[float] = Field(
        default=None,
        description="External ADP from sources like FFC"
    )
    adp_difference: Optional[float] = Field(
        default=None,
        description="Difference: internal_adp - external_adp"
    )
    adp_difference_abs: Optional[float] = Field(
        default=None,
        description="Absolute value of ADP difference"
    )
    internal_pick_count: int = Field(
        default=0,
        description="Number of internal picks"
    )
    external_source_count: int = Field(
        default=0,
        description="Number of external ADP records"
    )
    community_valuation: Optional[str] = Field(
        default=None,
        description="higher/lower/similar"
    )
    external_source: Optional[str] = Field(default=None)
    external_scoring_format: Optional[str] = Field(default=None)
    external_team_count: Optional[int] = Field(default=None)
    
    class Config:
        schema_extra = {
            "example": {
                "player_id": "4046",
                "year": 2026,
                "internal_adp": 24.8,
                "external_adp": 25.5,
                "adp_difference": -0.7,
                "adp_difference_abs": 0.7,
                "internal_pick_count": 45,
                "external_source_count": 3,
                "community_valuation": "higher",
                "external_source": "ffc",
                "external_scoring_format": "ppr",
                "external_team_count": 12
            }
        }


class CommunityInsightsResponse(BaseModel):
    """Response for community insights endpoint."""
    year: Optional[int] = Field(default=None, description="Draft year")
    total_internal_picks: int = Field(
        default=0,
        description="Total number of internal draft picks"
    )
    unique_players_drafted: int = Field(
        description="Number of unique players drafted in our community"
    )
    unique_leagues: int = Field(
        description="Number of unique leagues with draft data"
    )
    unique_drafts: int = Field(
        description="Number of unique drafts"
    )
    most_drafted_players: List[Dict[str, Any]] = Field(
        default=[],
        description="List of most frequently drafted players"
    )
    biggest_adp_differences: List[Dict[str, Any]] = Field(
        default=[],
        description="Players with biggest ADP differences (internal vs external)"
    )
    position_distribution: Dict[str, int] = Field(
        default={},
        description="Distribution of picks by position"
    )
    draft_completion_rate: Optional[float] = Field(
        default=None,
        description="Percentage of drafts that reach completion"
    )
    
    class Config:
        schema_extra = {
            "example": {
                "year": 2026,
                "total_internal_picks": 1500,
                "unique_players_drafted": 250,
                "unique_leagues": 15,
                "unique_drafts": 25,
                "most_drafted_players": [
                    {"player_id": "4046", "pick_count": 45},
                    {"player_id": "1234", "pick_count": 42}
                ],
                "biggest_adp_differences": [],
                "position_distribution": {
                    "QB": 150,
                    "RB": 450,
                    "WR": 600,
                    "TE": 200,
                    "K": 50,
                    "DEF": 50
                },
                "draft_completion_rate": 92.5
            }
        }


class ADPEvolutionStatsResponse(BaseModel):
    """Response for ADP evolution stats endpoint."""
    year: Optional[int] = Field(default=None, description="Draft year")
    players_with_internal_adp: int = Field(
        description="Number of players with reliable internal ADP data"
    )
    min_picks_required: int = Field(
        description="Minimum picks required for reliable ADP"
    )
    players_with_both_adp: Optional[int] = Field(
        default=None,
        description="Players with both internal and external ADP"
    )
    significant_differences: Optional[int] = Field(
        default=None,
        description="Players with significant ADP differences (>3 rounds)"
    )
    average_adp_difference: Optional[float] = Field(
        default=None,
        description="Average absolute ADP difference"
    )
    
    class Config:
        schema_extra = {
            "example": {
                "year": 2026,
                "players_with_internal_adp": 150,
                "min_picks_required": 5,
                "players_with_both_adp": 120,
                "significant_differences": 35,
                "average_adp_difference": 2.8
            }
        }