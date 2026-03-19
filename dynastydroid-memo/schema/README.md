# MEMO Schema Design

> pgvector-backed memory schema for Memory-Augmented Model Context Optimization

## Overview

MEMO replaces JSON files + keyword matching with a PostgreSQL + pgvector stack for semantic search across game trajectory insights.

**Tech stack:** PostgreSQL + pgvector (HNSW index) | Embedding dim: 1536 (ada-002 compatible)

---

## Schema Diagram

```
┌─────────────┐       ┌──────────────────┐       ┌─────────────┐
│   games     │       │  trajectories    │       │   states   │
│─────────────│       │──────────────────│       │─────────────│
│ id (PK)     │──1:N──│ id (PK)          │──1:N──│ id (PK)     │
│ game_type   │       │ game_id (FK)     │       │ trajectory_ │
│ name        │       │ outcome          │       │   id (FK)   │
│ config      │       │ agent_name       │       │ step_idx    │
│ created_at  │       │ player_id        │       │ state_json  │
└─────────────┘       │ game_length      │       │ reward      │
                      │ created_at       │       │ done        │
                      └──────────────────┘       │ created_at  │
                                                 └─────────────┘

┌──────────────────┐       ┌──────────────────────────┐
│    insights      │       │  insight_embeddings       │
│──────────────────│       │──────────────────────────│
│ id (PK)          │──1:1──│ id (PK)                  │
│ trajectory_id(FK)│       │ insight_id (FK)          │
│ state_id (FK)    │       │ embedding VECTOR(1536)   │
│ text             │       │ embedding_version        │
│ score            │       │ created_at               │
│ generation       │       └──────────────────────────┘
│ support_count    │                 │
│ status           │                 │ HNSW index
│ supersedes_      │                 │ (cosine similarity)
│   insight_id(FK) │                 ▼
│ embedding_model  │
│ created_at       │
│ updated_at       │
└──────────────────┘
```

---

## Table Details

### 1. `games`
Extensible registry for multiple game types.

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID | PK, defaults `gen_random_uuid()` |
| `game_type` | TEXT | e.g. `'chess'`, `'go'`, `'fantasy_football'` |
| `name` | TEXT | Human-readable name, unique with game_type |
| `config` | JSONB | Game-specific config (rules, parameters) |
| `created_at` | TIMESTAMPTZ | |

**Indexes:** `idx_games_game_type`

---

### 2. `trajectories`
Complete game play-throughs.

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID | PK |
| `game_id` | UUID | FK → games(id), ON DELETE CASCADE |
| `seed` | TEXT | Random seed for reproducibility |
| `outcome` | TEXT | CHECK IN `('win', 'loss', 'draw')` |
| `agent_name` | TEXT | Which agent played |
| `player_id` | TEXT | External player identifier |
| `total_format_errors` | INTEGER | Input format errors |
| `total_invalid_moves` | INTEGER | Illegal move attempts |
| `game_length` | INTEGER | Number of steps/turns |
| `created_at` | TIMESTAMPTZ | |

**Indexes:** `idx_trajectories_game_id`, `idx_trajectories_outcome`, `idx_trajectories_agent_name`, `idx_trajectories_created_at`

---

### 3. `states`
Individual steps within a trajectory.

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID | PK |
| `trajectory_id` | UUID | FK → trajectories(id), ON DELETE CASCADE |
| `step_idx` | INTEGER | Position in trajectory (0-indexed) |
| `state_json` | JSONB | Full state representation |
| `reward` | REAL | Reinforcement learning reward signal |
| `done` | BOOLEAN | Terminal state flag |
| `created_at` | TIMESTAMPTZ | |

**Indexes:** `idx_states_trajectory_id`, `idx_states_trajectory_step` (UNIQUE)

---

### 4. `insights`
Structured insights extracted from trajectories.

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID | PK |
| `trajectory_id` | UUID | FK → trajectories(id), nullable (cross-trajectory insights) |
| `state_id` | UUID | FK → states(id), nullable |
| `text` | TEXT | The insight content |
| `score` | REAL | Confidence/quality 0–1 |
| `generation` | INTEGER | MEMO optimization round (0 = initial) |
| `support_count` | INTEGER | How many trajectories support this |
| `status` | TEXT | CHECK IN `('active', 'deprecated', 'contradicted')` |
| `supersedes_insight_id` | UUID | FK → insights(id), lineage chain |
| `embedding_model` | TEXT | e.g. `'text-embedding-ada-002'` |
| `created_at` | TIMESTAMPTZ | |
| `updated_at` | TIMESTAMPTZ | Auto-updated via trigger |

**Indexes:** `idx_insights_supersedes`, `idx_insights_status` (WHERE active), `idx_insights_generation`, `idx_insights_support_count`, `idx_insights_active_gen_support` (composite)

**Trigger:** `trigger_insights_updated_at` — auto-updates `updated_at` on row change.

---

### 5. `insight_embeddings`
Pre-computed vector embeddings.

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID | PK |
| `insight_id` | UUID | FK → insights(id), ON DELETE CASCADE |
| `embedding` | VECTOR(1536) | OpenAI ada-002 compatible dimension |
| `embedding_version` | INTEGER | Enables re-embedding without data loss |
| `created_at` | TIMESTAMPTZ | |

**Indexes:** `idx_insight_embeddings_insight_id`, `idx_insight_embeddings_version`, `idx_insight_embeddings_embedding_hnsw` (HNSW, cosine)

---

## Key Design Decisions

### Soft Deletes via `status`
Never hard-delete insights. Three states:
- **`active`** — current, returned in search results
- **`deprecated`** — superseded by a better insight
- **`contradicted`** — later evidence refutes this insight

Soft deletes preserve the full history for analysis and prevent dangling references from lineage chains.

### Lineage Tracking via `supersedes_insight_id`
Each insight can reference the insight it replaces. The `v_insight_lineage` view traverses the full chain.

**Why:** MEMO iteratively improves insights. Lineage lets us:
1. Trace how understanding evolved across generations
2. Detect oscillating hypotheses
3. Aggregate evidence across the chain

### Support Count for Deduplication
`support_count` tracks how many independent trajectories support an insight.

**Deduplication policy:** Before inserting a new insight, compute cosine similarity to all active insights. If similarity > 0.9 to an existing insight, increment that insight's `support_count` instead of inserting a duplicate.

```sql
-- Pseudo-code
IF cosine_similarity(new_embedding, nearest_active_embedding) > 0.9:
    UPDATE insights SET support_count = support_count + 1 WHERE id = nearest_id
ELSE:
    INSERT new insight + embedding
```

### Generation Column
Tracks MEMO optimization rounds. Enables queries like:
- "Show all insights from generation 5+ that have high support"
- "How many insights were added/updated per generation?"
- "What was the average insight score improvement from gen 1→2?"

### Embedding Versioning
When the embedding model changes (e.g., ada-002 → babbage-002), we:
1. Insert new embeddings with `embedding_version = MAX + 1`
2. Old embeddings remain queryable by version
3. View `v_active_insight_embeddings` filters to latest version per insight

**Why:** Re-embedding is expensive and may be partial. Versioning prevents data loss and allows A/B comparison between models.

### pgvector Index Selection: HNSW over IVFFlat

| Index | Build time | Query speed | Memory | Accuracy |
|-------|-----------|-------------|--------|---------|
| HNSW | Slower | Faster | Higher | ~99% |
| IVFFlat | Fast | Moderate | Lower | ~95% |

**Decision: HNSW** (`m=16, ef_construction=100`)
- 1536-dim embeddings benefit most from HNSW's graph structure
- Production workloads prioritize query accuracy over build time
- `ef_construction=100` is the pgvector default and a good balance

### Idempotent Migrations
`schema_migrations` table tracks applied versions. The migration:
1. Acquires an advisory lock (`pg_advisory_lock`) to prevent concurrent runs
2. Inserts its version into `schema_migrations` with `ON CONFLICT DO NOTHING`
3. Releases the lock on exit

**Safe to re-run:** All `CREATE TABLE` and `CREATE INDEX` statements use `IF NOT EXISTS`/`IF NOT EXISTS`.

### Advisory Lock Pattern
```sql
SELECT pg_advisory_lock(hash::bigint)
FROM (SELECT hashtext('memo_schema_migration') AS hash) AS lock_;
-- ... run migration ...
SELECT pg_advisory_unlock(hash::bigint)
FROM (SELECT hashtext('memo_schema_migration') AS hash) AS lock_;
```
Prevents duplicate migrations from racing in connection pools.

---

## Helper Views

### `v_active_insight_embeddings`
Active insights + their latest embeddings. Ready for vector search join:

```sql
SELECT id, embedding FROM v_active_insight_embeddings
WHERE <condition>
ORDER BY embedding <=> query_embedding
LIMIT 20;
```

### `v_insight_lineage`
Recursive CTE tracing supersession chains:

```sql
SELECT id, root_id, depth, chain_length, id_path FROM v_insight_lineage;
```

---

## Operational Notes

### VACUUM after Bulk Operations
After bulk inserts, deletes, or re-embedding:
```sql
VACUUM ANALYZE insights;
VACUUM ANALYZE insight_embeddings;
```

### Monitoring Index Size
pgvector indexes grow with embedding count. Monitor:
```sql
SELECT pg_size_pretty(pg_relation_size('idx_insight_embeddings_embedding_hnsw'));
```

### Embedding Dimension Compatibility
`VECTOR(1536)` matches OpenAI's `text-embedding-ada-002`. If switching models:
- `text-embedding-3-small`: 1536 dim (compatible)
- `text-embedding-3-large`: 3072 dim (requires ALTER TABLE)

---

## File Structure

```
dynastydroid-memo/
├── schema/
│   ├── memo_schema.sql    # Full migration (idempotent)
│   └── README.md          # This file
├── src/
│   ├── trajectory_memory_system.py   # Trajectory analysis
│   ├── xml_crud_operations.py         # ADD/EDIT/REMOVE operations
│   └── state_registry.py              # (future: state management)
└── tests/
    └── test_schema_queries.py
```

---

## Future Extensions

1. **Tags/categories** — Add `insight_tags` table for filtering without full-text search
2. **Temporal decay** — Add `decay_factor` to `insights` to weight recent evidence higher
3. **Trajectory similarity** — Add `trajectory_embeddings` table for trajectory-to-trajectory matching
4. **Partial indexes** — Add partial indexes on `insights` for domain-specific hot paths (e.g., `WHERE game_type = 'fantasy_football'`)
5. **Partitioning** — Partition `states` by `trajectory_id` or time if row counts exceed ~10M

---

*Schema v1.0.0 — 2026-03-19*
