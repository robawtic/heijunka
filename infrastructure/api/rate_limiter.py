from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
import time
from typing import Dict, Tuple, Optional, Callable
import logging
from redis import asyncio as aioredis
import asyncio

from infrastructure.config.settings import settings

logger = logging.getLogger("heijunka_api.rate_limiter")

class RedisRateLimiter(BaseHTTPMiddleware):
    """
    Middleware for rate limiting API requests using Redis for distributed environments.

    This middleware limits the number of requests a client can make within a specified time window.
    It uses Redis for storage, making it suitable for distributed environments with multiple instances.
    """

    def __init__(
        self, 
        app, 
        redis_client=None,
        limit: int = 100, 
        window: int = 60, 
        key_func: Callable[[Request], str] = None
    ):
        """
        Initialize the rate limiter.

        Args:
            app: The FastAPI application
            redis_client: Redis client instance (will create one if not provided)
            limit: Maximum number of requests allowed within the window
            window: Time window in seconds
            key_func: Function to extract the client identifier from the request
        """
        super().__init__(app)
        self.app = app  # Store app reference for later use
        self.limit = limit
        self.window = window
        self.key_func = key_func or self._default_key_func
        self.redis = redis_client
        self._redis_initialized = False

    async def _ensure_redis_initialized(self):
        """
        Ensure Redis client is initialized.
        """
        if not self._redis_initialized:
            if self.redis is None:
                try:
                    self.redis = aioredis.from_url(
                        settings.redis_url,
                        encoding="utf8",
                        decode_responses=True
                    )
                    # Test the connection
                    await self.redis.ping()

                    # Store Redis client in app.state for shutdown cleanup
                    # Only if the attribute doesn't already exist
                    if hasattr(self.app, "state") and not hasattr(self.app.state, "redis_rate_limiter"):
                        self.app.state.redis_rate_limiter = self.redis

                    logger.info("Redis connection established for rate limiting")
                except Exception as e:
                    logger.error(f"Failed to connect to Redis for rate limiting: {str(e)}")
                    # Fall back to a dummy implementation that doesn't rate limit
                    self.redis = None
                    return False
            self._redis_initialized = True
        return self.redis is not None

    async def dispatch(self, request: Request, call_next) -> Response:
        """
        Process the request and apply rate limiting.

        Args:
            request: The incoming request
            call_next: The next middleware or route handler

        Returns:
            The response
        """
        # Skip rate limiting for certain paths
        if self._should_skip(request):
            return await call_next(request)

        # Ensure Redis is initialized
        redis_available = await self._ensure_redis_initialized()
        if not redis_available:
            logger.warning("Redis not available, skipping rate limiting")
            return await call_next(request)

        # Get client identifier
        key = self.key_func(request)
        rate_limit_key = f"rate_limit:{key}"

        # Check if client has exceeded rate limit
        is_limited, current_count = await self._is_rate_limited(rate_limit_key)

        # Add rate limit headers to response
        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(self.limit)
        response.headers["X-RateLimit-Remaining"] = str(max(0, self.limit - current_count))

        if is_limited:
            logger.warning(f"Rate limit exceeded for {key}")
            return JSONResponse(
                status_code=429,
                content={
                    "status_code": 429,
                    "message": "Too Many Requests",
                    "details": "Rate limit exceeded. Please try again later."
                },
                headers={
                    "X-RateLimit-Limit": str(self.limit),
                    "X-RateLimit-Remaining": "0",
                    "Retry-After": str(self.window)
                }
            )

        return response

    def _default_key_func(self, request: Request) -> str:
        """
        Default function to extract client identifier from request.

        Uses the client's IP address as the identifier.

        Args:
            request: The incoming request

        Returns:
            Client identifier
        """
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    async def _is_rate_limited(self, key: str) -> Tuple[bool, int]:
        """
        Check if a client has exceeded the rate limit using Redis.

        Args:
            key: Redis key for the client

        Returns:
            Tuple of (is_limited, current_count)
        """
        now = time.time()
        window_start = now - self.window

        try:
            # Use Redis pipeline for atomic operations
            pipe = self.redis.pipeline()

            # Remove counts older than the window
            pipe.zremrangebyscore(key, 0, window_start)

            # Add current request with timestamp as score
            pipe.zadd(key, {str(now): now})

            # Count requests in the current window
            pipe.zcard(key)

            # Set expiration on the key to clean up automatically
            pipe.expire(key, self.window)

            # Execute pipeline
            results = await pipe.execute()
            current_count = results[2]

            # Check if limit exceeded
            return current_count > self.limit, current_count
        except Exception as e:
            logger.error(f"Error checking rate limit: {str(e)}")
            # If there's an error, don't rate limit
            return False, 0

    def _should_skip(self, request: Request) -> bool:
        """
        Check if rate limiting should be skipped for this request.

        Args:
            request: The incoming request

        Returns:
            True if rate limiting should be skipped, False otherwise
        """
        # Skip rate limiting for health check endpoints
        path = request.url.path
        return path.endswith("/health") or path.endswith("/status")


# Keep the original RateLimiter for backward compatibility
class RateLimiter(BaseHTTPMiddleware):
    """
    Middleware for rate limiting API requests.

    This middleware limits the number of requests a client can make within a specified time window.

    Note: This implementation uses in-memory storage and is not suitable for distributed environments.
    Use RedisRateLimiter for distributed environments.
    """

    def __init__(
        self, 
        app, 
        limit: int = 100, 
        window: int = 60, 
        key_func: Callable[[Request], str] = None
    ):
        """
        Initialize the rate limiter.

        Args:
            app: The FastAPI application
            limit: Maximum number of requests allowed within the window
            window: Time window in seconds
            key_func: Function to extract the client identifier from the request
        """
        super().__init__(app)
        self.limit = limit
        self.window = window
        self.key_func = key_func or self._default_key_func
        self.requests: Dict[str, Tuple[int, float]] = {}  # {key: (count, first_request_time)}

        logger.warning("Using in-memory RateLimiter which is not suitable for distributed environments. Consider using RedisRateLimiter instead.")

    async def dispatch(self, request: Request, call_next) -> Response:
        """
        Process the request and apply rate limiting.

        Args:
            request: The incoming request
            call_next: The next middleware or route handler

        Returns:
            The response
        """
        # Skip rate limiting for certain paths
        if self._should_skip(request):
            return await call_next(request)

        # Get client identifier
        key = self.key_func(request)

        # Check if client has exceeded rate limit
        if self._is_rate_limited(key):
            logger.warning(f"Rate limit exceeded for {key}")
            return JSONResponse(
                status_code=429,
                content={
                    "status_code": 429,
                    "message": "Too Many Requests",
                    "details": "Rate limit exceeded. Please try again later."
                }
            )

        # Process the request
        return await call_next(request)

    def _default_key_func(self, request: Request) -> str:
        """
        Default function to extract client identifier from request.

        Uses the client's IP address as the identifier.

        Args:
            request: The incoming request

        Returns:
            Client identifier
        """
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    def _is_rate_limited(self, key: str) -> bool:
        """
        Check if a client has exceeded the rate limit.

        Args:
            key: Client identifier

        Returns:
            True if rate limited, False otherwise
        """
        now = time.time()

        # Clean up old entries
        self._cleanup(now)

        # Get or initialize client's request count and first request time
        count, first_request = self.requests.get(key, (0, now))

        # Check if window has expired
        if now - first_request > self.window:
            # Reset window
            count = 0
            first_request = now

        # Increment count
        count += 1
        self.requests[key] = (count, first_request)

        # Check if limit exceeded
        return count > self.limit

    def _cleanup(self, now: float) -> None:
        """
        Clean up expired entries.

        Args:
            now: Current time
        """
        expired_keys = [
            key for key, (_, first_request) in self.requests.items()
            if now - first_request > self.window
        ]

        for key in expired_keys:
            del self.requests[key]

    def _should_skip(self, request: Request) -> bool:
        """
        Check if rate limiting should be skipped for this request.

        Args:
            request: The incoming request

        Returns:
            True if rate limiting should be skipped, False otherwise
        """
        # Skip rate limiting for health check endpoints
        path = request.url.path
        return path.endswith("/health") or path.endswith("/status")
