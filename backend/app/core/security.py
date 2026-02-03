"""
Security utilities: JWT tokens, password hashing, authentication, rate limiting
"""

import re
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from fastapi import HTTPException, Request, status
from jose import JWTError, jwt
from passlib.context import CryptContext
from redis.asyncio import Redis

from .config import settings

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a hashed password"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password for storing"""
    return pwd_context.hash(password)


def create_access_token(
    data: Dict[str, Any], expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a JWT access token

    Args:
        data: Payload to encode in the token
        expires_delta: Optional custom expiration time

    Returns:
        Encoded JWT token
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )

    to_encode.update({"exp": expire, "type": "access"})
    encoded_jwt = jwt.encode(
        to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM
    )
    return encoded_jwt


def create_refresh_token(data: Dict[str, Any]) -> str:
    """
    Create a JWT refresh token with longer expiration

    Args:
        data: Payload to encode in the token

    Returns:
        Encoded JWT refresh token
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    encoded_jwt = jwt.encode(
        to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM
    )
    return encoded_jwt


def decode_token(token: str) -> Dict[str, Any]:
    """
    Decode and verify a JWT token

    Args:
        token: JWT token to decode

    Returns:
        Token payload

    Raises:
        HTTPException: If token is invalid or expired
    """
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        return payload
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Could not validate credentials: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )


# Rate Limiting
class RateLimiter:
    """
    Redis-based rate limiter for API endpoints
    """

    def __init__(
        self,
        redis: Redis,
        key_prefix: str = "rate_limit",
        max_requests: int = 60,
        window_seconds: int = 60,
    ):
        """
        Initialize rate limiter

        Args:
            redis: Redis client
            key_prefix: Prefix for Redis keys
            max_requests: Maximum requests allowed in window
            window_seconds: Time window in seconds
        """
        self.redis = redis
        self.key_prefix = key_prefix
        self.max_requests = max_requests
        self.window_seconds = window_seconds

    async def check_rate_limit(self, identifier: str) -> bool:
        """
        Check if request is within rate limit

        Args:
            identifier: Unique identifier (user_id, IP, etc.)

        Returns:
            True if within limit, False otherwise

        Raises:
            HTTPException: If rate limit exceeded
        """
        key = f"{self.key_prefix}:{identifier}"
        current = await self.redis.get(key)

        if current is None:
            # First request in window
            await self.redis.setex(key, self.window_seconds, 1)
            return True

        current_count = int(current)
        if current_count >= self.max_requests:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded. Max {self.max_requests} requests per {self.window_seconds} seconds.",
            )

        # Increment counter
        await self.redis.incr(key)
        return True

    async def get_remaining(self, identifier: str) -> int:
        """
        Get remaining requests in current window

        Args:
            identifier: Unique identifier

        Returns:
            Number of remaining requests
        """
        key = f"{self.key_prefix}:{identifier}"
        current = await self.redis.get(key)

        if current is None:
            return self.max_requests

        return max(0, self.max_requests - int(current))


async def rate_limit_dependency(
    request: Request, redis: Redis, user_id: Optional[str] = None
) -> bool:
    """
    FastAPI dependency for rate limiting

    Args:
        request: FastAPI request
        redis: Redis client
        user_id: Optional user ID (uses IP if not provided)

    Returns:
        True if within limit

    Raises:
        HTTPException: If rate limit exceeded
    """
    identifier = user_id or request.client.host
    limiter = RateLimiter(redis, max_requests=60, window_seconds=60)
    return await limiter.check_rate_limit(identifier)


# Input Sanitization
def sanitize_string(text: str, max_length: int = 10000) -> str:
    """
    Sanitize user input string

    Args:
        text: Input text
        max_length: Maximum allowed length

    Returns:
        Sanitized text

    Raises:
        HTTPException: If validation fails
    """
    if not text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Input text cannot be empty"
        )

    # Remove null bytes
    text = text.replace("\x00", "")

    # Limit length
    if len(text) > max_length:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Input text exceeds maximum length of {max_length} characters",
        )

    # Remove control characters except newlines, tabs
    text = "".join(
        char
        for char in text
        if char == "\n" or char == "\t" or not (0 <= ord(char) < 32)
    )

    return text.strip()


def detect_prompt_injection(prompt: str) -> bool:
    """
    Detect potential prompt injection attacks

    Args:
        prompt: User prompt/query

    Returns:
        True if injection detected, False otherwise
    """
    # Common prompt injection patterns
    injection_patterns = [
        r"ignore\s+(?:previous|above|all)\s+(?:instructions|prompts|directions)",
        r"disregard\s+(?:previous|above|all)",
        r"forget\s+(?:previous|above|all)",
        r"new\s+(?:instructions|task|role|prompt)",
        r"system\s*:\s*",
        r"<\s*script\s*>",
        r"<\s*iframe\s*>",
        r"\{\{.*\}\}",  # Template injection
        r"\$\{.*\}",  # Variable injection
    ]

    prompt_lower = prompt.lower()

    for pattern in injection_patterns:
        if re.search(pattern, prompt_lower, re.IGNORECASE):
            return True

    return False


def validate_and_sanitize_query(query: str, max_length: int = 5000) -> str:
    """
    Validate and sanitize user query for RAG system

    Args:
        query: User query
        max_length: Maximum query length

    Returns:
        Sanitized query

    Raises:
        HTTPException: If validation fails
    """
    # Basic sanitization
    query = sanitize_string(query, max_length=max_length)

    # Check for prompt injection
    if detect_prompt_injection(query):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Potential prompt injection detected. Please rephrase your query.",
        )

    # Minimum length check
    if len(query) < 3:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Query must be at least 3 characters long",
        )

    return query


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename to prevent path traversal

    Args:
        filename: Original filename

    Returns:
        Sanitized filename

    Raises:
        HTTPException: If filename is invalid
    """
    # Remove path components
    filename = filename.split("/")[-1].split("\\")[-1]

    # Remove null bytes
    filename = filename.replace("\x00", "")

    # Check for dangerous patterns
    if ".." in filename or filename.startswith("."):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid filename"
        )

    # Only allow alphanumeric, dash, underscore, dot
    if not re.match(r"^[a-zA-Z0-9_\-. ]+$", filename):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename contains invalid characters",
        )

    # Limit length
    if len(filename) > 255:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Filename too long"
        )

    return filename
