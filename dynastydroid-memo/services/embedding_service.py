"""
Pluggable embedding service for MEMO-pgvector.

Supports multiple backends: OpenAI, Anthropic, and local models.
All embeddings are version-tagged for lineage tracking.
"""

from __future__ import annotations

import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING, List, Optional

import numpy as np

from config.embedding_config import EmbeddingConfig, EmbeddingModel, get_config

if TYPE_CHECKING:
    import redis

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Model dimension registry
# ---------------------------------------------------------------------------

EMBEDDING_DIMENSIONS: dict[EmbeddingModel, int] = {
    EmbeddingModel.OPENAI_ADA002: 1536,
    EmbeddingModel.OPENAI_TEXT_EMBEDDING_3_SMALL: 1536,
    EmbeddingModel.OPENAI_TEXT_EMBEDDING_3_LARGE: 3072,
    EmbeddingModel.ANTHROPIC_EMBEDDING: 1024,
}

# Schema-compatible dimension (ada-002 baseline)
SCHEMA_VECTOR_DIM = 1536


# ---------------------------------------------------------------------------
# Embedding result container
# ---------------------------------------------------------------------------

@dataclass
class EmbeddingResult:
    """An embedding vector with full metadata."""

    vector: List[float]
    model: EmbeddingModel
    version: str
    dimensions: int
    token_count: Optional[int] = None

    def to_db_row(self, insight_id: str) -> dict:
        return {
            "insight_id": insight_id,
            "embedding": self.vector,
            "embedding_version": self._parse_version(),
        }

    def _parse_version(self) -> int:
        """Extract integer version from version string (e.g. 'v1' -> 1)."""
        try:
            return int(self.version.lstrip("v"))
        except ValueError:
            return 1


# ---------------------------------------------------------------------------
# Abstract embedding provider
# ---------------------------------------------------------------------------

class EmbeddingProvider(ABC):
    """Abstract base for embedding model backends."""

    @abstractmethod
    def embed(self, texts: List[str], model: EmbeddingModel) -> List[List[float]]:
        """Embed a batch of texts. Returns list of vectors."""
        ...

    @abstractmethod
    def health_check(self) -> bool:
        """Return True if the provider is reachable and ready."""
        ...


# ---------------------------------------------------------------------------
# OpenAI Provider
# ---------------------------------------------------------------------------

class OpenAIEmbeddingProvider(EmbeddingProvider):
    """OpenAI embedding models via openai-python."""

    def __init__(self, config: EmbeddingConfig):
        self.config = config
        self._client = None

    def _get_client(self):
        """Lazy init of OpenAI client."""
        if self._client is not None:
            return self._client

        try:
            import openai
        except ImportError:
            raise ImportError(
                "openai package required. Install with: pip install openai"
            )

        kwargs: dict = {"api_key": self.config.openai_api_key}
        if self.config.openai_base_url:
            kwargs["base_url"] = self.config.openai_base_url

        self._client = openai.OpenAI(**kwargs)
        return self._client

    def embed(self, texts: List[str], model: EmbeddingModel) -> List[List[float]]:
        """Call OpenAI embeddings API."""
        client = self._get_client()

        # Map our enum to OpenAI model name
        openai_model = model.value

        # Truncate texts that are too long (chars, not tokens)
        truncated = [t[: self.config.max_input_length] for t in texts]

        response = client.embeddings.create(model=openai_model, input=truncated)

        vectors = [item.embedding for item in response.data]
        return vectors

    def health_check(self) -> bool:
        try:
            client = self._get_client()
            # Lightweight call to verify connectivity
            client.embeddings.create(
                model=EmbeddingModel.OPENAI_ADA002.value, input=["health check"]
            )
            return True
        except Exception as e:
            logger.warning("OpenAI health check failed: %s", e)
            return False


# ---------------------------------------------------------------------------
# Anthropic Provider
# ---------------------------------------------------------------------------

class AnthropicEmbeddingProvider(EmbeddingProvider):
    """Anthropic embeddings via anthropic SDK."""

    def __init__(self, config: EmbeddingConfig):
        self.config = config
        self._client = None

    def _get_client(self):
        """Lazy init of Anthropic client."""
        if self._client is not None:
            return self._client

        try:
            from anthropic import Anthropic
        except ImportError:
            raise ImportError(
                "anthropic package required. Install with: pip install anthropic"
            )

        self._client = Anthropic(api_key=self.config.anthropic_api_key)
        return self._client

    def embed(self, texts: List[str], model: EmbeddingModel) -> List[List[float]]:
        """
        Call Anthropic embeddings API.
        Note: Anthropic embeddings API is accessed via the /v1/messages endpoint
        with embeddings beta, or directly via their embeddings API.
        """
        client = self._get_client()

        # Truncate inputs
        truncated = [t[: self.config.max_input_length] for t in texts]

        # Anthropic uses a different API shape; call the embeddings endpoint
        # Fallback: use POST /v1/embeddings
        import os as _os

        base_url = _os.getenv("ANTHROPIC_BASE_URL", "https://api.anthropic.com")
        api_key = self.config.anthropic_api_key

        import requests as _requests

        headers = {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }

        vectors: List[List[float]] = []
        for text in truncated:
            resp = _requests.post(
                f"{base_url}/v1/embeddings",
                headers=headers,
                json={"model": model.value, "input": text},
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
            vectors.append(data["embedding"])

        return vectors

    def health_check(self) -> bool:
        try:
            self.embed(["health check"], EmbeddingModel.ANTHROPIC_EMBEDDING)
            return True
        except Exception as e:
            logger.warning("Anthropic health check failed: %s", e)
            return False


# ---------------------------------------------------------------------------
# Local / Sentence-Transformers Provider
# ---------------------------------------------------------------------------

class LocalEmbeddingProvider(EmbeddingProvider):
    """
    Local embedding models via sentence-transformers.
    Good for development, air-gapped environments, or cost savings.
    """

    def __init__(self, config: EmbeddingConfig, model_name: str = "all-MiniLM-L6-v2"):
        self.config = config
        self.model_name = model_name
        self._model = None

    def _get_model(self):
        """Lazy init of sentence-transformers model."""
        if self._model is not None:
            return self._model

        try:
            from sentence_transformers import SentenceTransformer
        except ImportError:
            raise ImportError(
                "sentence-transformers required for local embeddings. "
                "Install with: pip install sentence-transformers"
            )

        self._model = SentenceTransformer(self.model_name)
        return self._model

    def embed(self, texts: List[str], model: EmbeddingModel) -> List[List[float]]:
        """Embed using sentence-transformers."""
        m = self._get_model()
        truncated = [t[: self.config.max_input_length] for t in texts]
        embeddings = m.encode(truncated, convert_to_numpy=True)
        # Convert to list of float
        return [row.tolist() for row in embeddings]

    def health_check(self) -> bool:
        try:
            self.embed(["health check"], EmbeddingModel.OPENAI_ADA002)
            return True
        except Exception as e:
            logger.warning("Local embedding health check failed: %s", e)
            return False


# ---------------------------------------------------------------------------
# Provider registry
# ---------------------------------------------------------------------------

_PROVIDER_REGISTRY: dict[str, type[EmbeddingProvider]] = {
    "openai": OpenAIEmbeddingProvider,
    "anthropic": AnthropicEmbeddingProvider,
    "local": LocalEmbeddingProvider,
}


def _build_provider(
    model: EmbeddingModel, config: EmbeddingConfig
) -> EmbeddingProvider:
    """Instantiate the correct provider for a model."""
    provider_name = model.provider
    provider_cls = _PROVIDER_REGISTRY.get(provider_name)
    if provider_cls is None:
        raise ValueError(f"No embedding provider for model type: {model.value}")
    return provider_cls(config)


# ---------------------------------------------------------------------------
# Embedding Service
# ---------------------------------------------------------------------------

class EmbeddingService:
    """
    High-level embedding service with:
    - Pluggable model backends
    - Redis caching
    - Version tracking
    - Dimension validation against schema (VECTOR(1536))
    """

    def __init__(
        self,
        config: Optional[EmbeddingConfig] = None,
        redis_client: Optional["redis.Redis"] = None,
    ):
        self.config = config or get_config()
        self._redis_client = redis_client
        self._providers: dict[EmbeddingModel, EmbeddingProvider] = {}

    # ------------------------------------------------------------------
    # Redis client (lazy, optional)
    # ------------------------------------------------------------------

    @property
    def redis(self) -> Optional["redis.Redis"]:
        """Lazy Redis connection."""
        if self._redis_client is None:
            try:
                import redis as _redis

                self._redis_client = _redis.Redis(
                    host=self.config.redis.host,
                    port=self.config.redis.port,
                    db=self.config.redis.db,
                    password=self.config.redis.password,
                    decode_responses=False,  # embeddings are bytes
                )
            except Exception as e:
                logger.warning("Could not connect to Redis: %s. Caching disabled.", e)
                self._redis_client = None
        return self._redis_client

    # ------------------------------------------------------------------
    # Provider management
    # ------------------------------------------------------------------

    def _get_provider(self, model: EmbeddingModel) -> EmbeddingProvider:
        """Get or create a provider instance for the given model."""
        if model not in self._providers:
            self._providers[model] = _build_provider(model, self.config)
        return self._providers[model]

    # ------------------------------------------------------------------
    # Core embedding methods
    # ------------------------------------------------------------------

    def embed_text(
        self,
        text: str,
        model: Optional[EmbeddingModel] = None,
        version: Optional[str] = None,
    ) -> EmbeddingResult:
        """
        Embed a single text string.

        Args:
            text: The text to embed.
            model: Embedding model to use (default: from config).
            version: Version tag for this embedding (default: 'v1').

        Returns:
            EmbeddingResult with vector, metadata.
        """
        model = model or self.config.default_model
        version = version or "v1"

        vectors = self.embed_batch([text], model=model)
        return EmbeddingResult(
            vector=vectors[0],
            model=model,
            version=version,
            dimensions=len(vectors[0]),
        )

    def embed_batch(
        self,
        texts: List[str],
        model: Optional[EmbeddingModel] = None,
        version: Optional[str] = None,
        show_progress: bool = False,
    ) -> List[List[float]]:
        """
        Embed a batch of texts, chunked to batch_size.

        Args:
            texts: List of texts to embed.
            model: Embedding model (default: from config).
            version: Version tag (for logging/tracing only).
            show_progress: Log progress for large batches.

        Returns:
            List of embedding vectors.
        """
        if not texts:
            return []

        model = model or self.config.default_model
        version = version or "v1"

        provider = self._get_provider(model)
        batch_size = self.config.batch_size
        all_vectors: List[List[float]] = []
        total = len(texts)

        for i in range(0, total, batch_size):
            chunk = texts[i : i + batch_size]
            if show_progress:
                logger.info(
                    "Embedding chunk %d-%d/%d (model=%s, version=%s)",
                    i + 1,
                    min(i + batch_size, total),
                    total,
                    model.value,
                    version,
                )
            vectors = provider.embed(chunk, model)
            all_vectors.extend(vectors)

            # Rate-limit delay between batches (helps with API quotas)
            if i + batch_size < total:
                time.sleep(0.1)

        # Validate dimensions
        expected_dim = EMBEDDING_DIMENSIONS[model]
        for vec in all_vectors:
            if len(vec) != expected_dim:
                raise ValueError(
                    f"Dimension mismatch for {model.value}: "
                    f"expected {expected_dim}, got {len(vec)}"
                )

        return all_vectors

    # ------------------------------------------------------------------
    # Schema dimension validation
    # ------------------------------------------------------------------

    def validate_for_schema(self, vector: List[float]) -> bool:
        """
        Check if a vector dimension matches SCHEMA_VECTOR_DIM (1536).
        Logs a warning if there's a mismatch.
        """
        if len(vector) != SCHEMA_VECTOR_DIM:
            logger.warning(
                "Embedding dimension %d != schema VECTOR(1536). "
                "May need ALTER TABLE for this model.",
                len(vector),
            )
            return False
        return True

    # ------------------------------------------------------------------
    # Similarity (cosine) using numpy
    # ------------------------------------------------------------------

    @staticmethod
    def cosine_similarity(a: List[float], b: List[float]) -> float:
        """Compute cosine similarity between two vectors."""
        import numpy as np

        vec_a = np.array(a, dtype=np.float32)
        vec_b = np.array(b, dtype=np.float32)
        dot = np.dot(vec_a, vec_b)
        norm_a = np.linalg.norm(vec_a)
        norm_b = np.linalg.norm(vec_b)
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return float(dot / (norm_a * norm_b))

    @staticmethod
    def cosine_distance(a: List[float], b: List[float]) -> float:
        """Compute cosine distance (1 - similarity)."""
        return 1.0 - EmbeddingService.cosine_similarity(a, b)

    # ------------------------------------------------------------------
    # Health check
    # ------------------------------------------------------------------

    def health_check(self) -> dict[str, bool]:
        """Check health of all configured providers and Redis."""
        results: dict[str, bool] = {}
        for model in EmbeddingModel:
            try:
                provider = self._get_provider(model)
                results[f"provider:{model.value}"] = provider.health_check()
            except Exception as e:
                logger.debug("Provider %s not available: %s", model.value, e)
                results[f"provider:{model.value}"] = False

        if self.redis:
            try:
                self.redis.ping()
                results["redis"] = True
            except Exception:
                results["redis"] = False
        else:
            results["redis"] = False

        return results

    # ------------------------------------------------------------------
    # Deduplication helper
    # ------------------------------------------------------------------

    def find_similar(
        self,
        query_vector: List[float],
        stored_vectors: List[tuple[str, List[float]]],
        threshold: float = 0.9,
    ) -> List[tuple[str, float]]:
        """
        Find items with cosine similarity above threshold.

        Args:
            query_vector: The query embedding.
            stored_vectors: List of (id, vector) tuples to search.
            threshold: Minimum similarity (0-1).

        Returns:
            List of (id, similarity_score) sorted by score descending.
        """
        results: List[tuple[str, float]] = []
        for item_id, vec in stored_vectors:
            sim = self.cosine_similarity(query_vector, vec)
            if sim >= threshold:
                results.append((item_id, sim))

        results.sort(key=lambda x: x[1], reverse=True)
        return results
