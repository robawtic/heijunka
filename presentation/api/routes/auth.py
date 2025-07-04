from fastapi import APIRouter, Depends, HTTPException, status, Request, Response, Cookie
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional, List
import logging

from infrastructure.api.auth import (
    create_access_token, 
    create_refresh_token,
    validate_refresh_token,
    Role, 
    ACCESS_TOKEN_EXPIRE_MINUTES, 
    REFRESH_TOKEN_EXPIRE_DAYS,
    get_current_user
)
from presentation.api.models import ErrorResponse, TokenRequest, TokenResponse, CSRFTokenResponse, UserMeResponse
from infrastructure.security.csrf import set_csrf_cookie, verify_csrf_token
from infrastructure.api.dependencies import get_user_service, get_refresh_token_repository
from domain.contexts.user_management.services.user_service import UserService
from domain.contexts.user_management.repositories.interfaces.refresh_token_repository import RefreshTokenRepositoryInterface
from domain.contexts.user_management.entities.user import User

router = APIRouter()
logger = logging.getLogger("heijunka_api.auth")

def get_user(username: str, user_service: UserService = Depends(get_user_service)) -> Optional[User]:
    """
    Retrieve user information from the database.

    Args:
        username: The username to look up
        user_service: The user service for accessing user data

    Returns:
        Optional[User]: User entity if found, None otherwise
    """
    if not username or len(username) > 100:  # Add reasonable length check
        return None
    return user_service.get_user_by_username(username)

@router.post("/token", response_model=TokenResponse, responses={401: {"model": ErrorResponse}, 400: {"model": ErrorResponse}, 403: {"model": ErrorResponse}})
async def login_for_access_token(
    request: Request,
    response: Response,
    form_data: TokenRequest,
    user_service: UserService = Depends(get_user_service),
    refresh_token_repository: RefreshTokenRepositoryInterface = Depends(get_refresh_token_repository),
    _=Depends(set_csrf_cookie)  # Set CSRF cookie but don't require validation for login
    # Note: We don't require CSRF validation for login since it's the initial authentication point
):
    """
    Get access and refresh tokens for authentication.

    Args:
        request: The HTTP request
        response: The HTTP response
        form_data: The token request containing username and password
        user_service: The user service for authentication
        refresh_token_repository: The repository for storing refresh tokens

    Returns:
        TokenResponse: The access token response with refresh token

    Raises:
        HTTPException: If authentication fails or input validation fails
    """
    # Validate input
    if not form_data.username or not form_data.password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username and password are required",
        )

    # Get device information for device-bound session management
    user_agent = request.headers.get("user-agent", "unknown")
    ip_address = request.client.host if request.client else "unknown"

    # Authenticate user with client information
    user = user_service.authenticate_user(
        form_data.username, 
        form_data.password,
        ip_address=ip_address,
        user_agent=user_agent
    )
    if not user:
        logger.warning(f"Failed login attempt for user: {form_data.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Get all the user's roles
    scopes = user.roles

    try:
        # Create access token
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user.username},
            roles=scopes,
            expires_delta=access_token_expires
        )

        # Device information already retrieved above

        # Create refresh token and store it in the database
        refresh_token_expires = timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
        refresh_token = create_refresh_token(
            data={"sub": user.username},
            user_id=user.id,
            refresh_token_repository=refresh_token_repository,
            device_info=user_agent,
            ip_address=ip_address,
            expires_delta=refresh_token_expires
        )

        # Calculate expiration timestamp for frontend
        expires_at = datetime.now(timezone.utc) + access_token_expires

        # Set refresh token in HTTP-only cookie
        response.set_cookie(
            key="refresh_token",
            value=refresh_token,
            httponly=True,
            secure=True,  # Only send over HTTPS
            samesite="strict",  # Prevent CSRF
            max_age=REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,  # in seconds
            path="/api/v1/auth/refresh-token",  # Only send to refresh endpoint
        )

        # Get request ID for logging
        request_id = getattr(request.state, "request_id", "unknown")
        logger.info(f"Successful login for user: {user.username} | request_id={request_id}")

        # CSRF token is set in the cookie by the set_csrf_cookie dependency
        return TokenResponse(
            access_token=access_token, 
            token_type="bearer",
            expires_at=expires_at.isoformat()
        )
    except Exception as e:
        logger.error(f"Token generation error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not generate authentication tokens"
        )

@router.get("/me", response_model=UserMeResponse, responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}})
async def read_users_me(
    current_user: Dict = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service),
    response: Response = None,
    _=Depends(set_csrf_cookie)  # Set CSRF cookie for subsequent requests
):
    """
    Get information about the current authenticated user.

    Args:
        current_user: The current authenticated user, obtained from the token
        user_service: The user service for accessing user data

    Returns:
        UserMeResponse: User information including username, roles, and other details

    Raises:
        HTTPException: If the user is not authenticated, doesn't have permission, or doesn't exist
    """
    # Get the full user information from the database
    username = current_user.get("username")
    user = user_service.get_user_by_username(username)

    if not user:
        logger.error(f"User {username} found in token but not in database")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Return user information as a UserMeResponse model
    return UserMeResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        roles=user.roles,
        is_active=user.is_active,
        last_login=user.last_login
    )

@router.post("/refresh-token", response_model=TokenResponse, responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}})
async def refresh_token_endpoint(
    request: Request,
    response: Response,
    refresh_token: Optional[str] = Cookie(None, alias="refresh_token"),
    refresh_token_repository: RefreshTokenRepositoryInterface = Depends(get_refresh_token_repository),
    user_service: UserService = Depends(get_user_service),
    _=Depends(set_csrf_cookie)
):
    """
    Refresh the access token using a refresh token.

    This endpoint allows users to get a new access token when their current one is about to expire,
    without having to re-authenticate with username and password.

    The refresh token is expected to be in an HTTP-only cookie named 'refresh_token'.

    This implementation uses token rotation for enhanced security:
    1. The old refresh token is revoked after use
    2. A new refresh token is issued and set in the cookie
    3. This prevents replay attacks where a stolen refresh token could be used multiple times

    Args:
        request: The HTTP request
        response: The HTTP response
        refresh_token: The refresh token from the cookie
        refresh_token_repository: The repository for validating refresh tokens
        user_service: The user service for accessing user data

    Returns:
        TokenResponse: A new access token

    Raises:
        HTTPException: If the refresh token is invalid or missing
    """
    if not refresh_token:
        logger.warning("Refresh token missing in request")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token is missing",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        # Validate the refresh token
        token_data = await validate_refresh_token(refresh_token, refresh_token_repository)
        username = token_data["username"]
        user_id = token_data["user_id"]

        # Get user from database to get roles
        user = user_service.get_user_by_username(username)

        if not user:
            logger.error(f"User {username} found in refresh token but not in database")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        # Get the token ID from the JWT
        try:
            payload = jwt.decode(refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
            token_id = payload.get("jti")
        except JWTError:
            logger.error("Failed to decode refresh token to get token ID")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Revoke the old refresh token (token rotation)
        if token_id:
            refresh_token_repository.revoke_token(token_id)
            logger.info(f"Revoked refresh token {token_id} for user {username}")

        # Create a new access token
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": username},
            roles=user.roles,
            expires_delta=access_token_expires
        )

        # Get device information for device-bound session management
        user_agent = request.headers.get("user-agent", "unknown")
        ip_address = request.client.host if request.client else "unknown"

        # Create a new refresh token (token rotation)
        refresh_token_expires = timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
        new_refresh_token = create_refresh_token(
            data={"sub": username},
            user_id=user.id,
            refresh_token_repository=refresh_token_repository,
            device_info=user_agent,
            ip_address=ip_address,
            expires_delta=refresh_token_expires
        )

        # Set the new refresh token in the cookie
        response.set_cookie(
            key="refresh_token",
            value=new_refresh_token,
            httponly=True,
            secure=True,  # Only send over HTTPS
            samesite="strict",  # Prevent CSRF
            max_age=REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,  # in seconds
            path="/api/v1/auth/refresh-token",  # Only send to refresh endpoint
        )

        # Calculate expiration timestamp for frontend
        expires_at = datetime.now(timezone.utc) + access_token_expires

        # Get request ID for logging
        request_id = getattr(request.state, "request_id", "unknown")
        logger.info(f"Token refreshed for user: {username} | request_id={request_id}")

        return TokenResponse(
            access_token=access_token,
            token_type="bearer",
            expires_at=expires_at.isoformat()
        )
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Token refresh error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not refresh authentication token"
        )

@router.post("/revoke-token", response_model=CSRFTokenResponse, responses={401: {"model": ErrorResponse}})
async def revoke_token(
    request: Request,
    response: Response,
    current_user: Dict = Depends(get_current_user),
    refresh_token: Optional[str] = Cookie(None, alias="refresh_token"),
    refresh_token_repository: RefreshTokenRepositoryInterface = Depends(get_refresh_token_repository),
    _=Depends(verify_csrf_token)
):
    """
    Revoke the refresh token for the current user.

    This endpoint is typically used for logout. It invalidates the refresh token
    by revoking it in the database and clearing the refresh_token cookie.

    Args:
        request: The HTTP request
        response: The HTTP response
        current_user: The current authenticated user
        refresh_token: The refresh token from the cookie
        refresh_token_repository: The repository for revoking refresh tokens

    Returns:
        CSRFTokenResponse: A message confirming the token was revoked
    """
    try:
        # Revoke the token in the database if it exists
        if refresh_token:
            try:
                # Extract the token ID from the JWT
                payload = jwt.decode(refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
                token_id = payload.get("jti")

                if token_id:
                    # Revoke the token in the database
                    refresh_token_repository.revoke_token(token_id)
                    logger.info(f"Revoked refresh token {token_id} for user {current_user['username']}")
            except JWTError as e:
                # Log the error but continue with cookie deletion
                logger.warning(f"Failed to decode refresh token during revocation: {str(e)}")

        # Clear the refresh token cookie
        response.delete_cookie(
            key="refresh_token",
            path="/api/v1/auth/refresh-token",
        )

        # Get request ID for logging
        request_id = getattr(request.state, "request_id", "unknown")
        logger.info(f"Token revoked for user: {current_user['username']} | request_id={request_id}")

        return CSRFTokenResponse(message="Token successfully revoked")
    except Exception as e:
        logger.error(f"Token revocation error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not revoke token"
        )

@router.get("/active-sessions", responses={401: {"model": ErrorResponse}, 500: {"model": ErrorResponse}})
async def list_active_sessions(
    current_user: Dict = Depends(get_current_user),
    refresh_token_repository: RefreshTokenRepositoryInterface = Depends(get_refresh_token_repository)
):
    """
    List all active sessions for the current user.

    This endpoint returns information about all active refresh tokens for the current user,
    including device information and creation time. This allows users to see all their
    active sessions and potentially revoke suspicious ones.

    Args:
        current_user: The current authenticated user
        refresh_token_repository: The repository for accessing refresh tokens

    Returns:
        List of active sessions with device information

    Raises:
        HTTPException: If there's an error retrieving the sessions
    """
    try:
        # Get the user ID from the current user
        user_service = get_user_service()
        user = user_service.get_user_by_username(current_user["username"])

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        # Get all active tokens for the user
        active_tokens = refresh_token_repository.get_active_tokens_for_user(user.id)

        # Format the response
        sessions = [
            {
                "token_id": token.token_id,
                "device_info": token.device_info,
                "ip_address": token.ip_address,
                "created_at": token.created_at.isoformat() if token.created_at else None,
                "expires_at": token.expires_at.isoformat() if token.expires_at else None
            }
            for token in active_tokens
        ]

        return sessions
    except Exception as e:
        logger.error(f"Error listing active sessions: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not retrieve active sessions"
        )

@router.post("/revoke-session/{token_id}", response_model=CSRFTokenResponse, responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}})
async def revoke_session(
    token_id: str,
    current_user: Dict = Depends(get_current_user),
    refresh_token_repository: RefreshTokenRepositoryInterface = Depends(get_refresh_token_repository),
    _=Depends(verify_csrf_token)
):
    """
    Revoke a specific session by its token ID.

    This endpoint allows users to revoke a specific refresh token, effectively
    terminating the associated session. This is useful for logging out from
    a specific device or terminating suspicious sessions.

    Args:
        token_id: The ID of the token to revoke
        current_user: The current authenticated user
        refresh_token_repository: The repository for revoking refresh tokens

    Returns:
        CSRFTokenResponse: A message confirming the session was revoked

    Raises:
        HTTPException: If the session doesn't exist or doesn't belong to the user
    """
    try:
        # Get the user ID from the current user
        user_service = get_user_service()
        user = user_service.get_user_by_username(current_user["username"])

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        # Get the token to verify it belongs to the user
        token = refresh_token_repository.get_by_token_id(token_id)

        if not token:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found"
            )

        if token.user_id != user.id:
            logger.warning(f"User {user.username} attempted to revoke token {token_id} belonging to user ID {token.user_id}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to revoke this session"
            )

        # Revoke the token
        refresh_token_repository.revoke_token(token_id)

        logger.info(f"Session {token_id} revoked by user {user.username}")

        return CSRFTokenResponse(message="Session successfully revoked")
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Error revoking session: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not revoke session"
        )

@router.post("/revoke-all-sessions", response_model=CSRFTokenResponse, responses={401: {"model": ErrorResponse}})
async def revoke_all_sessions(
    current_user: Dict = Depends(get_current_user),
    refresh_token_repository: RefreshTokenRepositoryInterface = Depends(get_refresh_token_repository),
    _=Depends(verify_csrf_token)
):
    """
    Revoke all active sessions for the current user.

    This endpoint allows users to revoke all their refresh tokens, effectively
    terminating all sessions except the current one. This is useful for a
    "sign out everywhere" feature.

    Args:
        current_user: The current authenticated user
        refresh_token_repository: The repository for revoking refresh tokens

    Returns:
        CSRFTokenResponse: A message confirming all sessions were revoked

    Raises:
        HTTPException: If there's an error revoking the sessions
    """
    try:
        # Get the user ID from the current user
        user_service = get_user_service()
        user = user_service.get_user_by_username(current_user["username"])

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        # Revoke all tokens for the user
        count = refresh_token_repository.revoke_all_tokens_for_user(user.id)

        logger.info(f"All sessions ({count} tokens) revoked by user {user.username}")

        return CSRFTokenResponse(message=f"Successfully revoked {count} sessions")
    except Exception as e:
        logger.error(f"Error revoking all sessions: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not revoke all sessions"
        )

@router.get("/csrf-token", response_model=CSRFTokenResponse, responses={500: {"model": ErrorResponse}})
async def get_csrf_token_endpoint(response: Response, _=Depends(set_csrf_cookie)):
    """
    Get a CSRF token for use in subsequent requests.

    This endpoint sets a CSRF token in a cookie and returns it in the response.
    Frontend applications should call this endpoint before making any requests
    that require CSRF protection.

    Args:
        response: The HTTP response

    Returns:
        CSRFTokenResponse: The CSRF token response

    Raises:
        HTTPException: If the CSRF token cannot be generated
    """
    try:
        # The CSRF token is set in the cookie by the set_csrf_cookie dependency
        # We return a message to confirm it was set
        logger.info("CSRF token provided to client")

        return CSRFTokenResponse(message="CSRF token set in cookie")
    except Exception as e:
        logger.error(f"CSRF token generation error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not generate CSRF token"
        )
