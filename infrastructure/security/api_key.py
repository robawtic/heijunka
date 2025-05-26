from fastapi import Request, Depends, HTTPException, status
from fastapi.security import APIKeyHeader
from typing import Optional, Dict, List
from datetime import datetime
import logging

from domain.entities.api_key import ApiKey
from domain.repositories.interfaces.api_key_repository import ApiKeyRepositoryInterface
from infrastructure.api.dependencies import get_api_key_repository, get_user_service
from domain.contexts.user_management.services.user_service import UserService

logger = logging.getLogger("heijunka_api.security")

# API key header scheme
API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)

async def get_api_key(
    request: Request,
    api_key: Optional[str] = Depends(API_KEY_HEADER),
    api_key_repository: ApiKeyRepositoryInterface = Depends(get_api_key_repository),
    user_service: UserService = Depends(get_user_service)
) -> Optional[Dict]:
    """
    Validate the API key and return the current user.

    This dependency can be used to authenticate API clients using an API key.
    It extracts the API key from the X-API-Key header and validates it against
    the database.

    Args:
        request: The HTTP request
        api_key: The API key from the X-API-Key header
        api_key_repository: The repository for validating API keys
        user_service: The user service for accessing user data

    Returns:
        Dict: A dictionary containing the username and roles, or None if no valid API key

    Raises:
        HTTPException: If the API key is invalid
    """
    if not api_key:
        return None

    # Validate the API key
    api_key_entity = api_key_repository.get_by_key_value(api_key)
    if not api_key_entity:
        logger.warning(f"Invalid API key: {api_key[:8]}...")
        return None

    if not api_key_entity.is_valid():
        logger.warning(f"Expired or inactive API key: {api_key[:8]}...")
        return None

    # Get the user from the database
    user = user_service.get_user_by_id(api_key_entity.user_id)
    if not user:
        logger.error(f"User ID {api_key_entity.user_id} from API key not found in database")
        return None

    if not user.is_active:
        logger.warning(f"User {user.username} is inactive")
        return None

    # Get client information
    client_ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "unknown")
    request_id = getattr(request.state, "request_id", "unknown")

    # Validate IP restrictions if configured
    if not api_key_entity.validate_ip(client_ip):
        logger.warning(f"IP address {client_ip} not allowed for API key {api_key[:8]}... | request_id={request_id}")
        return None

    # Validate user agent restrictions if configured
    if not api_key_entity.validate_user_agent(user_agent):
        logger.warning(f"User agent not allowed for API key {api_key[:8]}... | request_id={request_id}")
        return None

    # Store the API key entity in request state for scope validation in route handlers
    request.state.api_key_entity = api_key_entity

    # Set a flag in the request state to indicate this is an API client
    request.state.is_api_client = True

    # Update last_used_at timestamp
    api_key_entity.last_used_at = datetime.utcnow()
    api_key_repository.update(api_key_entity)

    # Log the API key usage
    logger.info(f"API key authentication successful for user: {user.username} | request_id={request_id} | ip={client_ip}")

    # Return the user information
    return {"username": user.username, "roles": user.roles}

def is_api_client(request: Request) -> bool:
    """
    Check if the request is from an API client.

    This function checks if the request has been authenticated using an API key.

    Args:
        request: The HTTP request

    Returns:
        bool: True if the request is from an API client, False otherwise
    """
    return getattr(request.state, "is_api_client", False)

def validate_api_key_scope(request: Request, required_scope: str) -> bool:
    """
    Validate that the API key has the required scope.

    This function checks if the API key used for authentication has the required scope.
    It should be used in route handlers to validate that the API key has the necessary
    permissions to access the endpoint.

    Args:
        request: The HTTP request
        required_scope: The scope required to access the endpoint

    Returns:
        bool: True if the API key has the required scope, False otherwise

    Raises:
        HTTPException: If the API key doesn't have the required scope
    """
    # If not an API client, return True (scope validation is handled by OAuth2 for JWT tokens)
    if not is_api_client(request):
        return True

    # Get the API key entity from the request state
    api_key_entity = getattr(request.state, "api_key_entity", None)
    if not api_key_entity:
        logger.warning("API key entity not found in request state")
        return False

    # Check if the API key has the required scope
    if not api_key_entity.has_scope(required_scope):
        logger.warning(f"API key doesn't have required scope: {required_scope}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"API key doesn't have required scope: {required_scope}"
        )

    return True
