from pydantic import BaseModel
from datetime import datetime
from typing import Optional, Dict, Any

class AssignmentResponseDto(BaseModel):
    """DTO for assignment responses to presentation layer."""
    assignment_id: int
    employee_id: int
    workstation_id: int
    start_time: datetime
    end_time: datetime
    assignment_type: str
    status: str
    priority: int
    notes: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }