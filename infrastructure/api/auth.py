from fastapi import Depends, HTTPException, status, Security
from fastapi.security import OAuth2PasswordBearer, SecurityScopes
from jose import JWTError, jwt
from datetime import datetime, timedelta
from typing import Optional, List, Set, Dict
from enum import Enum
import logging
import uuid

from infrastructure.config.settings import settings
from domain.entities.refresh_token import RefreshToken
from domain.repositories.interfaces.refresh_token_repository import RefreshTokenRepositoryInterface

# Use settings instead of hardcoded values
SECRET_KEY = settings.jwt_secret_key
ALGORITHM = settings.jwt_algorithm
ACCESS_TOKEN_EXPIRE_MINUTES = settings.jwt_expiration_minutes
REFRESH_TOKEN_EXPIRE_DAYS = 30  # 30 days for refresh token

logger = logging.getLogger("heijunka_api.auth")

# Define roles
class Role(str, Enum):
    ADMIN = "admin"
    SCHEDULER = "scheduler"
    OPERATOR = "operator"
    VIEWER = "viewer"

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/token",
    scopes={
        Role.ADMIN: "Full access to all resources",
        Role.SCHEDULER: "Create and manage schedules",
        Role.OPERATOR: "View and update assignments",
        Role.VIEWER: "Read-only access to resources",
    }
)

def create_access_token(
    data: dict, 
    roles: List[str] = None, 
    expires_delta: Optional[timedelta] = None
):
    """
    Create a JWT access token with optional roles.
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})

    # Add roles to token if provided
    if roles:
        # Convert Role objects to role names if needed
        role_names = [role.name if hasattr(role, 'name') else role for role in roles]
        to_encode.update({"roles": role_names})

    # Add token type
    to_encode.update({"token_type": "access"})

    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def create_refresh_token(
    data: dict,
    user_id: int,
    refresh_token_repository: RefreshTokenRepositoryInterface,
    device_info: Optional[str] = None,
    ip_address: Optional[str] = None,
    expires_delta: Optional[timedelta] = None
):
    """
    Create a JWT refresh token and store it in the database.

    Refresh tokens have longer expiration times and are used to obtain new access tokens.
    They don't contain roles as they're only used for refreshing access tokens.

    Args:
        data: The data to encode in the token
        user_id: The ID of the user
        refresh_token_repository: The repository for storing refresh tokens
        device_info: Optional device information (user agent)
        ip_address: Optional IP address
        expires_delta: Optional expiration time delta

    Returns:
        The encoded JWT refresh token
    """
    # Generate a unique token ID
    token_id = str(uuid.uuid4())

    # Create token data
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS))
    to_encode.update({
        "exp": expire,
        "token_type": "refresh",
        "jti": token_id  # JWT ID claim
    })

    # Encode the token
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

    # Store the token in the database
    refresh_token = RefreshToken(
        token_id=token_id,
        user_id=user_id,
        expires_at=expire,
        device_info=device_info,
        ip_address=ip_address
    )

    refresh_token_repository.add(refresh_token)

    return encoded_jwt

async def get_current_user(
    security_scopes: SecurityScopes,
    token: str = Depends(oauth2_scheme)
):
    """
    Validate the access token and return the current user with their roles.
    """
    if security_scopes.scopes:
        authenticate_value = f'Bearer scope="{security_scopes.scope_str}"'
    else:
        authenticate_value = "Bearer"

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": authenticate_value},
    )

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception

        # Verify this is an access token
        token_type = payload.get("token_type")
        if token_type != "access":
            logger.warning(f"Token type mismatch: expected 'access', got '{token_type}'")
            raise credentials_exception

        # Extract roles from token
        token_roles = payload.get("roles", [])

        # Check if the token has the required scopes
        if security_scopes.scopes:
            token_scope_set = set(token_roles)
            for scope in security_scopes.scopes:
                if scope not in token_scope_set:
                    logger.warning(f"User {username} attempted to access {scope} without permission")
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Not enough permissions",
                        headers={"WWW-Authenticate": authenticate_value},
                    )

        return {"username": username, "roles": token_roles}
    except JWTError as e:
        logger.error(f"JWT validation error: {str(e)}")
        raise credentials_exception

async def validate_refresh_token(
    refresh_token: str,
    refresh_token_repository: RefreshTokenRepositoryInterface
):
    """
    Validate a refresh token and return the username.

    Args:
        refresh_token: The refresh token to validate
        refresh_token_repository: The repository for validating refresh tokens

    Returns:
        Dict: A dictionary containing the username and user_id

    Raises:
        HTTPException: If the token is invalid
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid refresh token",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        # Decode the token
        payload = jwt.decode(refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception

        # Verify this is a refresh token
        token_type = payload.get("token_type")
        if token_type != "refresh":
            logger.warning(f"Token type mismatch: expected 'refresh', got '{token_type}'")
            raise credentials_exception

        # Get the token ID
        token_id = payload.get("jti")
        if token_id is None:
            logger.warning("Token ID (jti) missing in refresh token")
            raise credentials_exception

        # Verify the token exists in the database and is not revoked
        db_token = refresh_token_repository.get_by_token_id(token_id)
        if db_token is None:
            logger.warning(f"Refresh token with ID {token_id} not found in database")
            raise credentials_exception

        if db_token.is_revoked:
            logger.warning(f"Refresh token with ID {token_id} has been revoked")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token has been revoked",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if db_token.is_expired():
            logger.warning(f"Refresh token with ID {token_id} has expired")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token has expired",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return {"username": username, "user_id": db_token.user_id}
    except JWTError as e:
        logger.error(f"Refresh token validation error: {str(e)}")
        raise credentials_exception

# Role-based security dependencies
def get_admin_user(current_user: dict = Security(get_current_user, scopes=[Role.ADMIN])):
    return current_user

def get_scheduler_user(current_user: dict = Security(get_current_user, scopes=[Role.SCHEDULER, Role.ADMIN])):
    return current_user

def get_operator_user(current_user: dict = Security(get_current_user, scopes=[Role.OPERATOR, Role.SCHEDULER, Role.ADMIN])):
    return current_user

def get_viewer_user(current_user: dict = Security(get_current_user, scopes=[Role.VIEWER, Role.OPERATOR, Role.SCHEDULER, Role.ADMIN])):
    return current_user
