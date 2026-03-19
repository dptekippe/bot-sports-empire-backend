# MEMO Embedding Service

> Pluggable embedding backend with Redis caching and pgvector integration for MEMO-pgvector.

---

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                     Application Layer                         │
│  EmbeddingService  +  EmbeddingCache                        │
└─────────────────────────┬──────────────────────────────────┘
                           │
           ┌───────────────┴───────────────┐
           │                               │
           ▼                               ▼
┌─────────────────────┐      ┌─────────────────────────┐
│   Redis Cache       │      │  PostgreSQL / pgvector  │
│   (TTL, read-through)│     │  (Source of truth)     │
│                     │      │                         │
│ memo:insight:{id}:  │      │ insight_embeddings      │
│   embed:{version}   │      │ VECTOR(1536)            │
└─────────────────────┘      └─────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────────────────────────┐
│               Embedding Providers (Pluggable)               │
│  OpenAI  │  Anthropic  │  Local (sentence-transformers)   │
└─────────────────────────────────────────────────────────────┘
```

**Design decisions:**
- **Redis is a cache, not the source of truth.** PostgreSQL always wins.
- **Version-scoped keys** (`memo:insight:{id}:embed:{version}`) enable re-embedding without cache storms.
- **Cache invalidation is explicit** — called when an insight is deprecated/updated.
- **Embedding versioning is separate from cache versioning** — the `embedding_version` column in the DB tracks model versions; the cache key version tracks cache iterations.

---

## File Structure

```
dynastydroid-memo/
├── config/
│   └── embedding_config.py     # All settings (env vars + dataclasses)
├── services/
│   ├── __init__.py             # Public API surface
│   ├── embedding_service.py    # Pluggable embedding backends
│   └── embedding_cache.py     # Redis TTL cache layer
├── schema/
│   ├── memo_schema.sql         # pgvector schema (VECTOR(1536))
│   └── README.md               # Schema design decisions
└── README.md                   # This file
```

---

## Quick Start

```python
from config.embedding_config import get_config, EmbeddingModel
from services import EmbeddingService, EmbeddingCache

# Load config from environment
config = get_config()

# Embedding service
service = EmbeddingService(config)
result = service.embed_text("Josh Allen is the best QB in dynasty", version="v1")
print(result.vector[:5], "...", f"({result.dimensions}d, model={result.model.value})")

# Redis cache
cache = EmbeddingCache(config)
cache.set_cached("insight-uuid", "v1", result.vector)
cached = cache.get_cached("insight-uuid", "v1")
```

---

## Embedding Service

### Supported Models

| Enum | Model Name | Dimensions | Provider |
|------|-----------|-----------|----------|
| `OPENAI_ADA002` | `text-embedding-ada-002` | 1536 | OpenAI |
| `OPENAI_TEXT_EMBEDDING_3_SMALL` | `text-embedding-3-small` | 1536 | OpenAI |
| `OPENAI_TEXT_EMBEDDING_3_LARGE` | `text-embedding-3-large` | 3072 | OpenAI |
| `ANTHROPIC_EMBEDDING` | `claude-embedding` | 1024 | Anthropic |

> **Dimension note:** `text-embedding-3-large` (3072d) and `claude-embedding` (1024d) require `ALTER TABLE insight_embeddings ALTER COLUMN embedding TYPE VECTOR(3072)` or `VECTOR(1024)` before use. The schema ships with `VECTOR(1536)` (ada-002 compatible) as the default.

### Core Methods

```python
service = EmbeddingService(config)

# Single text
result = service.embed_text("insight text", model=EmbeddingModel.OPENAI_ADA002, version="v1")
# → EmbeddingResult(vector=[...], model=EmbeddingModel.OPENAI_ADA002, version="v1", dimensions=1536)

# Batch (auto-chunked to batch_size)
vectors = service.embed_batch(
    ["insight 1", "insight 2", "insight 3"],
    model=EmbeddingModel.OPENAI_ADA002,
    version="v1",
    show_progress=True,
)

# Dimension validation against schema
service.validate_for_schema(vectors[0])  # True for ada-002

# Cosine similarity (local, no DB needed)
sim = EmbeddingService.cosine_similarity(vec_a, vec_b)

# Find similar items above threshold
matches = service.find_similar(query_vector, [(id1, vec1), (id2, vec2)], threshold=0.9)
# → [(id2, 0.94), (id1, 0.91)]
```

### Adding a New Provider

1. Subclass `EmbeddingProvider` in `embedding_service.py`.
2. Implement `embed(texts, model)` and `health_check()`.
3. Register in `_PROVIDER_REGISTRY` dict.

```python
class MyEmbeddingProvider(EmbeddingProvider):
    def embed(self, texts, model):
        # Your implementation
        return [my_model.encode(t) for t in texts]

    def health_check(self):
        return my_model.is_ready()

_PROVIDER_REGISTRY["my_model"] = MyEmbeddingProvider
```

---

## Embedding Cache

### Key Design

| Key Pattern | Value | TTL |
|---|---|---|
| `memo:insight:{id}:embed:{version}` | Raw float32 bytes | Configurable (default 1h) |
| `memo:insight:{id}:versions` | Redis SET of version strings | 2× embedding TTL |

### Core Methods

```python
cache = EmbeddingCache(config)

# Direct get/set
cache.set_cached("insight-uuid", "v1", embedding_vector, ttl=3600)
vector = cache.get_cached("insight-uuid", "v1")

# Invalidation — clears all versions for an insight
cache.invalidate("insight-uuid")

# Read-through: check cache, call fetch_fn on miss, cache result
embedding = cache.get_or_fetch(
    "insight-uuid", "v1",
    fetch_fn=lambda: db.get_embedding("insight-uuid"),
)

# Bulk operations
cache.set_many_cached([("id1", "v1", vec1), ("id2", "v1", vec2)])
cache.invalidate_many(["id1", "id2", "id3"])

# Health check
cache.ping()         # → True/False
cache.cache_stats()  # → {"available": True, "total_keys": 123, "hits": 456, "misses": 12}
```

---

## pgvector Integration

### Storing Embeddings

```python
import uuid

# Embed the insight text
result = service.embed_text("Josh Allen is the best dynasty QB", version="v1")

# Store in PostgreSQL (pseudo-code — adapt to your DB layer)
db.execute("""
    INSERT INTO insight_embeddings (insight_id, embedding, embedding_version)
    VALUES (%s, %s, %s)
    ON CONFLICT (insight_id, embedding_version) DO UPDATE
    SET embedding = EXCLUDED.embedding
""", (insight_id, result.vector, result.to_db_row(insight_id)["embedding_version"]))
```

### Semantic Search (Cosine Similarity)

```python
# Find top-5 similar insights
query_vec = service.embed_text("best quarterback for dynasty")[0]

results = db.fetchall("""
    SELECT
        i.id,
        i.text,
        i.score,
        i.generation,
        1 - (ie.embedding <=> %s::vector) AS cosine_similarity
    FROM insights i
    JOIN insight_embeddings ie ON ie.insight_id = i.id
    WHERE i.status = 'active'
      AND ie.embedding_version = (
          SELECT MAX(ie2.embedding_version) FROM insight_embeddings ie2
          WHERE ie2.insight_id = i.id
      )
    ORDER BY ie.embedding <=> %s::vector
    LIMIT 5
""", (query_vec, query_vec))
```

### Re-embedding (Version Bump)

```python
# When switching embedding models:
# 1. Embed with new model (new version)
new_result = service.embed_text(old_insight_text, model=EmbeddingModel.OPENAI_TEXT_EMBEDDING_3_LARGE, version="v2")

# 2. Insert new embedding row (old rows preserved for lineage)
db.execute("""
    INSERT INTO insight_embeddings (insight_id, embedding, embedding_version)
    VALUES (%s, %s, 2)
""", (insight_id, new_result.vector))

# 3. Invalidate old cache entries
cache.invalidate(insight_id)

# 4. Query uses latest version automatically (view handles this)
# v_active_insight_embeddings filters to MAX(embedding_version) per insight
```

---

## Configuration

All settings are loaded from environment variables with sensible defaults.

### Environment Variables

| Variable | Default | Description |
|---|---|---|
| `MEMO_DEFAULT_EMBEDDING_MODEL` | `OPENAI_ADA002` | Default embedding model |
| `OPENAI_API_KEY` | — | OpenAI API key |
| `ANTHROPIC_API_KEY` | — | Anthropic API key |
| `OPENAI_BASE_URL` | — | Proxy base URL (optional) |
| `MEMO_REDIS_HOST` | `localhost` | Redis host |
| `MEMO_REDIS_PORT` | `6379` | Redis port |
| `MEMO_REDIS_PASSWORD` | — | Redis password |
| `MEMO_REDIS_SSL` | `false` | Use TLS for Redis |
| `MEMO_CACHE_TTL` | `3600` | Default cache TTL (seconds) |
| `MEMO_CACHE_TTL_ADA002` | `86400` | TTL for ada-002 embeddings (24h) |
| `MEMO_CACHE_TTL_LARGE` | `1800` | TTL for larger models (30min) |
| `MEMO_EMBED_BATCH_SIZE` | `100` | Batch size for embed_batch() |

### Validation

```python
config = get_config()
errors = config.validate()
if errors:
    raise ValueError("Config errors: " + ", ".join(errors))
```

---

## Deduplication Policy

Before inserting a new insight, check for near-duplicates:

```python
new_vector = service.embed_text(new_insight_text)[0]

# Find similar active insights (threshold 0.9)
matches = service.find_similar(new_vector, stored_vectors, threshold=0.9)

if matches:
    # Increment support_count of the existing insight
    existing_id, similarity = matches[0]
    db.execute("UPDATE insights SET support_count = support_count + 1 WHERE id = %s", (existing_id,))
    print(f"Duplicate detected (sim={similarity:.3f}), incremented support_count")
else:
    # Insert new insight + embedding
    insert_new_insight(new_insight_text, new_vector)
    cache.set_cached(new_insight_id, "v1", new_vector)
```

---

## Health Checks

```python
# All providers + Redis
health = service.health_check()
# {'provider:text-embedding-ada-002': True, 'provider:text-embedding-3-large': False, 'redis': True}

# Redis only
cache.ping()  # True/False

# Full stats
cache.cache_stats()
# {'available': True, 'total_keys': 142, 'hits': 3847, 'misses': 213}
```

---

## Dependencies

```bash
pip install openai           # OpenAI embeddings
pip install anthropic        # Anthropic embeddings
pip install sentence-transformers  # Local embeddings
pip install redis            # Redis client
pip install numpy            # Vector math
pip install pgvector         # pgvector Python bindings (if using pgvector directly)
```

---

*Service v1.0.0 — 2026-03-19*
