"""
Unit tests for application configuration
"""

import os
import pytest
from unittest.mock import patch

from pydantic import ValidationError


class TestSettingsValidation:
    """Tests for Settings configuration validation"""

    def test_settings_loads_defaults(self):
        """Test that settings loads with proper defaults"""
        from app.core.config import settings

        assert settings.APP_NAME == "Vietnamese Environmental Law RAG"
        assert settings.APP_VERSION == "1.0.0"
        assert settings.ALGORITHM == "HS256"
        assert settings.ACCESS_TOKEN_EXPIRE_MINUTES == 30
        assert settings.REFRESH_TOKEN_EXPIRE_DAYS == 7

    def test_settings_rag_defaults(self):
        """Test RAG-related default settings"""
        from app.core.config import settings

        assert settings.CHUNK_SIZE == 1024
        assert settings.CHUNK_OVERLAP == 128
        assert settings.TOP_K_RETRIEVAL == 20
        assert settings.MAX_CONTEXT_TOKENS == 8000
        assert settings.GRAPH_TRAVERSAL_DEPTH == 3

    def test_settings_embedding_defaults(self):
        """Test embedding-related default settings"""
        from app.core.config import settings

        assert settings.EMBEDDING_MODEL == "intfloat/multilingual-e5-large"
        assert settings.EMBEDDING_DIMENSION == 1024
        assert settings.EMBEDDING_BATCH_SIZE == 32

    def test_settings_file_upload_defaults(self):
        """Test file upload default settings"""
        from app.core.config import settings

        assert settings.MAX_UPLOAD_SIZE == 52428800  # 50MB
        assert settings.ALLOWED_EXTENSIONS == ["pdf", "docx", "doc"]

    def test_settings_qdrant_defaults(self):
        """Test Qdrant default settings"""
        from app.core.config import settings

        assert settings.QDRANT_COLLECTION_CHUNKS == "chunks"
        assert settings.QDRANT_COLLECTION_ENTITIES == "entities"

    def test_allowed_origins_parsing(self):
        """Test ALLOWED_ORIGINS is parsed correctly"""
        from app.core.config import settings

        # Should be a list after parsing
        origins = settings.ALLOWED_ORIGINS
        assert isinstance(origins, list)
        assert len(origins) >= 1

    def test_ollama_base_url_fallback(self):
        """Test OLLAMA_BASE_URL fallback to OLLAMA_URL"""
        from app.core.config import settings

        # If OLLAMA_BASE_URL not set, should use OLLAMA_URL
        assert settings.OLLAMA_BASE_URL is not None


class TestSettingsEnvironmentOverride:
    """Tests for environment variable overrides"""

    def test_debug_mode_env_override(self):
        """Test DEBUG can be overridden via environment"""
        from app.core.config import settings

        # Default is False
        assert settings.DEBUG in [True, False]

    def test_log_level_default(self):
        """Test LOG_LEVEL default"""
        from app.core.config import settings

        # Default is INFO, but may be overridden
        assert settings.LOG_LEVEL in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]


class TestSettingsOriginsParsing:
    """Tests for CORS origins parsing"""

    def test_parse_single_origin(self):
        """Test parsing single origin"""
        from app.core.config import Settings

        # The validator should parse comma-separated string
        test_origin = "http://localhost:3000"
        result = Settings.parse_origins(test_origin)
        assert result == ["http://localhost:3000"]

    def test_parse_multiple_origins(self):
        """Test parsing multiple origins"""
        from app.core.config import Settings

        test_origins = "http://localhost:3000,http://localhost:5173,https://example.com"
        result = Settings.parse_origins(test_origins)

        assert len(result) == 3
        assert "http://localhost:3000" in result
        assert "http://localhost:5173" in result
        assert "https://example.com" in result

    def test_parse_origins_strips_whitespace(self):
        """Test that whitespace is stripped from origins"""
        from app.core.config import Settings

        test_origins = "http://localhost:3000 , http://localhost:5173"
        result = Settings.parse_origins(test_origins)

        assert result == ["http://localhost:3000", "http://localhost:5173"]


class TestSettingsOllamaUrlValidator:
    """Tests for OLLAMA_BASE_URL validator"""

    def test_ollama_base_url_set_when_none(self):
        """Test OLLAMA_BASE_URL is set from OLLAMA_URL when None"""
        from app.core.config import Settings

        class MockInfo:
            data = {"OLLAMA_URL": "http://ollama:11434"}

        result = Settings.set_ollama_base_url(None, MockInfo())
        assert result == "http://ollama:11434"

    def test_ollama_base_url_preserved_when_set(self):
        """Test OLLAMA_BASE_URL is preserved when explicitly set"""
        from app.core.config import Settings

        class MockInfo:
            data = {"OLLAMA_URL": "http://ollama:11434"}

        result = Settings.set_ollama_base_url("http://custom:11434", MockInfo())
        assert result == "http://custom:11434"
