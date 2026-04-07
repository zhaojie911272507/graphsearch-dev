"""Local embedding service using M3E-Large via sentence-transformers.

Implements a thread-safe singleton pattern so the model is loaded exactly
once during application startup and shared across all async request handlers.
"""

import asyncio
import logging
import threading
import time
from collections import OrderedDict
from functools import lru_cache
from pathlib import Path

import torch
from sentence_transformers import SentenceTransformer

from app.config import EmbeddingSettings
from app.exceptions import EmbeddingDimensionMismatchError, EmbeddingModelLoadError
from app.observability.metrics import MetricsRegistry
from app.observability.tracing import TracingSetup

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Singleton embedding service backed by a local SentenceTransformer model.

    The model is loaded lazily on first use and kept in memory for the
    lifetime of the process. All public methods are async-safe via
    `asyncio.to_thread` to avoid blocking the event loop.

    Args:
        settings: Embedding configuration (model path, dimension, device).
    """

    _instance: "EmbeddingService | None" = None
    _lock: threading.Lock = threading.Lock()

    def __new__(cls, settings: EmbeddingSettings | None = None) -> "EmbeddingService":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    instance._initialized = False
                    cls._instance = instance
        return cls._instance

    def __init__(self, settings: EmbeddingSettings | None = None) -> None:
        if self._initialized:
            return
        if settings is None:
            settings = EmbeddingSettings()
        self._settings = settings
        self._model: SentenceTransformer | None = None
        self._initialized = True

        # Initialize cache
        self._cache: OrderedDict[str, list[float]] = OrderedDict()
        self._cache_max_size = settings.cache_max_size if settings.cache_enabled else 0

    @property
    def dimension(self) -> int:
        """Expected embedding vector dimension."""
        return self._settings.dimension

    @property
    def is_loaded(self) -> bool:
        """Whether the underlying model has been loaded."""
        return self._model is not None

    def load_model(self) -> None:
        """Synchronously load the SentenceTransformer model.

        Called during application startup (lifespan). Raises
        EmbeddingModelLoadError if the model path is invalid or
        loading fails for any reason.
        """
        model_path = Path(self._settings.model_path)
        if not model_path.exists():
            raise EmbeddingModelLoadError(
                f"Model path does not exist: {model_path.resolve()}",
                details={"path": str(model_path.resolve())},
            )

        try:
            device = self._settings.device
            if device == "cpu":
                # Optimize CPU inference threads
                torch.set_num_threads(min(4, torch.get_num_threads()))

            self._model = SentenceTransformer(
                str(model_path),
                device=device,
            )
            actual_dim = self._model.get_sentence_embedding_dimension()
            if actual_dim != self._settings.dimension:
                raise EmbeddingDimensionMismatchError(
                    f"Model dimension {actual_dim} != configured {self._settings.dimension}",
                    details={"actual": actual_dim, "expected": self._settings.dimension},
                )

            logger.info(
                "Embedding model loaded",
                extra={"path": str(model_path), "device": device, "dimension": actual_dim},
            )
        except (EmbeddingDimensionMismatchError, EmbeddingModelLoadError):
            raise
        except Exception as exc:
            raise EmbeddingModelLoadError(
                f"Failed to load embedding model: {exc}",
                details={"path": str(model_path), "error": str(exc)},
            ) from exc

    def _ensure_model(self) -> SentenceTransformer:
        """Return the loaded model or raise."""
        if self._model is None:
            raise EmbeddingModelLoadError(
                "Embedding model not loaded. Call load_model() during startup."
            )
        return self._model

    def _embed_sync(self, texts: list[str]) -> list[list[float]]:
        """Synchronous batch embedding (runs on the model thread)."""
        model = self._ensure_model()
        embeddings = model.encode(
            texts,
            batch_size=32,
            show_progress_bar=False,
            normalize_embeddings=True,
        )
        if hasattr(embeddings, "tolist"):
            return embeddings.tolist()  # type: ignore[union-attr]
        return embeddings  # type: ignore[return-value]

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of documents asynchronously.

        Args:
            texts: List of text strings to embed.

        Returns:
            List of embedding vectors, each of length `self.dimension`.

        Raises:
            EmbeddingModelLoadError: If the model is not loaded.
            EmbeddingDimensionMismatchError: If output dimensions are wrong.
        """
        if not texts:
            return []

        # Check cache first for each text
        uncached_texts: list[str] = []
        cached_vectors: list[list[float] | None] = [None] * len(texts)

        if self._cache_max_size > 0:
            for i, text in enumerate(texts):
                # Use hash as cache key for long texts
                cache_key = str(hash(text))
                if cache_key in self._cache:
                    cached_vectors[i] = self._cache[cache_key]
                    # Move to end (most recently used)
                    del self._cache[cache_key]
                    self._cache[cache_key] = cached_vectors[i]
                else:
                    uncached_texts.append(text)
        else:
            uncached_texts = texts

        # Embed any uncached texts
        if uncached_texts:
            new_vectors = await asyncio.to_thread(self._embed_sync, uncached_texts)

            # Add to cache
            if self._cache_max_size > 0:
                for text, vector in zip(uncached_texts, new_vectors, strict=True):
                    cache_key = str(hash(text))
                    self._cache[cache_key] = vector
                    # Evict oldest if cache full
                    while len(self._cache) > self._cache_max_size:
                        self._cache.popitem(last=False)

            # Merge cached and new vectors
            vectors = []
            new_idx = 0
            for cached in cached_vectors:
                if cached is not None:
                    vectors.append(cached)
                else:
                    vectors.append(new_vectors[new_idx])
                    new_idx += 1
        else:
            vectors = cached_vectors  # type: ignore[assignment]

        # Runtime dimension check
        for i, vec in enumerate(vectors):
            if len(vec) != self.dimension:
                raise EmbeddingDimensionMismatchError(
                    f"Vector {i} has dimension {len(vec)}, expected {self.dimension}",
                    details={"index": i, "actual": len(vec), "expected": self.dimension},
                )
        return vectors

    async def embed_query(self, text: str) -> list[float]:
        """Embed a single query string asynchronously.

        Args:
            text: Query text to embed.

        Returns:
            Embedding vector of length `self.dimension`.
        """
        start = time.monotonic()
        tracer = TracingSetup.get_tracer()

        with tracer.start_as_current_span("rag.embedding") as span:
            span.set_attribute("embedding.model", self._settings.model_path)
            span.set_attribute("embedding.device", self._settings.device)

            try:
                results = await self.embed_documents([text])
                result = results[0]

                duration = time.monotonic() - start
                MetricsRegistry.rag_embedding_latency_seconds.labels(
                    model=self._settings.model_path,
                    device=self._settings.device,
                ).observe(duration)

                span.set_attribute("embedding.duration_seconds", duration)
                span.set_attribute("embedding.dimension", len(result))

                return result

            except Exception as e:
                span.set_attribute("error", True)
                span.record_exception(e)
                raise

    @classmethod
    def reset(cls) -> None:
        """Reset the singleton — primarily for testing."""
        with cls._lock:
            if cls._instance is not None:
                cls._instance._model = None
                cls._instance._initialized = False
            cls._instance = None


@lru_cache(maxsize=1)
def get_embedding_service() -> EmbeddingService:
    """Factory for FastAPI dependency injection."""
    return EmbeddingService()
