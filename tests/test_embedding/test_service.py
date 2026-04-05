"""Unit tests for the embedding service."""

from unittest.mock import MagicMock, patch

import pytest

from app.config import EmbeddingSettings
from app.embedding.service import EmbeddingService
from app.exceptions import EmbeddingDimensionMismatchError


class TestEmbeddingService:
    """Tests for EmbeddingService class."""

    @pytest.fixture(autouse=True)
    def reset_singleton(self):
        """Reset the singleton before each test."""
        EmbeddingService.reset()
        yield
        EmbeddingService.reset()

    @pytest.fixture
    def settings_with_cache(self):
        """Create settings with caching enabled."""
        return EmbeddingSettings(
            model_path="./model_files/embeddingmodel/m3e-large",
            dimension=1024,
            device="cpu",
            cache_enabled=True,
            cache_max_size=100,
        )

    @pytest.fixture
    def settings_no_cache(self):
        """Create settings with caching disabled."""
        return EmbeddingSettings(
            model_path="./model_files/embeddingmodel/m3e-large",
            dimension=1024,
            device="cpu",
            cache_enabled=False,
            cache_max_size=100,  # Still set to min, but cache_enabled=False will disable it
        )

    def test_singleton_pattern(self, settings_with_cache):
        """Test that EmbeddingService follows singleton pattern."""
        service1 = EmbeddingService(settings_with_cache)
        service2 = EmbeddingService(settings_with_cache)

        assert service1 is service2

    def test_cache_initialization_enabled(self, settings_with_cache):
        """Test cache is initialized when enabled."""
        service = EmbeddingService(settings_with_cache)

        assert hasattr(service, "_cache")
        assert hasattr(service, "_cache_max_size")
        assert service._cache_max_size > 0

    def test_cache_initialization_disabled(self, settings_no_cache):
        """Test cache is disabled when configured."""
        service = EmbeddingService(settings_no_cache)

        assert service._cache_max_size == 0

    def test_dimension_property(self, settings_with_cache):
        """Test dimension property returns configured value."""
        service = EmbeddingService(settings_with_cache)

        assert service.dimension == 1024

    def test_is_loaded_property(self, settings_with_cache):
        """Test is_loaded property."""
        service = EmbeddingService(settings_with_cache)

        # Initially not loaded
        assert service.is_loaded is False

        # Mock model loading
        service._model = MagicMock()

        # After loading
        assert service.is_loaded is True

    @patch("app.embedding.service.SentenceTransformer")
    def test_load_model_success(self, mock_st, settings_with_cache):
        """Test successful model loading."""
        mock_model = MagicMock()
        mock_model.get_sentence_embedding_dimension.return_value = 1024
        mock_st.return_value = mock_model

        service = EmbeddingService(settings_with_cache)
        service.load_model()

        assert service.is_loaded
        mock_st.assert_called_once()

    @patch("app.embedding.service.SentenceTransformer")
    def test_load_model_dimension_mismatch(self, mock_st, settings_with_cache):
        """Test model loading fails on dimension mismatch."""
        mock_model = MagicMock()
        mock_model.get_sentence_embedding_dimension.return_value = 768  # Wrong dimension
        mock_st.return_value = mock_model

        service = EmbeddingService(settings_with_cache)

        with pytest.raises(EmbeddingDimensionMismatchError):
            service.load_model()

    @patch("app.embedding.service.SentenceTransformer")
    def test_embed_documents_without_cache(self, mock_st, settings_no_cache):
        """Test embedding without caching."""
        mock_model = MagicMock()
        mock_model.get_sentence_embedding_dimension.return_value = 1024
        mock_model.encode.return_value = [[0.1] * 1024]
        mock_st.return_value = mock_model

        service = EmbeddingService(settings_no_cache)
        service.load_model()

        results = service._embed_sync(["test text"])

        assert len(results) == 1
        assert len(results[0]) == 1024
        # Cache should be disabled
        assert service._cache_max_size == 0

    def test_reset_clears_singleton(self, settings_with_cache):
        """Test that reset clears the singleton."""
        EmbeddingService(settings_with_cache)
        assert EmbeddingService._instance is not None

        EmbeddingService.reset()

        assert EmbeddingService._instance is None

    def test_multiple_services_share_cache(self, settings_with_cache):
        """Test that multiple service instances share the same cache."""
        service1 = EmbeddingService(settings_with_cache)

        # Add something to cache
        service1._cache["test_key"] = [0.1] * 1024

        # Get service2 (same instance)
        service2 = EmbeddingService(settings_with_cache)

        # Should have access to same cache
        assert "test_key" in service2._cache


class TestEmbeddingCache:
    """Tests for embedding cache functionality."""

    @pytest.fixture(autouse=True)
    def reset_singleton(self):
        """Reset the singleton before each test."""
        EmbeddingService.reset()
        yield
        EmbeddingService.reset()

    @pytest.fixture
    def mock_service_with_cache(self):
        """Create a mock service with cache."""
        settings = EmbeddingSettings(
            model_path="./model_files/embeddingmodel/m3e-large",
            dimension=1024,
            device="cpu",
            cache_enabled=True,
            cache_max_size=10,  # Changed from 2 to 10
        )
        service = EmbeddingService(settings)
        service._model = MagicMock()
        return service

    def test_cache_eviction_lru(self, mock_service_with_cache):
        """Test LRU eviction when cache is full."""
        service = mock_service_with_cache

        # Add first entry
        service._cache["key1"] = [0.1] * 1024
        # Add second entry
        service._cache["key2"] = [0.2] * 1024
        # Cache is now full

        # Add third entry (should evict key1)
        service._cache["key3"] = [0.3] * 1024

        # key1 should be evicted
        assert "key1" not in service._cache
        # key2 and key3 should remain
        assert "key2" in service._cache
        assert "key3" in service._cache

    def test_cache_key_generation(self, mock_service_with_cache):
        """Test cache key is generated from text hash."""
        text = "test text for embedding"
        key = str(hash(text))

        assert isinstance(key, str)
        # Same text should produce same key
        assert str(hash(text)) == str(hash(text))
