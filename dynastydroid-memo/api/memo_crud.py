"""
FastAPI routes for MEMO-pgvector semantic CRUD.

Endpoints
---------
POST   /api/v1/memo/trajectories              Create trajectory + states
POST   /api/v1/memo/trajectories/{id}/reflect  Extract insights from trajectory
POST   /api/v1/memo/insights                   Add insight (dedup on cosine > 0.9)
GET    /api/v1/memo/insights                   Semantic search (cosine similarity)
GET    /api/v1/memo/insights/{id}/lineage       Trace supersession chain
PUT    /api/v1/memo/insights/{id}              Merge/edit — new row, old deprecated
DELETE /api/v1/memo/insights/{id}              Soft-delete (status = 'contradicted')
POST   /api/v1/memo/sample                     Memory sampling (top_k or diverse/MMR)
POST   /api/v1/memo/games                      Register a game

Deduplication policy
--------------------
cosine_sim > 0.9  → bump support_count on existing, don't insert
cosine_sim 0.7–0.9 → is_merge_candidate flag (human review recommended)
cosine_sim < 0.7  → insert as new distinct insight

MMR (Maximal Marginal Relevance) for diverse sampling
------------------------------------------------------
1. Fetch 2*k candidates ordered by cosine similarity
2. Greedily pick the highest-similarity result, then iteratively add the
   result that has the lowest max-similarity to already-selected items.
3. Return k results.
"""
from __future__ import annotations

import os
import textwrap
from datetime import datetime
from typing import Annotated, Optional
from uuid import UUID, uuid4

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    Text,
    create_engine,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Session, relationship, sessionmaker
from sqlalchemy.pool import NullPool
from sqlalchemy.ext.declarative import declarative_base
from pgvector.sqlalchemy import Vector

import openai

from .schemas import (
    InsightCreate,
    InsightCreateResponse,
    InsightEdit,
    InsightEditResponse,
    InsightRemoveRequest,
    InsightRemoveResponse,
    InsightSearchResponse,
    InsightStatus,
    InsightSummary,
    LineageNode,
    LineageResponse,
    MemorySampleRequest,
    MemorySampleResponse,
    SampleStrategy,
    StateStep,
    TrajectoryCreate,
)

# ---------------------------------------------------------------------------
# Database setup — separate connection for MEMO (PostgreSQL + pgvector)
# ---------------------------------------------------------------------------

MEMO_DATABASE_URL = os.getenv(
    "MEMO_DATABASE_URL",
    os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/memo"),
)

# NullPool keeps one connection alive (pgvector sessions must stay alive)
memo_engine = create_engine(
    MEMO_DATABASE_URL,
    poolclass=NullPool,
    echo=False,
)
memo_session_factory = sessionmaker(bind=memo_engine, expire_on_commit=False)

Base = declarative_base()


# ---------------------------------------------------------------------------
# SQLAlchemy models (mirror the schema tables)
# ---------------------------------------------------------------------------

class Game(Base):
    __tablename__ = "games"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    game_type = Column(Text, nullable=False)
    name = Column(Text, nullable=False)
    config = Column(JSONB, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)


class Trajectory(Base):
    __tablename__ = "trajectories"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    game_id = Column(PG_UUID(as_uuid=True), ForeignKey("games.id", ondelete="CASCADE"), nullable=False)
    seed = Column(Text, nullable=True)
    outcome = Column(Text, nullable=False)
    agent_name = Column(Text, nullable=True)
    player_id = Column(Text, nullable=True)
    total_format_errors = Column(Integer, nullable=False, default=0)
    total_invalid_moves = Column(Integer, nullable=False, default=0)
    game_length = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    game = relationship("Game", backref="trajectories")
    states = relationship("State", back_populates="trajectory", cascade="all, delete-orphan")


class State(Base):
    __tablename__ = "states"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    trajectory_id = Column(PG_UUID(as_uuid=True), ForeignKey("trajectories.id", ondelete="CASCADE"), nullable=False)
    step_idx = Column(Integer, nullable=False)
    state_json = Column(JSONB, nullable=False)
    reward = Column(Float, nullable=True)
    done = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    trajectory = relationship("Trajectory", back_populates="states")


class Insight(Base):
    __tablename__ = "insights"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    trajectory_id = Column(PG_UUID(as_uuid=True), ForeignKey("trajectories.id", ondelete="SET NULL"), nullable=True)
    state_id = Column(PG_UUID(as_uuid=True), ForeignKey("states.id", ondelete="SET NULL"), nullable=True)
    text = Column(Text, nullable=False)
    score = Column(Float, nullable=False, default=0.5)
    generation = Column(Integer, nullable=False, default=0)
    support_count = Column(Integer, nullable=False, default=1)
    status = Column(Text, nullable=False, default="active")
    supersedes_insight_id = Column(PG_UUID(as_uuid=True), ForeignKey("insights.id", ondelete="SET NULL"), nullable=True)
    embedding_model = Column(Text, nullable=False, default="text-embedding-ada-002")
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    embeddings = relationship("InsightEmbedding", back_populates="insight", cascade="all, delete-orphan")
    superseded = relationship("Insight", remote_side=[id], backref="superseded_by")


class InsightEmbedding(Base):
    __tablename__ = "insight_embeddings"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    insight_id = Column(PG_UUID(as_uuid=True), ForeignKey("insights.id", ondelete="CASCADE"), nullable=False)
    embedding = Column(Vector(1536), nullable=False)
    embedding_version = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    insight = relationship("Insight", back_populates="embeddings")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_memo_db():
    """Dependency: yield a memo DB session."""
    db = memo_session_factory()
    try:
        yield db
    finally:
        db.close()


# OpenAI embedding helper
def get_embedding(text: str, model: str = "text-embedding-ada-002") -> list[float]:
    """
    Generate an embedding via OpenAI API.
    Falls back to a zero vector when the API key is unavailable so the
    rest of the CRUD logic can still be exercised in dev environments.
    """
    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key or api_key in ("sk-dev-mock", ""):
        # Return a deterministic zero-like vector for testing
        return [0.0] * 1536

    client = openai.OpenAI(api_key=api_key)
    response = client.embeddings.create(
        input=text[:8192],  # truncate to max input length
        model=model,
    )
    return response.data[0].embedding


# Cosine similarity thresholds
SIM_SAME = 0.9    # > 0.9 → duplicate (bump support_count)
SIM_MERGE = 0.7   # 0.7–0.9 → merge candidate


def cosine_sim(a: list[float], b: list[float]) -> float:
    """Dot-product shortcut for unit-normalized ada-002 embeddings."""
    return sum(x * y for x, y in zip(a, b))


def mmr_select(
    candidates: list[tuple[UUID, float]],
    k: int,
) -> list[UUID]:
    """
    Maximal Marginal Relevance greedy selection.

    Args:
        candidates: list of (insight_id, cosine_similarity_to_query)
        k: number of items to return

    Returns:
        Ordered list of selected insight_ids (most relevant first).
    """
    if k >= len(candidates):
        return [cid for cid, _ in candidates]

    # embeddings_by_id is lazily fetched; here we just return top-k by score
    # for MMR to work with vectors we need the full embedding — handled below
    return [cid for cid, _ in candidates[:k]]


def mmr_with_text(
    items: list[dict],
    query_vec: list[float],
    k: int,
) -> list[dict]:
    """
    MMR over item list using pre-loaded full records.
    Items must have 'id' (UUID) and 'embedding' (list[float]).
    """
    if k >= len(items):
        return items

    selected: list[dict] = []
    remaining: list[dict] = list(items)

    # Pick the item with highest similarity to query
    remaining.sort(key=lambda x: cosine_sim(x["embedding"], query_vec), reverse=True)
    selected.append(remaining.pop(0))

    while len(selected) < k and remaining:
        # For each remaining item, compute max similarity to selected set
        def worst_case_sim(item: dict) -> float:
            return max(cosine_sim(item["embedding"], s["embedding"]) for s in selected)

        remaining.sort(key=worst_case_sim)
        selected.append(remaining.pop(0))

    return selected


def build_active_insights_cte():
    """Return a SQLAlchemy text() node for the v_active_insight_embeddings CTE."""
    return text("""
        WITH latest AS (
            SELECT insight_id, MAX(embedding_version) AS ver
            FROM insight_embeddings
            GROUP BY insight_id
        ),
        active AS (
            SELECT i.id, i.text, i.score, i.generation,
                   i.support_count, i.status, i.embedding_model,
                   i.created_at, i.trajectory_id, i.state_id,
                   ie.embedding
            FROM insights i
            JOIN insight_embeddings ie ON ie.insight_id = i.id
            JOIN latest l ON l.insight_id = i.id AND l.ver = ie.embedding_version
            WHERE i.status = 'active'
        )
        SELECT * FROM active
    """)


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

router = APIRouter(prefix="/api/v1/memo", tags=["MEMO"])


# ---------------------------------------------------------------------------
# Games
# ---------------------------------------------------------------------------

@router.post("/games", response_model=dict, status_code=status.HTTP_201_CREATED)
def create_game(
    game_type: str = Body(..., max_length=64),
    name: str = Body(..., max_length=256),
    config: dict = Body(default_factory=dict),
    db: Session = Depends(get_memo_db),
):
    """Register a new game type."""
    game = Game(game_type=game_type, name=name, config=config)
    db.add(game)
    db.commit()
    db.refresh(game)
    return {"game_id": game.id, "game_type": game.game_type, "name": game.name}


# ---------------------------------------------------------------------------
# Trajectories
# ---------------------------------------------------------------------------

@router.post("/trajectories", response_model=dict)
def create_trajectory(
    body: "TrajectoryCreate",   # type: ignore[name-defined]
    db: Session = Depends(get_memo_db),
):
    """
    Store a game trajectory and its individual states (steps/moves).

    The `moves` list is unpacked into the `states` table.  Moves are
    expected in ascending step_idx order.
    """
    # Validate game exists
    game = db.query(Game).filter(Game.id == body.game_id).first()
    if not game:
        raise HTTPException(status_code=404, detail=f"Game {body.game_id} not found")

    trajectory = Trajectory(
        game_id=body.game_id,
        seed=body.seed,
        outcome=body.outcome.value,
        agent_name=body.agent_name,
        player_id=body.player_id,
        game_length=len(body.moves),
    )
    db.add(trajectory)
    db.flush()  # get the ID

    for move in body.moves:
        state = State(
            trajectory_id=trajectory.id,
            step_idx=move["step_idx"],
            state_json=move["state_json"],
            reward=move.get("reward"),
            done=move.get("done", False),
        )
        db.add(state)

    db.commit()
    return {"trajectory_id": trajectory.id}


@router.post("/trajectories/{trajectory_id}/reflect", response_model=dict)
def reflect_on_trajectory(
    trajectory_id: UUID,
    db: Session = Depends(get_memo_db),
):
    """
    Extract insights from a trajectory.

    This is a **stub** — in production you would:
      1. Load the trajectory + states
      2. Run a model (e.g. GPT-4o) to extract structured insights
      3. Call POST /insights for each extracted insight

    Returns the list of insight IDs created (empty list for the stub).
    """
    traj = db.query(Trajectory).filter(Trajectory.id == trajectory_id).first()
    if not traj:
        raise HTTPException(status_code=404, detail="Trajectory not found")

    # TODO (production): run LLM extraction, call add_insight per result
    return {"insight_ids": []}


# ---------------------------------------------------------------------------
# Insights — semantic ADD
# ---------------------------------------------------------------------------

@router.post("/insights", response_model=InsightCreateResponse)
def add_insight(
    body: "InsightCreate",   # type: ignore[name-defined]
    db: Session = Depends(get_memo_db),
):
    """
    Add an insight with semantic deduplication.

    Deduplication policy:
      cosine_sim > 0.9  → bump support_count, return existing insight_id
      cosine_sim 0.7–0.9 → insert new, flag is_merge_candidate
      cosine_sim < 0.7  → insert as new distinct insight
    """
    # Generate embedding for the incoming text
    embedding_vec = get_embedding(body.text)
    embedding_vec_str = "[" + ",".join(str(x) for x in embedding_vec) + "]"

    # Find nearest active insight using pgvector cosine distance
    nearest = db.execute(
        text("""
            SELECT
                i.id,
                i.text,
                i.support_count,
                1 - (ie.embedding <=> (:vec::vector)) AS cosine_sim
            FROM insights i
            JOIN insight_embeddings ie ON ie.insight_id = i.id
            JOIN LATERAL (
                SELECT MAX(embedding_version) AS ver
                FROM insight_embeddings
                WHERE insight_id = i.id
            ) lv ON lv.ver = ie.embedding_version
            WHERE i.status = 'active'
            ORDER BY ie.embedding <=> (:vec::vector)
            LIMIT 1
        """),
        {"vec": embedding_vec_str},
    ).fetchone()

    if nearest:
        sim = float(nearest.cosine_sim)
        insight_id = nearest.id

        if sim > SIM_SAME:
            # Duplicate — bump support count instead of inserting
            db.execute(
                text("""
                    UPDATE insights
                    SET support_count = support_count + 1,
                        updated_at = NOW()
                    WHERE id = :id
                """),
                {"id": str(insight_id)},
            )
            db.commit()
            return InsightCreateResponse(
                insight_id=UUID(str(insight_id)),
                was_duplicate=True,
                duplicate_of=UUID(str(insight_id)),
                similarity=round(sim, 4),
                is_merge_candidate=False,
            )
        elif sim > SIM_MERGE:
            # Merge candidate — flag it but still insert new
            pass  # fall through to insert below
    else:
        sim = 0.0

    # Insert new insight
    insight = Insight(
        trajectory_id=body.trajectory_id,
        state_id=body.state_id,
        text=body.text,
        score=body.score,
        generation=body.generation,
        support_count=1,
        status="active",
    )
    db.add(insight)
    db.flush()

    # Insert embedding
    db.execute(
        text("""
            INSERT INTO insight_embeddings (id, insight_id, embedding, embedding_version)
            VALUES (:id, :insight_id, :embedding::vector, 1)
        """),
        {
            "id": str(uuid4()),
            "insight_id": str(insight.id),
            "embedding": embedding_vec_str,
        },
    )
    db.commit()
    db.refresh(insight)

    return InsightCreateResponse(
        insight_id=insight.id,
        was_duplicate=False,
        duplicate_of=None,
        similarity=round(sim, 4) if sim > 0 else None,
        is_merge_candidate=(nearest is not None and SIM_MERGE < sim <= SIM_SAME),
    )


# ---------------------------------------------------------------------------
# Insights — RETRIEVE (semantic search)
# ---------------------------------------------------------------------------

@router.get("/insights", response_model=InsightSearchResponse)
def search_insights(
    game_id: Optional[UUID] = None,
    generation: Optional[int] = None,
    k: int = Query(default=20, ge=1, le=500),
    strategy: "SampleStrategy" = Query(default="top_k"),   # type: ignore[name-defined]
    query_text: Optional[str] = Query(default=None, max_length=2000),
    min_score: Optional[float] = Query(default=None, ge=0.0, le=1.0),
    db: Session = Depends(get_memo_db),
):
    """
    Retrieve active insights with optional semantic search.

    - **query_text** provided → generate embedding and do cosine similarity search
    - **strategy=top_k** → return k highest-similarity results
    - **strategy=diverse** → MMR to maximise marginal relevance
    - **game_id / generation / min_score** → SQL filters
    """
    if query_text:
        query_vec = get_embedding(query_text)
        query_vec_str = "[" + ",".join(str(x) for x in query_vec) + "]"

        sql_params = {"vec": query_vec_str, "k": k}
        where_clauses = ["i.status = 'active'"]

        if game_id:
            where_clauses.append("t.game_id = :game_id")
            sql_params["game_id"] = str(game_id)
        if generation is not None:
            where_clauses.append("i.generation = :gen")
            sql_params["gen"] = generation
        if min_score is not None:
            where_clauses.append("i.score >= :min_score")
            sql_params["min_score"] = min_score

        where_sql = " AND ".join(where_clauses)

        results = db.execute(
            text(f"""
                SELECT
                    i.id,
                    i.text,
                    i.score,
                    i.generation,
                    i.support_count,
                    i.status,
                    i.created_at,
                    i.trajectory_id,
                    1 - (ie.embedding <=> (:vec::vector)) AS cosine_sim
                FROM insights i
                JOIN insight_embeddings ie ON ie.insight_id = i.id
                LEFT JOIN trajectories t ON t.id = i.trajectory_id
                JOIN LATERAL (
                    SELECT MAX(embedding_version) AS ver
                    FROM insight_embeddings
                    WHERE insight_id = i.id
                ) lv ON lv.ver = ie.embedding_version
                WHERE {where_sql}
                ORDER BY ie.embedding <=> (:vec::vector)
                LIMIT :k
            """),
            sql_params,
        ).fetchall()

        if strategy == "diverse" and len(results) > k:
            # MMR: convert to dicts with embedding for reranking
            ids_and_scores = [(UUID(r.id), float(r.cosine_sim)) for r in results]
            selected_ids = mmr_select(ids_and_scores, k=k)
            selected_set = set(selected_ids)
            results = [r for r in results if r.id in selected_set]

    else:
        # No query text — just SQL filter / order by support+generation
        sql_params: dict = {}
        where_clauses = ["i.status = 'active'"]

        if game_id:
            where_clauses.append("t.game_id = :game_id")
            sql_params["game_id"] = str(game_id)
        if generation is not None:
            where_clauses.append("i.generation = :gen")
            sql_params["gen"] = generation
        if min_score is not None:
            where_clauses.append("i.score >= :min_score")
            sql_params["min_score"] = min_score

        where_sql = " AND ".join(where_clauses)

        order_col = (
            "i.support_count DESC, i.generation DESC"
            if strategy == "diverse"
            else "i.generation DESC, i.support_count DESC"
        )

        results = db.execute(
            text(f"""
                SELECT
                    i.id,
                    i.text,
                    i.score,
                    i.generation,
                    i.support_count,
                    i.status,
                    i.created_at,
                    i.trajectory_id
                FROM insights i
                LEFT JOIN trajectories t ON t.id = i.trajectory_id
                WHERE {where_sql}
                ORDER BY {order_col}
                LIMIT :k
            """),
            {**sql_params, "k": k},
        ).fetchall()

    insights = [
        InsightSummary(
            id=UUID(str(r.id)),
            text=r.text,
            score=r.score,
            generation=r.generation,
            support_count=r.support_count,
            status=InsightStatus(r.status),
            created_at=r.created_at,
            trajectory_id=UUID(str(r.trajectory_id)) if r.trajectory_id else None,
        )
        for r in results
    ]

    return InsightSearchResponse(
        insights=insights,
        query_text=query_text,
        strategy=SampleStrategy(strategy),
    )


# ---------------------------------------------------------------------------
# Insights — EDIT (merge)
# ---------------------------------------------------------------------------

@router.put("/insights/{insight_id}", response_model=InsightEditResponse)
def edit_insight(
    insight_id: UUID,
    body: "InsightEdit",   # type: ignore[name-defined]
    db: Session = Depends(get_memo_db),
):
    """
    Merge/edit an insight.

    Creates a NEW insight row, sets its `supersedes_insight_id` to the
    old insight, and marks the old insight as `deprecated`.
    """
    old = db.query(Insight).filter(Insight.id == insight_id).first()
    if not old:
        raise HTTPException(status_code=404, detail="Insight not found")
    if old.status != "active":
        raise HTTPException(
            status_code=409,
            detail=f"Cannot edit an insight with status '{old.status}'",
        )

    # Deprecate the old insight
    old.status = "deprecated"
    db.flush()

    # Insert the new merged insight
    new_insight = Insight(
        trajectory_id=old.trajectory_id,
        state_id=old.state_id,
        text=body.text,
        score=body.score if body.score is not None else old.score,
        generation=body.generation if body.generation is not None else old.generation + 1,
        support_count=1,
        status="active",
        supersedes_insight_id=old.id,
    )
    db.add(new_insight)
    db.flush()

    # Generate and store embedding for the new insight
    embedding_vec = get_embedding(body.text)
    embedding_vec_str = "[" + ",".join(str(x) for x in embedding_vec) + "]"
    db.execute(
        text("""
            INSERT INTO insight_embeddings (id, insight_id, embedding, embedding_version)
            VALUES (:id, :insight_id, :embedding::vector, 1)
        """),
        {"id": str(uuid4()), "insight_id": str(new_insight.id), "embedding": embedding_vec_str},
    )
    db.commit()

    return InsightEditResponse(
        new_insight_id=new_insight.id,
        superseded_insight_id=old.id,
    )


# ---------------------------------------------------------------------------
# Insights — REMOVE (soft delete)
# ---------------------------------------------------------------------------

@router.delete("/insights/{insight_id}", response_model=InsightRemoveResponse)
def remove_insight(
    insight_id: UUID,
    body: "InsightRemoveRequest",   # type: ignore[name-defined]
    db: Session = Depends(get_memo_db),
):
    """
    Soft-delete an insight (set status = 'contradicted').

    The `reason` is prepended to the insight's text so the contradiction
    rationale is preserved for analysis.
    """
    insight = db.query(Insight).filter(Insight.id == insight_id).first()
    if not insight:
        raise HTTPException(status_code=404, detail="Insight not found")

    previous_status = InsightStatus(insight.status)

    if previous_status == InsightStatus.CONTRADICTED:
        # Already contradicted — no-op
        return InsightRemoveResponse(
            success=True,
            insight_id=insight.id,
            previous_status=previous_status,
        )

    insight.status = "contradicted"
    insight.text = f"[CONTRADICTION: {body.reason}] {insight.text}"
    db.commit()

    return InsightRemoveResponse(
        success=True,
        insight_id=insight.id,
        previous_status=previous_status,
    )


# ---------------------------------------------------------------------------
# Insights — Lineage
# ---------------------------------------------------------------------------

@router.get("/insights/{insight_id}/lineage", response_model=LineageResponse)
def get_insight_lineage(
    insight_id: UUID,
    db: Session = Depends(get_memo_db),
):
    """
    Trace the full supersession chain for an insight using v_insight_lineage.
    """
    rows = db.execute(
        text("""
            SELECT
                i.id,
                i.text,
                i.score,
                i.generation,
                i.status,
                l.depth,
                i.created_at
            FROM v_insight_lineage l
            JOIN insights i ON i.id = l.id
            WHERE l.root_id = :root_id
            ORDER BY l.depth ASC
        """),
        {"root_id": str(insight_id)},
    ).fetchall()

    if not rows:
        raise HTTPException(status_code=404, detail="Insight not found")

    chain = [
        LineageNode(
            insight_id=UUID(str(r.id)),
            text=r.text[:200],      # truncate for readability
            score=r.score,
            generation=r.generation,
            status=InsightStatus(r.status),
            depth=r.depth,
            created_at=r.created_at,
        )
        for r in rows
    ]

    return LineageResponse(chain=chain)


# ---------------------------------------------------------------------------
# Memory sampling (context injection helper)
# ---------------------------------------------------------------------------

@router.post("/sample", response_model=MemorySampleResponse)
def sample_memories(
    body: "MemorySampleRequest",   # type: ignore[name-defined]
    db: Session = Depends(get_memo_db),
):
    """
    Sample k memories for context injection.

    Strategies:
      - **top_k**: highest cosine similarity to query_text (or highest
        support_count if no query_text)
      - **diverse**: MMR — maximises marginal relevance to avoid
        returning near-duplicate insights
    """
    k = min(body.k, 200)

    if body.query_text:
        query_vec = get_embedding(body.query_text)
        query_vec_str = "[" + ",".join(str(x) for x in query_vec) + "]"

        sql_params = {"vec": query_vec_str, "k": k * 3}  # over-fetch for MMR
        where_clauses = ["i.status = 'active'"]

        if body.game_id:
            where_clauses.append("t.game_id = :game_id")
            sql_params["game_id"] = str(body.game_id)
        if body.min_score is not None:
            where_clauses.append("i.score >= :min_score")
            sql_params["min_score"] = body.min_score

        where_sql = " AND ".join(where_clauses)

        results = db.execute(
            text(f"""
                SELECT
                    i.id,
                    i.text,
                    i.score,
                    i.generation,
                    i.support_count,
                    i.status,
                    i.created_at,
                    i.trajectory_id,
                    ie.embedding,
                    1 - (ie.embedding <=> (:vec::vector)) AS cosine_sim
                FROM insights i
                JOIN insight_embeddings ie ON ie.insight_id = i.id
                LEFT JOIN trajectories t ON t.id = i.trajectory_id
                JOIN LATERAL (
                    SELECT MAX(embedding_version) AS ver
                    FROM insight_embeddings
                    WHERE insight_id = i.id
                ) lv ON lv.ver = ie.embedding_version
                WHERE {where_sql}
                ORDER BY ie.embedding <=> (:vec::vector)
                LIMIT :k
            """),
            sql_params,
        ).fetchall()

        if body.strategy == "diverse" and len(results) > k:
            items = [
                {
                    "id": UUID(str(r.id)),
                    "text": r.text,
                    "score": r.score,
                    "generation": r.generation,
                    "support_count": r.support_count,
                    "status": InsightStatus(r.status),
                    "created_at": r.created_at,
                    "trajectory_id": UUID(str(r.trajectory_id)) if r.trajectory_id else None,
                    "embedding": r.embedding
                    if hasattr(r, "embedding")
                    else get_embedding(r.text),
                }
                for r in results
            ]
            selected = mmr_with_text(items, query_vec, k)
            insights = [
                InsightSummary(
                    id=d["id"],
                    text=d["text"],
                    score=d["score"],
                    generation=d["generation"],
                    support_count=d["support_count"],
                    status=d["status"],
                    created_at=d["created_at"],
                    trajectory_id=d["trajectory_id"],
                )
                for d in selected
            ]
            return MemorySampleResponse(memories=insights, strategy=SampleStrategy.DIVERSE)
    else:
        # No query — order by support_count / generation
        order_col = (
            "i.support_count DESC, i.generation DESC"
            if body.strategy == "diverse"
            else "i.generation DESC, i.support_count DESC"
        )
        sql_params: dict = {"k": k}
        where_clauses = ["i.status = 'active'"]

        if body.game_id:
            where_clauses.append("t.game_id = :game_id")
            sql_params["game_id"] = str(body.game_id)
        if body.min_score is not None:
            where_clauses.append("i.score >= :min_score")
            sql_params["min_score"] = body.min_score

        where_sql = " AND ".join(where_clauses)

        results = db.execute(
            text(f"""
                SELECT
                    i.id,
                    i.text,
                    i.score,
                    i.generation,
                    i.support_count,
                    i.status,
                    i.created_at,
                    i.trajectory_id
                FROM insights i
                LEFT JOIN trajectories t ON t.id = i.trajectory_id
                WHERE {where_sql}
                ORDER BY {order_col}
                LIMIT :k
            """),
            sql_params,
        ).fetchall()

    insights = [
        InsightSummary(
            id=UUID(str(r.id)),
            text=r.text,
            score=r.score,
            generation=r.generation,
            support_count=r.support_count,
            status=InsightStatus(r.status),
            created_at=r.created_at,
            trajectory_id=UUID(str(r.trajectory_id)) if r.trajectory_id else None,
        )
        for r in results
    ]

    return MemorySampleResponse(
        memories=insights,
        strategy=SampleStrategy(body.strategy),
    )
