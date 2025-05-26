from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import SQLAlchemyError
from jose.exceptions import JWTError
import logging
from starlette.middleware.base import BaseHTTPMiddleware
from starlette_prometheus import PrometheusMiddleware, metrics
import time
import uuid
import asyncio

from infrastructure.api.rate_limiter import RedisRateLimiter, RateLimiter
from infrastructure.config.settings import settings
from infrastructure.logging.config import configure_logging, set_request_id, clear_request_id
from infrastructure.monitoring.metrics import MetricsMiddleware
from infrastructure.cache.config import setup_cache
from fastapi_csrf_protect import CsrfProtect
from infrastructure.config.csrf_config import get_csrf_config
from infrastructure.api.security import SecurityHeadersMiddleware
from infrastructure.api.sanitization import InputSanitizationMiddleware
from infrastructure.api.dependencies import get_refresh_token_repository

from presentation.api.routes import router
from infrastructure.exceptions import RepositoryError
from infrastructure.api.exception_handlers import (
    validation_exception_handler,
    repository_exception_handler,
    sqlalchemy_exception_handler,
    jwt_exception_handler,
    general_exception_handler
)

# Configure structured logging
configure_logging(settings.log_level)
logger = logging.getLogger("heijunka_api")

app = FastAPI(
    title="Heijunka API",
    description="API for the Heijunka scheduling system",
    version="1.0.0"
)

@app.on_event("startup")
async def startup_event():
    # Initialize cache
    await setup_cache(app)

    # Set up periodic token cleanup
    asyncio.create_task(setup_token_cleanup())

async def setup_token_cleanup():
    """
    Set up a periodic task to clean up expired refresh tokens.

    This function creates a background task that runs every day to delete
    expired refresh tokens from the database, preventing the database from
    growing indefinitely with expired tokens.
    """
    # Time between cleanup runs (24 hours)
    CLEANUP_INTERVAL = 24 * 60 * 60  # seconds

    async def cleanup_expired_tokens():
        """Delete expired refresh tokens from the database."""
        try:
            # Get the refresh token repository
            refresh_token_repository = get_refresh_token_repository()

            # Delete expired tokens
            deleted_count = refresh_token_repository.delete_expired_tokens()

            logger.info(f"Token cleanup: deleted {deleted_count} expired refresh tokens")
        except Exception as e:
            logger.error(f"Error during token cleanup: {str(e)}")

    async def periodic_task():
        """Run the cleanup task periodically."""
        while True:
            try:
                await cleanup_expired_tokens()
            except Exception as e:
                logger.error(f"Periodic token cleanup failed: {str(e)}")

            # Wait for the next interval
            await asyncio.sleep(CLEANUP_INTERVAL)

    # Start the periodic task
    asyncio.create_task(periodic_task())
    logger.info(f"Scheduled refresh token cleanup task (interval: {CLEANUP_INTERVAL} seconds)")

@app.on_event("shutdown")
async def shutdown_event():
    """
    Gracefully close Redis connections when the application shuts down.
    """
    try:
        if hasattr(app.state, "redis_cache") and app.state.redis_cache:
            logger.info("Closing Redis cache connection")
            await app.state.redis_cache.close()
    except Exception as e:
        logger.warning(f"Failed to close Redis cache: {e}")

    try:
        if hasattr(app.state, "redis_rate_limiter") and app.state.redis_rate_limiter:
            logger.info("Closing Redis rate limiter connection")
            await app.state.redis_rate_limiter.close()
    except Exception as e:
        logger.warning(f"Failed to close Redis rate limiter: {e}")

    logger.info("Redis shutdown completed.")

# Request logging middleware
class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        set_request_id(request_id)

        # Log request with structured data
        logger.info("Request started", extra={
            "request_method": request.method,
            "request_path": request.url.path,
            "request_id": request_id,
            "client_ip": request.client.host if request.client else "unknown",
            "user_agent": request.headers.get("user-agent", "unknown")
        })

        start_time = time.time()
        try:
            response = await call_next(request)

            # Log response with structured data
            process_time = time.time() - start_time
            logger.info("Request completed", extra={
                "request_method": request.method,
                "request_path": request.url.path,
                "request_id": request_id,
                "status_code": response.status_code,
                "duration_ms": round(process_time * 1000),
                "content_length": response.headers.get("content-length", 0)
            })

            # Add request ID to response headers
            response.headers["X-Request-ID"] = request_id
            return response
        except Exception as e:
            process_time = time.time() - start_time
            logger.error("Request failed", extra={
                "request_method": request.method,
                "request_path": request.url.path,
                "request_id": request_id,
                "error": str(e),
                "duration_ms": round(process_time * 1000),
                "exception_type": type(e).__name__
            })
            raise
        finally:
            clear_request_id()

# Add middlewares
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(MetricsMiddleware)
app.add_middleware(PrometheusMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,  # Use allowed_origins_list property to handle comma-separated string
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID", "X-CSRF-Token", "X-API-Key"],  # Add API key header
)
app.add_middleware(
    RedisRateLimiter,
    limit=100,  # 100 requests
    window=60,  # per minute
)

app.add_middleware(SecurityHeadersMiddleware)

# Add HTML sanitization middleware with bleach
app.add_middleware(
    InputSanitizationMiddleware,
    allowed_tags=['p', 'b', 'i', 'em', 'strong', 'a', 'ul', 'ol', 'li', 'br', 'hr'],
    allowed_attributes={'a': ['href', 'title']},
    strip=True
)

# CSRF protection is now handled by fastapi-csrf-protect
# No middleware is needed as it's dependency-injected

# Add Prometheus metrics endpoint
app.add_route("/metrics", metrics)

# Add exception handlers
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(RepositoryError, repository_exception_handler)
app.add_exception_handler(SQLAlchemyError, sqlalchemy_exception_handler)
app.add_exception_handler(JWTError, jwt_exception_handler)
app.add_exception_handler(Exception, general_exception_handler)

# Include routers
app.include_router(router, prefix="/api/v1")

@app.get("/")
def read_root():
    return {"message": "Welcome to the Heijunka API"}

# Custom OpenAPI schema
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title="Heijunka API",
        version=settings.version,
        description="""
        # Heijunka API

        API for the Heijunka scheduling system, providing endpoints for managing teams, employees, workstations, and schedules.

        ## Authentication

        ### JWT Authentication (Browser Clients)

        This API uses JWT tokens for authentication. To authenticate:
        1. Call the `/api/v1/auth/token` endpoint with your credentials
        2. Use the returned token in the Authorization header: `Bearer {token}`

        ### API Key Authentication (API Clients)

        For non-browser clients, the API supports authentication using API keys:
        1. Create an API key using the `/api/v1/api-keys` endpoint (requires JWT authentication)
        2. Include the API key in the `X-API-Key` header for subsequent requests
        3. API clients using API keys are exempt from CSRF protection

        ### Token Refresh Flow

        The API implements a secure token refresh mechanism to prevent users from having to re-authenticate
        when their access token expires:

        1. When you authenticate, a refresh token is set in an HTTP-only cookie
        2. The response includes an `expires_at` field indicating when the access token will expire
        3. Before the access token expires, call the `/api/v1/auth/refresh-token` endpoint
        4. This endpoint will use the refresh token cookie to issue a new access token
        5. The implementation uses token rotation for enhanced security:
           - The old refresh token is revoked after use
           - A new refresh token is issued and set in the cookie
           - This prevents replay attacks where a stolen refresh token could be used multiple times
        6. To logout, call the `/api/v1/auth/revoke-token` endpoint to invalidate the refresh token

        ### Session Management

        The API provides endpoints for managing user sessions:

        1. `/api/v1/auth/active-sessions` - Lists all active sessions for the current user
        2. `/api/v1/auth/revoke-session/{token_id}` - Revokes a specific session
        3. `/api/v1/auth/revoke-all-sessions` - Revokes all sessions for the current user ("sign out everywhere")

        Each session includes device information and IP address, allowing users to identify and
        terminate suspicious sessions.

        ## Rate Limiting

        The API implements Redis-based distributed rate limiting to prevent abuse. Limits are:
        - 100 requests per minute per client across all API instances

        ## Error Handling

        All errors follow a consistent format with status code, message, and details.

        ## Caching

        The API implements caching for read-only endpoints to improve performance.
        """,
        routes=app.routes,
    )

    # Add security schemes
    openapi_schema["components"]["securitySchemes"] = {
        "bearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
        },
        "apiKeyAuth": {
            "type": "apiKey",
            "in": "header",
            "name": "X-API-Key",
        }
    }

    # Add global security requirement
    openapi_schema["security"] = [{"bearerAuth": []}, {"apiKeyAuth": []}]

    # Add tags with descriptions
    openapi_schema["tags"] = [
        {
            "name": "teams",
            "description": "Operations related to teams"
        },
        {
            "name": "employees",
            "description": "Operations related to employees"
        },
        {
            "name": "workstations",
            "description": "Operations related to workstations"
        },
        {
            "name": "schedules",
            "description": "Operations related to schedules"
        },
        {
            "name": "assignments",
            "description": "Operations related to assignments"
        },
        {
            "name": "status",
            "description": "Operations related to system status"
        },
        {
            "name": "auth",
            "description": "Authentication operations"
        },
        {
            "name": "tasks",
            "description": "Operations related to background tasks"
        },
        {
            "name": "api-keys",
            "description": "Operations related to API keys for non-browser clients"
        }
    ]

    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi
