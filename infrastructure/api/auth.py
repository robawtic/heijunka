from fastapi import Depends, HTTPException, status, Security
from fastapi.security import OAuth2PasswordBearer, SecurityScopes
from jose import JWTError, jwt
from datetime import datetime, timedelta
from typing import Optional, List, Set
from enum import Enum
import logging

from infrastructure.config.settings import settings

# Use settings instead of hardcoded values
SECRET_KEY = settings.jwt_secret_key
ALGORITHM = settings.jwt_algorithm
ACCESS_TOKEN_EXPIRE_MINUTES = settings.jwt_expiration_minutes

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
        to_encode.update({"roles": roles})

    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(
    security_scopes: SecurityScopes,
    token: str = Depends(oauth2_scheme)
):
    """
    Validate the token and return the current user with their roles.
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

# Role-based security dependencies
def get_admin_user(current_user: dict = Security(get_current_user, scopes=[Role.ADMIN])):
    return current_user

def get_scheduler_user(current_user: dict = Security(get_current_user, scopes=[Role.SCHEDULER, Role.ADMIN])):
    return current_user

def get_operator_user(current_user: dict = Security(get_current_user, scopes=[Role.OPERATOR, Role.SCHEDULER, Role.ADMIN])):
    return current_user

def get_viewer_user(current_user: dict = Security(get_current_user, scopes=[Role.VIEWER, Role.OPERATOR, Role.SCHEDULER, Role.ADMIN])):
    return current_user
