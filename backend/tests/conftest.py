"""
Pytest configuration and fixtures for testing
"""

import asyncio
import os
from typing import AsyncGenerator, Generator

import pytest
import pytest_asyncio

# Set test environment variables BEFORE importing app modules
os.environ["DATABASE_URL"] = "postgresql+asyncpg://test:test@localhost:5432/test"
os.environ["REDIS_URL"] = "redis://localhost:6379"
os.environ["NEO4J_URI"] = "bolt://localhost:7687"
os.environ["NEO4J_PASSWORD"] = "testpassword"
os.environ["QDRANT_URL"] = "http://localhost:6333"
os.environ["OLLAMA_URL"] = "http://localhost:11434"
os.environ["SECRET_KEY"] = "test-secret-key-for-testing-only-not-for-production"


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create event loop for async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def sample_user_data():
    """Sample user data for testing"""
    return {
        "email": "test@example.com",
        "username": "testuser",
        "password": "testpassword123",
        "full_name": "Test User",
    }


@pytest.fixture
def sample_document_data():
    """Sample document data for testing"""
    return {
        "title": "Test Document",
        "filename": "test.pdf",
        "file_path": "/uploads/test.pdf",
        "file_type": "pdf",
        "file_size": 1024,
    }


@pytest.fixture
def auth_headers():
    """Generate auth headers for testing (mock JWT)"""
    # In real tests, you would generate a valid JWT token
    return {"Authorization": "Bearer mock_token_for_testing"}


# Integration test fixtures (only loaded when explicitly needed)
@pytest.fixture(scope="function")
def integration_test_db():
    """
    Database fixture for integration tests.
    Only use this for actual integration tests that need a database.
    Requires running PostgreSQL.
    """
    pytest.skip("Integration tests require running PostgreSQL")


@pytest_asyncio.fixture(scope="function")
async def test_engine():
    """
    Create async test engine for integration tests.
    Uses SQLite in-memory for fast tests.
    """
    from sqlalchemy.ext.asyncio import create_async_engine
    from sqlalchemy.pool import StaticPool

    TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    # Import Base here to avoid circular imports
    from app.core.database import Base

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def db_session(test_engine) -> AsyncGenerator:
    """Create async database session for testing"""
    from sqlalchemy.ext.asyncio import AsyncSession
    from sqlalchemy.orm import sessionmaker

    async_session = sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture(scope="function")
async def client(db_session) -> AsyncGenerator:
    """Create async HTTP client for testing API"""
    from httpx import AsyncClient

    from app.core.database import get_db
    from app.main import app

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()
