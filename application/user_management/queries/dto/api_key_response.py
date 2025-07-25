from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from application.shared.dto.base_dto import BaseResponse

class ApiKeyDto(BaseModel):
    """DTO for API key data in responses."""
    id: int
    key_id: str
    name: str
    user_id: int
    expires_at: Optional[datetime] = None
    is_active: bool
    created_at: datetime
    last_used_at: Optional[datetime] = None
    scopes: List[str] = Field(default_factory=list)
    # Note: key_value is intentionally excluded for security

class GetApiKeysResponse(BaseResponse):
    """Response for getting API keys for a user."""
    api_keys: List[ApiKeyDto] = Field(default_factory=list)
    total_count: int = 0