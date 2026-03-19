-- =============================================================================
-- MEMO (Memory-Augmented Model Context Optimization) - pgvector Schema
-- =============================================================================
-- Version: 1.0.0
-- Purpose: Semantic memory bank for self-play game trajectory analysis
-- Dependencies: pgvector extension (CREATE EXTENSION IF NOT EXISTS vector;)
-- =============================================================================

-- -----------------------------------------------------------------------------
-- Idempotent Migration Control
-- -----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS schema_migrations (
    version         TEXT        NOT NULL PRIMARY KEY,
    applied_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    description     TEXT
);

-- Lock to prevent concurrent migrations (advisory lock)
SELECT pg_advisory_lock(hash::bigint)
FROM (SELECT hashtext('memo_schema_migration') AS hash) AS lock_;

-- Track this migration
INSERT INTO schema_migrations (version, description)
VALUES ('001_memo_schema_v1', 'Initial MEMO schema with pgvector support')
ON CONFLICT (version) DO NOTHING;

-- -----------------------------------------------------------------------------
-- 1. GAMES TABLE
-- Extensible registry for multiple game types (chess, go, football, etc.)
-- -----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS games (
    id          UUID        NOT NULL DEFAULT gen_random_uuid() PRIMARY KEY,
    game_type   TEXT        NOT NULL,                        -- e.g. 'chess', 'go', 'fantasy_football'
    name        TEXT        NOT NULL,
    config      JSONB       NOT NULL DEFAULT '{}',           -- game-specific configuration
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Prevent duplicate game names per type
    CONSTRAINT games_name_type_unique UNIQUE (game_type, name)
);

-- Index for listing games by type
CREATE INDEX IF NOT EXISTS idx_games_game_type ON games (game_type);

-- =============================================================================
-- 2. TRAJECTORIES TABLE
-- Complete game play-throughs captured for analysis
-- =============================================================================

CREATE TABLE IF NOT EXISTS trajectories (
    id                  UUID        NOT NULL DEFAULT gen_random_uuid() PRIMARY KEY,
    game_id             UUID        NOT NULL REFERENCES games(id) ON DELETE CASCADE,
    seed                TEXT,                                       -- random seed for reproducibility
    outcome             TEXT        NOT NULL CHECK (outcome IN ('win', 'loss', 'draw')),
    agent_name          TEXT,                                       -- which agent/bot played
    player_id           TEXT,                                       -- external player identifier
    total_format_errors INTEGER     NOT NULL DEFAULT 0,
    total_invalid_moves INTEGER     NOT NULL DEFAULT 0,
    game_length         INTEGER     NOT NULL,                        -- number of steps/turns
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Index for querying by game and outcome
    CONSTRAINT trajectories_game_outcome_idx UNIQUE (game_id, outcome, id)
);

CREATE INDEX IF NOT EXISTS idx_trajectories_game_id   ON trajectories (game_id);
CREATE INDEX IF NOT EXISTS idx_trajectories_outcome    ON trajectories (outcome);
CREATE INDEX IF NOT EXISTS idx_trajectories_agent_name ON trajectories (agent_name);
CREATE INDEX IF NOT EXISTS idx_trajectories_created_at ON trajectories (created_at DESC);

-- =============================================================================
-- 3. STATES TABLE
-- Individual game states within a trajectory (step-by-step snapshot)
-- =============================================================================

CREATE TABLE IF NOT EXISTS states (
    id              UUID        NOT NULL DEFAULT gen_random_uuid() PRIMARY KEY,
    trajectory_id   UUID        NOT NULL REFERENCES trajectories(id) ON DELETE CASCADE,
    step_idx        INTEGER     NOT NULL,                        -- position in trajectory (0-indexed)
    state_json      JSONB       NOT NULL,                        -- full state representation
    reward          REAL,
    done            BOOLEAN     NOT NULL DEFAULT FALSE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Each step appears once per trajectory
    CONSTRAINT states_trajectory_step_unique UNIQUE (trajectory_id, step_idx)
);

CREATE INDEX IF NOT EXISTS idx_states_trajectory_id ON states (trajectory_id);
CREATE INDEX IF NOT EXISTS idx_states_step_idx     ON states (trajectory_id, step_idx);

-- =============================================================================
-- 4. INSIGHTS TABLE
-- Structured insights extracted from trajectory analysis
-- Key design: soft deletes, lineage tracking, deduplication support
-- =============================================================================

CREATE TABLE IF NOT EXISTS insights (
    id                      UUID        NOT NULL DEFAULT gen_random_uuid() PRIMARY KEY,
    trajectory_id           UUID        REFERENCES trajectories(id) ON DELETE SET NULL,
    state_id                UUID        REFERENCES states(id)        ON DELETE SET NULL,  -- nullable: some insights span trajectories
    text                    TEXT        NOT NULL,
    score                   REAL        NOT NULL DEFAULT 0.5,         -- confidence/quality score 0-1
    generation              INTEGER     NOT NULL DEFAULT 0,           -- MEMO optimization round (0 = initial)
    support_count           INTEGER     NOT NULL DEFAULT 1,           -- how many trajectories support this
    status                  TEXT        NOT NULL DEFAULT 'active'
                                                CHECK (status IN ('active', 'deprecated', 'contradicted')),
    supersedes_insight_id   UUID        REFERENCES insights(id) ON DELETE SET NULL,  -- lineage chain
    embedding_model          TEXT        NOT NULL DEFAULT 'text-embedding-ada-002',
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Index for semantic search join path: insight → embedding
CREATE INDEX IF NOT EXISTS idx_insights_id              ON insights (id);

-- Index for lineage traversal (find superseded insights)
CREATE INDEX IF NOT EXISTS idx_insights_supersedes      ON insights (supersedes_insight_id) WHERE supersedes_insight_id IS NOT NULL;

-- Index for filtering by status (active insights only in hot path)
CREATE INDEX IF NOT EXISTS idx_insights_status          ON insights (status) WHERE status = 'active';

-- Index for generation-based queries (MEMO round tracking)
CREATE INDEX IF NOT EXISTS idx_insights_generation      ON insights (generation DESC);

-- Index for support_count-based deduplication queries
CREATE INDEX IF NOT EXISTS idx_insights_support_count   ON insights (support_count DESC);

-- Index for time-series queries
CREATE INDEX IF NOT EXISTS idx_insights_created_at      ON insights (created_at DESC);

-- Composite index for the main query: active + generation + support
CREATE INDEX IF NOT EXISTS idx_insights_active_gen_support
    ON insights (status, generation DESC, support_count DESC)
    WHERE status = 'active';

-- =============================================================================
-- 5. INSIGHT_EMBEDDINGS TABLE
-- Pre-computed vector embeddings for fast cosine similarity search
-- Embedding versioning enables re-embedding without data loss
-- =============================================================================

CREATE TABLE IF NOT EXISTS insight_embeddings (
    id                 UUID        NOT NULL DEFAULT gen_random_uuid() PRIMARY KEY,
    insight_id         UUID        NOT NULL REFERENCES insights(id) ON DELETE CASCADE,
    embedding          VECTOR(1536) NOT NULL,                        -- OpenAI ada-002 compatible dim
    embedding_version  INTEGER     NOT NULL DEFAULT 1,
    created_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Only one active embedding per insight per version
    CONSTRAINT insight_embeddings_insight_version_unique UNIQUE (insight_id, embedding_version)
);

-- Index for join path
CREATE INDEX IF NOT EXISTS idx_insight_embeddings_insight_id ON insight_embeddings (insight_id);

-- Index for version lookups
CREATE INDEX IF NOT EXISTS idx_insight_embeddings_version    ON insight_embeddings (embedding_version);

-- =============================================================================
-- pgvector Index: HNSW index for approximate nearest neighbor search
-- hnsw_parameters: m=16, ef_construction=100 (good balance for 1536-dim)
-- =============================================================================

CREATE INDEX IF NOT EXISTS idx_insight_embeddings_embedding_hnsw
    ON insight_embeddings
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 100);

-- Alternative: ivfflat index (faster build, slightly less accurate)
-- Use ivfflat if build time is critical and accuracy can trade off ~5%:
-- CREATE INDEX idx_insight_embeddings_embedding_ivf
--     ON insight_embeddings
--     USING ivfflat (embedding vector_cosine_ops)
--     WITH (lists = 100);

-- =============================================================================
-- Helper function: update updated_at timestamp
-- =============================================================================

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Attach trigger to insights table
DROP TRIGGER IF EXISTS trigger_insights_updated_at ON insights;
CREATE TRIGGER trigger_insights_updated_at
    BEFORE UPDATE ON insights
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- =============================================================================
-- Helper view: active insights with their embeddings (ready for vector search)
-- =============================================================================

CREATE OR REPLACE VIEW v_active_insight_embeddings AS
SELECT
    i.id          AS insight_id,
    i.text,
    i.score,
    i.generation,
    i.support_count,
    i.status,
    i.embedding_model,
    i.created_at,
    ie.embedding,
    ie.embedding_version
FROM insights i
JOIN insight_embeddings ie ON ie.insight_id = i.id
WHERE i.status = 'active'
  AND ie.embedding_version = (
      SELECT MAX(ie2.embedding_version)
      FROM insight_embeddings ie2
      WHERE ie2.insight_id = i.id
  );

-- =============================================================================
-- Helper view: insight lineage tree (for tracing supersession chains)
-- =============================================================================

CREATE OR REPLACE VIEW v_insight_lineage AS
WITH RECURSIVE lineage AS (
    -- Base case: oldest insights (no supersedes)
    SELECT
        id,
        COALESCE(supersedes_insight_id, id) AS root_id,
        0 AS depth,
        ARRAY[status]    AS status_path,
        ARRAY[id::text]  AS id_path
    FROM insights
    WHERE supersedes_insight_id IS NULL

    UNION ALL

    -- Recursive case: newer insights
    SELECT
        i.id,
        l.root_id,
        l.depth + 1,
        l.status_path || i.status,
        l.id_path || i.id::text
    FROM insights i
    JOIN lineage l ON i.supersedes_insight_id = l.id
)
SELECT
    id,
    root_id,
    depth,
    status_path,
    id_path,
    array_length(id_path, 1) AS chain_length
FROM lineage;

-- =============================================================================
-- Release advisory lock
-- =============================================================================

SELECT pg_advisory_unlock(hash::bigint)
FROM (SELECT hashtext('memo_schema_migration') AS hash) AS lock_;

-- =============================================================================
-- SAMPLE QUERIES FOR COMMON OPERATIONS
-- =============================================================================

-- -----------------------------------------------------------------------------
-- Q1: Semantic search - find insights similar to a query embedding
-- Cosine similarity > 0.9 triggers deduplication policy
-- -----------------------------------------------------------------------------
/*
SELECT
    i.id,
    i.text,
    i.score,
    i.generation,
    i.support_count,
    1 - (ie.embedding <=> query_embedding) AS cosine_similarity
FROM insights i
JOIN insight_embeddings ie ON ie.insight_id = i.id
WHERE i.status = 'active'
  AND ie.embedding_version = 1
ORDER BY ie.embedding <=> query_embedding
LIMIT 20;
*/

-- -----------------------------------------------------------------------------
-- Q2: Check for duplicate before inserting (deduplication policy)
-- If any active insight has cosine similarity > 0.9, increment support_count
-- -----------------------------------------------------------------------------
/*
SELECT
    i.id,
    i.text,
    i.support_count,
    1 - (ie.embedding <=> new_embedding) AS cosine_similarity
FROM insights i
JOIN insight_embeddings ie ON ie.insight_id = i.id
WHERE i.status = 'active'
  AND ie.embedding_version = 1
  AND ie.embedding <=> new_embedding < 0.1  -- similarity > 0.9
LIMIT 1;
*/

-- -----------------------------------------------------------------------------
-- Q3: Insert new insight with embedding (two-step)
-- Step 1: Insert insight
-- Step 2: Insert embedding (same transaction)
-- -----------------------------------------------------------------------------
/*
INSERT INTO insights (trajectory_id, state_id, text, score, generation, support_count, status, embedding_model)
VALUES ('trajectory-uuid', 'state-uuid', 'Insight text here', 0.85, 3, 1, 'active', 'text-embedding-ada-002')
RETURNING id;

INSERT INTO insight_embeddings (insight_id, embedding, embedding_version)
VALUES ('new-insight-id', '[0.1, 0.2, ...1536 dims...]'::vector, 1);
*/

-- -----------------------------------------------------------------------------
-- Q4: Deprecate an insight and supersede with a better version (lineage update)
-- Preserves full history for analysis
-- -----------------------------------------------------------------------------
/*
UPDATE insights
SET status = 'deprecated',
    updated_at = NOW()
WHERE id = 'old-insight-id';

INSERT INTO insights (trajectory_id, state_id, text, score, generation, support_count, status, supersedes_insight_id, embedding_model)
VALUES ('trajectory-uuid', 'state-uuid', 'Improved insight text', 0.92, 4, 1, 'active', 'old-insight-id', 'text-embedding-ada-002')
RETURNING id;
*/

-- -----------------------------------------------------------------------------
-- Q5: Mark insight as contradicted (e.g., later evidence refutes it)
-- -----------------------------------------------------------------------------
/*
UPDATE insights
SET status = 'contradicted',
    updated_at = NOW()
WHERE id = 'insight-id';

-- Optionally add supporting contradicting evidence as new insight
INSERT INTO insights (trajectory_id, state_id, text, score, generation, support_count, status, supersedes_insight_id, embedding_model)
VALUES ('new-trajectory-id', NULL, 'Evidence contradicts prior insight', 0.9, 5, 1, 'active', 'insight-id', 'text-embedding-ada-002');
*/

-- -----------------------------------------------------------------------------
-- Q6: Get insights by generation (MEMO optimization round progress)
-- -----------------------------------------------------------------------------
/*
SELECT
    generation,
    COUNT(*)        AS insight_count,
    AVG(score)      AS avg_score,
    SUM(support_count) AS total_supports
FROM insights
WHERE status = 'active'
GROUP BY generation
ORDER BY generation DESC;
*/

-- -----------------------------------------------------------------------------
-- Q7: Get trajectory summary with all its states and insights
-- -----------------------------------------------------------------------------
/*
SELECT
    t.id          AS trajectory_id,
    t.outcome,
    t.game_length,
    COUNT(DISTINCT s.id)    AS state_count,
    COUNT(DISTINCT i.id)    AS insight_count,
    AVG(i.score)            AS avg_insight_score
FROM trajectories t
LEFT JOIN states s ON s.trajectory_id = t.id
LEFT JOIN insights i ON i.trajectory_id = t.id
WHERE t.id = 'trajectory-uuid'
GROUP BY t.id, t.outcome, t.game_length;
*/

-- -----------------------------------------------------------------------------
-- Q8: Re-embed all insights (version bump for model change)
-- Step 1: Insert new embeddings with version = version + 1
-- Step 2: Query using new version
-- -----------------------------------------------------------------------------
/*
-- Bulk re-embed (pseudo-code - implement in application layer)
INSERT INTO insight_embeddings (insight_id, embedding, embedding_version)
SELECT
    id,
    new_embedding_function(text),
    (SELECT COALESCE(MAX(embedding_version), 0) + 1 FROM insight_embeddings) AS new_version
FROM insights
WHERE status = 'active';
*/

-- -----------------------------------------------------------------------------
-- Q9: Search insights by game type (via trajectory → game join)
-- -----------------------------------------------------------------------------
/*
SELECT
    i.id,
    i.text,
    i.generation,
    i.support_count,
    g.game_type,
    t.outcome
FROM insights i
JOIN trajectories t ON t.id = i.trajectory_id
JOIN games g ON g.id = t.game_id
WHERE i.status = 'active'
  AND g.game_type = 'fantasy_football'
ORDER BY i.support_count DESC, i.generation DESC
LIMIT 50;
*/

-- -----------------------------------------------------------------------------
-- Q10: Vacuum and analyze (run after bulk inserts/deletes for query planner)
-- -----------------------------------------------------------------------------
/*
VACUUM ANALYZE insights;
VACUUM ANALYZE insight_embeddings;
VACUUM ANALYZE trajectories;
*/

-- =============================================================================
-- END OF SCHEMA
-- =============================================================================
