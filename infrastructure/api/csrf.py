from starlette_csrf import CSRFMiddleware
from starlette.middleware.sessions import SessionMiddleware
from fastapi import Request, HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from infrastructure.config.settings import settings
import uuid
import logging
import secrets
logger = logging.getLogger("heijunka_api.csrf")

# CSRF token dependency
csrf_bearer = HTTPBearer()

def get_csrf_token(credentials: HTTPAuthorizationCredentials = Depends(csrf_bearer)):
    """
    Validate CSRF token from Authorization header.

    This is used for API endpoints that modify data and require CSRF protection.
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CSRF token missing"
        )
    return credentials.credentials

def get_csrf_token_from_request(request: Request) -> str:
    """
    Extract CSRF token from the request object.

    This is used to get the CSRF token that was set by the CSRFMiddleware
    to include it in the response for client-side use.

    Args:
        request: The FastAPI request object

    Returns:
        str: The CSRF token

    Raises:
        HTTPException: If no CSRF token is found in the session
    """
    if not hasattr(request, "session"):
        raise HTTPException(status_code=500, detail="Session not initialized")
    token = request.session.get("csrftoken")
    if not token:
        # Generate a secure random CSRF token
        token = secrets.token_urlsafe(32)
        request.session["csrftoken"] = token
    return token

def setup_csrf(app):
    """
    Configure CSRF protection for the application.
    """
    # Session middleware is required for CSRF middleware
    app.add_middleware(
        SessionMiddleware, 
        secret_key=settings.secret_key,
        max_age=settings.session_max_age
    )

    # CSRF middleware
    app.add_middleware(
        CSRFMiddleware, 
        secret=settings.csrf_secret,
        cookie_secure=settings.cookie_secure,
        cookie_httponly=True,
        cookie_samesite="lax"
    )
