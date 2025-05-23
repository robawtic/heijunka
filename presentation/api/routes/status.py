from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session
import time
import platform
from datetime import datetime
import os

from infrastructure.api.dependencies import get_db
from infrastructure.api.auth import get_current_user
from presentation.api.models import SystemStatus
from infrastructure.config.settings import settings

# Track the start time of the application
START_TIME = time.time()

router = APIRouter()

@router.get("/", response_model=SystemStatus)
async def get_status(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get system status information."""
    # Calculate uptime
    uptime_seconds = time.time() - START_TIME
    days, remainder = divmod(uptime_seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, seconds = divmod(remainder, 60)

    uptime_str = f"{int(days)}d {int(hours)}h {int(minutes)}m {int(seconds)}s"

    # Check database connection
    db_connection = True
    try:
        # Try a simple query to check if the database is accessible
        db.execute("SELECT 1")
    except Exception:
        db_connection = False

    return SystemStatus(
        status="healthy" if db_connection else "unhealthy",
        version=settings.version,
        database_connection=db_connection,
        uptime=uptime_str
    )

@router.get("/health", status_code=200)
async def health_check(response: Response, db: Session = Depends(get_db)):
    """
    Enhanced health check endpoint that doesn't require authentication.

    This endpoint is designed for use with container orchestration systems
    like Kubernetes for readiness/liveness probes.
    """
    # Check critical dependencies
    checks = {
        "database": True,
        # Add other dependency checks as needed
    }

    # Check database connection
    try:
        db.execute("SELECT 1")
    except Exception:
        checks["database"] = False

    # Determine overall health
    is_healthy = all(checks.values())

    # Set appropriate status code
    if not is_healthy:
        response.status_code = 503  # Service Unavailable

    return {
        "status": "healthy" if is_healthy else "unhealthy",
        "version": settings.version,
        "timestamp": datetime.now().isoformat(),
        "checks": checks
    }

@router.get("/info")
async def system_info(current_user: dict = Depends(get_current_user)):
    """Get detailed system information."""
    return {
        "python_version": platform.python_version(),
        "system": platform.system(),
        "platform": platform.platform(),
        "processor": platform.processor(),
        "current_time": datetime.now().isoformat(),
        "start_time": datetime.fromtimestamp(START_TIME).isoformat(),
        "uptime_seconds": time.time() - START_TIME,
        "environment": os.environ.get("ENVIRONMENT", "development"),
        "app_version": settings.version
    }
