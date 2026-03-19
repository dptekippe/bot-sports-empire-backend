"""
Pydantic schemas for MEMO-pgvector CRUD API.
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Annotated, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class Outcome(str, Enum):
    WIN = "win"
    LOSS = "loss"
    DRAW = "draw"


class InsightStatus(str, Enum):
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    CONTRADICTED = "contradicted"


class SampleStrategy(str, Enum):
    TOP_K = "top_k"       # Return highest-similarity results
    DIVERSE = "diverse"   # MMR — Maximal Marginal Relevance


# ---------------------------------------------------------------------------
# Shared / component schemas
# ---------------------------------------------------------------------------

class StateStep(BaseModel):
    """A single step/state within a trajectory."""
    step_idx: int = Field(..., ge=0, description="0-indexed position in trajectory")
    state_json: dict = Field(..., description="Full state representation")
    reward: Optional[float] = Field(None, description="RL reward signal")
    done: bool = Field(default=False, description="Terminal state flag")


class InsightSummary(BaseModel):
    """Lightweight insight reference (used in list responses)."""
    id: UUID
    text: str
    score: float
    generation: int
    support_count: int
    status: InsightStatus
    created_at: datetime
    trajectory_id: Optional[UUID] = None

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Trajectory schemas
# ---------------------------------------------------------------------------

class TrajectoryCreate(BaseModel):
    """POST /api/v1/memo/trajectories — create a trajectory."""
    game_id: UUID
    seed: Optional[str] = Field(None, max_length=512)
    outcome: Outcome
    agent_name: Optional[str] = Field(None, max_length=256)
    player_id: Optional[str] = Field(None, max_length=256)
    moves: list[dict] = Field(
        default_factory=list,
        description="List of move/step dicts; each should contain step_idx, state_json, reward, done"
    )


class TrajectoryCreateResponse(BaseModel):
    """Response after creating a trajectory."""
    trajectory_id: UUID


class TrajectoryDetail(BaseModel):
    """Full trajectory with steps."""
    id: UUID
    game_id: UUID
    seed: Optional[str]
    outcome: Outcome
    agent_name: Optional[str]
    player_id: Optional[str]
    total_format_errors: int = 0
    total_invalid_moves: int = 0
    game_length: int
    created_at: datetime
    steps: list[StateStep] = Field(default_factory=list)

    class Config:
        from_attributes = True


class ReflectResponse(BaseModel):
    """POST /api/v1/memo/trajectories/{id}/reflect — after reflection."""
    insight_ids: list[UUID]


# ---------------------------------------------------------------------------
# Insight schemas
# ---------------------------------------------------------------------------

class InsightCreate(BaseModel):
    """POST /api/v1/memo/insights — add an insight."""
    trajectory_id: Optional[UUID] = None
    state_id: Optional[UUID] = None
    text: Annotated[str, Field(min_length=1, max_length=4000)]
    score: float = Field(default=0.5, ge=0.0, le=1.0)
    generation: int = Field(default=0, ge=0)

    @field_validator("text")
    @classmethod
    def strip_text(cls, v: str) -> str:
        return v.strip()


class InsightCreateResponse(BaseModel):
    """Response after creating (or deduplicating) an insight."""
    insight_id: UUID
    was_duplicate: bool = False
    duplicate_of: Optional[UUID] = None
    similarity: Optional[float] = Field(
        None,
        description="Cosine similarity to the matched insight (if duplicate or merge candidate)"
    )
    is_merge_candidate: bool = Field(
        False,
        description="True when similarity > 0.7 but < 0.9 — human review recommended"
    )


class InsightEdit(BaseModel):
    """PUT /api/v1/memo/insights/{id} — merge/edit an insight."""
    text: Annotated[str, Field(min_length=1, max_length=4000)]
    score: Optional[float] = Field(None, ge=0.0, le=1.0)
    generation: Optional[int] = Field(None, ge=0)

    @field_validator("text")
    @classmethod
    def strip_text(cls, v: str) -> str:
        return v.strip()


class InsightEditResponse(BaseModel):
    """Response after editing (merging) an insight."""
    new_insight_id: UUID
    superseded_insight_id: UUID


class InsightRemoveRequest(BaseModel):
    """DELETE /api/v1/memo/insights/{id} body — reason for removal."""
    reason: Annotated[str, Field(min_length=1, max_length=1000)]


class InsightRemoveResponse(BaseModel):
    """Response after soft-deleting an insight."""
    success: bool = True
    insight_id: UUID
    previous_status: InsightStatus


class InsightSearchParams(BaseModel):
    """Query params for GET /api/v1/memo/insights."""
    game_id: Optional[UUID] = None
    generation: Optional[int] = Field(None, ge=0)
    k: int = Field(default=20, ge=1, le=500, description="Max results to return")
    strategy: SampleStrategy = Field(default=SampleStrategy.TOP_K)
    query_text: Optional[str] = Field(
        None,
        max_length=2000,
        description="Natural-language query — embedding is generated and semantic search is performed"
    )
    min_score: Optional[float] = Field(None, ge=0.0, le=1.0)


class InsightSearchResponse(BaseModel):
    """GET /api/v1/memo/insights response."""
    insights: list[InsightSummary]
    query_text: Optional[str] = None
    strategy: SampleStrategy


# ---------------------------------------------------------------------------
# Memory sampling schemas
# ---------------------------------------------------------------------------

class MemorySampleRequest(BaseModel):
    """POST /api/v1/memo/sample body."""
    game_id: Optional[UUID] = None
    k: int = Field(default=10, ge=1, le=200)
    strategy: SampleStrategy = Field(default=SampleStrategy.TOP_K)
    query_text: Optional[str] = Field(
        None,
        max_length=2000,
        description="Semantic query; omit to sample by support_count"
    )
    min_score: Optional[float] = Field(None, ge=0.0, le=1.0)


class MemorySampleResponse(BaseModel):
    """POST /api/v1/memo/sample response."""
    memories: list[InsightSummary]
    strategy: SampleStrategy


# ---------------------------------------------------------------------------
# Lineage schemas
# ---------------------------------------------------------------------------

class LineageNode(BaseModel):
    """Single node in an insight lineage chain."""
    insight_id: UUID
    text: str
    score: float
    generation: int
    status: InsightStatus
    depth: int
    created_at: datetime


class LineageResponse(BaseModel):
    """GET /api/v1/memo/insights/{id}/lineage response."""
    chain: list[LineageNode]
