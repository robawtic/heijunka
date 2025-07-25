from pydantic import BaseModel, Field, model_validator
from typing import Optional
from datetime import datetime, timezone


class BaseRequest(BaseModel):
    model_config = {
        "validate_assignment": True,
        "use_enum_values": True,
        "populate_by_name": True,
    }

class BaseResponse(BaseModel):
    success: bool = True
    message: Optional[str] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = {
        "validate_assignment": True,
        "use_enum_values": True,
    }

class PaginatedResponse(BaseResponse):
    total_count: int = 0
    page: int = 1
    page_size: int = 10
    total_pages: int = 0

    @model_validator(mode="after")
    def compute_total_pages(self) -> "PaginatedResponse":
        if self.total_count > 0 and self.page_size > 0:
            object.__setattr__(
                self, "total_pages", (self.total_count + self.page_size - 1) // self.page_size
            )
        else:
            object.__setattr__(self, "total_pages", 0)
        return self
