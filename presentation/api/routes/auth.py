from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from datetime import timedelta
from typing import List

from infrastructure.api.auth import create_access_token, Role, ACCESS_TOKEN_EXPIRE_MINUTES, get_current_user
from presentation.api.models import ErrorResponse

router = APIRouter()

# This is a placeholder for a real user database
# In a real implementation, you would validate against a database
MOCK_USERS = {
    "admin": {
        "username": "admin",
        "hashed_password": "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW",  # "password"
        "roles": [Role.ADMIN]
    },
    "scheduler": {
        "username": "scheduler",
        "hashed_password": "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW",  # "password"
        "roles": [Role.SCHEDULER]
    },
    "operator": {
        "username": "operator",
        "hashed_password": "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW",  # "password"
        "roles": [Role.OPERATOR]
    },
    "viewer": {
        "username": "viewer",
        "hashed_password": "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW",  # "password"
        "roles": [Role.VIEWER]
    }
}

# Simple password verification (in a real app, use proper password hashing)
def verify_password(plain_password: str, hashed_password: str) -> bool:
    # This is a placeholder. In a real app, use bcrypt or similar
    return hashed_password == "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW"

def get_user(username: str):
    if username in MOCK_USERS:
        return MOCK_USERS[username]
    return None

@router.post("/token", responses={401: {"model": ErrorResponse}})
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    """
    Get an access token for authentication.

    Available test users:
    - admin/password (admin role)
    - scheduler/password (scheduler role)
    - operator/password (operator role)
    - viewer/password (viewer role)
    """
    user = get_user(form_data.username)
    if not user or not verify_password(form_data.password, user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Get the requested scopes that the user has access to
    scopes = []
    if form_data.scopes:
        for scope in form_data.scopes:
            if scope in [role.value for role in user["roles"]]:
                scopes.append(scope)
    else:
        # If no scopes requested, give all the user's roles
        scopes = [role.value for role in user["roles"]]

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user["username"]},
        roles=scopes,
        expires_delta=access_token_expires
    )

    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/me", responses={401: {"model": ErrorResponse}})
async def read_users_me(current_user: dict = Depends(get_current_user)):
    """Get information about the current authenticated user."""
    return current_user
