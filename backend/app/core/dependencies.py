"""
Dependency injection for FastAPI endpoints
"""

from typing import AsyncGenerator, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from neo4j import AsyncGraphDatabase
from qdrant_client import AsyncQdrantClient
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from .config import settings
from .security import decode_token

# Security
security = HTTPBearer()


# Database session (will be implemented with SQLAlchemy)
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Get async database session

    Yields:
        AsyncSession instance
    """
    # TODO: Implement after creating database.py
    raise NotImplementedError("Database session not yet implemented")


# Redis connection
async def get_redis() -> AsyncGenerator[Redis, None]:
    """
    Get Redis connection

    Yields:
        Redis client instance
    """
    redis = Redis.from_url(settings.REDIS_URL, decode_responses=True)
    try:
        yield redis
    finally:
        await redis.close()


# Qdrant client
async def get_qdrant() -> AsyncQdrantClient:
    """
    Get Qdrant client

    Returns:
        AsyncQdrantClient instance
    """
    return AsyncQdrantClient(url=settings.QDRANT_URL)


# Neo4j driver
async def get_neo4j():
    """
    Get Neo4j driver

    Returns:
        Neo4j driver instance
    """
    driver = AsyncGraphDatabase.driver(
        settings.NEO4J_URI, auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD)
    )
    try:
        yield driver
    finally:
        await driver.close()


# Current user dependency
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    # db: AsyncSession = Depends(get_db)  # Uncomment after implementing get_db
) -> dict:
    """
    Get current authenticated user from JWT token

    Args:
        credentials: HTTP Bearer token
        db: Database session

    Returns:
        User data dictionary

    Raises:
        HTTPException: If authentication fails
    """
    token = credentials.credentials
    payload = decode_token(token)

    user_id: Optional[str] = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # TODO: Fetch user from database
    # user = await db.get(User, user_id)
    # if user is None:
    #     raise HTTPException(status_code=404, detail="User not found")

    # For now, return payload
    return {"id": user_id, **payload}


# Optional current user (for endpoints that work with or without auth)
async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(
        HTTPBearer(auto_error=False)
    ),
) -> Optional[dict]:
    """
    Get current user if authenticated, None otherwise

    Args:
        credentials: Optional HTTP Bearer token

    Returns:
        User data or None
    """
    if credentials is None:
        return None

    try:
        return await get_current_user(credentials)
    except HTTPException:
        return None
