"""
Redis TTL cache layer for MEMO-pgvector embeddings.

Redis is a read-through/write-through cache in front of PostgreSQL.
Source of truth remains the insight_embeddings table.
Cache key shape: memo:insight:{id}:embed:{version}
"""

from __future__ import annotations

import json
import logging
import pickle
from typing import List, Optional

import numpy as np

from config.embedding_config import EmbeddingConfig, EmbeddingModel, get_config

logger = logging.getLogger(__name__)

# Redis key templates
_KEY_INSIGHT_EMBED = "memo:insight:{insight_id}:embed:{version}"
_KEY_INSIGHT_VERSIONS = "memo:insight:{insight_id}:versions"  # SET of known versions


def _serialize(embedding: List[float]) -> bytes:
    """Serialize embedding vector to bytes for Redis storage."""
    vec = np.array(embedding, dtype=np.float32)
    return vec.tobytes()


def _deserialize(data: bytes) -> List[float]:
    """Deserialize embedding vector from Redis bytes."""
    vec = np.frombuffer(data, dtype=np.float32)
    return vec.tolist()


# ---------------------------------------------------------------------------
# Embedding Cache
# ---------------------------------------------------------------------------

class EmbeddingCache:
    """
    Redis-based TTL cache for insight embeddings.

    Design:
    - Read-through: check cache before hitting DB
    - Write-through: populate cache after DB insert
    - Version-scoped: each embedding version has its own cache entry
    - Invalidation: clears all versions for an insight when invalidated

    Key shape: `memo:insight:{id}:embed:{version}`
    """

    def __init__(
        self,
        config: Optional[EmbeddingConfig] = None,
        redis_client=None,  # redis.Redis, injected for testing
    ):
        self.config = config or get_config()
        self._redis = redis_client

    # ------------------------------------------------------------------
    # Redis connection (lazy, optional)
    # ------------------------------------------------------------------

    @property
    def redis(self):
        """Lazy Redis connection. Returns None if Redis unavailable."""
        if self._redis is not None:
            return self._redis

        try:
            import redis as _redis

            self._redis = _redis.Redis(
                host=self.config.redis.host,
                port=self.config.redis.port,
                db=self.config.redis.db,
                password=self.config.redis.password,
                decode_responses=False,  # embeddings are raw bytes
                socket_timeout=5,
                socket_connect_timeout=5,
            )
            # Test connection
            self._redis.ping()
            logger.info("Redis connected: %s:%s", self.config.redis.host, self.config.redis.port)
        except Exception as e:
            logger.warning("Redis unavailable: %s. Cache disabled.", e)
            self._redis = None

        return self._redis

    # ------------------------------------------------------------------
    # Key helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _embed_key(insight_id: str, version: str) -> str:
        return _KEY_INSIGHT_EMBED.format(insight_id=insight_id, version=version)

    @staticmethod
    def _versions_key(insight_id: str) -> str:
        return _KEY_INSIGHT_VERSIONS.format(insight_id=insight_id)

    # ------------------------------------------------------------------
    # Core cache operations
    # ------------------------------------------------------------------

    def get_cached(
        self, insight_id: str, version: str
    ) -> Optional[List[float]]:
        """
        Retrieve a cached embedding if present.

        Args:
            insight_id: UUID of the insight.
            version: Embedding version string (e.g. 'v1').

        Returns:
            Embedding vector (List[float]) if cached, else None.
        """
        if self.redis is None:
            return None

        key = self._embed_key(insight_id, version)
        try:
            data = self.redis.get(key)
            if data is None:
                logger.debug("Cache MISS: %s", key)
                return None

            vector = _deserialize(data)
            logger.debug("Cache HIT: %s (dim=%d)", key, len(vector))
            return vector

        except Exception as e:
            logger.warning("Cache get failed for %s: %s", key, e)
            return None

    def set_cached(
        self,
        insight_id: str,
        version: str,
        embedding: List[float],
        ttl: Optional[int] = None,
    ) -> bool:
        """
        Write an embedding into the cache.

        Args:
            insight_id: UUID of the insight.
            version: Embedding version string.
            embedding: The embedding vector.
            ttl: TTL in seconds (auto from config if not provided).

        Returns:
            True if cached successfully, False otherwise.
        """
        if self.redis is None:
            return False

        ttl = ttl or self.config.cache.default_ttl
        key = self._embed_key(insight_id, version)
        versions_key = self._versions_key(insight_id)

        try:
            pipe = self.redis.pipeline()

            # Store the embedding vector as bytes
            pipe.set(key, _serialize(embedding), ex=ttl)

            # Track this version in the insight's version set (for invalidation)
            pipe.sadd(versions_key, version)
            pipe.expire(versions_key, ttl * 2)  # versions set lives 2x longer

            pipe.execute()

            logger.debug("Cache SET: %s (ttl=%ds, dim=%d)", key, ttl, len(embedding))
            return True

        except Exception as e:
            logger.warning("Cache set failed for %s: %s", key, e)
            return False

    def invalidate(self, insight_id: str) -> int:
        """
        Invalidate all cached embeddings for an insight.
        Called when an insight is deprecated/updated.

        Args:
            insight_id: UUID of the insight.

        Returns:
            Number of keys deleted.
        """
        if self.redis is None:
            return 0

        versions_key = self._versions_key(insight_id)

        try:
            # Get all known versions for this insight
            versions = self.redis.smembers(versions_key)

            if not versions:
                # Fall back to pattern scan if versions key is gone
                pattern = f"memo:insight:{insight_id}:embed:*"
                keys = list(self.redis.scan_iter(match=pattern, count=100))
            else:
                # Build keys from known versions
                keys = [self._embed_key(insight_id, v.decode()) for v in versions]

            if not keys:
                return 0

            # Delete all embedding keys + the versions set
            keys_to_delete = keys + [versions_key]
            deleted = self.redis.delete(*keys_to_delete)

            logger.info("Cache INVALIDATE: %s (deleted %d keys)", insight_id, deleted)
            return deleted

        except Exception as e:
            logger.warning("Cache invalidate failed for %s: %s", insight_id, e)
            return 0

    def get_or_fetch(
        self,
        insight_id: str,
        version: str,
        fetch_fn,  # callable that returns List[float]
        ttl: Optional[int] = None,
    ) -> Optional[List[float]]:
        """
        Read-through cache: try cache first, call fetch_fn on miss, cache result.

        Args:
            insight_id: UUID of the insight.
            version: Embedding version string.
            fetch_fn: Callable that returns the embedding (e.g. DB lookup).
            ttl: Cache TTL in seconds.

        Returns:
            Embedding vector, or None if fetch_fn returned None.
        """
        # Try cache first
        cached = self.get_cached(insight_id, version)
        if cached is not None:
            return cached

        # Cache miss — fetch from source of truth
        embedding = fetch_fn()
        if embedding is None:
            return None

        # Populate cache
        self.set_cached(insight_id, version, embedding, ttl=ttl)
        return embedding

    # ------------------------------------------------------------------
    # Bulk operations
    # ------------------------------------------------------------------

    def set_many_cached(
        self,
        items: List[tuple[str, str, List[float]]],  # [(insight_id, version, embedding), ...]
        ttl: Optional[int] = None,
    ) -> int:
        """
        Bulk write embeddings to cache (pipeline).

        Args:
            items: List of (insight_id, version, embedding) tuples.
            ttl: TTL in seconds per item.

        Returns:
            Number of items successfully cached.
        """
        if self.redis is None or not items:
            return 0

        ttl = ttl or self.config.cache.default_ttl
        pipe = self.redis.pipeline()
        count = 0

        try:
            for insight_id, version, embedding in items:
                key = self._embed_key(insight_id, version)
                versions_key = self._versions_key(insight_id)

                pipe.set(key, _serialize(embedding), ex=ttl)
                pipe.sadd(versions_key, version)
                pipe.expire(versions_key, ttl * 2)
                count += 1

            pipe.execute()
            logger.info("Cache bulk SET: %d items (ttl=%ds)", count, ttl)
            return count

        except Exception as e:
            logger.warning("Cache bulk set failed: %s", e)
            return 0

    def invalidate_many(self, insight_ids: list[str]) -> int:
        """
        Invalidate cache for multiple insights.

        Args:
            insight_ids: List of insight UUIDs.

        Returns:
            Total number of keys deleted across all insights.
        """
        total = 0
        for insight_id in insight_ids:
            total += self.invalidate(insight_id)
        return total

    # ------------------------------------------------------------------
    # Stats / debugging
    # ------------------------------------------------------------------

    def cache_stats(self) -> dict:
        """Return cache hit/miss statistics (scans Redis keys)."""
        if self.redis is None:
            return {"available": False}

        try:
            info = self.redis.info("stats")
            key_count = sum(
                1 for _ in self.redis.scan_iter("memo:insight:*", count=1000)
            )
            return {
                "available": True,
                "total_keys": key_count,
                "hits": info.get("keyspace_hits", 0),
                "misses": info.get("keyspace_misses", 0),
            }
        except Exception as e:
            logger.warning("Cache stats failed: %s", e)
            return {"available": False, "error": str(e)}

    def ping(self) -> bool:
        """Return True if Redis is reachable."""
        if self.redis is None:
            return False
        try:
            return self.redis.ping()
        except Exception:
            return False
