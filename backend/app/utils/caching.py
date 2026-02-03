"""
Redis caching utilities for performance optimization
"""

import asyncio
import hashlib
import json
from functools import wraps
from typing import Any, Callable, Optional

from redis.asyncio import Redis

from app.utils.monitoring import get_logger

logger = get_logger(__name__)


class CacheService:
    """
    Redis-based caching service
    """

    def __init__(self, redis: Redis, default_ttl: int = 3600):
        """
        Initialize cache service

        Args:
            redis: Redis client
            default_ttl: Default TTL in seconds (1 hour)
        """
        self.redis = redis
        self.default_ttl = default_ttl

    async def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found
        """
        try:
            value = await self.redis.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            logger.error(f"Cache get error for key {key}: {e}")
            return None

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """
        Set value in cache

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds (uses default if not provided)

        Returns:
            True if successful
        """
        try:
            ttl = ttl or self.default_ttl
            serialized = json.dumps(value)
            await self.redis.setex(key, ttl, serialized)
            return True
        except Exception as e:
            logger.error(f"Cache set error for key {key}: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """
        Delete value from cache

        Args:
            key: Cache key

        Returns:
            True if successful
        """
        try:
            await self.redis.delete(key)
            return True
        except Exception as e:
            logger.error(f"Cache delete error for key {key}: {e}")
            return False

    async def clear_pattern(self, pattern: str) -> int:
        """
        Clear all keys matching pattern

        Args:
            pattern: Key pattern (e.g., "user:*")

        Returns:
            Number of keys deleted
        """
        try:
            keys = []
            async for key in self.redis.scan_iter(match=pattern):
                keys.append(key)

            if keys:
                await self.redis.delete(*keys)
                return len(keys)
            return 0
        except Exception as e:
            logger.error(f"Cache clear pattern error for {pattern}: {e}")
            return 0

    async def exists(self, key: str) -> bool:
        """
        Check if key exists in cache

        Args:
            key: Cache key

        Returns:
            True if key exists
        """
        try:
            return await self.redis.exists(key) > 0
        except Exception as e:
            logger.error(f"Cache exists error for key {key}: {e}")
            return False

    async def increment(self, key: str, amount: int = 1) -> int:
        """
        Increment counter

        Args:
            key: Cache key
            amount: Amount to increment

        Returns:
            New value
        """
        try:
            return await self.redis.incrby(key, amount)
        except Exception as e:
            logger.error(f"Cache increment error for key {key}: {e}")
            return 0

    async def get_or_set(self, key: str, func: Callable, ttl: Optional[int] = None, *args, **kwargs) -> Any:
        """
        Get from cache or compute and set

        Args:
            key: Cache key
            func: Function to call if cache miss
            ttl: Time to live
            *args: Arguments for func
            **kwargs: Keyword arguments for func

        Returns:
            Cached or computed value
        """
        # Try cache first
        cached = await self.get(key)
        if cached is not None:
            logger.debug(f"Cache hit for key: {key}")
            return cached

        # Cache miss, compute value
        logger.debug(f"Cache miss for key: {key}")
        value = await func(*args, **kwargs) if asyncio.iscoroutinefunction(func) else func(*args, **kwargs)

        # Store in cache
        await self.set(key, value, ttl)

        return value


def cache_key(*args, prefix: str = "cache", **kwargs) -> str:
    """
    Generate cache key from arguments

    Args:
        *args: Positional arguments
        prefix: Key prefix
        **kwargs: Keyword arguments

    Returns:
        Cache key string
    """
    # Create deterministic key from arguments
    key_parts = [prefix]

    # Add positional args
    for arg in args:
        if isinstance(arg, (str, int, float, bool)):
            key_parts.append(str(arg))
        else:
            # Hash complex objects
            key_parts.append(hashlib.md5(str(arg).encode()).hexdigest()[:8])

    # Add keyword args (sorted for consistency)
    for k, v in sorted(kwargs.items()):
        if isinstance(v, (str, int, float, bool)):
            key_parts.append(f"{k}:{v}")
        else:
            key_parts.append(f"{k}:{hashlib.md5(str(v).encode()).hexdigest()[:8]}")

    return ":".join(key_parts)


def cached(ttl: int = 3600, key_prefix: str = "cache"):
    """
    Decorator to cache function results

    Args:
        ttl: Time to live in seconds
        key_prefix: Prefix for cache key

    Returns:
        Decorated function

    Example:
        @cached(ttl=600, key_prefix="user")
        async def get_user(user_id: int):
            return await db.get_user(user_id)
    """

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, redis: Redis = None, **kwargs):
            if redis is None:
                # No Redis available, just call function
                return await func(*args, **kwargs)

            # Generate cache key
            # Skip 'self' or 'cls' for methods
            cache_args = args[1:] if args and hasattr(args[0], "__class__") else args
            key = cache_key(*cache_args, prefix=f"{key_prefix}:{func.__name__}", **kwargs)

            # Try cache
            cache = CacheService(redis, default_ttl=ttl)
            cached_value = await cache.get(key)

            if cached_value is not None:
                logger.debug(f"Cache hit: {key}")
                return cached_value

            # Cache miss, call function
            logger.debug(f"Cache miss: {key}")
            result = await func(*args, **kwargs)

            # Store in cache
            await cache.set(key, result, ttl)

            return result

        return wrapper

    return decorator


# Specialized caching strategies
class QueryCache:
    """
    Cache for RAG query results
    """

    def __init__(self, redis: Redis):
        self.cache = CacheService(redis, default_ttl=3600)  # 1 hour
        self.prefix = "query"

    def _query_key(self, query: str, user_id: Optional[int] = None) -> str:
        """Generate cache key for query"""
        query_hash = hashlib.md5(query.encode()).hexdigest()
        if user_id:
            return f"{self.prefix}:user:{user_id}:{query_hash}"
        return f"{self.prefix}:{query_hash}"

    async def get_query_result(self, query: str, user_id: Optional[int] = None) -> Optional[dict]:
        """
        Get cached query result

        Args:
            query: User query
            user_id: Optional user ID for user-specific caching

        Returns:
            Cached result or None
        """
        key = self._query_key(query, user_id)
        return await self.cache.get(key)

    async def set_query_result(self, query: str, result: dict, user_id: Optional[int] = None, ttl: int = 3600) -> bool:
        """
        Cache query result

        Args:
            query: User query
            result: Query result
            user_id: Optional user ID
            ttl: Time to live

        Returns:
            True if successful
        """
        key = self._query_key(query, user_id)
        return await self.cache.set(key, result, ttl)

    async def invalidate_user_cache(self, user_id: int) -> int:
        """
        Invalidate all cached queries for user

        Args:
            user_id: User ID

        Returns:
            Number of keys deleted
        """
        pattern = f"{self.prefix}:user:{user_id}:*"
        return await self.cache.clear_pattern(pattern)


class EmbeddingCache:
    """
    Cache for text embeddings
    """

    def __init__(self, redis: Redis):
        self.cache = CacheService(redis, default_ttl=86400)  # 24 hours
        self.prefix = "embedding"

    def _embedding_key(self, text: str, model: str = "default") -> str:
        """Generate cache key for embedding"""
        text_hash = hashlib.md5(text.encode()).hexdigest()
        return f"{self.prefix}:{model}:{text_hash}"

    async def get_embedding(self, text: str, model: str = "default") -> Optional[list]:
        """
        Get cached embedding

        Args:
            text: Text to embed
            model: Model name

        Returns:
            Cached embedding or None
        """
        key = self._embedding_key(text, model)
        return await self.cache.get(key)

    async def set_embedding(self, text: str, embedding: list, model: str = "default", ttl: int = 86400) -> bool:
        """
        Cache embedding

        Args:
            text: Text
            embedding: Embedding vector
            model: Model name
            ttl: Time to live

        Returns:
            True if successful
        """
        key = self._embedding_key(text, model)
        return await self.cache.set(key, embedding, ttl)
