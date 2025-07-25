from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional, Dict, Any

class CreateAssignmentDto(BaseModel):
    """DTO for assignment creation requests from presentation layer."""
    employee_id: int
    workstation_id: int
    start_time: datetime
    end_time: datetime
    assignment_type: str = "manual"
    priority: Optional[int] = 1
    notes: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }