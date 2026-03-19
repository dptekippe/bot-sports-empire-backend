"""
Embedding configuration for MEMO-pgvector.
Loads settings from environment variables with sensible defaults.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class EmbeddingModel(str, Enum):
    """Supported embedding models with their dimensions."""

    OPENAI_ADA002 = "text-embedding-ada-002"
    OPENAI_TEXT_EMBEDDING_3_SMALL = "text-embedding-3-small"
    OPENAI_TEXT_EMBEDDING_3_LARGE = "text-embedding-3-large"
    ANTHROPIC_EMBEDDING = "claude-embedding"

    @property
    def dimensions(self) -> int:
        """Vector dimension for this model."""
        return {
            EmbeddingModel.OPENAI_ADA002: 1536,
            EmbeddingModel.OPENAI_TEXT_EMBEDDING_3_SMALL: 1536,
            EmbeddingModel.OPENAI_TEXT_EMBEDDING_3_LARGE: 3072,
            EmbeddingModel.ANTHROPIC_EMBEDDING: 1024,
        }[self]

    @property
    def provider(self) -> str:
        """Which provider hosts this model."""
        if self.startswith("text-embedding"):
            return "openai"
        if self == "claude-embedding":
            return "anthropic"
        return "unknown"


@dataclass
class RedisConfig:
    """Redis connection settings."""

    host: str = os.getenv("MEMO_REDIS_HOST", "localhost")
    port: int = int(os.getenv("MEMO_REDIS_PORT", "6379"))
    db: int = int(os.getenv("MEMO_REDIS_DB", "0"))
    password: Optional[str] = os.getenv("MEMO_REDIS_PASSWORD")
    ssl: bool = os.getenv("MEMO_REDIS_SSL", "false").lower() == "true"

    @property
    def url(self) -> str:
        scheme = "rediss" if self.ssl else "redis"
        auth = f":{self.password}@" if self.password else ""
        return f"{scheme}://{auth}{self.host}:{self.port}/{self.db}"


@dataclass
class CacheConfig:
    """Embedding cache TTL settings."""

    # Default TTL in seconds (1 hour)
    default_ttl: int = int(os.getenv("MEMO_CACHE_TTL", "3600"))
    # TTL for ada-002 embeddings (cheaper, longer TTL ok)
    ada002_ttl: int = int(os.getenv("MEMO_CACHE_TTL_ADA002", "86400"))
    # TTL for larger models (more expensive, shorter TTL)
    large_ttl: int = int(os.getenv("MEMO_CACHE_TTL_LARGE", "1800"))


@dataclass
class EmbeddingConfig:
    """Root configuration for the embedding service."""

    # Model selection
    default_model: EmbeddingModel = EmbeddingModel(
        os.getenv("MEMO_DEFAULT_EMBEDDING_MODEL", "OPENAI_ADA002")
    )

    # API keys
    openai_api_key: Optional[str] = field(
        default_factory=lambda: os.getenv("OPENAI_API_KEY")
    )
    anthropic_api_key: Optional[str] = field(
        default_factory=lambda: os.getenv("ANTHROPIC_API_KEY")
    )

    # Redis
    redis: RedisConfig = field(default_factory=RedisConfig)
    cache: CacheConfig = field(default_factory=CacheConfig)

    # Embedding service settings
    # Batch size for embed_batch()
    batch_size: int = int(os.getenv("MEMO_EMBED_BATCH_SIZE", "100"))
    # Max input text length (token limit; truncate at 8192 chars as safety margin)
    max_input_length: int = int(os.getenv("MEMO_EMBED_MAX_INPUT", "8192"))
    # OpenAI base URL (for proxies like one-api)
    openai_base_url: Optional[str] = field(
        default_factory=lambda: os.getenv("OPENAI_BASE_URL")
    )

    def ttl_for_model(self, model: EmbeddingModel) -> int:
        """Return appropriate cache TTL for a given model."""
        if model == EmbeddingModel.OPENAI_ADA002:
            return self.cache.ada002_ttl
        if model == EmbeddingModel.OPENAI_TEXT_EMBEDDING_3_LARGE:
            return self.cache.large_ttl
        return self.cache.default_ttl

    def validate(self) -> list[str]:
        """Return list of validation errors (empty if valid)."""
        errors = []
        if self.default_model.provider == "openai" and not self.openai_api_key:
            errors.append("OPENAI_API_KEY is required for OpenAI embedding models")
        if self.default_model.provider == "anthropic" and not self.anthropic_api_key:
            errors.append("ANTHROPIC_API_KEY is required for Anthropic embedding models")
        if self.batch_size < 1:
            errors.append("MEMO_EMBED_BATCH_SIZE must be >= 1")
        return errors


# Global singleton config instance
_config: Optional[EmbeddingConfig] = None


def get_config() -> EmbeddingConfig:
    """Get the global embedding config (lazy init)."""
    global _config
    if _config is None:
        _config = EmbeddingConfig()
    return _config


def reload_config() -> EmbeddingConfig:
    """Reload config from environment (useful for testing)."""
    global _config
    _config = EmbeddingConfig()
    return _config
