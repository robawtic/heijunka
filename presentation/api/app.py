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

from infrastructure.api.rate_limiter import RateLimiter
from infrastructure.config.settings import settings
from infrastructure.logging.config import configure_logging, set_request_id, clear_request_id
from infrastructure.monitoring.metrics import MetricsMiddleware
from infrastructure.cache.config import setup_cache
from infrastructure.api.csrf import setup_csrf
from infrastructure.api.security import SecurityHeadersMiddleware
from infrastructure.api.sanitization import InputSanitizationMiddleware

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
    allow_headers=["Authorization", "Content-Type", "X-Request-ID", "X-CSRF-Token"],  # Add CSRF token header
)
app.add_middleware(
    RateLimiter,
    limit=100,  # 100 requests
    window=60,  # per minute
)

app.add_middleware(SecurityHeadersMiddleware)

# Setup CSRF protection
setup_csrf(app)

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

        This API uses JWT tokens for authentication. To authenticate:
        1. Call the `/api/v1/auth/token` endpoint with your credentials
        2. Use the returned token in the Authorization header: `Bearer {token}`

        ## Rate Limiting

        The API implements rate limiting to prevent abuse. Limits are:
        - 100 requests per minute for most endpoints

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
        }
    }

    # Add global security requirement
    openapi_schema["security"] = [{"bearerAuth": []}]

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
        }
    ]

    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi
