from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from pydantic import BaseModel, validator
from typing import Dict, Optional, List
from datetime import datetime
import logging
import ipaddress

from infrastructure.api.auth import get_current_user, get_admin_user
from presentation.api.models import ErrorResponse
from infrastructure.api.dependencies import get_api_key_repository, get_user_service
from domain.contexts.user_management.repositories.interfaces.api_key_repository import ApiKeyRepositoryInterface
from domain.contexts.user_management.services.user_service import UserService
from domain.contexts.user_management.entities.api_key import ApiKey
from infrastructure.security.csrf import verify_csrf_token

router = APIRouter()
logger = logging.getLogger("heijunka_api.api_keys")

# Define API key models
class ApiKeyCreate(BaseModel):
    name: str
    expires_at: Optional[datetime] = None
    scopes: List[str] = []
    allowed_ips: List[str] = []
    allowed_user_agents: List[str] = []

    @validator('allowed_ips')
    def validate_ips(cls, ips):
        """Validate that all IPs are valid IPv4 or IPv6 addresses."""
        for ip in ips:
            try:
                ipaddress.ip_address(ip)
            except ValueError:
                raise ValueError(f"Invalid IP address: {ip}")
        return ips

class ApiKeyResponse(BaseModel):
    key_id: str
    name: str
    key_value: str  # Only returned when creating a new API key
    expires_at: Optional[str] = None
    created_at: str
    is_active: bool
    last_used_at: Optional[str] = None
    scopes: List[str] = []
    allowed_ips: List[str] = []
    allowed_user_agents: List[str] = []

class ApiKeyListResponse(BaseModel):
    key_id: str
    name: str
    expires_at: Optional[str] = None
    created_at: str
    is_active: bool
    last_used_at: Optional[str] = None
    scopes: List[str] = []
    allowed_ips: List[str] = []
    allowed_user_agents: List[str] = []

class ApiKeyUpdate(BaseModel):
    name: Optional[str] = None
    expires_at: Optional[datetime] = None
    is_active: Optional[bool] = None
    scopes: Optional[List[str]] = None
    allowed_ips: Optional[List[str]] = None
    allowed_user_agents: Optional[List[str]] = None

    @validator('allowed_ips')
    def validate_ips(cls, ips):
        """Validate that all IPs are valid IPv4 or IPv6 addresses."""
        if ips is None:
            return ips
        for ip in ips:
            try:
                ipaddress.ip_address(ip)
            except ValueError:
                raise ValueError(f"Invalid IP address: {ip}")
        return ips

@router.post("/", response_model=ApiKeyResponse, responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}})
async def create_api_key(
    request: Request,
    api_key_data: ApiKeyCreate,
    current_user: Dict = Depends(get_current_user),
    api_key_repository: ApiKeyRepositoryInterface = Depends(get_api_key_repository),
    user_service: UserService = Depends(get_user_service),
    _=Depends(verify_csrf_token)
):
    """
    Create a new API key for the current user.

    Args:
        request: The HTTP request
        api_key_data: The API key data
        current_user: The current authenticated user
        api_key_repository: The repository for storing API keys
        user_service: The user service for accessing user data

    Returns:
        ApiKeyResponse: The created API key

    Raises:
        HTTPException: If the user is not authenticated or there's an error creating the API key
    """
    try:
        # Get the user from the database
        user = user_service.get_user_by_username(current_user["username"])
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        # Create a new API key
        api_key = ApiKey(
            user_id=user.id,
            name=api_key_data.name,
            expires_at=api_key_data.expires_at,
            scopes=api_key_data.scopes,
            allowed_ips=api_key_data.allowed_ips,
            allowed_user_agents=api_key_data.allowed_user_agents
        )

        # Save the API key
        api_key = api_key_repository.add(api_key)

        # Log the API key creation
        request_id = getattr(request.state, "request_id", "unknown")
        logger.info(f"API key created for user: {user.username} | request_id={request_id}")

        # Return the API key
        return ApiKeyResponse(
            key_id=api_key.key_id,
            name=api_key.name,
            key_value=api_key.key_value,  # Only returned when creating a new API key
            expires_at=api_key.expires_at.isoformat() if api_key.expires_at else None,
            created_at=api_key.created_at.isoformat(),
            is_active=api_key.is_active,
            last_used_at=api_key.last_used_at.isoformat() if api_key.last_used_at else None,
            scopes=api_key.scopes,
            allowed_ips=api_key.allowed_ips,
            allowed_user_agents=api_key.allowed_user_agents
        )
    except Exception as e:
        logger.error(f"API key creation error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not create API key"
        )

@router.get("/", response_model=List[ApiKeyListResponse], responses={401: {"model": ErrorResponse}})
async def list_api_keys(
    current_user: Dict = Depends(get_current_user),
    api_key_repository: ApiKeyRepositoryInterface = Depends(get_api_key_repository),
    user_service: UserService = Depends(get_user_service)
):
    """
    List all API keys for the current user.

    Args:
        current_user: The current authenticated user
        api_key_repository: The repository for accessing API keys
        user_service: The user service for accessing user data

    Returns:
        List[ApiKeyListResponse]: A list of API keys

    Raises:
        HTTPException: If the user is not authenticated or there's an error retrieving the API keys
    """
    try:
        # Get the user from the database
        user = user_service.get_user_by_username(current_user["username"])
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        # Get all API keys for the user
        api_keys = api_key_repository.get_active_keys_for_user(user.id)

        # Format the response
        return [
            ApiKeyListResponse(
                key_id=api_key.key_id,
                name=api_key.name,
                expires_at=api_key.expires_at.isoformat() if api_key.expires_at else None,
                created_at=api_key.created_at.isoformat(),
                is_active=api_key.is_active,
                last_used_at=api_key.last_used_at.isoformat() if api_key.last_used_at else None,
                scopes=api_key.scopes,
                allowed_ips=api_key.allowed_ips,
                allowed_user_agents=api_key.allowed_user_agents
            )
            for api_key in api_keys
        ]
    except Exception as e:
        logger.error(f"Error listing API keys: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not retrieve API keys"
        )

@router.patch("/{key_id}", response_model=ApiKeyListResponse, responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}})
async def update_api_key(
    key_id: str,
    api_key_data: ApiKeyUpdate,
    current_user: Dict = Depends(get_current_user),
    api_key_repository: ApiKeyRepositoryInterface = Depends(get_api_key_repository),
    user_service: UserService = Depends(get_user_service),
    _=Depends(verify_csrf_token)
):
    """
    Update an API key.

    Args:
        key_id: The ID of the API key to update
        api_key_data: The updated API key data
        current_user: The current authenticated user
        api_key_repository: The repository for updating API keys
        user_service: The user service for accessing user data

    Returns:
        ApiKeyListResponse: The updated API key

    Raises:
        HTTPException: If the API key doesn't exist or doesn't belong to the user
    """
    try:
        # Get the user from the database
        user = user_service.get_user_by_username(current_user["username"])
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        # Get the API key
        api_key = api_key_repository.get_by_key_id(key_id)
        if not api_key:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="API key not found"
            )

        # Check if the API key belongs to the user
        if api_key.user_id != user.id:
            logger.warning(f"User {user.username} attempted to update API key {key_id} belonging to user ID {api_key.user_id}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to update this API key"
            )

        # Update the API key with the provided data
        if api_key_data.name is not None:
            api_key.name = api_key_data.name
        if api_key_data.expires_at is not None:
            api_key.expires_at = api_key_data.expires_at
        if api_key_data.is_active is not None:
            api_key.is_active = api_key_data.is_active
        if api_key_data.scopes is not None:
            api_key.scopes = api_key_data.scopes
        if api_key_data.allowed_ips is not None:
            api_key.allowed_ips = api_key_data.allowed_ips
        if api_key_data.allowed_user_agents is not None:
            api_key.allowed_user_agents = api_key_data.allowed_user_agents

        # Update the API key in the database
        api_key = api_key_repository.update(api_key)

        logger.info(f"API key {key_id} updated by user {user.username}")

        # Return the updated API key
        return ApiKeyListResponse(
            key_id=api_key.key_id,
            name=api_key.name,
            expires_at=api_key.expires_at.isoformat() if api_key.expires_at else None,
            created_at=api_key.created_at.isoformat(),
            is_active=api_key.is_active,
            last_used_at=api_key.last_used_at.isoformat() if api_key.last_used_at else None,
            scopes=api_key.scopes,
            allowed_ips=api_key.allowed_ips,
            allowed_user_agents=api_key.allowed_user_agents
        )
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Error updating API key: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not update API key"
        )

@router.delete("/{key_id}", response_model=Dict[str, str], responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}})
async def revoke_api_key(
    key_id: str,
    current_user: Dict = Depends(get_current_user),
    api_key_repository: ApiKeyRepositoryInterface = Depends(get_api_key_repository),
    user_service: UserService = Depends(get_user_service),
    _=Depends(verify_csrf_token)
):
    """
    Revoke an API key.

    Args:
        key_id: The ID of the API key to revoke
        current_user: The current authenticated user
        api_key_repository: The repository for revoking API keys
        user_service: The user service for accessing user data

    Returns:
        Dict[str, str]: A message confirming the API key was revoked

    Raises:
        HTTPException: If the API key doesn't exist or doesn't belong to the user
    """
    try:
        # Get the user from the database
        user = user_service.get_user_by_username(current_user["username"])
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        # Get the API key
        api_key = api_key_repository.get_by_key_id(key_id)
        if not api_key:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="API key not found"
            )

        # Check if the API key belongs to the user
        if api_key.user_id != user.id:
            logger.warning(f"User {user.username} attempted to revoke API key {key_id} belonging to user ID {api_key.user_id}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to revoke this API key"
            )

        # Revoke the API key
        api_key_repository.deactivate_key(key_id)

        logger.info(f"API key {key_id} revoked by user {user.username}")

        return {"message": "API key successfully revoked"}
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Error revoking API key: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not revoke API key"
        )
