"""
pgvector Client for Gymnasium RL Harness

Wraps the rl_memories table with Python + psycopg2.
Embedding via Ollama HTTP API (all-mpnet-base-v2).

Assumes rl_memories table exists with schema:
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid()
  state_embedded  vector(768)
  state_text      TEXT
  action          TEXT
  reward          REAL
  next_state_text TEXT
  episode_id      INTEGER
  episode_return  REAL
  importance       DOUBLE PRECISION DEFAULT 5.0
  created_at      TIMESTAMP DEFAULT NOW()
  created_at_ts   BIGINT  (Unix epoch seconds, for recency scoring)

If table doesn't exist it will be auto-created on first connect.
"""

import os
import json
import uuid
import math
import time
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field

import psycopg2
import psycopg2.extras
import requests


# ============ CONFIGURATION ============

@dataclass
class PgVectorConfig:
    connection_string: str = ""
    ollama_url: str = "http://localhost:11434"
    embedding_model: str = "all-mpnet-base-v2"
    dimensions: int = 768
    hybrid_weights: Dict[str, float] = field(default_factory=lambda: {
        "similarity": 0.5,
        "importance": 0.3,
        "recency": 0.2
    })

    @classmethod
    def from_env(cls) -> "PgVectorConfig":
        return cls(
            connection_string=os.environ.get(
                "DATABASE_URL",
                "postgresql://postgres:postgres@localhost:5432/postgres"
            ),
            ollama_url=os.environ.get("OLLAMA_URL", "http://localhost:11434"),
            embedding_model=os.environ.get("EMBEDDING_MODEL", "all-mpnet-base-v2"),
        )


# ============ EMBEDDING SERVICE ============

class OllamaEmbedder:
    """Embed text using Ollama's /api/embeddings endpoint."""

    def __init__(self, base_url: str, model: str, dimensions: int):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.dimensions = dimensions
        self._embedding_cache: Dict[str, List[float]] = {}

    def embed(self, text: str, use_cache: bool = True) -> List[float]:
        """Embed a single text string."""
        if use_cache and text in self._embedding_cache:
            return self._embedding_cache[text]

        url = f"{self.base_url}/api/embeddings"
        payload = {"model": self.model, "prompt": text}
        try:
            resp = requests.post(url, json=payload, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            embedding = data.get("embedding")
            if not embedding:
                raise ValueError(f"No embedding in response: {data}")
            if len(embedding) != self.dimensions:
                raise ValueError(
                    f"Expected {self.dimensions} dims, got {len(embedding)}"
                )
            if use_cache:
                self._embedding_cache[text] = embedding
            return embedding
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"Ollama embed failed: {e}") from e

    def embed_state(self, state: Any) -> List[float]:
        """Convert a Gymnasium state (numpy array / list) to a string then embed."""
        text = self._state_to_text(state)
        return self.embed(text)

    @staticmethod
    def _state_to_text(state: Any) -> str:
        """Flatten a Gymnasium state observation to a human-readable string."""
        if hasattr(state, "tolist"):
            state = state.tolist()
        if isinstance(state, (list, tuple)):
            parts = []
            for i, v in enumerate(state):
                if isinstance(v, (int, float)):
                    parts.append(f"x{i}={v:.4f}")
                else:
                    parts.append(f"x{i}={v}")
            return ", ".join(parts)
        return str(state)

    def clear_cache(self) -> None:
        self._embedding_cache.clear()


# ============ DATABASE CLIENT ============

class PgVectorClient:
    """
    Direct Python client for the rl_memories pgvector table.

    Provides:
      - store_experience()
      - recall()          → hybrid search for similar states
      - get_stats()
      - get_episode_memories()
      - ensure_table()     → auto-create table if missing
    """

    def __init__(self, config: Optional[PgVectorConfig] = None):
        self.config = config or PgVectorConfig.from_env()
        self._pool = None
        self._embedder = OllamaEmbedder(
            self.config.ollama_url,
            self.config.embedding_model,
            self.config.dimensions,
        )

    # ---- connection ----

    def _get_conn(self):
        kw = {}
        if "render.com" in self.config.connection_string:
            kw["sslmode"] = "require"
        return psycopg2.connect(self.config.connection_string, **kw)

    def _conn(self):
        return self._get_conn()

    # ---- table management ----

    def ensure_table(self) -> None:
        """Create rl_memories table + indexes if they don't exist."""
        conn = self._conn()
        try:
            with conn.cursor() as cur:
                # Enable pgvector
                cur.execute("CREATE EXTENSION IF NOT EXISTS vector")

                # Create table
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS rl_memories (
                        id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        state_embedded  vector(768),
                        state_text      TEXT,
                        action          TEXT,
                        reward          REAL,
                        next_state_text TEXT,
                        episode_id      INTEGER,
                        episode_return  REAL,
                        importance      DOUBLE PRECISION DEFAULT 5.0,
                        created_at      TIMESTAMP DEFAULT NOW(),
                        created_at_ts   BIGINT DEFAULT (
                            EXTRACT(EPOCH FROM NOW())::BIGINT
                        )
                    )
                """)

                # Indexes
                cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_rl_episode
                        ON rl_memories(episode_id)
                """)
                cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_rl_return
                        ON rl_memories(episode_return DESC)
                """)
                cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_rl_importance
                        ON rl_memories(importance DESC)
                """)
                # Vector index — try IVFFlat first, fall back to HNSW
                for idx_sql in [
                    """
                    CREATE INDEX IF NOT EXISTS idx_rl_embedding
                        ON rl_memories USING ivfflat
                        (state_embedded vector_cosine_ops)
                    """,
                    """
                    CREATE INDEX IF NOT EXISTS idx_rl_embedding_hnsw
                        ON rl_memories USING hnsw
                        (state_embedded vector_cosine_ops)
                    """,
                ]:
                    try:
                        cur.execute(idx_sql)
                    except Exception:
                        pass

            conn.commit()
        finally:
            conn.close()

    # ---- core operations ----

    def store_experience(
        self,
        state: Any,
        action: Any,
        reward: float,
        next_state: Any,
        episode_id: int,
        episode_return: float,
        importance: float = 5.0,
    ) -> Dict[str, Any]:
        """
        Store one RL transition (s, a, r, s') as a memory.

        Returns the inserted row dict.
        """
        self.ensure_table()

        state_vec = self._embedder.embed_state(state)
        state_text = self._embedder._state_to_text(state)
        next_text = self._embedder._state_to_text(next_state)
        action_str = str(action)

        conn = self._conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO rl_memories
                        (state_embedded, state_text, action, reward,
                         next_state_text, episode_id, episode_return, importance)
                    VALUES
                        (%s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING *
                    """,
                    (
                        state_vec,
                        state_text,
                        action_str,
                        float(reward),
                        next_text,
                        episode_id,
                        float(episode_return),
                        float(importance),
                    ),
                )
                row = cur.fetchone()
                cols = [desc[0] for desc in cur.description]
                conn.commit()
                return dict(zip(cols, row))
        finally:
            conn.close()

    def store_experience_batch(
        self,
        experiences: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Store multiple experiences in one transaction.
        Each dict: {state, action, reward, next_state, episode_id, episode_return, importance}
        """
        self.ensure_table()

        rows_out = []
        conn = self._conn()
        try:
            for exp in experiences:
                state_vec = self._embedder.embed_state(exp["state"])
                state_text = self._embedder._state_to_text(exp["state"])
                next_text = self._embedder._state_to_text(exp["next_state"])

                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO rl_memories
                            (state_embedded, state_text, action, reward,
                             next_state_text, episode_id, episode_return, importance)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        RETURNING *
                        """,
                        (
                            state_vec,
                            state_text,
                            str(exp["action"]),
                            float(exp["reward"]),
                            next_text,
                            int(exp["episode_id"]),
                            float(exp["episode_return"]),
                            float(exp.get("importance", 5.0)),
                        ),
                    )
                    row = cur.fetchone()
                    cols = [desc[ desc[0] for desc in cur.description]]
                    rows_out.append(dict(zip(cols, row)))
            conn.commit()
        finally:
            conn.close()
        return rows_out

    def recall(
        self,
        state: Any,
        top_k: int = 10,
        min_importance: float = 0.0,
    ) -> List[Dict[str, Any]]:
        """
        Hybrid search for memories similar to the given state.
        Returns top_k results scored by:
          similarity(50%) + importance(30%) + recency(20%)
        """
        self.ensure_table()

        state_vec = self._embedder.embed_state(state)
        conn = self._conn()
        try:
            with conn.cursor() as cur:
                now_ts = time.time()
                cur.execute(
                    """
                    UPDATE rl_memories
                    SET importance = importance  -- touch row implicitly
                    WHERE id IN (
                        SELECT id FROM rl_memories
                        ORDER BY state_embedded <=> %s::vector
                        LIMIT %s
                    )
                    """,
                    (state_vec, top_k * 3),
                )
                conn.commit()

                with conn.cursor() as cur:
                    cur.execute(
                        f"""
                        SELECT *,
                            0.5 * (1 - (state_embedded <=> %s::vector))
                            + 0.3 * (importance / 10.0)
                            + 0.2 * LEAST(1.0, %s / ( %s - created_at_ts + 1 ))
                            AS hybrid_score
                        FROM rl_memories
                        WHERE importance >= %s
                        ORDER BY hybrid_score DESC
                        LIMIT %s
                        """,
                        (
                            state_vec,
                            now_ts,        # now_ts
                            now_ts,        # same
                            min_importance,
                            top_k,
                        ),
                    )
                    rows = cur.fetchall()
                    cols = [d[0] for d in cur.description]
                    results = []
                    for row in rows:
                        d = dict(zip(cols, row))
                        # Convert vector to list if needed
                        vecs = d.get("state_embedded")
                        if vecs is not None and hasattr(vecs, "tolist"):
                            d["state_embedded"] = vecs.tolist()
                        results.append(d)
                    return results
        finally:
            conn.close()

    def get_episode_memories(
        self, episode_id: int
    ) -> List[Dict[str, Any]]:
        """Fetch all steps from a specific episode, ordered by step."""
        self.ensure_table()
        conn = self._conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT * FROM rl_memories
                    WHERE episode_id = %s
                    ORDER BY created_at ASC
                    """,
                    (episode_id,),
                )
                rows = cur.fetchall()
                cols = [d[0] for d in cur.description]
                return [dict(zip(cols, row)) for row in rows]
        finally:
            conn.close()

    def get_stats(self) -> Dict[str, Any]:
        """Return aggregate stats about the rl_memories table."""
        self.ensure_table()
        conn = self._conn()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) AS total FROM rl_memories")
                total = cur.fetchone()[0]

                cur.execute(
                    """
                    SELECT
                        COUNT(*)        AS count,
                        AVG(reward)     AS avg_reward,
                        AVG(episode_return) AS avg_episode_return,
                        MAX(episode_id) AS max_episode
                    FROM rl_memories
                    """
                )
                row = cur.fetchone()
                return {
                    "total_memories": total,
                    "avg_reward": float(row[1]) if row[1] else 0.0,
                    "avg_episode_return": float(row[2]) if row[2] else 0.0,
                    "max_episode": int(row[3]) if row[3] else 0,
                }
        finally:
            conn.close()

    def get_best_episodes(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Return the episodes with highest average returns."""
        self.ensure_table()
        conn = self._conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT
                        episode_id,
                        AVG(episode_return) AS avg_return,
                        MAX(episode_return) AS max_return,
                        COUNT(*)             AS steps
                    FROM rl_memories
                    GROUP BY episode_id
                    ORDER BY avg_return DESC
                    LIMIT %s
                    """,
                    (limit,),
                )
                rows = cur.fetchall()
                cols = [d[0] for d in cur.description]
                return [dict(zip(cols, row)) for row in rows]
        finally:
            conn.close()

    def delete_episode(self, episode_id: int) -> int:
        """Delete all memories for a given episode. Returns row count."""
        self.ensure_table()
        conn = self._conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM rl_memories WHERE episode_id = %s",
                    (episode_id,),
                )
                conn.commit()
                return cur.rowcount
        finally:
            conn.close()

    def close(self) -> None:
        if self._pool:
            self._pool.close()
