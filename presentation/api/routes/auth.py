from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from datetime import timedelta
from typing import Dict, Optional, List
import logging

from infrastructure.api.auth import create_access_token, Role, ACCESS_TOKEN_EXPIRE_MINUTES, get_current_user
from presentation.api.models import ErrorResponse, TokenRequest, TokenResponse, CSRFTokenResponse, UserMeResponse
from infrastructure.api.csrf import get_csrf_token, get_csrf_token_from_request
from infrastructure.api.dependencies import get_user_service
from domain.contexts.user_management.services.user_service import UserService
from domain.entities.user import User

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

@router.post("/token", response_model=TokenResponse, responses={401: {"model": ErrorResponse}, 400: {"model": ErrorResponse}})
async def login_for_access_token(
    request: Request, 
    form_data: TokenRequest,
    user_service: UserService = Depends(get_user_service)
):
    """
    Get an access token for authentication.

    Args:
        request: The HTTP request
        form_data: The token request containing username and password
        user_service: The user service for authentication

    Returns:
        TokenResponse: The access token response

    Raises:
        HTTPException: If authentication fails or input validation fails
    """
    # Validate input
    if not form_data.username or not form_data.password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username and password are required",
        )

    # Authenticate user
    user = user_service.authenticate_user(form_data.username, form_data.password)
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

        # Get CSRF token from the request context
        csrf_token = get_csrf_token_from_request(request)

        logger.info(f"Successful login for user: {user.username}")

        return TokenResponse(
            access_token=access_token, 
            token_type="bearer",
            csrf_token=csrf_token
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
    user_service: UserService = Depends(get_user_service)
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

@router.get("/csrf-token", response_model=CSRFTokenResponse, responses={500: {"model": ErrorResponse}})
async def get_csrf_token_endpoint(request: Request, response: Response):
    """
    Get a CSRF token for use in subsequent requests.

    This endpoint ensures a CSRF token is created if one doesn't exist yet.
    Frontend applications should call this endpoint before making any requests
    that require CSRF protection.

    Args:
        request: The HTTP request

    Returns:
        CSRFTokenResponse: The CSRF token response

    Raises:
        HTTPException: If the CSRF token cannot be generated
    """
    try:
        # Get or create a CSRF token
        csrf_token = get_csrf_token_from_request(request)
        response.headers["X-CSRF-Token"] = csrf_token

        logger.info("CSRF token provided to client")

        return CSRFTokenResponse(csrf_token=csrf_token)
    except Exception as e:
        logger.error(f"CSRF token generation error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not generate CSRF token"
        )
