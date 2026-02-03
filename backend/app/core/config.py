"""
Application configuration management using Pydantic Settings
"""

from typing import List, Optional

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    # Application
    APP_NAME: str = "Vietnamese Environmental Law RAG"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"

    # Database
    DATABASE_URL: str
    REDIS_URL: str
    NEO4J_URI: str
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str

    # Vector Database
    QDRANT_URL: str
    QDRANT_COLLECTION_CHUNKS: str = "chunks"
    QDRANT_COLLECTION_ENTITIES: str = "entities"

    # LLM
    OLLAMA_URL: str
    OLLAMA_BASE_URL: Optional[str] = None
    OLLAMA_MODEL: str = "qwen2.5:7b"
    OLLAMA_TIMEOUT: int = 300

    @field_validator("OLLAMA_BASE_URL")
    @classmethod
    def set_ollama_base_url(cls, v: Optional[str], info) -> str:
        """Set OLLAMA_BASE_URL from OLLAMA_URL if not provided"""
        return v or info.data.get("OLLAMA_URL", "http://ollama:11434")

    # Embeddings
    EMBEDDING_MODEL: str = "intfloat/multilingual-e5-large"
    EMBEDDING_DIMENSION: int = 1024
    EMBEDDING_BATCH_SIZE: int = 32

    # RAG Settings
    CHUNK_SIZE: int = 1024
    CHUNK_OVERLAP: int = 128
    TOP_K_RETRIEVAL: int = 20
    MAX_CONTEXT_TOKENS: int = 8000
    GRAPH_TRAVERSAL_DEPTH: int = 3

    # Security
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # CORS
    ALLOWED_ORIGINS: str = "http://localhost:5173,http://localhost:80"

    @field_validator("ALLOWED_ORIGINS")
    @classmethod
    def parse_origins(cls, v: str) -> List[str]:
        """Parse comma-separated origins into list"""
        return [origin.strip() for origin in v.split(",")]

    # File Upload
    MAX_UPLOAD_SIZE: int = 52428800  # 50MB
    UPLOAD_DIR: str = "/app/uploads"
    ALLOWED_EXTENSIONS: List[str] = ["pdf", "docx", "doc"]

    # Monitoring
    ENABLE_METRICS: bool = True

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=True, extra="ignore"
    )


# Global settings instance
settings = Settings()
