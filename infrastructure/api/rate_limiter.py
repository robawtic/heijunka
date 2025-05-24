from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
import time
from typing import Dict, Tuple, Optional, Callable
import logging

logger = logging.getLogger("heijunka_api.rate_limiter")

class RateLimiter(BaseHTTPMiddleware):
    """
    Middleware for rate limiting API requests.
    
    This middleware limits the number of requests a client can make within a specified time window.
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