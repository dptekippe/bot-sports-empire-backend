"""
MEMO-pgvector services package.

Modules:
    embedding_service  — Pluggable embedding backends (OpenAI, Anthropic, local)
    embedding_cache    — Redis TTL cache for embeddings

Usage:
    from services import EmbeddingService, EmbeddingCache
    from config.embedding_config import get_config, EmbeddingModel

    # Basic usage
    config = get_config()
    service = EmbeddingService(config)
    cache = EmbeddingCache(config)

    # Embed a single text
    result = service.embed_text("This is a game insight", version="v1")
    print(f"Dimensions: {result.dimensions}, Version: {result.version}")

    # Embed a batch
    vectors = service.embed_batch(["insight 1", "insight 2"], version="v1")

    # Cache operations
    cache.set_cached("insight-uuid", "v1", vectors[0])
    cached = cache.get_cached("insight-uuid", "v1")

    # Read-through cache helper
    embedding = cache.get_or_fetch(
        "insight-uuid",
        "v1",
        fetch_fn=lambda: db_lookup("insight-uuid"),
    )
"""

from __future__ import annotations

from services.embedding_cache import EmbeddingCache
from services.embedding_service import (
    EMBEDDING_DIMENSIONS,
    EmbeddingModel,
    EmbeddingProvider,
    EmbeddingResult,
    EmbeddingService,
    SCHEMA_VECTOR_DIM,
)

__all__ = [
    "EmbeddingService",
    "EmbeddingCache",
    "EmbeddingModel",
    "EmbeddingProvider",
    "EmbeddingResult",
    "EMBEDDING_DIMENSIONS",
    "SCHEMA_VECTOR_DIM",
]
