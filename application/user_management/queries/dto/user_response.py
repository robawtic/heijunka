from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from application.shared.dto.base_dto import BaseResponse

class UserDto(BaseModel):
    """DTO for user data in responses."""
    id: int
    username: str
    email: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    is_active: bool
    is_verified: bool
    roles: List[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime
    last_login_at: Optional[datetime] = None

class GetUserResponse(BaseResponse):
    """Response for getting a single user."""
    user: Optional[UserDto] = None

class ListUsersResponse(BaseResponse):
    """Response for listing users with pagination."""
    users: List[UserDto] = Field(default_factory=list)
    total_count: int = 0
    page: int = 1
    page_size: int = 10
    total_pages: int = 0
    
    def __init__(self, **data):
        super().__init__(**data)
        if self.total_count > 0 and self.page_size > 0:
            self.total_pages = (self.total_count + self.page_size - 1) // self.page_size