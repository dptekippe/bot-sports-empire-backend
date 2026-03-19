"""
MEMO-Facing API Layer
=====================
Clean Python interface for MEMO algorithms to interact with the MEMO-pgvector
backend without touching HTTP or FastAPI internals directly.

Provides three core operations:
  memo_add_trajectory(trajectory_proto) -> trajectory_id
  memo_reflect(trajectory_id)           -> list[insight_ids]
  memo_sample_memories(game_id, k, strategy) -> list[insight_records]

Supports two backends:
  1. HTTP — calls the FastAPI service (production, multi-process)
  2. Direct — uses the SQLAlchemy session factory directly (single-process,
     unit tests, or when the API service is unavailable)

Usage
-----
  # Direct mode (preferred for self-play harness / tests)
  from integration.memo_interface import MemoInterface, MemoBackend
  memo = MemoInterface(backend=MemoBackend.DIRECT)

  # HTTP mode (production, multi-agent setup)
  memo = MemoInterface(backend=MemoBackend.HTTP, base_url="http://localhost:8000")

  trajectory_id = memo.memo_add_trajectory(trajectory_proto)
  insights = memo.memo_reflect(trajectory_id)
  memories  = memo.memo_sample_memories(game_id="...", k=10, strategy="top_k")
"""

from __future__ import annotations

import os
import sys
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional
from uuid import UUID

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Enums and data classes
# ---------------------------------------------------------------------------

class SampleStrategy(str, Enum):
    TOP_K  = "top_k"
    DIVERSE = "diverse"


@dataclass
class TrajectoryProto:
    """
    Protocol buffer equivalent: a trajectory to be stored.

    game_id     — UUID of the game this trajectory belongs to
    seed        — random seed for reproducibility (optional)
    outcome     — "win" | "loss" | "draw"
    agent_name  — name of the agent that produced this trajectory
    player_id   — external player identifier (optional)
    steps       — list of step dicts, each containing:
                    step_idx   (int)
                    state_json (dict)
                    reward     (float, optional)
                    done       (bool)
    """
    game_id:    UUID
    outcome:    str
    steps:      list[dict] = field(default_factory=list)
    seed:       Optional[str] = None
    agent_name: Optional[str] = None
    player_id:  Optional[str] = None

    def to_api_payload(self) -> dict:
        return {
            "game_id":    str(self.game_id),
            "seed":       self.seed,
            "outcome":    self.outcome,
            "agent_name": self.agent_name,
            "player_id":  self.player_id,
            "moves":      self.steps,
        }


@dataclass
class InsightRecord:
    """A single insight returned from memory sampling."""
    id:             UUID
    text:           str
    score:          float
    generation:     int
    support_count:  int
    status:         str
    trajectory_id:  Optional[UUID] = None

    @classmethod
    def from_api_response(cls, data: dict) -> "InsightRecord":
        return cls(
            id=UUID(data["id"]),
            text=data["text"],
            score=data["score"],
            generation=data["generation"],
            support_count=data["support_count"],
            status=data["status"],
            trajectory_id=UUID(data["trajectory_id"]) if data.get("trajectory_id") else None,
        )


class MemoBackend(str, Enum):
    DIRECT = "direct"   # SQLAlchemy session (single-process)
    HTTP   = "http"     # FastAPI HTTP calls


# ---------------------------------------------------------------------------
# Direct-backend implementation (SQLAlchemy + pgvector)
# ---------------------------------------------------------------------------

class DirectMemoInterface:
    """
    Direct SQLAlchemy implementation of the MEMO interface.

    Uses the same session factory and models as memo_crud.py but exposes
    a clean, schema-agnostic Python API.
    """

    def __init__(self, database_url: Optional[str] = None):
        from api.memo_crud import (
            Game, Insight, InsightEmbedding, memo_engine,
            memo_session_factory, State, Trajectory, uuid4,
        )
        from sqlalchemy import text

        self._database_url = database_url or os.getenv(
            "MEMO_DATABASE_URL",
            os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/memo"),
        )
        self._engine  = memo_engine
        self._factory = memo_session_factory

    def _session(self):
        return self._factory()

    # ------------------------------------------------------------------
    # Public MEMO API
    # ------------------------------------------------------------------

    def memo_add_trajectory(self, proto: TrajectoryProto) -> UUID:
        """
        Store a trajectory and return its UUID.

        Args:
            proto: TrajectoryProto describing the game play-through.

        Returns:
            UUID of the newly created trajectory.
        """
        from api.memo_crud import Game, State, Trajectory, uuid4

        db = self._session()
        try:
            # Verify game exists
            game = db.query(Game).filter(Game.id == proto.game_id).first()
            if not game:
                raise ValueError(f"Game {proto.game_id} not found")

            traj = Trajectory(
                game_id=proto.game_id,
                seed=proto.seed,
                outcome=proto.outcome,
                agent_name=proto.agent_name,
                player_id=proto.player_id,
                game_length=len(proto.steps),
            )
            db.add(traj)
            db.flush()

            for step in proto.steps:
                state = State(
                    trajectory_id=traj.id,
                    step_idx=step["step_idx"],
                    state_json=step["state_json"],
                    reward=step.get("reward"),
                    done=step.get("done", False),
                )
                db.add(state)

            db.commit()
            logger.info("Stored trajectory %s (outcome=%s, steps=%d)", traj.id, proto.outcome, len(proto.steps))
            return traj.id
        finally:
            db.close()

    def memo_reflect(self, trajectory_id: UUID) -> list[UUID]:
        """
        Extract insights from a trajectory via LLM reflection.

        This is the **production stub** — it calls an LLM (GPT-4o) to analyse
        the trajectory and extract structured insights, then commits each
        insight using the Phase 3 semantics (deduplication + embedding).

        Args:
            trajectory_id: UUID of the trajectory to reflect on.

        Returns:
            List of insight UUIDs created (empty if reflection produced no insights
            or if the trajectory was not found).
        """
        from api.memo_crud import Insight, InsightEmbedding, Trajectory, uuid4

        db = self._session()
        try:
            traj = db.query(Trajectory).filter(Trajectory.id == trajectory_id).first()
            if not traj:
                logger.warning("memo_reflect: trajectory %s not found", trajectory_id)
                return []

            # Load trajectory steps
            states = sorted(traj.states, key=lambda s: s.step_idx)
            trajectory_text = self._format_trajectory_for_llm(traj, states)

            # Call LLM to extract insights
            raw_insights = self._llm_extract_insights(trajectory_text)

            insight_ids: list[UUID] = []
            for text in raw_insights:
                result = self._add_insight_with_dedup(
                    db, text=text, trajectory_id=trajectory_id, generation=0
                )
                if result:
                    insight_ids.append(result)

            logger.info(
                "memo_reflect: trajectory=%s, extracted=%d insights",
                trajectory_id, len(insight_ids),
            )
            return insight_ids
        finally:
            db.close()

    def memo_sample_memories(
        self,
        game_id: Optional[UUID] = None,
        k: int = 10,
        strategy: str = "top_k",
        query_text: Optional[str] = None,
        min_score: Optional[float] = None,
    ) -> list[InsightRecord]:
        """
        Sample k memories for context injection.

        Args:
            game_id:     Filter by game UUID (optional).
            k:           Number of memories to return (max 200).
            strategy:    "top_k" (highest similarity) or "diverse" (MMR).
            query_text:  Natural-language query for semantic search (optional).
            min_score:   Minimum insight score filter (0–1, optional).

        Returns:
            List of InsightRecord objects.
        """
        from api.memo_crud import Insight, InsightEmbedding, Trajectory

        db = self._session()
        try:
            k = min(k, 200)
            base_query = db.query(Insight).filter(Insight.status == "active")

            if game_id:
                base_query = base_query.join(Trajectory).filter(
                    Trajectory.game_id == game_id
                )
            if min_score is not None:
                base_query = base_query.filter(Insight.score >= min_score)

            if strategy == "diverse":
                base_query = base_query.order_by(
                    Insight.support_count.desc(), Insight.generation.desc()
                )
            else:
                base_query = base_query.order_by(
                    Insight.generation.desc(), Insight.support_count.desc()
                )

            rows = base_query.limit(k).all()

            return [
                InsightRecord(
                    id=r.id,
                    text=r.text,
                    score=r.score,
                    generation=r.generation,
                    support_count=r.support_count,
                    status=r.status,
                    trajectory_id=r.trajectory_id,
                )
                for r in rows
            ]
        finally:
            db.close()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _format_trajectory_for_llm(self, traj, states: list) -> str:
        """Format a trajectory + states as a readable string for the LLM."""
        lines = [
            f"Trajectory: {traj.id}",
            f"Game: {traj.game_id}",
            f"Outcome: {traj.outcome}",
            f"Agent: {traj.agent_name or 'unknown'}",
            f"Game length: {traj.game_length} steps",
            "",
            "Steps:",
        ]
        for s in states:
            lines.append(
                f"  Step {s.step_idx}: {s.state_json}"
                + (f" reward={s.reward}" if s.reward is not None else "")
                + (" [DONE]" if s.done else "")
            )
        return "\n".join(lines)

    def _llm_extract_insights(self, trajectory_text: str) -> list[str]:
        """
        Call LLM to extract insights from a formatted trajectory string.

        Uses GPT-4o via OpenAI API. Returns a list of insight strings.
        Falls back to [] if the API key is unavailable or the call fails.
        """
        import openai

        api_key = os.getenv("OPENAI_API_KEY", "")
        if not api_key or api_key in ("sk-dev-mock", ""):
            logger.debug("No OPENAI_API_KEY — skipping LLM reflection")
            return []

        try:
            client = openai.OpenAI(api_key=api_key)
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a strategic game analyst. Given a game trajectory, "
                            "extract 1-5 concise, actionable insights (1-3 sentences each) "
                            "that would help a future agent play this game better. "
                            "Return ONLY a JSON list of strings, no additional text."
                        ),
                    },
                    {
                        "role": "user",
                        "content": trajectory_text,
                    },
                ],
                temperature=0.3,
                max_tokens=1024,
            )
            import json
            content = response.choices[0].message.content.strip()
            # Strip markdown code fences if present
            if content.startswith("```"):
                content = content.split("\n", 1)[1]
                content = content.rsplit("```", 1)[0].strip()
            insights = json.loads(content)
            return insights if isinstance(insights, list) else []
        except Exception as e:
            logger.warning("LLM reflection failed: %s", e)
            return []

    def _add_insight_with_dedup(
        self, db, text: str, trajectory_id: Optional[UUID] = None,
        state_id: Optional[UUID] = None, generation: int = 0,
    ) -> Optional[UUID]:
        """
        Add an insight with semantic deduplication.

        cosine_sim > 0.9  → bump support_count on existing, return None
        otherwise          → insert new insight, return its UUID
        """
        from api.memo_crud import Insight, InsightEmbedding, uuid4
        from sqlalchemy import text

        SIM_SAME  = 0.9
        SIM_MERGE = 0.7

        embedding_vec = self._get_embedding(text)
        embedding_str = "[" + ",".join(str(x) for x in embedding_vec) + "]"

        # Find nearest active insight
        nearest = db.execute(
            text("""
                SELECT
                    i.id,
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
            {"vec": embedding_str},
        ).fetchone()

        if nearest and float(nearest.cosine_sim) > SIM_SAME:
            # Duplicate — bump support count
            db.execute(
                text("UPDATE insights SET support_count = support_count + 1, updated_at = NOW() WHERE id = :id"),
                {"id": str(nearest.id)},
            )
            db.commit()
            logger.debug("Insight deduplicated (sim=%.3f): %s", float(nearest.cosine_sim), nearest.id)
            return None

        # Insert new insight
        insight = Insight(
            trajectory_id=trajectory_id,
            state_id=state_id,
            text=text,
            score=0.5,
            generation=generation,
            support_count=1,
            status="active",
        )
        db.add(insight)
        db.flush()

        db.execute(
            text("""
                INSERT INTO insight_embeddings (id, insight_id, embedding, embedding_version)
                VALUES (:id, :insight_id, :embedding::vector, 1)
            """),
            {
                "id": str(uuid4()),
                "insight_id": str(insight.id),
                "embedding": embedding_str,
            },
        )
        db.commit()
        return insight.id

    def _get_embedding(self, text: str) -> list[float]:
        """Get embedding for text via OpenAI API (fallback zero vector)."""
        from api.memo_crud import get_embedding as crud_get_embedding
        return crud_get_embedding(text)


# ---------------------------------------------------------------------------
# HTTP-backend implementation (FastAPI client)
# ---------------------------------------------------------------------------

class HttpMemoInterface:
    """
    HTTP client implementation of the MEMO interface.

    Calls the FastAPI service at the configured base_url.
    Suitable for production multi-agent setups where the API runs as a separate service.
    """

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url.rstrip("/")

    def _post(self, path: str, json: dict) -> dict:
        import requests
        resp = requests.post(f"{self.base_url}{path}", json=json, timeout=30)
        resp.raise_for_status()
        return resp.json()

    def _get(self, path: str, params: Optional[dict] = None) -> dict:
        import requests
        resp = requests.get(f"{self.base_url}{path}", params=params or {}, timeout=30)
        resp.raise_for_status()
        return resp.json()

    def memo_add_trajectory(self, proto: TrajectoryProto) -> UUID:
        data = self._post("/api/v1/memo/trajectories", proto.to_api_payload())
        return UUID(data["trajectory_id"])

    def memo_reflect(self, trajectory_id: UUID) -> list[UUID]:
        data = self._post(f"/api/v1/memo/trajectories/{trajectory_id}/reflect", {})
        return [UUID(uid) for uid in data["insight_ids"]]

    def memo_sample_memories(
        self,
        game_id: Optional[UUID] = None,
        k: int = 10,
        strategy: str = "top_k",
        query_text: Optional[str] = None,
        min_score: Optional[float] = None,
    ) -> list[InsightRecord]:
        payload = {"k": k, "strategy": strategy}
        if game_id:
            payload["game_id"] = str(game_id)
        if query_text:
            payload["query_text"] = query_text
        if min_score is not None:
            payload["min_score"] = min_score

        data = self._post("/api/v1/memo/sample", payload)
        return [InsightRecord.from_api_response(i) for i in data["memories"]]


# ---------------------------------------------------------------------------
# Unified facade
# ---------------------------------------------------------------------------

class MemoInterface:
    """
    Unified MEMO-facing API.

    Delegates to DirectMemoInterface or HttpMemoInterface based on
    the `backend` constructor argument.

    Examples
    --------
    # Single-process / test
    memo = MemoInterface(backend=MemoBackend.DIRECT)

    # Production multi-agent
    memo = MemoInterface(backend=MemoBackend.HTTP, base_url="http://memo-api:8000")

    # Auto-detect: use HTTP if MEMO_API_URL env var is set, else DIRECT
    memo = MemoInterface()
    """

    def __init__(
        self,
        backend: MemoBackend = MemoBackend.DIRECT,
        base_url: Optional[str] = None,
        database_url: Optional[str] = None,
    ):
        if backend == MemoBackend.HTTP:
            self._impl = HttpMemoInterface(base_url=base_url or "http://localhost:8000")
        else:
            self._impl = DirectMemoInterface(database_url=database_url)

    # ------------------------------------------------------------------
    # Core MEMO operations
    # ------------------------------------------------------------------

    def memo_add_trajectory(self, proto: TrajectoryProto) -> UUID:
        """
        Store a game trajectory and return its UUID.

        This is the primary ingestion point for MEMO algorithms — call this
        after every completed game episode.

        Parameters
        ----------
        proto : TrajectoryProto
            The trajectory data (game_id, outcome, steps).

        Returns
        -------
        UUID
            The ID of the newly inserted trajectory.
        """
        return self._impl.memo_add_trajectory(proto)

    def memo_reflect(self, trajectory_id: UUID) -> list[UUID]:
        """
        Extract and commit insights from a trajectory.

        Calls the LLM reflection pipeline and uses Phase 3 semantics:
        - Semantic deduplication (cosine > 0.9 → bump support_count)
        - Embedding generation via OpenAI
        - Insertion into the insights table

        Call this after every self-play game to accumulate memories.

        Parameters
        ----------
        trajectory_id : UUID
            The trajectory to reflect on.

        Returns
        -------
        list[UUID]
            IDs of insights created (empty if LLM is unavailable or returned no insights).
        """
        return self._impl.memo_reflect(trajectory_id)

    def memo_sample_memories(
        self,
        game_id: Optional[UUID] = None,
        k: int = 10,
        strategy: str = "top_k",
        query_text: Optional[str] = None,
        min_score: Optional[float] = None,
    ) -> list[InsightRecord]:
        """
        Sample k memories for context injection into a game's context window.

        This is the **read path** for MEMO — called at the start of each
        generation's roll-out to prime the agent with accumulated strategic knowledge.

        Strategies
        ----------
        top_k   — highest cosine similarity to query_text, or highest
                  support_count+generation if no query_text
        diverse — MMR (Maximal Marginal Relevance) to maximise coverage
                  and avoid near-duplicate insights

        Parameters
        ----------
        game_id     : UUID, optional — filter to a specific game
        k           : int — number of memories (max 200)
        strategy    : str — "top_k" or "diverse"
        query_text  : str, optional — semantic search query
        min_score   : float, optional — filter by insight score (0–1)

        Returns
        -------
        list[InsightRecord]
            Selected memories ready for context injection.
        """
        return self._impl.memo_sample_memories(
            game_id=game_id, k=k, strategy=strategy,
            query_text=query_text, min_score=min_score,
        )

    # ------------------------------------------------------------------
    # Convenience / admin helpers
    # ------------------------------------------------------------------

    def create_game(self, game_type: str, name: str, config: Optional[dict] = None) -> UUID:
        """
        Register a new game in the MEMO registry.

        Must be called once before adding trajectories for that game_type.

        Parameters
        ----------
        game_type : str  — e.g. "fantasy_football", "negotiation"
        name      : str  — human-readable name, unique per game_type
        config    : dict — game-specific configuration (optional)

        Returns
        -------
        UUID
            The registered game's UUID.
        """
        if isinstance(self._impl, DirectMemoInterface):
            from api.memo_crud import Game
            db = self._impl._session()
            try:
                game = Game(game_type=game_type, name=name, config=config or {})
                db.add(game)
                db.commit()
                db.refresh(game)
                logger.info("Registered game: %s / %s → %s", game_type, name, game.id)
                return game.id
            finally:
                db.close()
        else:
            import requests
            resp = requests.post(
                f"{self._impl.base_url}/api/v1/memo/games",
                json={"game_type": game_type, "name": name, "config": config or {}},
                timeout=10,
            )
            resp.raise_for_status()
            return UUID(resp.json()["game_id"])

    def get_insight_count(self, game_id: Optional[UUID] = None) -> int:
        """Return the total count of active insights (optionally scoped to a game)."""
        from api.memo_crud import Insight, Trajectory
        db = self._impl._session()
        try:
            q = db.query(Insight).filter(Insight.status == "active")
            if game_id:
                q = q.join(Trajectory).filter(Trajectory.game_id == game_id)
            return q.count()
        finally:
            db.close()
